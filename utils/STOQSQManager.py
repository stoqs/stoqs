__author__    = 'Mike McCann'
__copyright__ = '2012'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

STOQS Query manager for building ajax responces to selections made for QueryUI

@undocumented: __doc__ parser
@status: production
@license: GPL
'''

from django.conf import settings
from django.db.models import Q, Max, Min, Sum
from django.db.models.sql import query
from django.contrib.gis.geos import fromstr, MultiPoint, GEOSGeometry
from django.db.models import Avg
from django.db.utils import DatabaseError
from django.http import HttpResponse
from stoqs import models
from loaders import MEASUREDINSITU
from loaders.SampleLoaders import SAMPLED
from utils import round_to_n, postgresifySQL
from utils import getGet_Actual_Count, getShow_Sigmat_Parameter_Values, getShow_StandardName_Parameter_Values, getShow_All_Parameter_Values, getDisplay_Parameter_Platform_Data
from MPQuery import MPQuery
from Viz import ContourPlots
from coards import to_udunits
from datetime import datetime
import logging
import pprint
import calendar
import re
import locale
import time
import os
import tempfile

logger = logging.getLogger(__name__)

class STOQSQManager(object):
    '''
    This class is designed to handle building and managing queries against the STOQS database.
    Chander Ganesan <chander@otg-nc.com>
    '''
    def __init__(self, request, response, dbname):
        '''
        This object should be created by passing in an HTTPRequest Object, an HTTPResponse object
        and the name of the database to be used.
        '''
        self.request = request
        self.dbname = dbname
        self.response = response
        self.mpq = MPQuery(request)
        # monkey patch sql/query.py to make it use our database for sql generation
        query.DEFAULT_DB_ALIAS = dbname
        
    def buildQuerySets(self, *args, **kwargs):
        '''
        Build the query sets based on any selections from the UI.  We need one for Activities and one for Samples
        '''
        kwargs['fromTable'] = 'Activity'
        self._buildQuerySet(**kwargs)
        kwargs['fromTable'] = 'Sample'
        self._buildQuerySet(**kwargs)
        kwargs['fromTable'] = 'ActivityParameterHistogram'
        self._buildQuerySet(**kwargs)

    def _buildQuerySet(self, *args, **kwargs):
        '''
        Build the query set based on any selections from the UI. For the first time through  kwargs will be empty 
        and self.qs will be built of a join of activities, parameters, and platforms with no constraints.

        Right now supported keyword arguments are the following:
            sampledparametersgroup - a list of sampled parameter names to include
            measuredparametersgroup - a list of measured parameter names to include
            parameterstandardname - a list of parameter styandard_names to include
            platforms - a list of platform names to include
            time - a two-tuple consisting of a start and end time, if either is None, the assumption is no start (or end) time
            depth - a two-tuple consisting of a range (start/end depth, if either is None, the assumption is no start (or end) depth
            parametervalues - a dictionary of parameter names and tuples of min & max values to use as constraints

        These are all called internally - so we'll assume that all the validation has been done in advance,
        and the calls to this method meet the requirements stated above.
        '''
        fromTable = 'Activity'              # Default is Activity
        if kwargs.has_key('fromTable'):
            fromTable = kwargs['fromTable']

        if 'qs' in args:
            logger.debug('Using query string passed in to make a non-activity based query')
            qs = args['qs']
        else:
            # Provide "base" querysets with depth and filters so that more efficient inner joins are generated
            if fromTable == 'Activity':
                logger.debug('Making default activity based query')
                if (not kwargs):
                    qs = models.Activity.objects.using(self.dbname).select_related(depth=3).filter( activityparameter__parameter__pk__isnull=False,
                                                                                                    activityparameter__activity__pk__isnull=False,
                                                                                                    simpledepthtime__pk__isnull=False,
                                                                                                    platform__pk__isnull=False)
                else:
                    qs = models.Activity.objects.using(self.dbname).select_related(depth=3).all()   # To receive filters constructed below from kwargs
            elif fromTable == 'Sample':
                logger.debug('Making %s based query', fromTable)
                if (not kwargs):
                    qs = models.Sample.objects.using(self.dbname).select_related(depth=3).filter( sampledparameter__parameter__pk__isnull=False,
                                                                                                  instantpoint__activity__pk__isnull=False,
                                                                                                  instantpoint__activity__platform__pk__isnull=False)
                else:
                    qs = models.Sample.objects.using(self.dbname).select_related(depth=3).all()   # To receive filters constructed below from kwargs
            elif fromTable == 'ActivityParameterHistogram':
                logger.debug('Making %s based query', fromTable)
                if (not kwargs):
                    qs = models.ActivityParameterHistogram.objects.using(self.dbname).select_related(depth=3).filter( activityparameter__parameter__pk__isnull=False,
                                                                                                  activityparameter__activity__pk__isnull=False,
                                                                                                  activityparameter__activity__platform__pk__isnull=False)
                else:
                    qs = models.ActivityParameterHistogram.objects.using(self.dbname).select_related(depth=3).all()   # To receive filters constructed below from kwargs
            else:
                logger.exception('No handler for fromTable = %s', fromTable)
    
        self.args = args
        self.kwargs = kwargs
        for k, v in kwargs.iteritems():
            '''
            Check to see if there is a "builder" for a Q object using the given parameters.
            '''
            if not v:
                continue
            if k == 'fromTable':
                continue
            if hasattr(self, '_%sQ' % (k,)):
                # Call the method if it exists, and add the resulting Q object to the filtered
                # queryset.
                q = getattr(self,'_%sQ' % (k,))(v, fromTable)
                logger.debug('fromTable = %s, k = %s, v = %s, q = %s', fromTable, k, v, q)
                qs = qs.filter(q)

        # Assign query sets for the current UI selections
        if fromTable == 'Activity':
            self.qs = qs.using(self.dbname)
            ##logger.debug('Activity query = %s', str(self.qs.query))
        elif fromTable == 'Sample':
            self.sample_qs = qs.using(self.dbname)
            logger.debug('Sample query = %s', str(self.sample_qs.query))
        elif fromTable == 'ActivityParameterHistogram':
            self.activityparameterhistogram_qs = qs.using(self.dbname)
            logger.debug('activityparameterhistogram_qs = %s', str(self.activityparameterhistogram_qs.query))

    def generateOptions(self):
        '''
        Generate a dictionary of all the selectable parameters by executing each of the functions
        to generate those parameters.  In this case, we'll simply do it by defining the dictionary and it's associated
        function, then iterate over that dictionary calling the function(s) to get the value to be returned.
        Note that in the case of parameters the return is a list of 2-tuples of (name, standard_name) and for
        platforms the result is a list of 3-tuples of (name, id, color) the associated elements.  
        For time and depth, the result is a single 2-tuple with the min and max value (respectively.)  
        
        These objects are "simple" dictionaries using only Python's built-in types - so conversion to a
        corresponding JSON object should be trivial.
        '''
        options_functions={
                           'sampledparametersgroup': self.getParameters,
                           'measuredparametersgroup': self.getParameters,
                           ##'parameters': self.getParameters,
                           'parameterminmax': self.getParameterMinMax,
                           'platforms': self.getPlatforms,
                           'time': self.getTime,
                           'depth': self.getDepth,
                           'simpledepthtime': self.getSimpleDepthTime,
                           'sampledepthtime': self.getSampleDepthTime,
                           'count': self.getLocalizedCount,
                           'ap_count': self.getAPCount,
                           'sql': self.mpq.getMeasuredParametersPostgreSQL,
                           'extent': self.getExtent,
                           'activityparameterhistograms': self.getActivityParameterHistograms,
                           'parameterplatformdatavaluepng': self.getParameterPlatformDatavaluePNG,
                           ##'activityparamhistrequestpngs': self.getActivityParamHistRequestPNGs,
                           }
        
        results = {}
        for k,v in options_functions.iteritems():
            if k == 'measuredparametersgroup':
                results[k] = v(MEASUREDINSITU)
                # To support legacy databases that do not have ParamaterGroup.name populated
                if not results[k]:
                    results[k] = v()
            elif k == 'sampledparametersgroup':
                results[k] = v(SAMPLED)
            else:
                results[k] = v()
        
        ##logger.info('qs.query = %s', pprint.pformat(str(self.qs.query)))
        ##logger.info('results = %s', pprint.pformat(results))
        return results
    
    #
    # Methods that generate summary data, based on the current query criteria.
    #
    def getLocalizedCount(self):
        '''
        Get the localized count (with commas) of measured parameters giving the exising query and return as string
        '''
        
        qs_ap = self.getActivityParametersQS()                  # Approximate count from ActivityParameter
        if qs_ap:
            ap_count = qs_ap.count()
            approximate_count = qs_ap.aggregate(Sum('number'))['number__sum']
            locale.setlocale(locale.LC_ALL, 'en_US')
            if getGet_Actual_Count(self.kwargs):
                if not self.mpq.qs_mp:
                    self.mpq.buildMPQuerySet(*self.args, **self.kwargs)
                return self.mpq.getLocalizedMPCount()
            else:
                return locale.format("%d", approximate_count, grouping=True)
        else:
            return 0

    def getAPCount(self):
        '''
        Return count of ActivityParameters given the current constraints
        ''' 
        qs_ap = self.getActivityParametersQS()                  # Approximate count from ActivityParameter
        if qs_ap:
            return qs_ap.count()
        else:
            return 0
        
    def getActivityParametersQS(self):
        '''
        Return query set of ActivityParameters given the current constraints. 
        '''
        qparams = {}

        qs_ap = models.ActivityParameter.objects.using(self.dbname).all()
        if self.kwargs.has_key('measuredparametersgroup'):
            if self.kwargs['measuredparametersgroup']:
                qs_ap = qs_ap.filter(Q(parameter__name__in=self.kwargs['measuredparametersgroup']))
        if self.kwargs.has_key('parameterstandardname'):
            if self.kwargs['parameterstandardname']:
                qs_ap = qs_ap.filter(Q(parameter__standard_name__in=self.kwargs['parameterstandardname']))
        if self.kwargs.has_key('platforms'):
            if self.kwargs['platforms']:
                qs_ap = qs_ap.filter(Q(activity__platform__name__in=self.kwargs['platforms']))
        if self.kwargs.has_key('time'):
            if self.kwargs['time'][0] is not None:
                q1 = Q(activity__startdate__lte=self.kwargs['time'][0]) & Q(activity__enddate__gte=self.kwargs['time'][0])
            if self.kwargs['time'][1] is not None:
                q2 = Q(activity__startdate__lte=self.kwargs['time'][1]) & Q(activity__enddate__gte=self.kwargs['time'][1])
            if self.kwargs['time'][0] is not None and self.kwargs['time'][1] is not None:
                q3 = Q(activity__startdate__gte=self.kwargs['time'][0]) & Q(activity__startdate__lte=self.kwargs['time'][1]
                    ) & Q(activity__enddate__gte=self.kwargs['time'][0]) & Q(activity__enddate__lte=self.kwargs['time'][1])

                qs_ap = qs_ap.filter(q1 | q2 | q3)

                logger.debug('ORing Q objects %s, %s, %s', q1, q2, q3)

        if self.kwargs.has_key('depth'):
            if self.kwargs['depth'][0] is not None:
                q1 = Q(activity__mindepth__lte=self.kwargs['depth'][0]) & Q(activity__maxdepth__gte=self.kwargs['depth'][0])
            if self.kwargs['depth'][1] is not None:
                q2 = Q(activity__mindepth__lte=self.kwargs['depth'][1]) & Q(activity__maxdepth__gte=self.kwargs['depth'][1])
            if self.kwargs['depth'][0] is not None and self.kwargs['depth'][1] is not None:
                q3 = Q(activity__mindepth__gte=self.kwargs['depth'][0]) & Q(activity__mindepth__lte=self.kwargs['depth'][1]
                    ) & Q(activity__maxdepth__gte=self.kwargs['depth'][0]) & Q(activity__maxdepth__lte=self.kwargs['depth'][1])
                qs_ap = qs_ap.filter(q1 | q2 | q3)

        if qs_ap:
            logger.debug(pprint.pformat(str(qs_ap.query)))
        else:
            logger.debug("No queryset returned for ")
        return qs_ap

    def getActivityParameterHistogramsQS(self):
        '''
        Return query set of ActivityParameterHistograms given the current constraints. 
        '''
        if not self.activityparameterhistogram_qs:
            logger.warn("self.activityparameterhistogram_qs is None")
            return
        if self.activityparameterhistogram_qs:
            return self.activityparameterhistogram_qs

    def getSampleQS(self):
        '''
        Return query set of Samples given the current constraints. 
        '''
        if not self.sample_qs:
            logger.warn("self.sample_qs is None")
            return
        else:
            return self.sample_qs

    def getActivities(self):
        '''
        Get a list of the unique activities based on the current query criteria.  
        return the UUID's of those, since we need to return those to perform the query later.
        Lastly, we assume here that the uuid's and name's have a 1:1 relationship - this should be enforced
        somewhere in the database hopefully.  If not, we'll return the duplicate name/uuid pairs as well.
        '''
        qs = self.qs.values('uuid', 'name').distinct()
        results=[]
        for row in qs:
            name = row['name']
            uuid = row['uuid']
            if name is not None and uuid is not None:
                results.append((name,uuid,))
        return results

    def getParameters(self, groupName=''):
        '''
        Get a list of the unique parameters that are left based on the current query criteria.  Also
        return the UUID's of those, since we need to return those to perform the query later.
        Lastly, we assume here that the name is unique and is also used for the id - this is enforced on 
        data load.
        '''
        # Django makes it easy to do sub-queries: Get Parameters from list of Activities matching current selection
        p_qs = models.Parameter.objects.using(self.dbname).filter(Q(activityparameter__activity__in=self.qs))
        if groupName:
            p_qs = p_qs.filter(parametergroupparameter__parametergroup__name=groupName)

        p_qs = p_qs.values('name','standard_name','id','units').distinct().order_by('name')
        # Odd: Trying to print the query gives "Can't do subqueries with queries on different DBs."
        ##logger.debug('----------- p_qs.query (%s) = %s', groupName, str(p_qs.query))

        results=[]
        for row in p_qs:
            name = row['name']
            standard_name = row['standard_name']
            id = row['id']
            units = row['units']
            if not standard_name:
                standard_name = ''
            if name is not None:
                results.append((name,standard_name,id,units))

        return results

    def getParameterMinMax(self):
        '''
        If a single parameter has been selected return the average 2.5 and 97.5 percentiles of the
        data and call them min and max for purposes of plotting
        '''
        results = []
        if self.kwargs.has_key('measuredparametersgroup'):
            if len(self.kwargs['measuredparametersgroup']) == 1:
                qs = self.getActivityParametersQS().aggregate(Avg('p025'), Avg('p975'))
                try:
                    results = [self.kwargs['measuredparametersgroup'][0], round_to_n(qs['p025__avg'],3), round_to_n(qs['p975__avg'],3)]
                except TypeError, e:
                    logger.exception(e)
        if self.kwargs.has_key('parameterstandardname'):
            if len(self.kwargs['parameterstandardname']) == 1:
                qs = self.getActivityParametersQS().aggregate(Avg('p025'), Avg('p975'))
                results = [self.kwargs['parameterstandardname'][0], round_to_n(qs['p025__avg'],3), round_to_n(qs['p975__avg'],3)]
        return results
    
    def getPlatforms(self):
        '''
        Get a list of the unique platforms that are left based on the current query criteria.  Also
        return the UUID's of those, since we need to return those to perform the query later.
        Lastly, we assume here that the name is unique and is also used for the id - this is enforced on 
        data load.
        '''
        qs=self.qs.values('platform__uuid', 'platform__name', 'platform__color').distinct()
        results=[]
        for row in qs:
            name=row['platform__name']
            id=row['platform__name']
            color=row['platform__color']
            if name is not None and id is not None:
                results.append((name,id,color,))
        return results
    
    def getTime(self):
        '''
        Based on the current selected query criteria, determine the available time range.  That'll be
        returned as a 2-tuple as the min and max values that are selectable.
        '''

        # Documentation of some query optimization (tested with dorado & tethys data from June 2010 loaded with a stide of 100)
        # =====================================================================================================================
        # The statements:
        #   qs=self.qs.aggregate(Max('instantpoint__timevalue'), Min('instantpoint__timevalue'))
        #   return (qs['instantpoint__timevalue__min'], qs['instantpoint__timevalue__max'],)
        # produce this SQL which takes 75.2 ms to execute:

        # stoqs_june2011=# explain analyze SELECT DISTINCT MAX("stoqs_instantpoint"."timevalue") AS "instantpoint__timevalue__max", MIN("stoqs_instantpoint"."timevalue") AS "instantpoint__timevalue__min" FROM "stoqs_activity" LEFT OUTER JOIN "stoqs_instantpoint" ON ("stoqs_activity"."id" = "stoqs_instantpoint"."activity_id");
        #                                                                                    QUERY PLAN                                                                                    
        # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        #  HashAggregate  (cost=738.13..738.14 rows=1 width=8) (actual time=75.154..75.154 rows=1 loops=1)
        #    ->  Aggregate  (cost=738.11..738.12 rows=1 width=8) (actual time=75.144..75.145 rows=1 loops=1)
        #          ->  Merge Left Join  (cost=0.00..629.34 rows=21755 width=8) (actual time=0.032..51.337 rows=21726 loops=1)
        #                Merge Cond: (stoqs_activity.id = stoqs_instantpoint.activity_id)
        #                ->  Index Scan using stoqs_activity_pkey on stoqs_activity  (cost=0.00..17.58 rows=45 width=4) (actual time=0.008..0.058 rows=36 loops=1)
        #                ->  Index Scan using stoqs_instantpoint_activity_id on stoqs_instantpoint  (cost=0.00..707.58 rows=21755 width=12) (actual time=0.016..19.982 rows=21726 loops=1)
        #  Total runtime: 75.231 ms
        # (7 rows)
        # 
        # The statements:
        #   qs=self.qs.aggregate(Max('enddate'), Min('startdate'))
        #   return (qs['startdate__min'], qs['enddate__max'],)
        # take 0.22 ms 
        # stoqs_june2011=# explain analyze SELECT DISTINCT MIN("stoqs_activity"."startdate") AS "startdate__min", MAX("stoqs_activity"."enddate") AS "enddate__max" FROM "stoqs_activity";
        #                                                      QUERY PLAN                                                       
        # -----------------------------------------------------------------------------------------------------------------------
        #  HashAggregate  (cost=5.69..5.70 rows=1 width=16) (actual time=0.154..0.156 rows=1 loops=1)
        #    ->  Aggregate  (cost=5.67..5.69 rows=1 width=16) (actual time=0.143..0.144 rows=1 loops=1)
        #          ->  Seq Scan on stoqs_activity  (cost=0.00..5.45 rows=45 width=16) (actual time=0.009..0.064 rows=36 loops=1)
        #  Total runtime: 0.219 ms
        # (4 rows)
        #
        # While only a fraction of a second different, it is 342 times faster!

        qs=self.qs.aggregate(Max('enddate'), Min('startdate'))
        return (time.mktime(qs['startdate__min'].timetuple())*1000, time.mktime(qs['enddate__max'].timetuple())*1000,)
    
    def getDepth(self):
        '''
        Based on the current selected query criteria, determine the available depth range.  That'll be
        returned as a 2-tuple as the min and max values that are selectable.
        '''
        # Original query that dives into the measurment table via instantpoint
        ##qs=self.qs.aggregate(Max('instantpoint__measurement__depth'), Min('instantpoint__measurement__depth'))
        ##return (qs['instantpoint__measurement__depth__min'],qs['instantpoint__measurement__depth__max'])

        # Alternate query to use stats stored with the Activity
        qs=self.qs.aggregate(Max('maxdepth'), Min('mindepth'))
        return ('%.2f' % qs['mindepth__min'], '%.2f' % qs['maxdepth__max'])
        
    def getSimpleDepthTime(self):
        '''
        Based on the current selected query criteria for activities, return the associated SimpleDepth time series
        values as a 2-tuple list inside a 2 level hash of platform__name (with its color) and activity__name.
        '''
        sdt = {}
        colors = {}
        for p in self.getPlatforms():
            qs = self.qs.filter(platform__name = p[0]).values_list(
                                    'simpledepthtime__epochmilliseconds', 
                                    'simpledepthtime__depth',
                                    'name'
                                ).order_by('simpledepthtime__epochmilliseconds')
            sdt[p[0]] = {}
            colors[p[0]] = p[2]
            # Create hash with date-time series organized by activity__name key within a platform__name key
            # This will let flot plot the series with gaps between the surveys -- not connected
            for s in qs:
                try:
                    ##logger.debug('s[2] = %s', s[2])
                    sdt[p[0]][s[2]].append( [s[0], '%.2f' % s[1]] )
                except KeyError:
                    sdt[p[0]][s[2]] = []                                    # First time seeing activity__name, make it a list
                    if s[1]:
                        sdt[p[0]][s[2]].append( [s[0], '%.2f' % s[1]] )     # Append first value
                except TypeError:
                    continue                                                # Likely "float argument required, not NoneType"

        return({'sdt': sdt, 'colors': colors})

    def getSampleDepthTime(self):
        '''
        Based on the current selected query criteria for activities, return the associated SampleDepth time series
        values as a 2-tuple list.  The name similarity to getSimpleDepthTime name is a pure coincidence.
        '''
        samples = []
        if self.getSampleQS():
            qs = self.getSampleQS().values_list(
                                    'instantpoint__timevalue', 
                                    'depth',
                                    'instantpoint__activity__name',
                                    'name'
                                ).order_by('instantpoint__timevalue')
            for s in qs:
                ems = 1000 * to_udunits(s[0], 'seconds since 1970-01-01')
                # Kludgy handling of activity names - flot needs 2 items separated by a space to handle sample event clicking
                if (s[2].find('_decim') != -1):
                    label = '%s %s' % (s[2].split('_decim')[0], s[3],)              # Lop off '_decim.nc (stride=xxx)' part of name
                elif (s[2].find(' ') != -1):
                    label = '%s %s' % (s[2].split(' ')[0], s[3],)                   # Lop off everything after a space in the activity name
                else:
                    label = '%s %s' % (s[2], s[3],)                                 # Show entire Activity name & sample name

                rec = {'label': label, 'data': [[ems, '%.2f' % s[1]]]}
                ##logger.debug('Appending %s', rec)
                samples.append(rec)

        return(samples)

    def getActivityParameterHistograms(self):
        '''
        Based on the current selected query criteria for activities, return the associated histograms of the selected
        parameters as a list of hashes, one hash per parameter with pairs of binlo and bincount for flot to make bar charts.
        Order in a somewhat complicated nested structure of hashes of hashes that permit the jQuery client to properly
        color and plot the data.
        '''
        aphHash = {}
        pUnits = {}
        showAllParameterValuesFlag = getShow_All_Parameter_Values(self.kwargs)
        showSigmatParameterValuesFlag = getShow_Sigmat_Parameter_Values(self.kwargs)
        showStandardnameParameterValuesFlag = getShow_StandardName_Parameter_Values(self.kwargs)
        for pa in models.Parameter.objects.using(self.dbname).all():

            # Apply (negative) logic on whether to continue with creating histograms based on checkboxes checked in the queryUI
            if not showAllParameterValuesFlag:
                if not showStandardnameParameterValuesFlag:
                    if not showSigmatParameterValuesFlag:
                        continue
                    elif pa.standard_name != 'sea_water_sigma_t':
                        continue
                elif not pa.standard_name:
                        continue

            histList = {}
            binwidthList = {}
            platformList = {}
            activityList = {}
            # Collect histograms organized by activity and platform names.  The SQL execution is sequential, a query
            # is executed for each parameter and here we organize by platform and activity.
            for aph in self.getActivityParameterHistogramsQS().select_related().filter(
                                activityparameter__parameter=pa).values('activityparameter__activity__name', 
                                'activityparameter__activity__platform__name', 'binlo', 'binhi', 'bincount').order_by(
                                'activityparameter__activity__platform__name', 'activityparameter__activity__name', 'binlo'):
                # Save histogram data by activity name
                try:
                    histList[aph['activityparameter__activity__name']].append([aph['binlo'], aph['bincount']])
                except KeyError:
                    # First time seeing this activity name, create a list and add the first histogram point
                    histList[aph['activityparameter__activity__name']] = []
                    histList[aph['activityparameter__activity__name']].append([aph['binlo'], aph['bincount']])
                    binwidthList[aph['activityparameter__activity__name']] = []
                    binwidthList[aph['activityparameter__activity__name']] = aph['binhi'] - aph['binlo']
                    platformList[aph['activityparameter__activity__name']] = []
                    platformList[aph['activityparameter__activity__name']].append(aph['activityparameter__activity__platform__name'])

                    logger.debug('pa.name = %s, aname = %s', pa.name, aph['activityparameter__activity__name'])

            # Unwind the platformList to get activities by platform name
            for an, pnList in platformList.iteritems():
                logger.debug('an = %s, pnList = %s', an, pnList)
                for pn in pnList:
                    try:
                        activityList[pn].append(an)
                    except KeyError:
                        activityList[pn] = []
                        activityList[pn].append(an)

            # Build the final data structure organized by platform -> activity
            plHash = {}
            for plat in activityList.keys():
                logger.debug('plat = %s', plat)
                for an in activityList[plat]:
                    try:
                        plHash[plat][an] = {'binwidth': binwidthList[an], 'hist': histList[an]}
                    except KeyError:
                        plHash[plat] = {}
                        plHash[plat][an] = {'binwidth': binwidthList[an], 'hist': histList[an]}

            # Assign histogram data to the hash keyed by parameter name
            if plHash:
                aphHash[pa.name] = plHash
                pUnits[pa.name] = pa.units

        # Make RGBA colors from the hex colors - needed for opacity in flot bars
        rgbas = {}
        for p in self.getPlatforms():
            r,g,b = (p[2][:2], p[2][2:4], p[2][4:])
            rgbas[p[0]] = 'rgba(%d, %d, %d, 0.4)' % (int(r,16), int(g,16), int(b,16))

        return {'histdata': aphHash, 'rgbacolors': rgbas, 'parameterunits': pUnits}

    def getActivityParamHistRequestPNGs(self):
        '''
        Return list of URLs that return a PNG image for the histograms of paramters contained in
        the Activity queryset.  The client can display these with an <img src=".." /> tag.
        '''
        urlList = []
        for qs in self.getActivityParameterHistogramsQS():
            pass

        return urlList

    def getParameterPlatformDatavaluePNG(self):
        '''
        Called when user interface has selected just one Parameter and just one Platform, in which case
        produce a depth-time section plot for overlay on the flot plot.  Return a png image file name for inclusion
        in the AJAX response.
        '''
        if not getDisplay_Parameter_Platform_Data(self.kwargs):
            return None, None, 'Contour data values checkbox not checked'
        if len(self.kwargs['measuredparametersgroup']) != 1:
            return None, None, 'Parameter name not selected'
        if len(self.getPlatforms()) != 1:
            if len(self.kwargs['platforms']) != 1:
                return None, None, 'Platform not selected'
        try:
            platformName = self.getPlatforms()[0][0]
        except IndexError, e:
            logger.warn(e)
            return None, None, 'Could not get platform name'
            
        logger.debug('platformName = %s', platformName)
        logger.debug('Instantiating Viz.ContourPlots............................................')
        if not self.mpq.qs_mp:
            self.mpq.buildMPQuerySet(*self.args, **self.kwargs)
        cp = ContourPlots(self.kwargs, self.request, self.qs, self.mpq.qs_mp,
                              self.getParameterMinMax(), self.getSampleQS(), platformName)

        return cp.contourDatavaluesForFlot()


    #
    # Methods that generate Q objects used to populate the query.
    #    
        
    def _sampledparametersgroupQ(self, parameterid, fromTable='Activity'):
        '''
        Build a Q object to be added to the current queryset as a filter.  This should 
        ensure that our result doesn't contain any parameter names that were not selected.
        We use id for sampledparametersgroup as the name may contain special characters.
        '''
        q=Q()
        if parameterid is None:
            return q
        else:
            if fromTable == 'Activity':
                q=Q(activityparameter__parameter__id__in=parameterid)
            elif fromTable == 'Sample':
                q=Q(sampledparameter__parameter__id__in=parameterid)
            elif fromTable == 'ActivityParameterHistogram':
                q=Q(activityparameter__parameter__id__in=parameterid)
        return q

    def _measuredparametersgroupQ(self, parametername, fromTable='Activity'):
        '''
        Build a Q object to be added to the current queryset as a filter.  This should 
        ensure that our result doesn't contain any parameter names that were not selected.
        '''
        q=Q()
        if parametername is None:
            return q
        else:
            if fromTable == 'Activity':
                q=Q(activityparameter__parameter__name__in=parametername)
            elif fromTable == 'Sample':
                # Use sub-query to find all Samples from Activities that are in the existing Activity queryset
                # Note: must do the monkey patch in __init__() so that Django's django/db/models/sql/query.py 
                # statement "sql, params = self.get_compiler(DEFAULT_DB_ALIAS).as_sql()" uses the right connection.
                # This is not a Django bug according to source code comment at:
                #    https://github.com/django/django/blob/master/django/db/models/sql/query.py
                q=Q(instantpoint__activity__in=self.qs)
            elif fromTable == 'ActivityParameterHistogram':
                # Use sub-query to find all ActivityParameterHistogram from Activities that are in the existing Activity queryset
                q=Q(activityparameter__activity__in=self.qs)
        return q

    def _parameterstandardnameQ(self, parameterstandardname, fromTable='Activity'):
        '''
        Build a Q object to be added to the current queryset as a filter.  This should 
        ensure that our result doesn't contain any parameter standard_names that were not selected.
        '''
        q=Q()
        if parameterstandardname is None:
            return q
        else:
            if fromTable == 'Activity':
                q=Q(activityparameter__parameter__standard_name__in=parameterstandardname)
            elif fromTable == 'Sample':
                # Use sub-query to find all Samples from Activities that are in the existing Activity queryset
                q=Q(instantpoint__activity__in=self.qs)
            elif fromTable == 'ActivityParameterHistogram':
                # Use sub-query to find all ActivityParameterHistogram from Activities that are in the existing Activity queryset
                q=Q(activityparameter__activity__in=self.qs)
        return q

    def _platformsQ(self, platforms, fromTable='Activity'):
        '''
        Build a Q object to be added to the current queryset as a filter.  This will ensure that we
        only generate the other values/sets for platforms that were selected.
        '''
        q=Q()
        if platforms is None:
            return q
        else:
            if fromTable == 'Activity':
                q=Q(platform__name__in=platforms)
            elif fromTable == 'Sample':
                # Use sub-query to find all Samples from Activities that are in the existing Activity queryset
                q=Q(instantpoint__activity__in=self.qs)
            elif fromTable == 'ActivityParameterHistogram':
                # Use sub-query to find all ActivityParameterHistogram from Activities that are in the existing Activity queryset
                q=Q(activityparameter__activity__in=self.qs)
        return q    
    
    def _timeQ(self, times, fromTable='Activity'):
        '''
        Build a Q object to be added to the current queryset as a filter.  This ensures that we limit
        things down based on the time range selected by the user.
        '''
        q=Q()
        if not times:
            return q
        if times[0] is not None:
            if fromTable == 'Activity':
                q=Q(enddate__gte=times[0])
            elif fromTable == 'Sample':
                q=Q(instantpoint__timevalue__gte=times[0])
            elif fromTable == 'ActivityParameterHistogram':
                q=Q(activityparameter__activity__enddate__gte=times[0])
        if times[1] is not None:
            if fromTable == 'Activity':
                q=q & Q(startdate__lte=times[1])
            elif fromTable == 'Sample':
                q=q & Q(instantpoint__timevalue__lte=times[1])
            elif fromTable == 'ActivityParameterHistogram':
                q=q & Q(activityparameter__activity__startdate__lte=times[1])
        return q
    
    def _depthQ(self, depth, fromTable='Activity'):
        '''
        Build a Q object to be added to the current queryset as a filter.  Once again, we want
        to make sure that we only generate the "leftover" components based on the selected depth
        range.
        '''
        q=Q()
        if not depth:
            return q
        if depth[0] is not None:
            if fromTable == 'Activity':
                q=Q(maxdepth__gte=depth[0])
            elif fromTable == 'Sample':
                q=Q(depth__gte=depth[0])
            elif fromTable == 'ActivityParameterHistogram':
                q=Q(activityparameter__activity__maxdepth__gte=depth[0])
        if depth[1] is not None:
            if fromTable == 'Activity':
                q=q & Q(mindepth__lte=depth[1])
            elif fromTable == 'Sample':
                q=q & Q(depth__lte=depth[1])
            elif fromTable == 'ActivityParameterHistogram':
                q=q & Q(activityparameter__activity__mindepth__lte=depth[1])
        return q
    

    #
    # Methods to get the query used based on the current Q object.
    #
    def getSQLWhere(self):
        '''
        This method will generate a pseudo-query, and then normalize it to a standard SQL query.  While for
        PostgreSQL this is usually the actual query, we might need to massage it a bit to handle quoting
        issues and such.  The string representation of the queryset's query attribute gives us the query.
        
        This is really useful when we want to generate a new mapfile based on the current query result.  We just want
        the WHERE clause of the query, since that's where the predicate exists.
        '''
        querystring = str(self.qs.query)
        
        return querystring

    def getActivityGeoQuery(self, Q_object = None):
        '''
        This method generates a string that can be put into a Mapserver mapfile DATA statment.
        It is for returning Activities.
        '''
        qs = self.qs

        # Add any more filters (Q objects) if specified
        if Q_object:
            qs = qs.filter(Q_object)

        # Query for mapserver
        geo_query = '''geom from (%s)
            as subquery using unique gid using srid=4326''' % postgresifySQL(qs.query).rstrip()
        
        return geo_query

    def getSampleGeoQuery(self, Q_object = None):
        '''
        This method generates a string that can be put into a Mapserver mapfile DATA statment.
        It is for returning Samples.
        '''
        qs = self.sample_qs
        if not qs:
            return

        # Add any more filters (Q objects) if specified
        if Q_object:
            qs = self.sample_qs.using(self.dbname).filter(Q_object)

        # Query for mapserver
        geo_query = 'geom from (%s) as subquery using unique gid using srid=4326' % postgresifySQL(qs.query, sampleFlag=True)

        logger.debug('geo_query = %s', geo_query)
        
        return geo_query

    def getSampleExtent(self, geoqueryset, srid=4326):
        """
        Accepts a GeoQuerySet and SRID. 
        Returns the extent as a GEOS object in the Google Maps projection.
        The result can be directly passed out for direct use in OpenLayers.
        """
        area = geoqueryset.area()
        extent = fromstr('MULTIPOINT (%s %s, %s %s)' % geoqueryset.extent(), srid=srid)
        ul = extent[0]
        lr = extent[1]
        dist = ul.distance(lr)
        
        # if the points are all in one location then expand the extent so openlayers
        # will zoom to something that is visible
        if not dist:
            ul.x = ul.x-0.15
            ul.y = ul.y+0.15
            lr.x = lr.x+0.15
            lr.y = lr.y-0.15
            extent = MultiPoint(ul,lr)
            extent.srid = srid

        extent.transform(900913)
        return extent

    def getExtent(self, srid=4326):
        '''
        Return GEOSGeometry extent of all the geometry contained in the Activity and Sample geoquerysets.
        The result can be directly passed out for direct use in a OpenLayers.
        '''        
        extent = None

        # Check all geometry types encountered in Activity GeoQuerySet in priority order
        extentList = [] 
        for geom_field in (('maptrack', 'mappoint', 'plannedtrack')):
            try:
                extentList.append(self.qs.extent(field_name=geom_field))
            except DatabaseError:
                logger.warn('Database %s does not have field %s', self.dbname, geom_field)
            except TypeError:
                logger.debug('Field %s is Null in Activity GeoQuerySet: %s', geom_field, str(self.qs) )

        # Append the Sample geometries 
        try:
            sqs = self.getSampleQS()
            extentList.append(sqs.extent(field_name='geom'))
        except:
            logger.debug('Could not get an extent for Sample GeoQuerySet')

        # Take the union of all geometry types found in Activities and Samples
        logger.debug("Collected %d geometry extents from Activities and Samples", len(extentList))
        if extentList:
            geom_union = fromstr('LINESTRING (%s %s, %s %s)' % extentList[0], srid=srid)
            for extent in extentList[1:]:
                logger.debug('extent = %s', extent)
                geom_union = geom_union.union(fromstr('LINESTRING (%s %s, %s %s)' % extent, srid=srid))

            # Aggressive try/excepts done here for better reporting on the production servers
            logger.debug('geom_union = %s', geom_union)
            try:
                geomstr = 'LINESTRING (%s %s, %s %s)' % geom_union.extent
            except TypeError:
                logger.exception('Tried to get extent for self.qs.query =  %s, but failed. Check the database loader and make sure a geometry type (maptrack or mappoint) is assigned for each activity.', str(self.qs.query))

            logger.debug('geomstr = %s', geomstr)
            try:
                extent = fromstr(geomstr, srid=srid)
            except:
                logger.exception('Could not get extent for geomstr = %s, srid = %d', geomstr, srid)

            try:
                extent.transform(900913)
            except:
                logger.exception('Cannot get transorm to 900913 for geomstr = %s, srid = %d', geomstr, srid)
        
        return extent

