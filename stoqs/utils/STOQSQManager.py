__author__    = 'Mike McCann'
__copyright__ = '2012'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

STOQS Query manager for building ajax responses to selections made for QueryUI

@undocumented: __doc__ parser
@status: production
@license: GPL
'''

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Max, Min, Sum, Avg
from django.db.models.sql import query
from django.contrib.gis.geos import fromstr, MultiPoint
from django.db.utils import DatabaseError
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from stoqs import models
from loaders import MEASUREDINSITU, X3DPLATFORMMODEL, X3D_MODEL
from loaders.SampleLoaders import SAMPLED, NETTOW
from utils import round_to_n, postgresifySQL, EPOCH_STRING, EPOCH_DATETIME
from utils import getGet_Actual_Count, getShow_Sigmat_Parameter_Values, getShow_StandardName_Parameter_Values, getShow_All_Parameter_Values, getShow_Parameter_Platform_Data, getShow_Geo_X3D_Data
from utils import simplify_points, getParameterGroups
from geo import GPS
from MPQuery import MPQuery
from PQuery import PQuery
from Viz import MeasuredParameter, ParameterParameter, PPDatabaseException, PlatformAnimation
from coards import to_udunits
from datetime import datetime
from django.contrib.gis import gdal
import logging
import pprint
import calendar
import re
import locale
import time
import os
import tempfile
import numpy as np

logger = logging.getLogger(__name__)

# Constants to be also used by classifiers in contrib/analysis
LABEL = 'label'
DESCRIPTION = 'description'
COMMANDLINE = 'commandline'
spherical_mercator_srid = 3857

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
        self.pq = PQuery(request)
        self.pp = None
        self._actual_count = None
        self.initialQuery = True

        # monkey patch sql/query.py to make it use our database for sql generation
        query.DEFAULT_DB_ALIAS = dbname

        # Dictionary of items that get returned via AJAX as the JSON response.  Make available as member variable.
        self.options_functions = {
            'sampledparametersgroup': self.getParameters,
            'measuredparametersgroup': self.getParameters,
            'parameterminmax': self.getParameterMinMax,
            'platforms': self.getPlatforms,
            'time': self.getTime,
            'depth': self.getDepth,
            'simpledepthtime': self.getSimpleDepthTime,
            ##'simplebottomdepthtime': self.getSimpleBottomDepthTime,
            'parametertime': self.getParameterTime,
            'sampledepthtime': self.getSampleDepthTime,
            'nettowdepthtime': self.getNetTowDepthTime,
            'counts': self.getCounts,
            'mpsql': self.getMeasuredParametersPostgreSQL,
            'spsql': self.getSampledParametersPostgreSQL,
            'extent': self.getExtent,
            'activityparameterhistograms': self.getActivityParameterHistograms,
            'parameterplatformdatavaluepng': self.getParameterPlatformDatavaluePNG,
            'parameterparameterx3d': self.getParameterParameterX3D,
            'measuredparameterx3d': self.getMeasuredParameterX3D,
            'platformanimation': self.getPlatformAnimation,
            'parameterparameterpng': self.getParameterParameterPNG,
            'parameterplatforms': self.getParameterPlatforms,
            'x3dterrains': self.getX3DTerrains,
            'x3dplaybacks': self.getX3DPlaybacks,
            'resources': self.getResources,
            'attributes': self.getAttributes,
        }
        
    def buildQuerySets(self, *args, **kwargs):
        '''
        Build the query sets based on any selections from the UI.  We need one for Activities and one for Samples
        '''
        kwargs['fromTable'] = 'Activity'
        self._buildQuerySet(**kwargs)

        kwargs['fromTable'] = 'Sample'
        self._buildQuerySet(**kwargs)

        kwargs['fromTable'] = 'ActivityParameter'
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
                              these are passed onto MPQuery and processed from the kwargs dictionary
            parameterparameter - a tuple of Parameter ids for x, y, z axes and color for correlation plotting

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
                qs = models.Activity.objects.using(self.dbname).all()   # To receive filters constructed below from kwargs
                qs_platform = qs
            elif fromTable == 'Sample':
                logger.debug('Making %s based query', fromTable)
                qs = models.Sample.objects.using(self.dbname).all()   # To receive filters constructed below from kwargs
                # Exclude sub (child) samples where name is not set.  Flot UI needs a name for its selector
                qs = qs.exclude(name__isnull=True)
            elif fromTable == 'ActivityParameter':
                logger.debug('Making %s based query', fromTable)
                qs = models.ActivityParameter.objects.using(self.dbname).all()   # To receive filters constructed below from kwargs
            elif fromTable == 'ActivityParameterHistogram':
                logger.debug('Making %s based query', fromTable)
                qs = models.ActivityParameterHistogram.objects.using(self.dbname).all()   # To receive filters constructed below from kwargs
            else:
                logger.exception('No handler for fromTable = %s', fromTable)
    
        self.args = args
        self.kwargs = kwargs

        # Determine if this is the intial query and set a flag
        for k, v in kwargs.iteritems():
            # Test keys that can affect the MeasuredParameter count
            if  k == 'depth' or k == 'time':
                if v[0] is not None or v[1] is not None:
                    self.initialQuery = False
            elif k in ['measuredparametersgroup', 'parameterstandardname', 'platforms']:
                if v:
                    logger.debug('Setting self.initialQuery = False because %s = %s', k, v)
                    self.initialQuery = False

        logger.debug('self.initialQuery = %s', self.initialQuery)

        # Check to see if there is a "builder" for a Q object using the given parameters and build up the filter from the Q objects
        for k, v in kwargs.iteritems():
            if not v:
                continue
            if k == 'fromTable':
                continue
            if hasattr(self, '_%sQ' % (k,)):
                # Call the method if it exists, and add the resulting Q object to the filtered queryset.
                q = getattr(self,'_%sQ' % (k,))(v, fromTable)
                logger.debug('fromTable = %s, k = %s, v = %s, q = %s', fromTable, k, v, q)
                qs = qs.filter(q)
                if k != 'platforms' and fromTable == 'Activity':
                    qs_platform = qs_platform.filter(q)

        # Assign query sets for the current UI selections
        if fromTable == 'Activity':
            self.qs = qs.using(self.dbname)
            self.qs_platform = qs_platform.using(self.dbname)
            ##logger.debug('Activity query = %s', str(self.qs.query))
        elif fromTable == 'Sample':
            self.sample_qs = qs.using(self.dbname)
            ##logger.debug('Sample query = %s', str(self.sample_qs.query))
        elif fromTable == 'ActivityParameter':
            self.activityparameter_qs = qs.using(self.dbname)
            ##logger.debug('activityparameter_qs = %s', str(self.activityparameter_qs.query))
        elif fromTable == 'ActivityParameterHistogram':
            self.activityparameterhistogram_qs = qs.using(self.dbname)
            ##logger.debug('activityparameterhistogram_qs = %s', str(self.activityparameterhistogram_qs.query))

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
        
        results = {}
        for k,v in self.options_functions.iteritems():
            if self.kwargs['only'] != []:
                if k not in self.kwargs['only']:
                    continue
            if k in self.kwargs['except']:
                continue

            if k == 'measuredparametersgroup':
                results[k] = v(MEASUREDINSITU)
            elif k == 'sampledparametersgroup':
                results[k] = v(SAMPLED)
            else:
                results[k] = v()
        
        ##logger.info('qs.query = %s', pprint.pformat(str(self.qs.query)))
        ##logger.info('results = %s', pprint.pformat(results))
        return results
    
    #
    # Methods that generate summary data, based on the current query criteria
    #
    def getCounts(self):
        '''
        Collect all of the various counts into a dictionary
        '''
        # Always get approximate count
        logger.debug('str(self.getActivityParametersQS(forCount=True).query) = %s', str(self.getActivityParametersQS(forCount=True).query))
        approximate_count = self.getActivityParametersQS(forCount=True).aggregate(Sum('number'))['number__sum']
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

        # Actual counts are None unless the 'Get actual count' box is checked
        actual_count = None
        actual_count_localized = None
        if getGet_Actual_Count(self.kwargs):
            if not self.mpq.qs_mp:
                self.mpq.buildMPQuerySet(*self.args, **self.kwargs)

            if self._actual_count:
                actual_count = self._actual_count
            else:
                logger.debug('Calling self.mpq.getMPCount()')
                actual_count = self.mpq.getMPCount()
                logger.debug('actual_count = %s', actual_count)

        try:
            approximate_count_localized = locale.format("%d", approximate_count, grouping=True)
        except TypeError:
            logger.exception('Failed to format approximate_count = %s into a number', approximate_count)
            approximate_count_localized = None
        
        if actual_count:
            try:
                actual_count_localized = locale.format("%d", actual_count, grouping=True)
            except TypeError:
                logger.exception('Failed to format actual_count = %s into a number', actual_count)


        return {    'ap_count': self.getAPCount(), 
                    'approximate_count': approximate_count,
                    'approximate_count_localized': approximate_count_localized,
                    'actual_count': actual_count,
                    'actual_count_localized': actual_count_localized
                }

    def getMeasuredParametersPostgreSQL(self):
        '''
        Wrapper around self.mpq.getMeasuredParametersPostgreSQL(), ensure that we have qs_mp built before calling 
        '''
        sql = ''
        if not self.mpq.qs_mp:
            self.mpq.buildMPQuerySet(*self.args, **self.kwargs)
        self.mpq.initialQuery = self.initialQuery
        try:
            sql = self.mpq.getMeasuredParametersPostgreSQL()
            self._actual_count = self.mpq.getMPCount()
        except Exception as e:
            logger.warn('Could not get MeasuredParametersPostgreSQL: %s', e)

        return sql

    def getSampledParametersPostgreSQL(self):
        '''
        Wrapper around self.mpq.getSampledParametersPostgreSQL(), ensure that we have qs_mp built before calling 
        '''
        if not self.mpq.qs_mp:
            self.mpq.buildMPQuerySet(*self.args, **self.kwargs)
        self.mpq.initialQuery = self.initialQuery
        sql = self.mpq.getSampledParametersPostgreSQL()

        return sql

    def getAPCount(self):
        '''
        Return count of ActivityParameters given the current constraints
        ''' 
        qs_ap = self.getActivityParametersQS()                  # Approximate count from ActivityParameter
        if qs_ap:
            return qs_ap.count()
        else:
            return 0
        
    def getActivityParametersQS(self, forCount=False):
        '''
        Return query set of ActivityParameters given the current constraints. 
        If forCount is True then add list of measured parameters to the query; this is done here for the query
        needed for getting the count.  The ParameterParameter min & max query also uses self.activityparameter_qs
        and we don't want the addition of the measured parameters query for that.
        '''
        if not self.activityparameter_qs:
            logger.warn("self.activityparameter_qs is None")
        if forCount:
            if self.kwargs['measuredparametersgroup']:
                logger.debug('Adding Q object for parameter__name__in = %s', self.kwargs['measuredparametersgroup'])
                return self.activityparameter_qs.filter(Q(parameter__name__in=self.kwargs['measuredparametersgroup']))
            else:
                return self.activityparameter_qs
        else:
            return self.activityparameter_qs

    def getActivityParameterHistogramsQS(self):
        '''
        Return query set of ActivityParameterHistograms given the current constraints. 
        '''
        return self.activityparameterhistogram_qs

    def getSampleQS(self):
        '''
        Return query set of Samples given the current constraints. 
        '''
        return self.sample_qs

    def getParameters(self, groupName=''):
        '''
        Get a list of the unique parameters that are left based on the current query criteria.  Also
        return the UUID's of those, since we need to return those to perform the query later.
        Lastly, we assume here that the name is unique and is also used for the id - this is enforced on 
        data load.
        '''
        # Django makes it easy to do sub-queries: Get Parameters from list of Activities matching current selection
        p_qs = models.Parameter.objects.using(self.dbname).filter(Q(activityparameter__activity__in=self.qs)).order_by('name')
        if 'mplabels' in self.kwargs:
            if self.kwargs['mplabels']:
                # Get all Parameters that have common Measurements given the filter of the selected labels
                # - this allows selection of co-located MeasuredParameters
                commonMeasurements = models.MeasuredParameterResource.objects.using(self.dbname).filter( 
                                        resource__id__in=self.kwargs['mplabels']).values_list(
                                        'measuredparameter__measurement__id', flat=True)
                p_qs = p_qs.filter(Q(id__in=models.MeasuredParameter.objects.using(self.dbname).filter(
                        Q(measurement__id__in=commonMeasurements)).values_list('parameter__id', flat=True).distinct()))

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

    def getParameterMinMax(self, pid=None, percentileAggregateType='avg'):
        '''
        If a single parameter has been selected in the filter for data access return the average 2.5 and 97.5 
        percentiles of the data and call them min and max for purposes of data access, namely KML generation in 
        the UI - assign these values to the 'dataaccess' key of the return hash.  If pid is specificed then 
        assign values to the 'plot' key of the return hash.  If @percentileAggregateType is 'avg' (the default)
        then the average of all the 2.5 and 97.5 percentiles will be used.  This would be appropriate for
        contour or scatter plotting.  If @percentileAggregateType is 'extrema' then the aggregate Min is used 
        for 'p010' and Max for 'p990'.  This is appropriate for parameter-parameter plotting.
        '''
        da_results = []
        plot_results = []

        # pid takes precedence over parameterplot being specified in kwargs
        if pid:
            try:            
                if percentileAggregateType == 'extrema':
                    logger.debug('self.getActivityParametersQS().filter(parameter__id=%s) = %s', pid, str(self.getActivityParametersQS().filter(parameter__id=pid).query))
                    qs = self.getActivityParametersQS().filter(parameter__id=pid).aggregate(Min('p010'), Max('p990'), Avg('median'))
                    logger.debug('qs = %s', qs)
                    try:
                        plot_results = [pid, round_to_n(qs['p010__min'],4), round_to_n(qs['p990__max'],4)]
                    except TypeError:
                        logger.exception('Failed to get plot_results for qs = %s', qs)
                else:
                    qs = self.getActivityParametersQS().filter(parameter__id=pid).aggregate(Avg('p025'), Avg('p975'), Avg('median'))
                    try:
                        plot_results = [pid, round_to_n(qs['p025__avg'],4), round_to_n(qs['p975__avg'],4)]
                        if plot_results[1] == plot_results[2]:
                            logger.debug('Standard min and max for for pid %s are the same. Getting the overall min and max values.', pid)
                            qs = self.getActivityParametersQS().filter(parameter__id=pid).aggregate(Min('p025'), Max('p975'))
                            plot_results = [pid, round_to_n(qs['p025__min'],4), round_to_n(qs['p975__max'],4)]
                    except TypeError:
                        logger.exception('Failed to get plot_results for qs = %s', qs)
            except ValueError as e:
                if pid in ('longitude', 'latitude'):
                    # Get limits from Activity maptrack for which we have our getExtent() method
                    extent, lon_mid, lat_mid = self.getExtent(outputSRID=4326)
                    if pid == 'longitude':
                        plot_results = ['longitude', round_to_n(extent[0][0], 4), round_to_n(extent[1][0],4)]
                    if pid == 'latitude':
                        plot_results = ['latitude', round_to_n(extent[0][1], 4), round_to_n(extent[1][1],4)]
                elif pid == 'depth':
                    dminmax = self.qs.aggregate(Min('mindepth'), Max('maxdepth'))
                    plot_results = ['depth', round_to_n(dminmax['mindepth__min'], 4), round_to_n(dminmax['maxdepth__max'],4)]
                elif pid == 'time':
                    epoch = EPOCH_DATETIME
                    tminmax = self.qs.aggregate(Min('startdate'), Max('enddate'))
                    tmin = (tminmax['startdate__min'] - epoch).days + (tminmax['startdate__min'] - epoch).seconds / 86400.
                    tmax = (tminmax['enddate__max'] - epoch).days + (tminmax['enddate__max'] - epoch).seconds / 86400.
                    plot_results = ['time', tmin, tmax]
                else:
                    logger.error('%s, but pid text = %s is not a coordinate', e, pid)

                return {'plot': plot_results, 'dataaccess': []}

        elif 'parameterplot' in self.kwargs:
            if self.kwargs['parameterplot'][0]:
                parameterID = self.kwargs['parameterplot'][0]
                try:
                    if percentileAggregateType == 'extrema':
                        qs = self.getActivityParametersQS().filter(parameter__id=parameterID).aggregate(Min('p025'), Max('p975'))
                        plot_results = [parameterID, round_to_n(qs['p025__min'],4), round_to_n(qs['p975__max'],4)]
                    else:
                        qs = self.getActivityParametersQS().filter(parameter__id=parameterID).aggregate(Avg('p025'), Avg('p975'))
                        plot_results = [parameterID, round_to_n(qs['p025__avg'],4), round_to_n(qs['p975__avg'],4)]
                except TypeError as e:
                    logger.exception(e)

        if self.kwargs.has_key('measuredparametersgroup'):
            if len(self.kwargs['measuredparametersgroup']) == 1:
                mpname = self.kwargs['measuredparametersgroup'][0]
                try:
                    pid = models.Parameter.objects.using(self.dbname).get(name=mpname).id
                    logger.debug('pid = %s', pid)
                    if percentileAggregateType == 'extrema':
                        qs = self.getActivityParametersQS().filter(parameter__id=pid).aggregate(Min('p010'), Max('p990'))
                        da_results = [pid, round_to_n(qs['p010__min'],4), round_to_n(qs['p990__max'],4)]
                    else:
                        qs = self.getActivityParametersQS().filter(parameter__id=pid).aggregate(Avg('p025'), Avg('p975'))
                        da_results = [pid, round_to_n(qs['p025__avg'],4), round_to_n(qs['p975__avg'],4)]
                except TypeError as e:
                    logger.exception(e)

        if self.kwargs.has_key('sampledparametersgroup'):
            if len(self.kwargs['sampledparametersgroup']) == 1:
                spid = self.kwargs['sampledparametersgroup'][0]
                try:
                    pid = models.Parameter.objects.using(self.dbname).get(id=spid).id
                    logger.debug('pid = %s', pid)
                    if percentileAggregateType == 'extrema':
                        qs = self.getActivityParametersQS().filter(parameter__id=pid).aggregate(Min('p010'), Max('p990'))
                        da_results = [pid, round_to_n(qs['p010__min'],4), round_to_n(qs['p990__max'],4)]
                    else:
                        qs = self.getActivityParametersQS().filter(parameter__id=pid).aggregate(Avg('p025'), Avg('p975'))
                        da_results = [pid, round_to_n(qs['p025__avg'],4), round_to_n(qs['p975__avg'],4)]
                except TypeError as e:
                    logger.exception(e)

        if self.kwargs.has_key('parameterstandardname'):
            if len(self.kwargs['parameterstandardname']) == 1:
                sname = self.kwargs['parameterstandardname'][0]
                try:
                    if percentileAggregateType == 'extrema':
                        qs = self.getActivityParametersQS().filter(parameter__standard_name=sname).aggregate(Min('p025'), Max('p975'))
                        da_results = [sname, round_to_n(qs['p025__min'],4), round_to_n(qs['p975__max'],4)]
                    else:
                        qs = self.getActivityParametersQS().filter(parameter__standard_name=sname).aggregate(Avg('p025'), Avg('p975'))
                        da_results = [sname, round_to_n(qs['p025__avg'],4), round_to_n(qs['p975__avg'],4)]
                except TypeError as e:
                    logger.exception(e)

        # Sometimes da_results is empty, make it the same as plot_results if this happens
        # TODO: simplify the logic implemented above...
        if not da_results:
            da_results = plot_results

        return {'plot': plot_results, 'dataaccess': da_results}

    def _getPlatformModel(self, platformName):
        '''Return Platform X3D model information. Designed for stationary
        platforms from non-trajectory Activities.
        '''
        @transaction.atomic(using=self.dbname)
        def _innerGetPlatformModel(self, platform):
            modelInfo = None, None, None, None

            pModel = models.PlatformResource.objects.using(self.dbname).filter(
                        resource__resourcetype__name=X3DPLATFORMMODEL,
                        resource__name=X3D_MODEL,
                        platform__name=platformName).values_list(
                                'resource__uristring', flat=True).distinct()
            if pModel:
                # Timeseries and timeseriesProfile data for a single platform
                # (even if composed of multiple Activities) must have single
                # unique horizontal position.
                geom_list = self.qs.filter(platform__name=platformName).values_list(
                        'nominallocation__geom', flat=True).distinct()
                try:
                    geom = geom_list[0]
                except IndexError:
                    return modelInfo
                if len(geom_list) > 1:
                    logger.error('More than one location for %s returned.'
                                 'Using first one found: %s', platformName, geom)

                # TimeseriesProfile data has multiple nominaldepths - look to 
                # Resource for nominaldepth of the Platform for these kind of data.
                depth_list = self.qs.filter(platform__name=platformName).values_list(
                        'nominallocation__depth', flat=True).distinct()
                if len(depth_list) > 1:
                    logger.debug('More than one depth for %s returned. Checking '
                                 'Resource for nominaldepth', platformName)
                    try:
                        depth = float(models.PlatformResource.objects.using(self.dbname).filter( 
                                resource__resourcetype__name=X3DPLATFORMMODEL, 
                                platform__name=platformName, 
                                resource__name='X3D_MODEL_nominaldepth'
                                ).values_list('resource__value', flat=True)[0])
                    except (IndexError, ObjectDoesNotExist):
                        logger.warn('Resource name X3D_MODEL_nominaldepth not found for '
                                    'for platform %s. Using a nominaldepth of 0.0', platformName)
                        depth = 0.0
                else:
                    depth = depth_list[0]

                modelInfo = (pModel[0], geom.y, geom.x, 
                             -depth * float(self.request.GET.get('ve', 10)))

            return modelInfo

        return _innerGetPlatformModel(self, platformName)       
    
    def getPlatforms(self):
        '''
        Get a list of the unique platforms that are left based on the current query criteria.
        We assume here that the name is unique and is also used for the id - this is enforced on 
        data load.  Organize the platforms into a dictionary keyed by platformType.
        '''
        qs = self.qs_platform.values('platform__uuid', 'platform__name', 'platform__color', 'platform__platformtype__name'
                            ).distinct().order_by('platform__name')
        results = []
        platformTypeHash = {}
        for row in qs:
            name=row['platform__name']
            id=row['platform__name']
            color=row['platform__color']
            platformType = row['platform__platformtype__name']
            if name is not None and id is not None:
                # Get the featureType from the Resource
                fts = models.ActivityResource.objects.using(self.dbname).filter(resource__name='featureType', 
                               activity__platform__name=name).values_list('resource__value', flat=True).distinct()
                try:
                    featureType = fts[0]
                except IndexError:
                    logger.warn('No featureType returned for platform name = %s.  Setting it to "trajectory".', name)
                    featureType = 'trajectory'
                if len(fts) > 1:
                    logger.warn('More than one featureType returned for platform %s: %s.  Using the first one.', name, fts)

                if 'trajectory' in featureType:
                    try:
                        platformTypeHash[platformType].append((name, id, color, featureType, ))
                    except KeyError:
                        platformTypeHash[platformType] = []
                        platformTypeHash[platformType].append((name, id, color, featureType, ))
                else:
                    x3dModel, x, y, z = self._getPlatformModel(name) 
                    if x3dModel:
                        try:
                            platformTypeHash[platformType].append((name, id, color, featureType, x3dModel, x, y, z))
                        except KeyError:
                            platformTypeHash[platformType] = []
                            platformTypeHash[platformType].append((name, id, color, featureType, x3dModel, x, y, z))
                    else:
                        try:
                            platformTypeHash[platformType].append((name, id, color, featureType, ))
                        except KeyError:
                            platformTypeHash[platformType] = []
                            platformTypeHash[platformType].append((name, id, color, featureType, ))

        return platformTypeHash
    
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
        try:
            times = (time.mktime(qs['startdate__min'].timetuple())*1000, time.mktime(qs['enddate__max'].timetuple())*1000,)
        except AttributeError:
            logger.exception('Failed to get timetuple from qs = %s', qs)
            return
        else:
            return times
    
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
        try:
            depths = ('%.2f' % qs['mindepth__min'], '%.2f' % qs['maxdepth__max'])
        except TypeError:
            logger.exception('Failed to convert mindepth__min and/or maxdepth__max to float from qs = %s', qs)
            return
        else:
            return depths
            
    def getSimpleDepthTime(self):
        '''
        Based on the current selected query criteria for activities, return the associated SimpleDepth time series
        values as a 2-tuple list inside a 2 level hash of platform__name (with its color) and activity__name.
        '''
        sdt = {}
        colors = {}

        trajectoryQ = self._trajectoryQ()
        timeSeriesQ = self._timeSeriesQ()
        timeSeriesProfileQ = self._timeSeriesProfileQ()
        trajectoryProfileQ = self._trajectoryProfileQ()

        for plats in self.getPlatforms().values():
            for p in plats:
                plq = Q(platform__name = p[0])
                sdt[p[0]] = {}
                colors[p[0]] = p[2]

                if p[3].lower() == 'trajectory':
                    # Overkill to also filter on trajectoryQ too if p[3].lower() == 'trajectory' - old Tethys data does not have NC_GLOBAL featureType
                    qs_traj = self.qs.filter(plq).values_list( 'simpledepthtime__epochmilliseconds', 'simpledepthtime__depth',
                                        'name').order_by('simpledepthtime__epochmilliseconds')
                    # Add to sdt hash date-time series organized by activity__name key within a platform__name key
                    # This will let flot plot the series with gaps between the surveys -- not connected
                    for s in qs_traj:
                        try:
                            ##logger.debug('s[2] = %s', s[2])
                            sdt[p[0]][s[2]].append( [s[0], '%.2f' % s[1]] )
                        except KeyError:
                            ##logger.debug('First time seeing activity__name = %s, making it a list in sdt', s[2])
                            sdt[p[0]][s[2]] = []                                    # First time seeing activity__name, make it a list
                            if s[1] is not None:
                                sdt[p[0]][s[2]].append( [s[0], '%.2f' % s[1]] )     # Append first value, even if it is 0.0
                        except TypeError:
                            continue                                                # Likely "float argument required, not NoneType"

                elif p[3].lower() == 'timeseries' or p[3].lower() == 'timeseriesprofile':
                    iptvq = Q()
                    qs_tsp = None
                    if 'time' in self.kwargs:
                        if self.kwargs['time'][0] is not None and self.kwargs['time'][1] is not None:
                            iptvq = Q(instantpoint__timevalue__gte = self.kwargs['time'][0]) & Q(instantpoint__timevalue__lte = self.kwargs['time'][1])
                            qs_tsp = self.qs.filter(plq & (timeSeriesQ | timeSeriesProfileQ) & iptvq).annotate(mintime=Min('instantpoint__timevalue'), 
                                                    maxtime=Max('instantpoint__timevalue')).select_related().values( 'name',
                                                    'simpledepthtime__nominallocation__depth', 'mintime', 'maxtime').order_by(
                                                    'simpledepthtime__nominallocation__depth').distinct()
                    if not qs_tsp:
                        qs_tsp = self.qs.filter(plq & (timeSeriesQ | timeSeriesProfileQ)).select_related().values( 
                                                'simpledepthtime__epochmilliseconds', 'simpledepthtime__depth', 'name',
                                                'simpledepthtime__nominallocation__depth').order_by('simpledepthtime__epochmilliseconds').distinct()

                    # Add to sdt hash date-time series organized by activity__name_nominallocation__depth key within a platform__name key
                    for sd in qs_tsp:
                        ##logger.debug('sd = %s', sd)
                        an_nd = '%s_%s' % (sd['name'], sd['simpledepthtime__nominallocation__depth'])
                        ##logger.debug('an_nd = %s', an_nd)
                        ##logger.debug('sd = %s', sd)
                        if 'simpledepthtime__epochmilliseconds' in sd:
                            try:
                                sdt[p[0]][an_nd].append( [sd['simpledepthtime__epochmilliseconds'], '%.2f' % sd['simpledepthtime__nominallocation__depth']] )
                            except KeyError:
                                sdt[p[0]][an_nd] = []                                    # First time seeing this activityName_nominalDepth, make it a list
                                if sd['simpledepthtime__nominallocation__depth']:
                                    sdt[p[0]][an_nd].append( [sd['simpledepthtime__epochmilliseconds'], '%.2f' % sd['simpledepthtime__nominallocation__depth']] )
                            except TypeError:
                                continue                                                 # Likely "float argument required, not NoneType"
    
                        else:
                            s_ems = int(1000 * to_udunits(sd['mintime'], 'seconds since 1970-01-01'))
                            e_ems = int(1000 * to_udunits(sd['maxtime'], 'seconds since 1970-01-01'))
                            try:
                                sdt[p[0]][an_nd].append( [s_ems, '%.2f' % sd['simpledepthtime__nominallocation__depth']] )
                                sdt[p[0]][an_nd].append( [e_ems, '%.2f' % sd['simpledepthtime__nominallocation__depth']] )
                            except KeyError:
                                sdt[p[0]][an_nd] = []                                    # First time seeing this activityName_nominalDepth, make it a list
                                if sd['simpledepthtime__nominallocation__depth']:
                                    sdt[p[0]][an_nd].append( [s_ems, '%.2f' % sd['simpledepthtime__nominallocation__depth']] )
                                    sdt[p[0]][an_nd].append( [e_ems, '%.2f' % sd['simpledepthtime__nominallocation__depth']] )
                            except TypeError:
                                continue                                                 # Likely "float argument required, not NoneType"

                elif p[3].lower() == 'trajectoryprofile':
                    iptvq = Q()
                    qs_tp = None
                    if 'time' in self.kwargs:
                        if self.kwargs['time'][0] is not None and self.kwargs['time'][1] is not None:
                            s_ems = time.mktime(datetime.strptime(self.kwargs['time'][0], '%Y-%m-%d %H:%M:%S').timetuple())*1000
                            e_ems = time.mktime(datetime.strptime(self.kwargs['time'][1], '%Y-%m-%d %H:%M:%S').timetuple())*1000
                            iptvq = Q(simpledepthtime__epochmilliseconds__gte = s_ems) & Q(simpledepthtime__epochmilliseconds__lte = e_ems)
                            qs_tp = self.qs.filter(plq & trajectoryProfileQ & iptvq).select_related().values( 'name', 'simpledepthtime__depth',
                                                    'simpledepthtime__nominallocation__depth', 'simpledepthtime__epochmilliseconds').order_by(
                                                    'simpledepthtime__nominallocation__depth', 'simpledepthtime__epochmilliseconds').distinct()
                    if not qs_tp:
                        qs_tp = self.qs.filter(plq & trajectoryProfileQ).select_related().values( 'name', 'simpledepthtime__depth',
                                                'simpledepthtime__nominallocation__depth', 'simpledepthtime__epochmilliseconds').order_by(
                                                'simpledepthtime__nominallocation__depth', 'simpledepthtime__epochmilliseconds').distinct()

                    # Add to sdt hash date-time series organized by activity__name_nominallocation__depth key within a platform__name key - use real depths
                    for sd in qs_tp:
                        ##logger.debug('sd = %s', sd)
                        an_nd = '%s_%s' % (sd['name'], sd['simpledepthtime__nominallocation__depth'])
                        ##logger.debug('an_nd = %s', an_nd)
                        if 'simpledepthtime__epochmilliseconds' in sd:
                            try:
                                sdt[p[0]][an_nd].append( [sd['simpledepthtime__epochmilliseconds'], '%.2f' % sd['simpledepthtime__depth']] )
                            except KeyError:
                                sdt[p[0]][an_nd] = []                                    # First time seeing this activityName_nominalDepth, make it a list
                                if sd['simpledepthtime__depth']:
                                    sdt[p[0]][an_nd].append( [sd['simpledepthtime__epochmilliseconds'], '%.2f' % sd['simpledepthtime__depth']] )
                            except TypeError:
                                continue                                                 # Likely "float argument required, not NoneType"
    

        return({'sdt': sdt, 'colors': colors})

    def getSimpleBottomDepthTime(self):
        '''
        Based on the current selected query criteria for activities, return the associated SimpleBottomDepth time series
        values as a 2-tuple list inside a 2 level hash of platform__name and activity__name.  Append a third value to the 
        x,y time series of a maximum depth (positive number in meters) so that Flot will fill downward. See:
        http://stackoverflow.com/questions/23790277/flot-fill-color-above-a-line-graph
        '''
        sbdt = {}
        maxDepth = 10971        # Max ocean depth 

        trajectoryQ = self._trajectoryQ()

        for plats in self.getPlatforms().values():
            for p in plats:
                plq = Q(platform__name = p[0])
                sbdt[p[0]] = {}
    
                if p[3].lower() == 'trajectory':
                    qs_traj = self.qs.filter(plq & trajectoryQ).values_list( 'simplebottomdepthtime__epochmilliseconds', 'simplebottomdepthtime__bottomdepth',
                                        'name').order_by('simplebottomdepthtime__epochmilliseconds')
                    # Add to sbdt hash date-time series organized by activity__name key within a platform__name key
                    # This will let flot plot the series with gaps between the surveys -- not connected
                    for s in qs_traj:
                        try:
                            sbdt[p[0]][s[2]].append( [s[0], '%.2f' % s[1], maxDepth] )
                        except KeyError:
                            sbdt[p[0]][s[2]] = []                                               # First time seeing activity__name, make it a list
                            if s[1] is not None:
                                sbdt[p[0]][s[2]].append( [s[0], '%.2f' % s[1], maxDepth] )      # Append first value, even if it is 0.0
                        except TypeError:
                            continue                                                            # Likely "float argument required, not NoneType"

        return({'sbdt': sbdt})

    #
    # The following set of private (_...) methods are for building the parametertime response
    #
    def _collectParameters(self, platform, pt, pa_units, is_standard_name, ndCounts, strides, colors):
        '''
        Get parameters for this platform and collect units in a parameter name hash, use standard_name if set and repair bad names.
        Return a tuple of pa_units, is_standard_name, ndCounts, and pt dictionaries.
        '''

        # Get parameters for this platform and collect units in a parameter name hash, use standard_name if set and repair bad names
        p_qs = models.Parameter.objects.using(self.dbname).filter(Q(activityparameter__activity__in=self.qs))
        logger.debug("self.kwargs['parametertimeplotid'] = %s", self.kwargs['parametertimeplotid'])
        if self.kwargs['parametertimeplotid']:
            p_qs = p_qs.filter(Q(id__in=self.kwargs['parametertimeplotid']))
        p_qs = p_qs.filter(activityparameter__activity__platform__name=platform[0]).distinct()
        for parameter in p_qs:
            unit = parameter.units

            # Get the number of nominal depths for this parameter
            nds =  models.NominalLocation.objects.using(self.dbname
                                    ).filter( Q(activity__in=self.qs),
                                              activity__platform__name=platform[0],
                                              measurement__measuredparameter__parameter=parameter
                                    ).values('depth').distinct().count()
            # Check if timeSeries plotting is requested for trajectory data
            plotTimeSeriesDepth = models.ParameterResource.objects.using(self.dbname).filter(parameter__name=parameter,
                                resource__name='plotTimeSeriesDepth').values_list('resource__value')
            
            if nds == 0 and not plotTimeSeriesDepth:
                continue

            if parameter.standard_name == 'sea_water_salinity':
                unit = 'PSU'
            if parameter.standard_name and parameter.standard_name.strip() != '':
                logger.debug('Parameter name "%s" has standard_name = %s', parameter.name, parameter.standard_name)
                pa_units[parameter.standard_name] = unit
                is_standard_name[parameter.standard_name] = True
                ndCounts[parameter.standard_name] = nds
                colors[parameter.standard_name] = parameter.id
                strides[parameter.standard_name] = {}
            else:
                logger.debug('Parameter name "%s" does not have a standard_name', parameter.name)
                pa_units[parameter.name] = unit
                is_standard_name[parameter.name] = False
                ndCounts[parameter.name] = nds
                colors[parameter.name] = parameter.id
                strides[parameter.name] = {}

            # Initialize pt dictionary of dictionaries with its keys
            if unit not in pt.keys():
                logger.debug('Initializing pt[%s] = {}', unit)
                pt[unit] = {}

        return (pa_units, is_standard_name, ndCounts, pt, colors, strides)

    def _getParameterTimeFromMP(self, qs_mp, pt, pa_units, a, p, is_standard_name, stride):
        '''
        Return hash of time series measuredparameter data with specified stride
        '''
        # See if timeSeries plotting is requested for trajectory data, e.g. BEDS
        plotTimeSeriesDepth = models.ParameterResource.objects.using(self.dbname).filter(parameter__name=p, 
                                resource__name='plotTimeSeriesDepth').values_list('resource__value')
        if not plotTimeSeriesDepth:
            # See if there is one for standard_name
            plotTimeSeriesDepth = models.ParameterResource.objects.using(self.dbname).filter(parameter__standard_name=p, 
                                    resource__name='plotTimeSeriesDepth').values_list('resource__value')

        # Order by nominal depth first so that strided access collects data correctly from each depth
        pt_qs_mp = qs_mp.order_by('measurement__nominallocation__depth', 'measurement__instantpoint__timevalue')[::stride]
        logger.debug('Adding time series of parameter = %s in key = %s', p, pa_units[p])
        for mp in pt_qs_mp:
            if not mp['datavalue']:
                continue

            tv = mp['measurement__instantpoint__timevalue']
            ems = int(1000 * to_udunits(tv, 'seconds since 1970-01-01'))
            nd = mp['measurement__depth']       # Will need to switch to mp['measurement__mominallocation__depth'] when
                                                # mooring microcat actual depths are put into mp['measurement__depth']
            ##if p == 'BED_DEPTH':
            ##    logger.debug('nd = %s, tv = %s', nd, tv)
            ##    raise Exception('DEBUG')        # Useful for examining queries in the postgresql log

            if plotTimeSeriesDepth:
                an_nd = "%s - %s starting @ %s m" % (p, a.name, plotTimeSeriesDepth[0][0],)
            else:
                an_nd = "%s - %s @ %s" % (p, a.name, nd,)
    
            try:
                pt[pa_units[p]][an_nd].append((ems, mp['datavalue']))
            except KeyError:
                pt[pa_units[p]][an_nd] = []
                pt[pa_units[p]][an_nd].append((ems, mp['datavalue']))

        return pt
        
    def _getParameterTimeFromAP(self, pt, pa_units, a, p):
        '''
        Return hash of time series min and max values for specified activity and parameter.  To be used when duration
        of an activity is less than the pixel width of the flot plot area.  This can occur for short event data sets
        such as from Benthic Event Detector deployments.
        '''

        aps = models.ActivityParameter.objects.using(self.dbname).filter(activity=a, parameter__name=p).values('min', 'max')

        start_ems = int(1000 * to_udunits(a.startdate, 'seconds since 1970-01-01'))
        end_ems = int(1000 * to_udunits(a.startdate, 'seconds since 1970-01-01'))

        pt[pa_units[p]][a.name] = [[start_ems, aps[0]['min']], [end_ems, aps[0]['max']]]

        return pt

    def _parameterInSelection(self, p, is_standard_name, parameterType=MEASUREDINSITU):
        '''
        Return True if parameter name is in the UI selection, either from constraints other than
        direct selection or if specifically selected in the UI.  
        '''
        isInSelection = False
        if is_standard_name[p]:
            if p in [parms[1] for parms in self.getParameters(parameterType)]:
                isInSelection = True
        else:
            if p in [parms[0] for parms in self.getParameters(parameterType)]:
                isInSelection = True

        if not isInSelection:
            if self.kwargs['measuredparametersgroup']:
                if p in self.kwargs['measuredparametersgroup']:
                    isInSelection = True
                else:
                    isInSelection = False

        return isInSelection 

    def _buildParameterTime(self, pa_units, is_standard_name, ndCounts, pt, strides, pt_qs_mp):
        '''
        Build structure of timeseries/timeseriesprofile parameters organized by units
        '''
        PIXELS_WIDE = 800                   # Approximate pixel width of parameter-time-flot window
        units = {}

        # Build units hash of parameter names for labeling axes in flot
        for p,u in pa_units.iteritems():
            logger.debug('is_standard_name = %s.  p, u = %s, %s', is_standard_name, p, u)
            if not self._parameterInSelection(p, is_standard_name):
                logger.debug('Parameter is not in selection')
                continue

            try:
                units[u] = units[u] + ' ' + p
            except KeyError:
                units[u] = p

            # Apply either parameter name or standard_name to MeasuredParameter and Activity query sets
            if is_standard_name[p]:
                qs_mp = pt_qs_mp.filter(parameter__standard_name=p)
                qs_awp = self.qs.filter(activityparameter__parameter__standard_name=p)
            else:
                qs_mp = pt_qs_mp.filter(parameter__name=p)
                qs_awp = self.qs.filter(activityparameter__parameter__name=p)

            qs_awp = qs_awp.filter(Q(activityresource__resource__value__icontains='timeseries') |
                                   Q(activityparameter__parameter__parameterresource__resource__name__icontains='plotTimeSeriesDepth')).distinct()

            try:
                secondsperpixel = self.kwargs['secondsperpixel'][0]
            except IndexError:
                secondsperpixel = 1500                              # Default is a 2-week view  (86400 * 14 / 800)
            except KeyError:
                secondsperpixel = 1500                              # Default is a 2-week view  (86400 * 14 / 800)

            logger.debug('--------------------p = %s, u = %s, is_standard_name[p] = %s', p, u, is_standard_name[p])
            
            # Select each time series by Activity and test against secondsperpixel for deciding on min & max or stride selection
            if not ndCounts[p]:
                ndCounts[p] = 1         # Trajectories with plotTimeSeriesDepth will not have a nominal depth, set to 1 for calculation below
            for a in qs_awp:
                qs_mp_a = qs_mp.filter(measurement__instantpoint__activity__name=a.name)
                ad = (a.enddate-a.startdate)
                aseconds = ad.days * 86400 + ad.seconds
                logger.debug('a.name = %s, a.startdate = %s, a.enddate %s, aseconds = %s, secondsperpixel = %s', a.name, a.startdate, a.enddate, aseconds, secondsperpixel)
                if float(aseconds) > float(secondsperpixel):
                    # Multiple points of this activity can be displayed in the flot, get an appropriate stride
                    logger.debug('PIXELS_WIDE = %s, ndCounts[p] = %s', PIXELS_WIDE, ndCounts[p])
                    stride = qs_mp_a.count() / PIXELS_WIDE / ndCounts[p]        # Integer factors -> integer result
                    if stride < 1:
                        stride = 1
                    logger.debug('Getting timeseries from MeasuredParameter table with stride = %s', stride)
                    strides[p][a.name] = stride
                    logger.debug('Adding timeseries for p = %s, a = %s', p, a)
                    pt = self._getParameterTimeFromMP(qs_mp_a, pt, pa_units, a, p, is_standard_name, stride)
                else:
                    # Construct just two points for this activity-parameter using the min & max from the AP table
                    pt = self._getParameterTimeFromAP(pt, pa_units, a, p)

        return (pt, units, strides)

    def getParameterTime(self):
        '''
        Based on the current selected query criteria for activities, return the associated MeasuredParameter datavalue time series
        values as a 2-tuple list inside a 3 level hash of featureType, units, and an "activity__name + nominal depth" key
        for each line to be drawn by flot.  The MeasuredParameter queries here can be costly.  Only perform them if the
        UI has request only 'parametertime' or if the Parameter tab is active in the UI as indicated by 'parametertab' in self.kwargs.
        If part of the larger SummaryData request then return the structure with just counts set - a much cheaper query.
        '''
        pt = {}
        units = {}
        colors = {}
        strides = {}
        pa_units = {}
        is_standard_name = {}
        ndCounts = {}
        colors = {}
        counts = 0

        # Look for platforms that have featureTypes ammenable for Parameter time series visualization
        for plats in self.getPlatforms().values():
            for platform in plats:
                timeSeriesParmCount = 0
                trajectoryParmCount = 0
                if platform[3].lower() == 'timeseriesprofile' or platform[3].lower() == 'timeseries':
                    # Do cheap query to count the number of timeseriesprofile or timeseries parameters
                    timeSeriesParmCount = models.Parameter.objects.using(self.dbname).filter(
                                        activityparameter__activity__activityresource__resource__name__iexact='featureType',
                                        activityparameter__activity__activityresource__resource__value__iexact=platform[3].lower()
                                        ).distinct().count()
                elif platform[3].lower() == 'trajectory':
                    # Count trajectory Parameters for which timeSeries plotting has been requested
                    trajectoryParmCount = models.Parameter.objects.using(self.dbname).filter(
                                        activityparameter__activity__activityresource__resource__name__iexact='featureType',
                                        activityparameter__activity__activityresource__resource__value__iexact=platform[3].lower(),
                                        parameterresource__resource__name__iexact='plotTimeSeriesDepth',
                                        ).distinct().count()
                counts += timeSeriesParmCount + trajectoryParmCount
                if counts:
                    if 'parametertime' in self.kwargs['only'] or self.kwargs['parametertab']:
                        # Initialize structure organized by units for parameters left in the selection 
                        logger.debug('Calling self._collectParameters() with platform = %s', platform)
                        pa_units, is_standard_name, ndCounts, pt, colors, strides = self._collectParameters(platform, pt, 
                                                                    pa_units, is_standard_name, ndCounts, strides, colors)
  
        if pa_units: 
            # The base MeasuredParameter query set for existing UI selections
            if not self.mpq.qs_mp:
                self.mpq.buildMPQuerySet(*self.args, **self.kwargs)
                self.mpq.initialQuery = self.initialQuery

            # Perform more expensive query: start with no_order version of the MeasuredParameter query set
            pt_qs_mp = self.mpq.qs_mp_no_order
            
            logger.debug('Before self._buildParameterTime: pt = %s', pt.keys()) 
            pt, units, strides = self._buildParameterTime(pa_units, is_standard_name, ndCounts, pt, strides, pt_qs_mp)
            logger.debug('After self._buildParameterTime: pt = %s', pt.keys()) 

        return({'pt': pt, 'units': units, 'counts': counts, 'colors': colors, 'strides': strides})

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
                ems = int(1000 * to_udunits(s[0], 'seconds since 1970-01-01'))
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

    def getNetTowDepthTime(self):
        '''
        Based on the current selected query criteria for activities, return the associated NetTow time series
        values as a 2 2-tuple list.  Theses are like SampleDepthTime, but have a start and end time/depth.
        The UI uses a different glyph which is why these are delivered in a separate structure.
        The convention for NetTows is for one Sample per activity, therefore we can examine the attributes
        of the activity to get the start and end time and min and max depths. 
        '''
        nettows = []
        nettow = models.SampleType.objects.filter(name__contains=NETTOW)
        if self.getSampleQS() and nettow:
            qs = self.getSampleQS().filter(sampletype=nettow).values_list(
                                    'instantpoint__timevalue', 
                                    'depth',
                                    'instantpoint__activity__name',
                                    'name',
                                    'instantpoint__activity__startdate',
                                    'instantpoint__activity__enddate',
                                    'instantpoint__activity__mindepth',
                                    'instantpoint__activity__maxdepth',
                                ).order_by('instantpoint__timevalue')
            for s in qs:
                s_ems = int(1000 * to_udunits(s[4], 'seconds since 1970-01-01'))
                e_ems = int(1000 * to_udunits(s[5], 'seconds since 1970-01-01'))
                # Kludgy handling of activity names - flot needs 2 items separated by a space to handle sample event clicking
                if (s[2].find('_decim') != -1):
                    label = '%s %s' % (s[2].split('_decim')[0], s[3],)              # Lop off '_decim.nc (stride=xxx)' part of name
                elif (s[2].find(' ') != -1):
                    label = '%s %s' % (s[2].split(' ')[0], s[3],)                   # Lop off everything after a space in the activity name
                else:
                    label = '%s %s' % (s[2], s[3],)                                 # Show entire Activity name & sample name

                rec = {'label': label, 'data': [[s_ems, '%.2f' % s[7]], [e_ems, '%.2f' % s[6]]]}
                nettows.append(rec)

        return(nettows)


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
                if np.isnan(aph['binlo']) or np.isnan(aph['binhi']):
                    continue
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

                    ##logger.debug('pa.name = %s, aname = %s', pa.name, aph['activityparameter__activity__name'])

            # Unwind the platformList to get activities by platform name
            for an, pnList in platformList.iteritems():
                ##logger.debug('an = %s, pnList = %s', an, pnList)
                for pn in pnList:
                    try:
                        activityList[pn].append(an)
                    except KeyError:
                        activityList[pn] = []
                        activityList[pn].append(an)

            # Build the final data structure organized by platform -> activity
            plHash = {}
            for plat in activityList.keys():
                ##logger.debug('plat = %s', plat)
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
        for plats in self.getPlatforms().values():
            for p in plats:
                r,g,b = (p[2][:2], p[2][2:4], p[2][4:])
                rgbas[p[0]] = 'rgba(%d, %d, %d, 0.4)' % (int(r,16), int(g,16), int(b,16))

        return {'histdata': aphHash, 'rgbacolors': rgbas, 'parameterunits': pUnits}

    def getParameterPlatformDatavaluePNG(self):
        '''
        Called when user interface has selected just one Parameter and just one Platform, in which case
        produce a depth-time section plot for overlay on the flot plot.  Return a png image file name for inclusion
        in the AJAX response.
        '''
        # Check for parameter-plot-radio button being selected, which inherently ensures that a
        # single parameter name is selected for plotting.  The client code will also ensure that
        # extra platforms measuring the same parameter name are filtered out in the selection so
        # there's no need for this server code to check for just one platform in the selection.
        parameterID = None
        platformName = None
        logger.debug('self.kwargs = %s', self.kwargs)
        if 'parameterplot' in self.kwargs:
            if self.kwargs['parameterplot'][0]:
                parameterID = self.kwargs['parameterplot'][0]
                parameter = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=parameterID)
                parameterGroups = getParameterGroups(self.request.META['dbAlias'], parameter)
            if self.kwargs['parameterplot'][1]:
                platformName = self.kwargs['parameterplot'][1]
        if not parameterID or not platformName:
            # With Plot radio button, must have parameterID and platformName
            return None, None, 'Problem with getting parameter-plot-radio button info'

        logger.debug('Instantiating Viz.MeasuredParameter............................................')
        
        self.mpq.buildMPQuerySet(*self.args, **self.kwargs)

        if SAMPLED in parameterGroups:
            # The fourth item should be for SampledParameter if that is the group of the Parameter
            cp = MeasuredParameter(self.kwargs, self.request, self.qs, self.mpq.qs_sp_no_order,
                                    self.getParameterMinMax(pid=parameterID)['plot'], self.getSampleQS(), platformName, 
                                    parameterID, parameterGroups)
        else:
            cp = MeasuredParameter(self.kwargs, self.request, self.qs, self.mpq.qs_mp_no_order,
                                    self.getParameterMinMax(pid=parameterID)['plot'], self.getSampleQS(), platformName, 
                                    parameterID, parameterGroups)

        return cp.renderDatavaluesForFlot()

    def getParameterParameterPNG(self):
        '''
        If at least the X and Y radio buttons are checked produce a scatter plot for delivery back to the client
        '''
        plotResults = None
        if (self.kwargs.has_key('parameterparameter')):
            px = self.kwargs['parameterparameter'][0]
            py = self.kwargs['parameterparameter'][1]
            pc = self.kwargs['parameterparameter'][3]

            if (px and py):
                # PQuery is used here so as to combine Measured and Sampled Parameters
                if not self.pq.qs_mp:
                    self.pq.buildPQuerySet(*self.args, **self.kwargs)

                # We have enough information to generate a 2D scatter plot
                ##if not self.pp:     # ...png always gets called before ...x3d - unless we change the key names...
                pMinMax = { 'x': self.getParameterMinMax(px, percentileAggregateType='extrema')['plot'], 
                            'y': self.getParameterMinMax(py, percentileAggregateType='extrema')['plot'], 
                            'c': self.getParameterMinMax(pc)['plot']}
                logger.debug('pMinMax = %s', pMinMax)
                if not pMinMax['x'] or not pMinMax['y']:
                    return '', 'Selected x and y axis parameters are not in filtered selection.'
                self.pp = ParameterParameter(self.request, {'x': px, 'y': py, 'c': pc}, self.mpq, self.pq, pMinMax)
                try:
                    ppPngFile, infoText, sql = self.pp.make2DPlot()
                except PPDatabaseException as e:
                    return None, e.message, e.sql

                plotResults = ppPngFile, infoText, sql

        return plotResults

    def getParameterParameterX3D(self):
        '''
        If at least the X, Y, and Z radio buttons are checked produce an X3D response for delivery back to the client
        '''
        x3dDict = None
        if (self.kwargs.has_key('parameterparameter')):
            px = self.kwargs['parameterparameter'][0]
            py = self.kwargs['parameterparameter'][1]
            pz = self.kwargs['parameterparameter'][2]
            pc = self.kwargs['parameterparameter'][3]
            logger.debug('px = %s, py = %s, pz = %s, pc = %s', px, py, pz, pc)

            if (px and py and pz):
                if not self.pq.qs_mp:
                    self.pq.buildPQuerySet(*self.args, **self.kwargs)

                # We have enough information to generate X3D XML
                pMinMax = { 'x': self.getParameterMinMax(px, percentileAggregateType='extrema')['plot'], 
                            'y': self.getParameterMinMax(py, percentileAggregateType='extrema')['plot'], 
                            'z': self.getParameterMinMax(pz, percentileAggregateType='extrema')['plot'], 
                            'c': self.getParameterMinMax(pc)['plot'] }
                
                if not pMinMax['x'] or not pMinMax['y'] or not pMinMax['z']:
                    return '', 'Selected x, y, z, c Parameters not in filtered selection.'

                logger.debug('Instantiating Viz.PropertyPropertyPlots for X3D............................................')
                self.pp = ParameterParameter(self.request, {'x': px, 'y': py, 'z': pz, 'c': pc}, self.mpq, self.pq, pMinMax)
                try:
                    x3dDict = self.pp.makeX3D()
                except DatabaseError as e:
                    return '', e
                try:
                    x3dDict['sql'] += ';'
                except TypeError:
                    return '', 'Selected x, y, z, c Parameters not in filtered selection.'
            
        return x3dDict

    def getMeasuredParameterX3D(self):
        '''Returns dictionary of X3D elements for rendering by X3DOM
        '''
        x3dDict = None
        if getShow_Geo_X3D_Data(self.kwargs):
            if 'parameterplot' in self.kwargs:
                if self.kwargs['parameterplot'][0]:
                    parameterID = self.kwargs['parameterplot'][0]
                    parameterGroups = getParameterGroups(self.request.META['dbAlias'], 
                              models.Parameter.objects.using(self.request.META['dbAlias']
                              ).get(id=parameterID))
                    try:
                        count = self.mpq.count()
                        logger.debug('count = %s', count)
                    except AttributeError:
                        logger.debug('Calling self.mpq.buildMPQuerySet()')
                        self.mpq.buildMPQuerySet(*self.args, **self.kwargs)
                    else:
                        logger.debug('self.mpq.qs_mp = %s', self.mpq.qs_mp)
                    try:
                        platformName = self.kwargs['parameterplot'][1]
                    except IndexError as e:
                        logger.warn(e)
                        platformName = None

                    logger.debug('Getting data values in X3D for platformName = %s', platformName) 
                    mpdv  = MeasuredParameter(self.kwargs, self.request, self.qs, self.mpq.qs_mp, 
                            self.getParameterMinMax()['plot'], self.getSampleQS(), 
                            platformName, parameterID, parameterGroups)
                    # Default vertical exaggeration is 10x
                    x3dDict = mpdv.dataValuesX3D(float(self.request.GET.get('ve', 10)))
            
        return x3dDict

    def getPlatformAnimation(self):
        '''
        Based on the current selected query criteria for activities, 
        return the associated PlatformAnimation time series of X3D scene graph.
        If roll, pitch and yaw exist as the platform standard names include
        orienation angles, otherwise returns just the position animation scene.
        '''
        orientDict = {}
        if self.request.GET.get('showplatforms', False):
            try:
                count = self.mpq.count()
            except AttributeError:
                self.mpq.buildMPQuerySet(*self.args, **self.kwargs)

            # Test if there are any X3D platform models in the selection
            platformsHavingModels = {pr.platform for pr in models.PlatformResource.objects.using(
                    self.dbname).filter(resource__resourcetype__name=X3DPLATFORMMODEL, 
                    platform__in=[a.platform for a in self.qs])}
            platforms_trajectories = {ar.activity.platform for ar in models.ActivityResource.objects.using(
                    self.dbname).filter(resource__name='featureType', resource__value='trajectory', 
                    activity__platform__in=[a.platform for a in self.qs])}
            platforms_to_animate = platformsHavingModels & platforms_trajectories
            if platforms_to_animate:
                # Use qs_mp_no_parm QuerySet as it contains roll, pitch, and yaw values
                mppa = PlatformAnimation(platforms_to_animate, self.kwargs, 
                        self.request, self.qs, self.mpq.qs_mp_no_parm)
                # Default vertical exaggeration is 10x and default geoorigin is empty string
                orientDict = mppa.platformAnimationDataValuesForX3D(
                                float(self.request.GET.get('ve', 10)), 
                                self.request.GET.get('geoorigin', ''), 
                                scale=1000, speedup=10)
            
        return orientDict

    def getParameterPlatforms(self):
        '''
        Retrun hash of parmameter ids (keys) and the platforms (a list) that measured/sampled them
        '''
        ppHash = {}
        for ap in models.ActivityParameter.objects.using(self.dbname).filter(activity__in=self.qs).values('parameter__id', 'activity__platform__name').distinct():
            try:
                ppHash[ap['parameter__id']].append(ap['activity__platform__name'])
            except KeyError:
                ppHash[ap['parameter__id']] = []
                ppHash[ap['parameter__id']].append(ap['activity__platform__name'])
    
        return ppHash

    def getX3DTerrains(self):
        '''
        Query Resources to get any X3D Terrain information for this Campaign and return as a hash for the STOQS UI to use
        '''
        x3dtHash = {}
        try:
            for r in models.Resource.objects.using(self.dbname).filter(resourcetype__name='x3dterrain').all():
                try:
                    x3dtHash[r.uristring][r.name] = r.value
                except KeyError:
                    x3dtHash[r.uristring] = {}
                    x3dtHash[r.uristring][r.name] = r.value
        except DatabaseError as e:
            logger.warn('No resourcetype__name of x3dterrain in %s: %s', self.dbname, e)

        return x3dtHash

    def getX3DPlaybacks(self):
        '''
        Query Resources to get any X3D Playback information for the Activities remaining in the selection
        '''
        x3dpHash = {}
        try:
            for r in models.Resource.objects.using(self.dbname).filter(resourcetype__name='x3dplayback').values(
                        'uristring', 'name', 'value', 'activityresource__activity__name'):
                ms = models.Measurement.objects.using(self.dbname).filter(instantpoint__activity__name=r['activityresource__activity__name'])
                try:
                    x3dpHash[r['uristring']][r['name']] = r['value']
                    x3dpHash[r['uristring']]['startGeoCoords'] = '%s %s %s' % (ms[0].geom.y, ms[0].geom.x, -ms[0].depth)
                except KeyError:
                    x3dpHash[r['uristring']] = {}
                    x3dpHash[r['uristring']][r['name']] = r['value']
                    x3dpHash[r['uristring']]['startGeoCoords'] = '%s %s %s' % (ms[0].geom.y, ms[0].geom.x, -ms[0].depth)
        except DatabaseError as e:
            logger.warn('No resourcetype__name of x3dplayback in %s: %s', self.dbname, e)

        return x3dpHash

    def getResources(self):
        '''
        Query ActivityResources for Resources remaining in Activity selection
        '''
        netcdfHash = {}
        # Simple name/value attributes
        for ar in models.ActivityResource.objects.using(self.dbname).filter(activity__in=self.qs
                        ,resource__name__in=['title', 'summary', 'opendap_url']
                        ).values('activity__platform__name', 'activity__name', 'activity__comment', 'resource__name', 'resource__value'):
            try:
                netcdfHash[ar['activity__platform__name']][ar['activity__name']][ar['resource__name']] = ar['resource__value']
                netcdfHash[ar['activity__platform__name']][ar['activity__name']]['comment'] = ar['activity__comment']
            except KeyError:
                try:
                    netcdfHash[ar['activity__platform__name']][ar['activity__name']] = {}
                except KeyError:
                    netcdfHash[ar['activity__platform__name']] = {}
                    netcdfHash[ar['activity__platform__name']][ar['activity__name']] = {}

                netcdfHash[ar['activity__platform__name']][ar['activity__name']][ar['resource__name']] = ar['resource__value']
                netcdfHash[ar['activity__platform__name']][ar['activity__name']]['comment'] = ar['activity__comment']

        # Quick Look plots
        qlHash = {}
        for ar in models.ActivityResource.objects.using(self.dbname).filter(activity__in=self.qs, resource__resourcetype__name='quick_look').values(
                        'activity__platform__name', 'activity__name', 'resource__name', 'resource__uristring'):
            try:
                qlHash[ar['activity__platform__name']][ar['activity__name']][ar['resource__name']] = ar['resource__uristring']
            except KeyError:
                try:
                    qlHash[ar['activity__platform__name']][ar['activity__name']] = {}
                except KeyError:
                    qlHash[ar['activity__platform__name']] = {}
                    qlHash[ar['activity__platform__name']][ar['activity__name']] = {}

                qlHash[ar['activity__platform__name']][ar['activity__name']][ar['resource__name']] = ar['resource__uristring']

        return {'netcdf': netcdfHash, 'quick_look': qlHash}

    def getAttributes(self):
        '''
        Query for "Attributes" which are specific ResourceTypes or fields of other classes. Initially for tagged measurements
        and for finding comments about Samples, but can encompass any other way a STOQS database may be filtered os searched.
        '''
        measurementHash = {}

        sources = models.ResourceResource.objects.using(self.dbname).filter(toresource__name=COMMANDLINE
                                ).values_list('fromresource__resourcetype__name', 'toresource__value').distinct()

        if sources:
            measurementHash['commandlines'] = dict((s[0], s[1]) for s in sources)

        for mpr in models.MeasuredParameterResource.objects.using(self.dbname).filter(activity__in=self.qs
                        ,resource__name__in=[LABEL]).values( 'resource__resourcetype__name', 'resource__value', 
                        'resource__id').distinct().order_by('resource__value'):

            # Include all description resources associated with this label
            descriptions = ' '.join(models.ResourceResource.objects.using(self.dbname).filter(fromresource__id=mpr['resource__id'], 
                            toresource__name=DESCRIPTION).values_list('toresource__value', flat=True))
            try:
                measurementHash[mpr['resource__resourcetype__name']].append((mpr['resource__id'], mpr['resource__value'], descriptions))
            except KeyError:
                measurementHash[mpr['resource__resourcetype__name']] = []
                measurementHash[mpr['resource__resourcetype__name']].append((mpr['resource__id'], mpr['resource__value'], descriptions))

        return {'measurement': measurementHash}

    #
    # Methods that generate Q objects used to populate the query.
    #    
        
    def _sampledparametersgroupQ(self, parameterid, fromTable='Activity'):
        '''
        Build a Q object to be added to the current queryset as a filter.  This should 
        ensure that our result doesn't contain any parameter names that were not selected.
        We use id for sampledparametersgroup as the name may contain special characters.
        '''
        q = Q()
        if parameterid is None:
            return q
        else:
            if fromTable == 'Activity':
                q = Q(activityparameter__parameter__id__in=parameterid)
            elif fromTable == 'Sample':
                q = Q(sampledparameter__parameter__id__in=parameterid)
            elif fromTable == 'ActivityParameter':
                q = Q(parameter__id__in=parameterid)
            elif fromTable == 'ActivityParameterHistogram':
                q = Q(activityparameter__parameter__id__in=parameterid)
        return q

    def _measuredparametersgroupQ(self, parametername, fromTable='Activity'):
        '''
        Build a Q object to be added to the current queryset as a filter.  This should 
        ensure that our result doesn't contain any parameter names that were not selected.
        '''
        q = Q()
        if parametername is None:
            return q
        else:
            if fromTable == 'Activity':
                q = Q(activityparameter__parameter__name__in=parametername)
            elif fromTable == 'Sample':
                # Use sub-query to find all Samples from Activities that are in the existing Activity queryset
                # Note: must do the monkey patch in __init__() so that Django's django/db/models/sql/query.py 
                # statement "sql, params = self.get_compiler(DEFAULT_DB_ALIAS).as_sql()" uses the right connection.
                # This is not a Django bug according to source code comment at:
                #    https://github.com/django/django/blob/master/django/db/models/sql/query.py
                q = Q(instantpoint__activity__in=self.qs)
            elif fromTable == 'ActivityParameter':
                # Use sub-query to restrict ActivityParameters to those that are in the list of Activities in the selection
                q = Q(activity__in=self.qs)
            elif fromTable == 'ActivityParameterHistogram':
                # Use sub-query to find all ActivityParameterHistogram from Activities that are in the existing Activity queryset
                q = Q(activityparameter__activity__in=self.qs)
        return q

    def _parameterstandardnameQ(self, parameterstandardname, fromTable='Activity'):
        '''
        Build a Q object to be added to the current queryset as a filter.  This should 
        ensure that our result doesn't contain any parameter standard_names that were not selected.
        '''
        q = Q()
        if parameterstandardname is None:
            return q
        else:
            if fromTable == 'Activity':
                q = Q(activityparameter__parameter__standard_name__in=parameterstandardname)
            elif fromTable == 'Sample':
                # Use sub-query to find all Samples from Activities that are in the existing Activity queryset
                q = Q(instantpoint__activity__in=self.qs)
            elif fromTable == 'ActivityParameter':
                q = Q(activity__in=self.qs)
            elif fromTable == 'ActivityParameterHistogram':
                # Use sub-query to find all ActivityParameterHistogram from Activities that are in the existing Activity queryset
                q = Q(activityparameter__activity__in=self.qs)
        return q

    def _platformsQ(self, platforms, fromTable='Activity'):
        '''
        Build a Q object to be added to the current queryset as a filter.  This will ensure that we
        only generate the other values/sets for platforms that were selected.
        '''
        q = Q()
        if platforms is None:
            return q
        else:
            if fromTable == 'Activity':
                q = Q(platform__name__in=platforms)
            elif fromTable == 'Sample':
                # Use sub-query to find all Samples from Activities that are in the existing Activity queryset
                q = Q(instantpoint__activity__in=self.qs)
            elif fromTable == 'ActivityParameter':
                q = Q(activity__in=self.qs)
            elif fromTable == 'ActivityParameterHistogram':
                # Use sub-query to find all ActivityParameterHistogram from Activities that are in the existing Activity queryset
                q = Q(activityparameter__activity__in=self.qs)
        return q    
    
    def _timeQ(self, times, fromTable='Activity'):
        '''
        Build a Q object to be added to the current queryset as a filter.  This ensures that we limit
        things down based on the time range selected by the user.
        '''
        q = Q()
        if not times:
            return q
        if times[0] is not None:
            if fromTable == 'Activity':
                q = Q(enddate__gte=times[0])
            elif fromTable == 'Sample':
                q = Q(instantpoint__timevalue__gte=times[0])
            elif fromTable == 'ActivityParameter':
                q = Q(activity__enddate__gte=times[0])
            elif fromTable == 'ActivityParameterHistogram':
                q = Q(activityparameter__activity__enddate__gte=times[0])
        if times[1] is not None:
            if fromTable == 'Activity':
                q = q & Q(startdate__lte=times[1])
            elif fromTable == 'Sample':
                q = q & Q(instantpoint__timevalue__lte=times[1])
            elif fromTable == 'ActivityParameter':
                q = q & Q(activity__startdate__lte=times[1])
            elif fromTable == 'ActivityParameterHistogram':
                q = q & Q(activityparameter__activity__startdate__lte=times[1])
        return q
    
    def _depthQ(self, depth, fromTable='Activity'):
        '''
        Build a Q object to be added to the current queryset as a filter.  Once again, we want
        to make sure that we only generate the "leftover" components based on the selected depth
        range.
        '''
        q = Q()
        if not depth:
            return q
        if depth[0] is not None:
            if fromTable == 'Activity':
                q = Q(maxdepth__gte=depth[0])
            elif fromTable == 'Sample':
                q = Q(depth__gte=depth[0])
            elif fromTable == 'ActivityParameter':
                q = Q(activity__maxdepth__gte=depth[0])
            elif fromTable == 'ActivityParameterHistogram':
                q = Q(activityparameter__activity__maxdepth__gte=depth[0])
        if depth[1] is not None:
            if fromTable == 'Activity':
                q = q & Q(mindepth__lte=depth[1])
            elif fromTable == 'Sample':
                q = q & Q(depth__lte=depth[1])
            elif fromTable == 'ActivityParameter':
                q = q & Q(activity__mindepth__lte=depth[1])
            elif fromTable == 'ActivityParameterHistogram':
                q = q & Q(activityparameter__activity__mindepth__lte=depth[1])
        return q

    def _mplabelsQ(self, resourceids, fromTable='Activity'):
        '''
        Build a Q object to be added to the current queryset as a filter.  This will ensure that we
        only generate the other values/sets for attributes (initially resources that have names of 'label' 
        that are MeasuredParameter labels) that were selected.
        '''
        q = Q()
        if not resourceids:
            return q
        else:
            if fromTable == 'Activity':
                q = Q(id__in=models.MeasuredParameterResource.objects.using(self.dbname).filter(
                                                    resource__id__in=resourceids).values_list('activity__id').distinct())
            elif fromTable == 'ActivityParameter':
                q = Q(activity__id__in=models.MeasuredParameterResource.objects.using(self.dbname).filter(
                                                    resource__id__in=resourceids).values_list('activity__id').distinct())

        return q    

    def _trajectoryQ(self):
        '''
        Return Q object that is True if the activity is of featureType trajectory
        '''
        # Restrict selection to Activities that are trajectories.  Can have pre CF-1.6 UCDD and CF-1.6 and later metadata.
        udcc_q1 = Q(activityresource__resource__name__iexact='thredds_data_type') & Q(activityresource__resource__value__iexact='Trajectory')
        udcc_q2 = Q(activityresource__resource__name__iexact='cdm_data_type') & Q(activityresource__resource__value__iexact='trajectory')
        udcc_q3 = Q(activityresource__resource__name__iexact='CF%3afeatureType') & Q(activityresource__resource__value__iexact='trajectory')
        udcc_q4 = Q(activityresource__resource__name__iexact='CF_featureType') & Q(activityresource__resource__value__iexact='trajectory')
        cf16_q = Q(activityresource__resource__name__iexact='featureType') & Q(activityresource__resource__value__iexact='trajectory')

        q = (udcc_q1 | udcc_q2 | udcc_q3 | udcc_q4 | cf16_q)
    
        return q

    def _timeSeriesQ(self):
        '''
        Return Q object that is True if the activity is of featureType timeSeries
        '''
        # Restrict selection to Activities that are trajectories.  Can have pre CF-1.6 UCDD and CF-1.6 and later metadata.
        udcc_q1 = Q(activityresource__resource__name__iexact='thredds_data_type') & Q(activityresource__resource__value__iexact='station')
        udcc_q2 = Q(activityresource__resource__name__iexact='cdm_data_type') & Q(activityresource__resource__value__iexact='station')
        cf16_q = Q(activityresource__resource__name__iexact='featureType') & Q(activityresource__resource__value__iexact='timeSeries')

        q = (udcc_q1 | udcc_q2 | cf16_q)
    
        return q

    def _timeSeriesProfileQ(self):
        '''
        Return Q object that is True if the activity is of featureType timeSeries
        '''
        # Restrict selection to Activities that are trajectories.  Can have pre CF-1.6 UCDD and CF-1.6 and later metadata.
        udcc_q1 = Q(activityresource__resource__name__iexact='thredds_data_type') & Q(activityresource__resource__value__iexact='station')
        udcc_q2 = Q(activityresource__resource__name__iexact='cdm_data_type') & Q(activityresource__resource__value__iexact='station')
        cf16_q = Q(activityresource__resource__name__iexact='featureType') & Q(activityresource__resource__value__iexact='timeSeriesProfile')

        q = (udcc_q1 | udcc_q2 | cf16_q)
    
        return q

    def _trajectoryProfileQ(self):
        '''
        Return Q object that is True if the activity is of featureType timeSeries
        '''
        # Restrict selection to Activities that are trajectoryProfiles - a featureType new in CF-1.6
        cf16_q = Q(activityresource__resource__name__iexact='featureType') & Q(activityresource__resource__value__iexact='trajectoryProfile')

        q = (cf16_q)
    
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

    def getActivityGeoQuery(self, Q_object = None, pointFlag=False):
        '''
        This method generates a string that can be put into a Mapserver mapfile DATA statment.
        It is for returning Activities.  If @param pointFlag is True then postgresifySQL() will
        deliver the mappoint field as geom, otherwise it will deliver maptrack (trajectory) as geom.
        '''
        qs = self.qs

        # Add any more filters (Q objects) if specified
        if Q_object:
            qs = qs.filter(Q_object)

        # Query for mapserver
        geo_query = 'geom from (%s) as subquery using unique gid using srid=4326' % postgresifySQL(qs.query, pointFlag).rstrip()
        
        return geo_query

    def getSampleGeoQuery(self, Q_object = None):
        '''
        This method generates a string that can be put into a Mapserver mapfile DATA statment.
        It is for returning Samples.
        '''
        qs = self.sample_qs
        if not qs:
            return ''

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

        extent.transform(self.spherical_mercator_srid)
        return extent

    def getExtent(self, srid=4326, outputSRID=spherical_mercator_srid):
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
                pass
                ##logger.debug('Field %s is Null in Activity GeoQuerySet: %s', geom_field, str(self.qs) )

        # Append the Sample geometries 
        try:
            sqs = self.getSampleQS()
            extentList.append(sqs.extent(field_name='geom'))
        except:
            logger.debug('Could not get an extent for Sample GeoQuerySet')

        # Take the union of all geometry types found in Activities and Samples
        logger.debug("Collected %d geometry extents from Activities and Samples", len(extentList))
        if extentList:
            logger.debug('extentList = %s', extentList)

            # Initialize geom_union with first not None extent 
            for index, ext in enumerate(extentList):
                if ext is not None:
                    geom_union = fromstr('LINESTRING (%s %s, %s %s)' % ext, srid=srid)
                    break

            # Union additional extents
            for extent in extentList[index:]:
                if extent is not None:
                    if extent[0] == extent[2] and extent[1] == extent[3]:
                        logger.debug('Unioning extent = %s as a POINT', extent)
                        geom_union = geom_union.union(fromstr('POINT (%s %s)' % extent[:2], srid=srid))
                    else:
                        logger.debug('Unioning extent = %s as a LINESTRING', extent)
                        geom_union = geom_union.union(fromstr('LINESTRING (%s %s, %s %s)' % extent, srid=srid))

            # Aggressive try/excepts done here for better reporting on the production servers
            try:
                logger.debug('Final geom_union = %s', geom_union)
            except UnboundLocalError:
                logger.exception('geom_union could not be set from extentList = %s', extentList)
                return ([], None, None)

            try:
                geomstr = 'LINESTRING (%s %s, %s %s)' % geom_union.extent
            except TypeError:
                logger.exception('Tried to get extent for self.qs.query =  %s, but failed. Check the database loader and make sure a geometry type (maptrack or mappoint) is assigned for each activity.', str(self.qs.query))
            except ValueError:
                logger.exception('Tried to get extent for self.qs.query =  %s, but failed. Check the database loader and make sure a geometry type (maptrack or mappoint) is assigned for each activity.', str(self.qs.query))
            else:
                logger.debug('geomstr = %s', geomstr)

            try:
                extent = fromstr(geomstr, srid=srid)
            except:
                logger.exception('Could not get extent for geomstr = %s, srid = %d', geomstr, srid)

            # Compute midpoint of extent for use in GeoViewpoint for Oculus Rift viewpoint setting
            lon_midpoint = (extent[0][0] + extent[1][0]) / 2.0
            lat_midpoint = (extent[0][1] + extent[1][1]) / 2.0

            try:
                extent.transform(outputSRID)
            except:
                logger.exception('Cannot get transorm to %s for geomstr = %s, srid = %d', outputSRID, geomstr, srid)
        
        return (extent, lon_midpoint, lat_midpoint)

