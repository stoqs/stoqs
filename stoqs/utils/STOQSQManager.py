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

# To debug this on a docker production development system run:
#   docker-compose exec stoqs /bin/bash
#   stoqs/manage.py runserver_plus 0.0.0.0:8001 --settings=config.settings.local
# Place breakpoint()s in this code and hit http://localhost:8001 from your host

from collections import defaultdict
from collections.abc import Mapping
from django.conf import settings
from django.db import transaction
from django.db.models import Q, Max, Min, Sum, Avg
from django.db.models.sql import query
from django.contrib.gis.db.models import Extent, Union
from django.contrib.gis.geos import fromstr, MultiPoint, Point
from django.db.utils import DatabaseError, DataError
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from stoqs import models
from loaders import MEASUREDINSITU, X3DPLATFORMMODEL, X3D_MODEL
from loaders.SampleLoaders import SAMPLED, NETTOW, PLANKTONPUMP, ESP_FILTERING, sample_simplify_crit, SAMPLE_TYPES
from matplotlib.colors import rgb2hex
from .utils import round_to_n, postgresifySQL, EPOCH_STRING, EPOCH_DATETIME
from .utils import (getGet_Actual_Count, getShow_Sigmat_Parameter_Values, getShow_StandardName_Parameter_Values, 
                   getShow_All_Parameter_Values, getShow_Parameter_Platform_Data)
from .utils import simplify_points, getParameterGroups
from .geo import GPS
from .MPQuery import MPQuery
from .PQuery import PQuery
from .Viz import MeasuredParameter, ParameterParameter, PPDatabaseException, PlatformAnimation
from coards import to_udunits
from datetime import datetime
from django.contrib.gis import gdal
import logging
import matplotlib.pyplot as plt
import calendar
import re
import locale
import time
import os
import numpy as np

logger = logging.getLogger(__name__)

# Constants to be also used by classifiers in contrib/analysis
LABEL = 'label'
DESCRIPTION = 'description'
COMMANDLINE = 'commandline'
LRAUV_MISSION = 'LRAUV Mission'
spherical_mercator_srid = 3857

# Constants for parametertime coordinates
LONGITUDE_UNITS = 'degrees_east'
LATITUDE_UNITS = 'degrees_north'
DEPTH_UNITS = 'm'
TIME_UNITS = 'seconds since 1970-01-01'


class STOQSQManager(object):
    '''
    This class is designed to handle building and managing queries against the STOQS database.
    Chander Ganesan <chander@otg-nc.com>
    '''
    def __init__(self, request, response, dbname, *args, **kwargs):
        '''
        This object should be created by passing in an HTTPRequest Object, an HTTPResponse object
        and the name of the database to be used.
        '''
        self.request = request
        self.dbname = dbname
        self.kwargs = kwargs
        self.response = response
        self.mpq = MPQuery(request)
        self.contour_mpq = MPQuery(request)
        self.pq = PQuery(request)
        self.pp = None
        self._actual_count = None
        self.initialQuery = True
        self.platformTypeHash = {}

        # monkey patch sql/query.py to make it use our database for sql generation
        query.DEFAULT_DB_ALIAS = dbname

        # Dictionary of items that get returned via AJAX as the JSON response.  Make available as member variable.
        self.options_functions = {
            'activitynames': self.getActivityNames,
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
            'sampledurationsdepthtime': self.getSampleDurationDepthTime,
            'counts': self.getCounts,
            'mpsql': self.getMeasuredParametersPostgreSQL,
            'spsql': self.getSampledParametersPostgreSQL,
            'extent': self.getExtent,
            'activityparameterhistograms': self.getActivityParameterHistograms,
            'parameterplatformdatavaluepng': self.getParameterDatavaluePNG,
            'parameterparameterx3d': self.getParameterParameterX3D,
            'measuredparameterx3d': self.getMeasuredParameterX3D,
            'curtainx3d': self.getPDV_IFSs,
            'platformanimation': self.getPlatformAnimation,
            'parameterparameterpng': self.getParameterParameterPNG,
            'parameterplatforms': self.getParameterPlatforms,
            'x3dterrains': self.getX3DTerrains,
            'x3dplaybacks': self.getX3DPlaybacks,
            'resources': self.getResources,
            'attributes': self.getAttributes,
            'updatefromzoom': self.getUpdateFromZoom,
        }
        
    def buildQuerySets(self, *args):
        '''
        Build the query sets based on any selections from the UI.  We need one for Activities and one for Samples
        '''
        self.kwargs['fromTable'] = 'Activity'
        self._buildQuerySet()

        self.kwargs['fromTable'] = 'Sample'
        self._buildQuerySet()

        self.kwargs['fromTable'] = 'ActivityParameter'
        self._buildQuerySet()

        self.kwargs['fromTable'] = 'ActivityParameterHistogram'
        self._buildQuerySet()

    def _buildQuerySet(self, *args):
        '''
        Build the query set based on any selections from the UI. For the first time through  kwargs will be empty 
        and self.qs will be built of a join of activities, parameters, and platforms with no constraints.

        Right now supported keyword arguments are the following:
            sampledparametersgroup - a list of sampled parameter ids to include
            measuredparametersgroup - a list of measured parameter ids to include
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
        if 'fromTable' in self.kwargs:
            fromTable = self.kwargs['fromTable']

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

        # Determine if this is the intial query and set a flag
        for k, v in list(self.kwargs.items()):
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
        for k, v in list(self.kwargs.items()):
            if not v:
                continue
            if k == 'fromTable':
                continue
            if hasattr(self, '_%sQ' % (k,)):
                # Call the method if it exists, and add the resulting Q object to the filtered queryset.
                q = getattr(self,'_%sQ' % (k,))(v, fromTable)
                logger.debug('fromTable = %s, k = %s, v = %s, q = %s', fromTable, k, v, q)
                qs = qs.filter(q)
                # Build qs_platform for Platform UI buttons to work
                if k != 'platforms' and fromTable == 'Activity':
                    qs_platform = qs_platform.filter(q)

        # Assign query sets for the current UI selections
        if fromTable == 'Activity':
            self.qs = qs.using(self.dbname)
            self.qs_platform = qs_platform
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
        for k, v in list(self.options_functions.items()):
            if self.kwargs['only'] != []:
                if k not in self.kwargs['only']:
                    continue
            if k in self.kwargs['except']:
                continue

            start_time = time.time()
            if k == 'measuredparametersgroup':
                results[k] = v(MEASUREDINSITU)
            elif k == 'sampledparametersgroup':
                results[k] = v(SAMPLED)
            else:
                results[k] = v()

            logger.info(f"Built in {1000*(time.time()-start_time):6.1f} ms {k} with {str(v).split('.')[1].split(' ')[0]}()")
        
        return results
    
    #
    # Methods that generate summary data, based on the current query criteria
    #
    def getUpdateFromZoom(self):
        if self.request.GET.get('updatefromzoom', '0') == '1':
            return 1
        else:
            return 0

    def getActivityNames(self):
        '''Return list of activities that have been selected in UI's Metadata -> NetCDF section
        '''
        activity_names = None
        if 'activitynames' in self.kwargs:
            activity_names = self.kwargs.get('activitynames')

        return activity_names

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
            logger.warn('Failed to format approximate_count = %s into a number, setting to None', approximate_count)
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
                logger.debug('Adding Q object for parameter__id__in = %s', self.kwargs['measuredparametersgroup'])
                return self.activityparameter_qs.filter(Q(parameter__id__in=self.kwargs['measuredparametersgroup']))
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
        Get a list of the unique parameters that are left based on the current query criteria.
        We assume here that the name is unique and is also used for the id
        '''
        # Django makes it easy to do sub-queries: Get Parameters from list of Activities matching current selection
        # Better to use 'exclude' to get remaining Activities so as to include those Activities
        # (dorado_Gulper, daphne_Sipper, makai_ESP, etc.) that aren't in the checkbox list
        qs_acts = self.qs
        if self.kwargs.get('exclude_ans'):
            qs_acts = qs_acts.exclude(name__in=self.kwargs.get('exclude_ans'))
        p_qs = models.Parameter.objects.using(self.dbname).filter(Q(activityparameter__activity__in=qs_acts))

        if 'mplabels' in self.kwargs:
            if self.kwargs['mplabels']:
                # Get all Parameters that have common Measurements given the filter of the selected labels
                # - this allows selection of co-located MeasuredParameters
                commonMeasurements = models.MeasuredParameterResource.objects.using(self.dbname).filter( 
                                        resource__id__in=self.kwargs['mplabels']).values_list(
                                        'measuredparameter__measurement__id', flat=True)
                p_qs = p_qs.filter(Q(id__in=models.MeasuredParameter.objects.using(self.dbname).filter(
                        Q(measurement__id__in=commonMeasurements)).values_list('parameter__id', flat=True)))

        if groupName:
            p_qs = p_qs.filter(parametergroupparameter__parametergroup__name=groupName)

        p_qs = p_qs.values('name', 'standard_name', 'id', 'units', 'long_name', 'description').distinct()

        results=[]
        for row in p_qs.order_by('name'):
            name = row['name']
            standard_name = row['standard_name']
            id = row['id']
            units = row['units']

            # Get additional Parameter information from NetCDF variable attributes
            long_name = row['long_name']
            if not long_name:
                long_name_q = models.ParameterResource.objects.using(self.dbname).filter(
                                    parameter__id=id, resource__name='long_name').values(
                                    'resource__value')
                if long_name_q:
                    long_name = long_name_q[0].get('resource__value', '')
                else:
                    long_name = ''

            comment = ''
            comment_q = models.ParameterResource.objects.using(self.dbname).filter(
                                parameter__id=id, resource__name='comment').values(
                                'resource__value', 'parameter__name')
            if not comment_q:
                pass
            else:
                comment = f"{comment_q[0].get('resource__value', '')}"
                if comment_q.count() > 1:
                    comment += f" ({(comment_q.count() -1)} comments for additional platforms not shown)"
                comment += ". "

            description = row.get('description', '')
            if not description:
                description = ''

            if not standard_name:
                standard_name = ''
            if name is not None:
                results.append((name, standard_name, id, units, long_name, comment, description))

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
                        logger.warn('Failed to get plot_results for qs = %s', qs)
                else:
                    # Eliminate Gulper Activities which skew the result badly resulting in a bad color lookup table
                    qs = self.getActivityParametersQS().filter(parameter__id=pid, number__gt=4)
                    if qs.count() == 0:
                        # Relax the constraint eliminating Gulper Activities that have a number of 4 or less
                        qs = self.getActivityParametersQS().filter(parameter__id=pid)
                    qs = qs.aggregate(Avg('p025'), Avg('p975'))

                    try:
                        plot_results = [pid, round_to_n(qs['p025__avg'],4), round_to_n(qs['p975__avg'],4)]
                        if plot_results[1] == plot_results[2]:
                            logger.debug('Standard min and max for for pid %s are the same. Getting the overall min and max values.', pid)
                            qs = self.getActivityParametersQS().filter(parameter__id=pid).aggregate(Min('p025'), Max('p975'))
                            plot_results = [pid, round_to_n(qs['p025__min'],4), round_to_n(qs['p975__max'],4)]
                    except TypeError:
                        logger.debug('Failed to get plot_results for qs = %s', qs)
            except ValueError as e:
                if pid in ('longitude', 'latitude'):
                    # Get limits from Activity maptrack for which we have our getExtent() method
                    extent, lon_mid, lat_mid, _ = self.getExtent(outputSRID=4326)
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
            except DataError as e:
                # Likely "value out of range: overflow", clamp to limits of single-precision floats
                logger.warn(f'{e}')
                logger.warn(f'Setting pid = {pid} in plot_results to min/max to limits of single-precision floats')
                plot_results = [pid, round_to_n(np.finfo('f').min, 4), round_to_n(np.finfo('f').max, 4)]

        elif 'parameterplot' in self.kwargs:
            if self.kwargs['parameterplot'][0]:
                parameterID = self.kwargs['parameterplot'][0]
                try:
                    if percentileAggregateType == 'extrema':
                        qs = self.getActivityParametersQS().filter(parameter__id=parameterID).aggregate(Min('p025'), Max('p975'))
                        plot_results = [parameterID, round_to_n(qs['p025__min'],4), round_to_n(qs['p975__max'],4)]
                    else:
                        # Eliminate Gulper Activities which skew the result badly resulting in a bad color lookup table
                        qs = self.getActivityParametersQS().filter(parameter__id=parameterID, number__gt=4)
                        if qs.count() == 0:
                            # Relax the constraint eliminating Gulper Activities that have a number of 4 or less
                            qs = self.getActivityParametersQS().filter(parameter__id=parameterID)
                        qs = qs.aggregate(Avg('p025'), Avg('p975'))
                        plot_results = [parameterID, round_to_n(qs['p025__avg'],4), round_to_n(qs['p975__avg'],4)]
                except TypeError as e:
                    # Likely 'Cannot plot Parameter' that is not in selection, ignore for cleaner functional tests
                    logger.debug(f'parameterID = {parameterID}: {str(e)}')
                except DataError as e:
                    logger.warn(f'{e}')
                    logger.warn(f'Setting pid = {pid} in plot_results to min/max to limits of single-precision floats')
                    plot_results = [pid, round_to_n(np.finfo('f').min, 4), round_to_n(np.finfo('f').max, 4)]

        if 'measuredparametersgroup' in self.kwargs:
            if len(self.kwargs['measuredparametersgroup']) == 1:
                mpid = self.kwargs['measuredparametersgroup'][0]
                try:
                    pid = models.Parameter.objects.using(self.dbname).get(id=mpid).id
                    logger.debug('pid = %s', pid)
                    if percentileAggregateType == 'extrema':
                        qs = self.getActivityParametersQS().filter(parameter__id=pid).aggregate(Min('p010'), Max('p990'))
                        da_results = [pid, round_to_n(qs['p010__min'],4), round_to_n(qs['p990__max'],4)]
                    else:
                        qs = self.getActivityParametersQS().filter(parameter__id=pid).aggregate(Avg('p025'), Avg('p975'))
                        da_results = [pid, round_to_n(qs['p025__avg'],4), round_to_n(qs['p975__avg'],4)]
                except TypeError as e:
                    logger.exception(e)
                except DataError as e:
                    logger.warn(f'{e}')
                    logger.warn(f'Setting pid = {pid} in da_results to min/max to limits of single-precision floats')
                    da_results = [pid, round_to_n(np.finfo('f').min, 4), round_to_n(np.finfo('f').max, 4)]

        if 'sampledparametersgroup' in self.kwargs:
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

        if 'parameterstandardname' in self.kwargs:
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

        cmincmax = []
        if self.request.GET.get('cmin') and self.request.GET.get('cmax'):
            if plot_results:
                cmincmax = [plot_results[0],
                            float(self.request.GET.get('cmin')), 
                            float(self.request.GET.get('cmax'))]
                if self.request.GET.get('cmincmax_lock') == '1':
                    plot_results = cmincmax
            else:
                # Likely a selection from the UI that doesn't include the plot parameter
                logger.debug('plot_results is empty')

        return {'plot': plot_results, 'dataaccess': da_results, 'cmincmax': cmincmax}

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
                geom_list = list([_f for _f in self.qs.filter(platform__name=platformName)
                                         .values_list('nominallocation__geom', flat=True)
                                         .distinct() if _f])
                try:
                    geom = geom_list[0]
                except IndexError:
                    return modelInfo

                if not geom:
                    return modelInfo

                if len(geom_list) > 1:
                    logger.debug('More than one location for %s returned.'
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
                        logger.debug('Got depth = %s from X3D_MODEL_nominaldepth in '
                                     'PlatformResource', depth)
                    except (IndexError, ObjectDoesNotExist):
                        logger.warn('Resource name X3D_MODEL_nominaldepth not found for '
                                    'for platform %s. Using a nominaldepth of 0.0', platformName)
                        depth = 0.0
                else:
                    depth = depth_list[0]

                modelInfo = (pModel[0], geom.y, geom.x, 
                             -depth * float(self.request.GET.get('ve', 1)))

            return modelInfo

        return _innerGetPlatformModel(self, platformName)       
    
    def getPlatforms(self):
        '''
        Get a list of the unique platforms that are left based on the current query criteria.
        We assume here that the name is unique and is also used for the id - this is enforced on 
        data load.  Organize the platforms into a dictionary keyed by platformType.
        '''
        if self.platformTypeHash:
            return self.platformTypeHash

        # Use queryset that does not filter out platforms - so that Platform buttons work in the UI
        qs = (self.qs_platform.filter(~Q(activitytype__name=LRAUV_MISSION))
                              .values('platform__uuid', 'platform__name', 'platform__color', 
                                      'platform__platformtype__name').distinct().order_by('platform__name'))
        # Better to use 'exclude' to get remaining Activities so as to include those Activities
        # (dorado_Gulper, daphne_Sipper, makai_ESP, etc.) that aren't in the checkbox list
        if self.kwargs.get('exclude_ans'):
            qs = qs.exclude(name__in=self.kwargs.get('exclude_ans'))

        platformTypeHash = defaultdict(list)
        logger.debug(f"Begining to build platformTypeHash...")
        for row in qs:
            logger.debug(f"Checking row = {row}")
            name=row['platform__name']
            id=row['platform__name']
            color=row['platform__color']
            platformType = row['platform__platformtype__name']
            if name is not None and id is not None:
                # Get the featureType(s) from the Resource
                fts = models.ActivityResource.objects.using(self.dbname).filter(resource__name='featureType', 
                               activity__platform__name=name).values_list('resource__value', flat=True).distinct()
                # Make all lower case
                fts = [ft.lower() for ft in fts]
                if len(fts) > 1:
                    logger.warn('More than one featureType returned for platform %s: %s.', name, fts)
                    logger.warn(f"Using '{fts[0]}'.  Consider using a different Platform name for the other featureType(s).")
                try:
                    featureType = fts[0]
                except IndexError:
                    logger.warn('No featureType returned for platform name = %s.  Setting it to "trajectory".', name)
                    featureType = 'trajectory'

                if 'trajectory' in featureType:
                    platformTypeHash[platformType].append((name, id, color, featureType, ))
                else:
                    # Filter out models from static platforms not in the selection
                    if name in self.qs.values_list('platform__name', flat=True):
                        logger.debug(f"Seeing if Platform {name} has an x3dModel...")
                        x3dModel, x, y, z = self._getPlatformModel(name) 
                        if not x3dModel:
                            logger.debug("No x3dModel. Not adding x3dModel")
                            platformTypeHash[platformType].append((name, id, color, featureType, ))
                            continue

                        # Only add stationary X3D model for platforms that don't have roll, pitch and yaw
                        # Platforms with rotations have their X3D model added to the scene in stoqs/utils/Viz/animation.py
                        logger.debug(f"Seeing if Platform {name} has roll, pitch, and yaw Parameters...")
                        pr_qs = models.ActivityParameter.objects.using(self.dbname).filter(activity__platform__name=name)
                        has_roll = pr_qs.filter(parameter__standard_name='platform_roll_angle')
                        has_pitch = pr_qs.filter(parameter__standard_name='platform_pitch_angle')
                        has_yaw = pr_qs.filter(parameter__standard_name='platform_yaw_angle')
                        if has_roll or has_pitch or has_yaw:
                            logger.debug("Has roll, pitch, or yaw. Not adding x3dModel")
                            platformTypeHash[platformType].append((name, id, color, featureType, ))
                        else: 
                            logger.debug("Has x3dModel, no rotations, adding x3dModel")
                            platformTypeHash[platformType].append((name, id, color, featureType, x3dModel, x, y, z))

        logger.debug(f"Done building platformTypeHash.")
        self.platformTypeHash = platformTypeHash
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

    def _add_ts_tsp_to_sdt(self, p, plq, timeSeriesQ, timeSeriesProfileQ, sdt):
        '''Add to the sdt hash a timeseries or timeseries structure
        '''
        iptvq = Q()
        qs_tsp = None
        logger.debug(f"Building sdt for Platform {p}")
        qs_tsp = (self.qs.filter(plq & (timeSeriesQ | timeSeriesProfileQ))
                         .select_related()
                         .values('simpledepthtime__epochmilliseconds', 
                                 'simpledepthtime__depth', 'name', 
                                 'simpledepthtime__nominallocation__depth')
                         .order_by('simpledepthtime__epochmilliseconds')
                         .distinct())

        if 'time' in self.kwargs:
            if self.kwargs['time'][0] is not None and self.kwargs['time'][1] is not None:
                logger.debug(f"Querying beween {self.kwargs['time']}")
                qs_tsp = qs_tsp.filter(Q(instantpoint__timevalue__gte = self.kwargs['time'][0]) &
                                       Q(instantpoint__timevalue__lte = self.kwargs['time'][1]))

        # Add to sdt hash date-time series organized by 
        # activity__name_nominallocation__depth key within a platform__name key
        logger.debug(' filling sdt[]')
        for sd in qs_tsp:
            an_nd = '%s_%s' % (sd['name'], sd['simpledepthtime__nominallocation__depth'])
            if 'simpledepthtime__epochmilliseconds' in sd:
                sdt[p[0]][an_nd].append( 
                            [sd['simpledepthtime__epochmilliseconds'], 
                            '%.2f' % sd['simpledepthtime__nominallocation__depth']] )

        logger.debug(' Done filling sdt[].')
            
    def getSimpleDepthTime(self):
        '''
        Based on the current selected query criteria for activities, return the associated SimpleDepth time series
        values as a 2-tuple list inside a 2 level hash of platform__name (with its color) and activity__name.
        Multiple simpledepthtimes may be created. There is always a 'default', which is the original concept with
        the sdt items organized by Activities associated with the data sources -- usually NetCDF files.
        SimpleDepthTimes may also be organized by some other criteria, for example LRAUV_MISSION type of 
        Activities.  If these exist in the database, then additional top-level hashes with the ActivityType
        as the key will be created.
        '''

        trajectoryQ = self._trajectoryQ()
        timeSeriesQ = self._timeSeriesQ()
        timeSeriesProfileQ = self._timeSeriesProfileQ()
        trajectoryProfileQ = self._trajectoryProfileQ()

        # Define colors for other_activitytypes - at some point these will also need to go into the Spatial panel
        at_colors = defaultdict(dict)
        other_activitytypes = (LRAUV_MISSION, )
        gist_ncar = plt.cm.gist_ncar
        for at in other_activitytypes:
            acts = models.Activity.objects.using(self.request.META['dbAlias']).filter(activitytype__name=at)
            for act, c in zip(acts, gist_ncar(np.linspace(0, gist_ncar.N, len(acts), dtype=int))):
                at_colors[at][act.name] = rgb2hex(c)[1:]

        # Always have a 'default' ActivityType, and can loop over any number of other ActivityTypes
        # - As of May 2019 only 'trajectory's have other_activitytypes, skip for timeseries, etc.
        sdt_groups = defaultdict(dict)
        for act_type in ('default', ) + other_activitytypes:
            sdt_groups[act_type]['sdt'] = defaultdict(dict)
            sdt_groups[act_type]['colors'] = defaultdict(dict)
            for plats in list(self.getPlatforms().values()):
                for p in plats:
                    logger.debug('Platform name: ' + p[0])
                    plq = Q(platform__name = p[0])
                    sdt_groups[act_type]['sdt'][p[0]] = defaultdict(list)
                    if act_type == 'default':
                        sdt_groups[act_type]['colors'][p[0]] = p[2]
                    else:
                        sdt_groups[act_type]['colors'][p[0]] = {}

                    if p[3].lower() == 'trajectory':
                        # Overkill to also filter on trajectoryQ too if p[3].lower() == 'trajectory' 
                        # - old Tethys data does not have NC_GLOBAL featureType
                        qs_traj = (self.qs.filter(plq)
                                          .values_list('simpledepthtime__epochmilliseconds', 
                                                       'simpledepthtime__depth', 'name')
                                          .order_by('simpledepthtime__epochmilliseconds'))
                        if act_type == 'default':
                            # The default does not include the other ActivityTypes
                            qs_traj = qs_traj.filter(~Q(activitytype__name__in=other_activitytypes))
                        else:
                            qs_traj = qs_traj.filter(activitytype__name=act_type)
                        # Add to sdt hash date-time series organized by activity__name key 
                        # within a platform__name key. This will let flot plot the series with 
                        # gaps between the surveys -- not connected
                        logger.debug(f"-trajectory, filling sdt_groups['{act_type}']['sdt']['{p[0]}'][]")
                        # Better to use 'exclude' to get remaining Activities so as to include those Activities
                        # (dorado_Gulper, daphne_Sipper, makai_ESP, etc.) that aren't in the checkbox list
                        if self.kwargs.get('exclude_ans'):
                            logger.debug('exclude_ans = %s', self.kwargs.get('exclude_ans'))
                            qs_traj = qs_traj.exclude(name__in=self.kwargs.get('exclude_ans'))
                        for s in qs_traj:
                            if s[1] is not None:
                                sdt_groups[act_type]['sdt'][p[0]][s[2]].append( [s[0], '%.2f' % s[1]] )
                        if act_type != 'default':
                            for number, act_mission in enumerate(sdt_groups[act_type]['sdt'][p[0]].keys()):
                                sdt_groups[act_type]['colors'][p[0]][act_mission] = at_colors[act_type][act_mission]
                        logger.debug(f" Done filling sdt_groups['{act_type}']['sdt']['{p[0]}'][]")

                    elif (p[3].lower() == 'timeseries' or p[3].lower() == 'timeseriesprofile') and act_type == 'default':
                        self._add_ts_tsp_to_sdt(p, plq, timeSeriesQ, timeSeriesProfileQ, sdt_groups[act_type]['sdt'])

                    elif p[3].lower() == 'trajectoryprofile' and act_type == 'default': # pragma: no cover
                        iptvq = Q()
                        qs_tp = None
                        if 'time' in self.kwargs:
                            if self.kwargs['time'][0] is not None and self.kwargs['time'][1] is not None:
                                s_ems = time.mktime(datetime
                                                    .strptime(self.kwargs['time'][0], '%Y-%m-%d %H:%M:%S')
                                                    .timetuple())*1000
                                e_ems = time.mktime(datetime
                                                    .strptime(self.kwargs['time'][1], '%Y-%m-%d %H:%M:%S')
                                                    .timetuple())*1000
                                iptvq = (Q(simpledepthtime__epochmilliseconds__gte = s_ems) & 
                                         Q(simpledepthtime__epochmilliseconds__lte = e_ems))
                                qs_tp = (self.qs.filter(plq & trajectoryProfileQ & iptvq)
                                                .select_related()
                                                .values('name', 'simpledepthtime__depth',
                                                        'simpledepthtime__nominallocation__depth', 
                                                        'simpledepthtime__epochmilliseconds')
                                                .order_by('simpledepthtime__nominallocation__depth',
                                                          'simpledepthtime__epochmilliseconds')
                                                .distinct())
                        if not qs_tp:
                            qs_tp = (self.qs.filter(plq & trajectoryProfileQ).select_related()
                                            .values('name', 'simpledepthtime__depth',
                                                    'simpledepthtime__nominallocation__depth',
                                                    'simpledepthtime__epochmilliseconds')
                                            .order_by('simpledepthtime__nominallocation__depth',
                                                      'simpledepthtime__epochmilliseconds')
                                            .distinct())

                        # Better to use 'exclude' to get remaining Activities so as to include those Activities
                        # (dorado_Gulper, daphne_Sipper, makai_ESP, etc.) that aren't in the checkbox list
                        if self.kwargs.get('exclude_ans'):
                            qs_tp = qs_tp.exclude(name__in=self.kwargs.get('exclude_ans'))
                        # Add to sdt hash date-time series organized by activity__name_nominallocation__depth 
                        # key within a platform__name key - use real depths
                        for sd in qs_tp:
                            ##logger.debug('sd = %s', sd)
                            an_nd = '%s_%s' % (sd['name'], sd['simpledepthtime__nominallocation__depth'])
                            ##logger.debug('an_nd = %s', an_nd)
                            if 'simpledepthtime__epochmilliseconds' in sd:
                                sdt_groups[act_type]['sdt'][p[0]][an_nd].append(
                                            [sd['simpledepthtime__epochmilliseconds'], 
                                            '%.2f' % sd['simpledepthtime__depth']])

                    # Cleanup - remove platforms that have no simpledepthtime data values
                    if not sdt_groups[act_type]['sdt'][p[0]]:
                        del sdt_groups[act_type]['sdt'][p[0]]
                        del sdt_groups[act_type]['colors'][p[0]]

            # Remove ActivityTypes that ave no simpledepthtime data
            if not sdt_groups[act_type]['sdt']:
                del sdt_groups[act_type]

        return sdt_groups 

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

        for plats in list(self.getPlatforms().values()):
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

    def _assign_no_units(self, parameter, pa_units):
        "Need to assign a unit for organizing plot hashes"
        if parameter.name in pa_units.keys():
            return pa_units[parameter.name]
        num = 1
        for val in pa_units.values():
            # Use separate units so as not to share axes
            if val.startswith('no_units'):
                num = int(val.split('_')[-1]) + 1
        return f'no_units_{num}'

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
        else:
            p_qs = []

        for parameter in p_qs:
            unit = parameter.units

            # Get the number of nominal depths for this parameter
            nds =  models.NominalLocation.objects.using(self.dbname
                                    ).filter( Q(activity__in=self.qs),
                                              activity__platform__name=platform[0],
                                              measurement__measuredparameter__parameter=parameter
                                    ).values('depth').distinct().count()
            # Check if timeSeries plotting is requested for trajectory data
            plotTimeSeriesDepths = models.ParameterResource.objects.using(self.dbname).filter(
                                        parameter__name=parameter, resource__name='plotTimeSeriesDepth'
                                        ).values_list('resource__value')
           
            if nds == 0 and plotTimeSeriesDepths == []:
                continue

            if not parameter.units:
                unit = self._assign_no_units(parameter, pa_units)
            if parameter.standard_name == 'sea_water_salinity':
                unit = 'PSU'
            logger.debug(f"Adding pa_units, key = {parameter.name}, value = {unit}")
            pa_units[parameter.name] = unit
            is_standard_name[parameter.name] = False
            ndCounts[parameter.name] = nds
            colors[parameter.name] = parameter.id
            strides[parameter.name] = {}

            # Initialize pt dictionary of dictionaries with its keys
            if unit not in list(pt.keys()):
                logger.debug('Initializing pt[%s] = {}', unit)
                pt[unit] = {}

        # Add coordinates keys if asked for from the UI
        if self.kwargs['parametertimeplotcoord']:
            if 'Longitude' in self.kwargs['parametertimeplotcoord']:
                pt[LONGITUDE_UNITS] = {}
                pa_units['Longitude'] = LONGITUDE_UNITS
                strides['Longitude'] = {}
                is_standard_name['Longitude'] = False
                ndCounts['Longitude'] = 1
            if 'Latitude' in self.kwargs['parametertimeplotcoord']:
                pt[LATITUDE_UNITS] = {}
                pa_units['Latitude'] = LATITUDE_UNITS
                strides['Latitude'] = {}
                is_standard_name['Latitude'] = False
                ndCounts['Latitude'] = 1
            if 'Depth' in self.kwargs['parametertimeplotcoord']:
                pt[DEPTH_UNITS] = {}
                pa_units['Depth'] = DEPTH_UNITS
                strides['Depth'] = {}
                is_standard_name['Depth'] = False
                ndCounts['Depth'] = 1
            if 'Time' in self.kwargs['parametertimeplotcoord']:
                pt[TIME_UNITS] = {}
                pa_units['Time'] = TIME_UNITS
                strides['Time'] = {}
                is_standard_name['Time'] = False
                ndCounts['Time'] = 1

        return (pa_units, is_standard_name, ndCounts, pt, colors, strides)

    def _get_activity_nominaldepths(self, p):
        '''Return hash of starting depths for parameter keyed by activity
        '''
        plotTimeSeriesActivityDepths = {}

        # See if timeSeries plotting is requested for trajectory data, e.g. BEDS
        pr_qs = models.ParameterResource.objects.using(self.dbname).filter(parameter__name=p, 
                                resource__name='plotTimeSeriesDepth')
        if not pr_qs:
            # See if there is one for standard_name
            pr_qs = models.ParameterResource.objects.using(self.dbname).filter(parameter__standard_name=p, 
                                    resource__name='plotTimeSeriesDepth')
        try:
            for pr in pr_qs:
                logger.debug('pr.parameter.name, pr.resource.value = {}, {}'.format(pr.parameter.name, pr.resource.value))
                ars = models.ActivityResource.objects.using(self.dbname).filter(
                                resource=pr.resource, resource__name='plotTimeSeriesDepth')
                # Resource with same value will be one record that may be reused by different 
                # Activities/Platforms, just blindly fill hash keyed by Activity
                for ar in ars:
                    logger.debug('ar.activity.name = {}'.format(ar.activity.name))
                    plotTimeSeriesActivityDepths[ar.activity] = pr.resource.value
        except ObjectDoesNotExist:
            # Likely database loaded before plotTimeSeriesDepth was added to ActivityResource, quietly use first value
            for act in self.qs:
                plotTimeSeriesActivityDepths[act] = pr_qs[0].resource.value

        return plotTimeSeriesActivityDepths

    def _append_coords_to_pt(self, qs_mp, pt, pa_units, a, stride, units_dict, strides):
        '''
        Add coordinates to pt dictionary of dictionaries, making sure to append only once.
        Only called if self.kwargs['parametertimeplotcoord'], and needs to be called once per request
        '''
        # Order by nominal depth first so that strided access collects data correctly from each depth
        pt_qs_mp = qs_mp.order_by('measurement__nominallocation__depth', 'measurement__instantpoint__timevalue')[::stride]
        logger.debug(f'Adding coordinates for a.name = {a.name}')
        for mp in pt_qs_mp:
            if mp['datavalue'] is None:
                continue

            tv = mp['measurement__instantpoint__timevalue']
            ems = int(1000 * to_udunits(tv, 'seconds since 1970-01-01'))

            if 'Longitude' in self.kwargs['parametertimeplotcoord']:
                units = LONGITUDE_UNITS
                an_nd = f"{units} - Longitude - {a.name}"
                units_dict[units] = 'Longitude'
                strides['Longitude'][a.name] = stride
                try:
                    pt[units][an_nd].append((ems, mp['measurement__geom'].x))
                except KeyError:
                    pt[units][an_nd] = []
                    pt[units][an_nd].append((ems, mp['measurement__geom'].x))
            if 'Latitude' in self.kwargs['parametertimeplotcoord']:
                units = LATITUDE_UNITS
                an_nd = f"{units} - Latitude - {a.name}"
                units_dict[units] = 'Latitude'
                strides['Latitude'][a.name] = stride
                try:
                    pt[units][an_nd].append((ems, mp['measurement__geom'].y))
                except KeyError:
                    pt[units][an_nd] = []
                    pt[units][an_nd].append((ems, mp['measurement__geom'].y))
            if 'Depth' in self.kwargs['parametertimeplotcoord']:
                units = DEPTH_UNITS
                an_nd = f"{units} - Depth - {a.name}"
                units_dict[units] = 'Depth'
                strides['Depth'][a.name] = stride
                try:
                    pt[units][an_nd].append((ems, mp['measurement__depth']))
                except KeyError:
                    pt[units][an_nd] = []
                    pt[units][an_nd].append((ems, mp['measurement__depth']))
            if 'Time' in self.kwargs['parametertimeplotcoord']:
                units = TIME_UNITS
                an_nd = f"{units} - Time - {a.name}"
                units_dict[units] = 'Time'
                strides['Time'][a.name] = stride
                try:
                    pt[units][an_nd].append((ems, ems))
                except KeyError:
                    pt[units][an_nd] = []
                    pt[units][an_nd].append((ems, ems))

        return pt, units_dict, strides

    def _getParameterTimeFromMP(self, qs_mp, pt, pa_units, a, p, is_standard_name, stride, a_nds, units_dict, strides, save_mp_for_plot=True):
        '''
        Return hash of time series measuredparameter data with specified stride
        '''
        # Order by nominal depth first so that strided access collects data correctly from each depth
        pt_qs_mp = qs_mp.order_by('measurement__nominallocation__depth', 'measurement__instantpoint__timevalue')[::stride]
        logger.debug('Adding time series of parameter = %s in key = %s', p, pa_units[p])
        for mp in pt_qs_mp:
            if mp['datavalue'] is None:
                continue

            tv = mp['measurement__instantpoint__timevalue']
            ems = int(1000 * to_udunits(tv, 'seconds since 1970-01-01'))

            nd = mp['measurement__nominallocation__depth']
            if nd:
                an_nd = "%s - %s - %s @ %s" % (pa_units[p], p, a.name, nd,)
            elif a in a_nds:
                try:
                    an_nd = "%s - %s - %s starting @ %s m" % (pa_units[p], p, a.name, a_nds[a],)
                except KeyError:
                    # Likely data from a load before plotTimeSeriesDepth was added to ActivityResource
                    an_nd = "%s - %s - %s starting @ ? m" % (pa_units[p], p, a.name)
            else:
                an_nd = "%s - %s - %s" % (pa_units[p], p, a.name)
   
            if save_mp_for_plot: 
                try:
                    pt[pa_units[p]][an_nd].append((ems, mp['datavalue']))
                except KeyError:
                    pt[pa_units[p]][an_nd] = []
                    pt[pa_units[p]][an_nd].append((ems, mp['datavalue']))

        return pt, units_dict, strides
        
    def _getParameterTimeFromAP(self, pt, pa_units, a, p):
        '''
        Return hash of time series min and max values for specified activity and parameter.  To be used when duration
        of an activity is less than the pixel width of the flot plot area.  This can occur for short event data sets
        such as from Benthic Event Detector deployments.
        '''

        aps = models.ActivityParameter.objects.using(self.dbname).filter(activity=a, parameter__name=p).values('min', 'max')
        if not aps:
            aps = models.ActivityParameter.objects.using(self.dbname).filter(activity=a, 
                                        parameter__standard_name=p).values('min', 'max')

        start_ems = int(1000 * to_udunits(a.startdate, 'seconds since 1970-01-01'))
        end_ems = int(1000 * to_udunits(a.enddate, 'seconds since 1970-01-01'))

        pt[pa_units[p]][a.name] = [[start_ems, aps[0]['min']], [end_ems, aps[0]['max']]]

        return pt

    def _parameterInSelection(self, p, is_standard_name, parameterType=MEASUREDINSITU):
        '''
        Return True if parameter name is in the UI selection, either from constraints other than
        direct selection or if specifically selected in the UI.  
        '''
        # Coordinates are always in the selection
        if p in ('Longitude', 'Latitude', 'Depth', 'Time'):
            return True

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

        # Check if only coord(s) in pa_units 
        only_coords_flag = False
        save_mp_for_plot = True
        if not set(pa_units.keys()) - set(('Longitude', 'Latitude', 'Depth', 'Time')):
            only_coords_flag = True

        # Build units hash of parameter names for labeling axes in flot
        for pcount, (p, u) in enumerate(list(pa_units.items())):
            logger.debug('is_standard_name = %s.  p, u = %s, %s', is_standard_name, p, u)
            if not self._parameterInSelection(p, is_standard_name):
                logger.debug('Parameter is not in selection')
                continue

            if p in ('Longitude', 'Latitude', 'Depth', 'Time'):
                units[u] = p
            else:
                try:
                    units[u] = units[u] + ' ' + p
                except KeyError:
                    units[u] = p

            # Apply either parameter name or standard_name to MeasuredParameter and Activity query sets
            if is_standard_name[p]:
                qs_mp = pt_qs_mp.filter(parameter__standard_name=p)
                qs_awp = self.qs.filter(activityparameter__parameter__standard_name=p)
            elif only_coords_flag:
                # Choose a dummy Parameter and mark for not plotting so that we can collect coordinates
                dummy_parm = self.getParameters()[0][0]
                logger.info(f"Only coords selected, using {dummy_parm} to go through MPs to get coords")
                qs_mp = pt_qs_mp.filter(parameter__name=dummy_parm)
                qs_awp = self.qs.filter(activityparameter__parameter__name=dummy_parm)
                save_mp_for_plot = False
            else:
                qs_mp = pt_qs_mp.filter(parameter__name=p)
                qs_awp = self.qs.filter(activityparameter__parameter__name=p)

            # Better to use 'exclude' to get remaining Activities so as to include those Activities
            # (dorado_Gulper, daphne_Sipper, makai_ESP, etc.) that aren't in the checkbox list
            if self.kwargs.get('exclude_ans'):
                qs_awp = qs_awp.exclude(name__in=self.kwargs.get('exclude_ans'))

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
            a_nds = self._get_activity_nominaldepths(p)
            # See: https://stackoverflow.com/questions/20582966/django-order-by-filter-with-distinct
            for acount, a in enumerate(qs_awp.distinct('startdate', 'name').order_by('startdate')):
                qs_mp_a = qs_mp.filter(measurement__instantpoint__activity__name=a.name)
                ad = (a.enddate-a.startdate)
                aseconds = ad.days * 86400 + ad.seconds
                logger.debug('a.name = %s, a.startdate = %s, a.enddate %s, aseconds = %s, secondsperpixel = %s', 
                             a.name, a.startdate, a.enddate, aseconds, secondsperpixel)
                if float(aseconds) > float(secondsperpixel) or len(self.kwargs.get('platforms')) == 1:
                    # Multiple points of this activity can be displayed in the flot, get an appropriate stride
                    logger.debug('PIXELS_WIDE = %s, ndCounts[p] = %s', PIXELS_WIDE, ndCounts[p])
                    stride = int(round(qs_mp_a.count() / PIXELS_WIDE / ndCounts[p]))
                    if stride < 1:
                        stride = 1
                    logger.debug('Getting timeseries from MeasuredParameter table with stride = %s', stride)
                    strides[p][a.name] = stride
                    logger.debug('Adding timeseries for p = %s, a = %s', p, a)
                    pt, units, strides = self._getParameterTimeFromMP(qs_mp_a, pt, pa_units, a, p, is_standard_name, stride, a_nds, units, strides, save_mp_for_plot)
                    if self.kwargs['parametertimeplotcoord'] and acount == 0 and pcount == 0:
                        pt, units, strides = self._append_coords_to_pt(qs_mp, pt, pa_units, a, stride, units, strides)

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
        for plats in list(self.getPlatforms().values()):
            for platform in plats:
                if self.kwargs.get('platforms'):
                    # getPlatforms() includes all Platforms, skip over ones not in the selection
                    if platform[0] not in self.kwargs.get('platforms'):
                        continue
                timeSeriesParmCount = 0
                trajectoryParmCount = 0
                logger.debug('Doing cheap query for ' + platform[0] + '...')
                if platform[3].lower() == 'timeseriesprofile' or platform[3].lower() == 'timeseries':
                    # Do cheap query to count the number of timeseriesprofile or timeseries parameters
                    timeSeriesParmCount = models.Parameter.objects.using(self.dbname).filter( 
                                        activityparameter__activity__activityresource__resource__name__iexact='featureType',
                                        activityparameter__activity__activityresource__resource__value__iexact=platform[3].lower(),
                                        activityparameter__activity__platform__name=platform[0],
                                        ).count()
                elif platform[3].lower() == 'trajectory':
                    # Count trajectory Parameters for which timeSeries plotting has been requested
                    trajectoryParmCount = models.Parameter.objects.using(self.dbname).filter(
                                        activityparameter__activity__activityresource__resource__name__iexact='featureType',
                                        activityparameter__activity__activityresource__resource__value__iexact=platform[3].lower(),
                                        parameterresource__resource__name__iexact='plotTimeSeriesDepth',
                                        activityparameter__activity__platform__name=platform[0],
                                        ).count()
                counts += timeSeriesParmCount + trajectoryParmCount
                if counts and (self.kwargs.get('parametertimeplotid') or 'parametertimeplotcoord' in self.kwargs):
                    if 'parametertime' in self.kwargs['only'] or self.kwargs['parametertab']:
                        # Initialize structure organized by units for parameters left in the selection 
                        logger.debug('Calling self._collectParameters() with platform = %s', platform)
                        pa_units, is_standard_name, ndCounts, pt, colors, strides = self._collectParameters(platform, pt, 
                                                                    pa_units, is_standard_name, ndCounts, strides, colors)
                logger.debug('Done, counts = {}'.format(counts))
  
        if pa_units: 
            # The base MeasuredParameter query set for existing UI selections
            if not self.mpq.qs_mp:
                self.mpq.buildMPQuerySet(*self.args, **self.kwargs)
                self.mpq.initialQuery = self.initialQuery

            # Perform more expensive query: start with qs_mp_no_parm version of the MeasuredParameter query set
            pt_qs_mp = self.mpq.qs_mp_no_parm

            logger.debug('Before self._buildParameterTime: pt = %s', list(pt.keys())) 
            pt, units, strides = self._buildParameterTime(pa_units, is_standard_name, ndCounts, pt, strides, pt_qs_mp)
            logger.debug('After self._buildParameterTime: pt = %s', list(pt.keys())) 

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

            # Better to use 'exclude' to get remaining Activities so as to include those Activities
            # (dorado_Gulper, daphne_Sipper, makai_ESP, etc.) that aren't in the checkbox list
            if self.kwargs.get('exclude_ans'):
                qs = qs.exclude(instantpoint__activity__name__in=self.kwargs.get('exclude_ans'))

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

    def getSampleDurationDepthTime(self):
        '''
        Based on the current selected query criteria for activities, return the associated SampleDuration time series
        values as a 2 2-tuple list.  Theses are like SampleDepthTime, but have a depth time series.
        The UI uses a different glyph which is why these are delivered in a separate structure.
        The convention for SampleDurations is for one Sample per activity, therefore we can examine the attributes
        of the activity to get the start and end time and min and max depths, or the depth time series. 
        '''
        sample_durations = []
        try:
            nettow = models.SampleType.objects.using(self.dbname).get(name__contains=NETTOW)
        except models.SampleType.DoesNotExist:
            nettow = None
        try:
            planktonpump = models.SampleType.objects.using(self.dbname).get(name__contains=PLANKTONPUMP)
        except models.SampleType.DoesNotExist:
            planktonpump = None
        try:
            esp_archive = models.SampleType.objects.using(self.dbname).get(name__contains=ESP_FILTERING)
        except models.SampleType.DoesNotExist:
            esp_archive = None
        try:
            esp_archive_at = models.ActivityType.objects.using(self.dbname).get(name__contains=ESP_FILTERING)
        except models.ActivityType.DoesNotExist:
            esp_archive_at = None

        # Samples for which activity mindepth and maxdepth are sufficient for simpledepthtime display
        if self.getSampleQS() and (nettow or planktonpump):
            qs = self.getSampleQS().filter(  Q(sampletype=nettow)
                                           | Q(sampletype=planktonpump)
                                          ).values_list(
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

                try:
                    rec = {'label': label, 'data': [[s_ems, '%.2f' % s[7]], [e_ems, '%.2f' % s[6]]]}
                except TypeError:
                    # Likely s[6] and s[7] are None
                    continue

                sample_durations.append(rec)

        # Long duration Samples for which we use the whole depth time series
        if self.getSampleQS() and (esp_archive):
            samples = (self.qs.filter(activitytype=esp_archive_at).order_by('name'))
            for samp in samples:
                sample_number = samp.name.split('_')[-1]
                samp_depth_time_series = []
                for td in (self.qs.filter(name=samp.name)
                                   .values_list('simpledepthtime__epochmilliseconds',
                                                'simpledepthtime__depth', 'name')
                                   .order_by('simpledepthtime__epochmilliseconds')):
                    samp_depth_time_series.append([td[0], td[1]])
                    
                if ' ' in samp.name:
                    label = '%s %s' % (samp.name.split(' ')[0], sample_number)  # Lop off everything after first space in the activity name
                else:
                    label = '%s %s' % (samp.name, sample_number)                # Show entire Activity name & sample name

                sample_durations.append({'label': label, 'data': samp_depth_time_series})

        return(sample_durations)

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
            for an, pnList in list(platformList.items()):
                ##logger.debug('an = %s, pnList = %s', an, pnList)
                for pn in pnList:
                    try:
                        activityList[pn].append(an)
                    except KeyError:
                        activityList[pn] = []
                        activityList[pn].append(an)

            # Build the final data structure organized by platform -> activity
            plHash = {}
            for plat in list(activityList.keys()):
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
        for plats in list(self.getPlatforms().values()):
            for p in plats:
                r,g,b = (p[2][:2], p[2][2:4], p[2][4:])
                rgbas[p[0]] = 'rgba(%d, %d, %d, 0.4)' % (int(r,16), int(g,16), int(b,16))

        return {'histdata': aphHash, 'rgbacolors': rgbas, 'parameterunits': pUnits}

    def _build_mpq_queryset(self):
        '''Factored out method used to construct query for getting data values to
        produce png images of data in the selection - e.g. for Flot and X3D IndexedFaceSets
        '''
        # Check for parameter-plot-radio button being selected, which inherently ensures that a
        # single parameter name is selected for plotting.  Modifies member items from member items.
        parameterID = None
        platformName = None
        contourparameterID = None # parameter for Contour plots
        contourplatformName = None
        parameterGroups = []
        contourparameterGroups = []
        logger.debug('self.kwargs = %s', self.kwargs)
        
        if self.request.GET.get('showplatforms', False):
            # Allow for platform animation without selecting a parameterplot
            self.mpq.buildMPQuerySet(*self.args, **self.kwargs)

        if 'parameterplot' in self.kwargs:
            if self.kwargs['parameterplot'][0]:
                parameterID = self.kwargs['parameterplot'][0]
                parameter = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=parameterID)
                parameterGroups = getParameterGroups(self.request.META['dbAlias'], parameter)
            if self.kwargs['parameterplot'][1]:
                platformName = self.kwargs['parameterplot'][1]
            if parameterID:
                self.mpq.buildMPQuerySet(*self.args, **self.kwargs)
      
        if 'parametercontourplot' in self.kwargs:
            if self.kwargs['parametercontourplot'][0]:
                contourparameterID = self.kwargs['parametercontourplot'][0]
                contourparameter = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=contourparameterID)
                contourparameterGroups = getParameterGroups(self.request.META['dbAlias'], contourparameter)
            if self.kwargs['parametercontourplot'][1]:
                contourplatformName = self.kwargs['parametercontourplot'][1]
            self.kwargs['parameterplot_id'] = contourparameterID
            if contourparameterID:
                self.contour_mpq.buildMPQuerySet(*self.args, **self.kwargs)

        return parameterID, platformName, contourparameterID, contourplatformName, parameterGroups, contourparameterGroups

    def _get_plot_min_max(self, parameterID, contourparameterID):
        min_max = self.getParameterMinMax(pid=parameterID)['plot']
        if not parameterID and contourparameterID: 
            min_max = self.getParameterMinMax(pid=contourparameterID)['plot']

        return min_max

    def getParameterDatavaluePNG(self):
        '''
        Called when user interface has selected one Parameter for plotting, in which case
        produce a depth-time section plot for overlay on the flot plot.  Return a png image 
        file name for inclusion in the AJAX response.
        '''
        parameterID, platformName, contourparameterID, contourplatformName, parameterGroups, contourparameterGroups = self._build_mpq_queryset()
      
        if parameterID or platformName or contourparameterID or contourplatformName:
            pass
        else:
            return

        min_max = self._get_plot_min_max(parameterID, contourparameterID)
        if not min_max:
            return None, None, 'Cannot plot Parameter'

        if SAMPLED in parameterGroups:
            # The fourth item should be for SampledParameter if that is the group of the Parameter
            cp = MeasuredParameter(self.kwargs, self.request, self.qs, self.mpq.qs_sp_no_order, self.contour_mpq.qs_sp_no_order,
                                    min_max, self.getSampleQS(), platformName, 
                                    parameterID, parameterGroups, contourplatformName, contourparameterID, contourparameterGroups)
        else:
            cp = MeasuredParameter(self.kwargs, self.request, self.qs, self.mpq.qs_mp_no_order, self.contour_mpq.qs_mp_no_order,
                                    min_max, self.getSampleQS(), platformName, 
                                    parameterID, parameterGroups, contourplatformName, contourparameterID, contourparameterGroups)

        return cp.renderDatavaluesNoAxes()

    def _combine_sample_platforms(self, platforms):
        '''Mainly for LRAUV data: combine <platform>_ESP_filtering or <platform>_Sipper Platform name
        with <platform> for creating the image(s) by renderDatavaluesNoAxes()
        '''
        has_samples = []
        combined_platforms = []
        for platform in platforms.split(','):
            for sample_type in SAMPLE_TYPES:
                if platform.endswith(sample_type):
                    parent_platform = platform.split('_'+sample_type)[0]
                    if parent_platform in platforms:
                        has_samples.append(platform)
                        has_samples.append(parent_platform)
                        combined_platforms.append(f"{parent_platform},{platform}")
                    else:
                        # Possible to have samples without the parent platform
                        combined_platforms.append(platform)
            if platform not in has_samples:
                combined_platforms.append(platform)

        return combined_platforms

    def getPDV_IFSs(self):
        '''Return X3D scene of Parameter DataValue IndexedFaceSets of curtains constructed 
        from ParameterDatavaluePNG images when contour and 3D data are checked.
        '''
        x3d_dict = {}
        contourFlag = False
        if 'showdataas' in self.kwargs:
            if self.kwargs['showdataas']:
                if self.kwargs['showdataas'][0] == 'contour':
                    contourFlag = True
        if contourFlag and self.kwargs.get('showgeox3dmeasurement'):
            # Set a single min_max for all the curtains
            parameterID, platformName, contourparameterID, contourplatformName, parameterGroups, contourparameterGroups = self._build_mpq_queryset()
            min_max = self._get_plot_min_max(parameterID, contourparameterID)
            if not min_max:
                return None, None, 'Cannot plot Parameter'

            # platformName and contourplatformName are for display purposes and may look like:
            # 'daphne,makai_ESP_filtering,tethys,makai'; _combine_sample_platforms() divies them up for image generation
            saved_platforms = self.kwargs['platforms']
            for pns in self._combine_sample_platforms(platformName):
                # Rebuild query set for just this platform as qs_mp_no_order is an MPQuerySet which has no filter() method
                self.kwargs['platforms'] = pns.split(',')
                platform_single = self.kwargs['platforms'][0]
                # All Activities in the selection, do not inlcude 'special Activities' like LRAUV Mission
                for act in self.qs.filter(Q(platform__name=platform_single) & ~Q(activitytype__name=LRAUV_MISSION)):
                    # Set self.mpq.qs_mp to None to bypass the Singleton nature of MPQuery and have _build_mpq_queryset() build new self.mpq items
                    self.mpq.qs_mp = None
                    self.kwargs['activitynames'] = [act.name]
                    parameterID, platformName, contourparameterID, contourplatformName, parameterGroups, contourparameterGroups = self._build_mpq_queryset()
                    logger.info(f"Rendering image for pns='{pns}', act.name='{act.name}'")
                    cp = MeasuredParameter(self.kwargs, self.request, self.qs, self.mpq.qs_mp, self.contour_mpq.qs_mp_no_order,
                                            min_max, self.getSampleQS(), pns,
                                            parameterID, parameterGroups, contourplatformName, contourparameterID, contourparameterGroups)
                    x3d_items, shape_id_dict = cp.curtainX3D(pns, float(self.request.GET.get('ve', 10)), 
                                                     int(self.request.GET.get('slice_minutes')))
                    if x3d_items:
                        x3d_dict.update(x3d_items)
                        try:
                            x3d_dict['shape_id_dict'].update(shape_id_dict)
                        except KeyError:
                            x3d_dict['shape_id_dict'] = {}
                            x3d_dict['shape_id_dict'].update(shape_id_dict)

            self.kwargs['platforms'] = saved_platforms
            if x3d_dict:
                x3d_dict['speedup'] = self._get_speedup({act.platform for act in self.qs})
                cycInt = (self.max_end_time - self.min_start_time).total_seconds() / x3d_dict['speedup']
                x3d_dict['timesensor'] = PlatformAnimation.timesensor_template.format(cycInt=cycInt)

                sec_interval = (cp.x[2] - cp.x[1]) * cp.scale_factor
                spaced_ts = np.arange(self.min_start_time.timestamp(), self.max_end_time.timestamp(), sec_interval)
                x3d_dict['limits'] = (0, len(spaced_ts))

                cp.makeColorBar(cp.colorbarPngFileFullPath, cp.pMinMax)
                x3d_dict['colorbar'] = cp.colorbarPngFile

        return x3d_dict

    def getParameterParameterPNG(self):
        '''
        If at least the X and Y radio buttons are checked produce a scatter plot for delivery back to the client
        '''
        plotResults = None
        if 'parameterparameter' in self.kwargs:
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
                self.pp = ParameterParameter(self.kwargs, self.request, {'x': px, 'y': py, 'c': pc}, self.mpq, self.pq, pMinMax)
                try:
                    ppPngFile, infoText, sql = self.pp.make2DPlot()
                except PPDatabaseException as e:
                    return None, str(e), e.sql

                plotResults = ppPngFile, infoText, sql

        return plotResults

    def getParameterParameterX3D(self):
        '''
        If at least the X, Y, and Z radio buttons are checked produce an X3D response for delivery back to the client
        '''
        x3dDict = None
        if 'parameterparameter' in self.kwargs:
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
                self.pp = ParameterParameter(self.kwargs, self.request, {'x': px, 'y': py, 'z': pz, 'c': pc}, self.mpq, self.pq, pMinMax)
                try:
                    x3dDict = self.pp.makeX3D()
                except DatabaseError as e:
                    return '', e
                try:
                    x3dDict['sql'] += ';'
                except TypeError:
                    return '', 'Selected x, y, z, c Parameters not in filtered selection.'
            
        return x3dDict

    def _get_speedup(self, platforms=()):
        # Hard-code appropriate speedup for different platforms
        speedup = 10
        for platform in platforms:
            if 'BED' in platform.name.upper():
                speedup = 1
        # Override speedup if provided by request from UI
        if self.kwargs.get('speedup'):
            speedup = float(self.kwargs.get('speedup')[0])

        return speedup

    def getMeasuredParameterX3D(self):
        '''Returns dictionary of X3D elements for rendering by X3DOM.
        The dictionary is arganized by Platform. The dataValuesX3D() method returns items 
        organized by Activity and slice_minute Shape slices.
        '''
        x3d_dict = {}
        if self.kwargs.get('showgeox3dmeasurement') and 'parameterplot' in self.kwargs:
            # Set a single min_max for coloring all the lines
            parameterID, platformName, contourparameterID, contourplatformName, parameterGroups, contourparameterGroups = self._build_mpq_queryset()
            min_max = self._get_plot_min_max(parameterID, contourparameterID)
            if not min_max:
                return x3d_dict

            # platformName and contourplatformName are for display purposes and may look like:
            # 'daphne,makai_ESP_filtering,tethys,makai'; _combine_sample_platforms() divies them up to get by-platform querystrings
            saved_platforms = self.kwargs['platforms']
            saved_activitynames = self.kwargs['activitynames']
            min_sec_interval = 10e10
            for pns in self._combine_sample_platforms(platformName):
                # Rebuild query set for just this platform as qs_mp_no_order is an MPQuerySet which has no filter() method
                self.kwargs['platforms'] = pns.split(',')
                platform_single = self.kwargs['platforms'][0]
                self.min_start_time = datetime.utcnow()
                self.max_end_time = datetime.utcfromtimestamp(0)
                # All Activities in the selection, do not inlcude 'special Activities' like LRAUV Mission
                for act in self.qs.filter(Q(platform__name=platform_single) & ~Q(activitytype__name=LRAUV_MISSION)):
                    if act.startdate < self.min_start_time:
                        self.min_start_time = act.startdate
                    if act.enddate > self.max_end_time:
                        self.max_end_time = act.enddate
                    # Set self.mpq.qs_mp to None to bypass the Singleton nature of MPQuery and have _build_mpq_queryset() build new self.mpq items
                    self.mpq.qs_mp = None
                    # Better to use 'exclude' to get remaining Activities so as to include those Activities
                    # (dorado_Gulper, daphne_Sipper, makai_ESP, etc.) that aren't in the checkbox list
                    if self.kwargs.get('exclude_ans'):
                        if act.name in self.kwargs.get('exclude_ans'):
                            continue
                    self.kwargs['activitynames'] = [act.name]
                    parameterID, platformName, contourparameterID, contourplatformName, parameterGroups, contourparameterGroups = self._build_mpq_queryset()
                    logger.info(f"Getting dataValues for pns='{pns}', act.name='{act.name}'")
                    cp = MeasuredParameter(self.kwargs, self.request, self.qs, self.mpq.qs_mp, self.contour_mpq.qs_mp_no_order,
                                            min_max, self.getSampleQS(), pns,
                                            parameterID, parameterGroups, contourplatformName, contourparameterID, contourparameterGroups)
                    x3d_items, shape_id_dict = cp.dataValuesX3D(platform_single, float(self.request.GET.get('ve', 10)), 
                                                                                   int(self.request.GET.get('slice_minutes', 30)))
                    if x3d_items:
                        x3d_dict.update(x3d_items)
                        try:
                            x3d_dict['shape_id_dict'].update(shape_id_dict)
                        except KeyError:
                            x3d_dict['shape_id_dict'] = {}
                            x3d_dict['shape_id_dict'].update(shape_id_dict)

                        try:
                            sec_interval = (cp.x[1] - cp.x[0]) * cp.scale_factor
                        except IndexError as e:
                            logger.warning(f"{e}: Likely no data in this slice.")
                            continue
                        if sec_interval < min_sec_interval and sec_interval > 0:
                            min_sec_interval = sec_interval

            self.kwargs['platforms'] = saved_platforms
            self.kwargs['activitynames'] = saved_activitynames
            if x3d_dict:
                x3d_dict['speedup'] = self._get_speedup({act.platform for act in self.qs})
                cycInt = (self.max_end_time - self.min_start_time).total_seconds() / x3d_dict['speedup']
                x3d_dict['timesensor'] = PlatformAnimation.timesensor_template.format(cycInt=cycInt)

                spaced_ts = np.arange(self.min_start_time.timestamp(), self.max_end_time.timestamp(), min_sec_interval)
                x3d_dict['limits'] = (0, len(spaced_ts))

                cp.makeColorBar(cp.colorbarPngFileFullPath, cp.pMinMax)
                x3d_dict['colorbar'] = cp.colorbarPngFile

        return x3d_dict

    def getPlatformAnimation(self):
        '''
        Based on the current selected query criteria for activities, 
        return the associated PlatformAnimation time series of X3D scene graph.
        If roll, pitch and yaw exist as the platform standard names include
        orientation angles, otherwise returns just the position animation scene.
        '''
        orientDict = {}
        if self.request.GET.get('showplatforms', False):
            self.mpq.qs_mp = None
            self.kwargs['activitynames'] = []
            parameterID, platformName, contourparameterID, contourplatformName, parameterGroups, contourparameterGroups = self._build_mpq_queryset()

            # Test if there are any X3D platform models in the selection
            platformsHavingModels = {pr.platform for pr in models.PlatformResource.objects.using(
                    self.dbname).filter(resource__resourcetype__name=X3DPLATFORMMODEL, 
                    platform__in=[a.platform for a in self.qs])}
            platforms_trajectories = {ar.activity.platform for ar in models.ActivityResource.objects.using(
                    self.dbname).filter(resource__name='featureType', resource__value='trajectory', 
                    activity__platform__in=[a.platform for a in self.qs])}
            # For detecting non-trajectory BEDS that have rotation data (ANGLE, AXIS_X, AXIS_Y, AXIS_Z)
            # This is a weak test (for just 'AXIS_X'), but with also weak consequences, maybe an error
            # reported to the UI if the other required Parameters are not present
            platforms_rotations = {ar.activity.platform for ar in models.ActivityResource.objects.using(
                    self.dbname).filter(activity__activityparameter__parameter__name='AXIS_X',
                        activity__platform__in=[a.platform for a in self.qs])}

            platforms_to_animate = platformsHavingModels & (platforms_trajectories | platforms_rotations)
            if platforms_to_animate:
                # Use qs_mp_no_parm QuerySet as it contains roll, pitch, and yaw values
                mppa = PlatformAnimation(platforms_to_animate, self.kwargs, 
                        self.request, self.qs, self.mpq.qs_mp_no_parm)
                speedup = self._get_speedup(platforms_to_animate)
                # Default vertical exaggeration is 10x and default geoorigin is empty string
                orientDict = mppa.platformAnimationDataValuesForX3D(
                                float(self.request.GET.get('ve', 10)), 
                                self.request.GET.get('geoorigin', ''), 
                                scale=1, speedup=speedup)
            
        return orientDict

    def getParameterPlatforms(self):
        '''
        Return hash of parmameter ids (keys) and the platforms (a list) that measured/sampled them
        '''
        ppHash = {}
        pp_qs = (models.ActivityParameter.objects.using(self.dbname)
                                         .filter(activity__in=self.qs)
                                         .values('parameter__id', 'activity__platform__name')
                                         .distinct())
        # Better to use 'exclude' to get remaining Activities so as to include those Activities
        # (dorado_Gulper, daphne_Sipper, makai_ESP, etc.) that aren't in the checkbox list
        if self.kwargs.get('exclude_ans'):
            pp_qs = pp_qs.exclude(activity__name__in=self.kwargs.get('exclude_ans'))

        for ap in pp_qs:
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
        logger.debug("Begining to loop though ActivityResource query to build netcdfHash...")
        # Original way of loading netCDF nc_global attributes
        nc_global_names = ['title', 'summary', 'comment']
        ars = models.ActivityResource.objects.using(self.dbname).filter(activity__in=self.qs
                    ,resource__name__in=nc_global_names
                    ).values('activity__platform__name', 'activity__name', 'activity__comment', 'resource__name', 'resource__value')
        if not ars:
            # Check if new way, since October 2022, of loading netCDF metadata Resources
            nc_global_names = ['nc_global.title', 'nc_global.summary', 'nc_global.comment']
            ars = models.ActivityResource.objects.using(self.dbname).filter(activity__in=self.qs
                        ,resource__name__in=nc_global_names
                        ).values('activity__platform__name', 'activity__name', 'activity__comment', 'resource__name', 'resource__value')
        for ar in models.ActivityResource.objects.using(self.dbname).filter(activity__in=self.qs
                        ,resource__name__in=nc_global_names + ['opendap_url']
                        ).values('activity__platform__name', 'activity__name', 'activity__comment', 'resource__name', 'resource__value', 'activity__loaded_date'):
            try:
                netcdfHash[ar['activity__platform__name']][ar['activity__name']][ar['resource__name']] = ar['resource__value']
                netcdfHash[ar['activity__platform__name']][ar['activity__name']]['comment'] = ar['activity__comment']
                netcdfHash[ar['activity__platform__name']][ar['activity__name']]['loaded_date'] = ar['activity__loaded_date']
            except KeyError:
                try:
                    netcdfHash[ar['activity__platform__name']][ar['activity__name']] = {}
                except KeyError:
                    netcdfHash[ar['activity__platform__name']] = {}
                    netcdfHash[ar['activity__platform__name']][ar['activity__name']] = {}

                netcdfHash[ar['activity__platform__name']][ar['activity__name']][ar['resource__name']] = ar['resource__value']
                netcdfHash[ar['activity__platform__name']][ar['activity__name']]['comment'] = ar['activity__comment']
                netcdfHash[ar['activity__platform__name']][ar['activity__name']]['loaded_date'] = ar['activity__loaded_date']

        logger.debug("Done building netcdfHash.")

        # Quick Look plots
        qlHash = defaultdict(lambda: defaultdict(dict))
        logger.debug("Begining to loop though ActivityResource query to build qlHash...")
        for ar in models.ActivityResource.objects.using(self.dbname).filter(activity__in=self.qs, resource__resourcetype__name='quick_look').values(
                        'activity__platform__name', 'activity__name', 'resource__name', 'resource__uristring'):
            logger.debug("activity__name = %s", ar['activity__name'])
            qlHash[ar['activity__platform__name']][ar['activity__name']][ar['resource__name']] = ar['resource__uristring']
        logger.debug("Done building qlHash.")

        # Campaign information
        c_hash = {}
        logger.debug("Begining to loop though ActivityResource query to build c_hash...")
        for cr in models.CampaignResource.objects.using(self.dbname).all():
            c_hash[cr.resource.name] = cr.resource.value

        logger.debug("Done building c_hash.")
        return {'netcdf': netcdfHash, 'quick_look': qlHash, 'campaign': c_hash}

    def getAttributes(self):
        '''
        Query for "Attributes" which are specific ResourceTypes or fields of other classes. Initially for tagged measurements
        and for finding comments about Samples, but can encompass any other way a STOQS database may be filtered os searched.
        May 2019: Added LRAUV Missions -- shoe-horning into the mplabel scheme developed for machine learning, cause it mostly fits.
        '''
        measurementHash = {}

        sources = models.ResourceResource.objects.using(self.dbname).filter(toresource__name=COMMANDLINE
                                ).values_list('fromresource__resourcetype__name', 'toresource__value').distinct()

        if sources:
            logger.debug('Building commandlines element in measurementHash...')
            measurementHash['commandlines'] = dict((s[0], s[1]) for s in sources)
        else:
            # Check for LRAUV Missions
            sources = (models.ResourceResource.objects.using(self.dbname)
                                              .filter(toresource__name=LRAUV_MISSION)
                                              .values_list('fromresource__resourcetype__name', 'toresource__value')
                                              .distinct())
            if sources:
                logger.debug('Building "syslogs" element in measurementHash...')
                measurementHash['commandlines'] = dict((s[0], s[1]) for s in sources)

        for mpr in models.MeasuredParameterResource.objects.using(self.dbname).filter(activity__in=self.qs
                        ,resource__name__in=[LABEL, LRAUV_MISSION]).values( 'resource__resourcetype__name', 'resource__value', 
                        'resource__id').distinct().order_by('resource__value'):

            # Include all description resources associated with this label
            descriptions = ' '.join(models.ResourceResource.objects.using(self.dbname).filter(fromresource__id=mpr['resource__id'], 
                            toresource__name=DESCRIPTION).values_list('toresource__value', flat=True))
            try:
                measurementHash[mpr['resource__resourcetype__name']].append((mpr['resource__id'], mpr['resource__value'], descriptions))
            except KeyError:
                measurementHash[mpr['resource__resourcetype__name']] = []
                measurementHash[mpr['resource__resourcetype__name']].append((mpr['resource__id'], mpr['resource__value'], descriptions))

        logger.debug('Returning from getAttributes with  measurementHash = %s', measurementHash)

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

    def _measuredparametersgroupQ(self, parameterid, fromTable='Activity'):
        '''
        Build a Q object to be added to the current queryset as a filter.  This should 
        ensure that our result doesn't contain any parameters that were not selected.
        '''
        q = Q()
        if parameterid is None:
            return q
        else:
            if fromTable == 'Activity':
                q = Q(activityparameter__parameter__id__in=parameterid)
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
        Return Q object that is True if the activity is of featureType trajectoryProfile
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
        # Better to use 'exclude' to get remaining Activities so as to include those Activities
        # (dorado_Gulper, daphne_Sipper, makai_ESP, etc.) that aren't in the checkbox list
        if self.kwargs.get('exclude_ans'):
            qs = qs.exclude(name__in=self.kwargs.get('exclude_ans'))

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
        # Better to use 'exclude' to get remaining Activities so as to include those Activities
        # (dorado_Gulper, daphne_Sipper, makai_ESP, etc.) that aren't in the checkbox list
        if self.kwargs.get('exclude_ans'):
            qs = qs.exclude(instantpoint__activity__name__in=self.kwargs.get('exclude_ans'))

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
                qs_ext = self.qs.aggregate(Extent(geom_field))
                extentList.append(qs_ext[geom_field + '__extent'])
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
        geom_union = None
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
                        logger.debug('Unioning extent = %s as a Point', extent)
                        geom_union = geom_union.union(Point(*extent[:2], srid=srid))
                    else:
                        logger.debug('Unioning extent = %s as a LINESTRING', extent)
                        geom_union = geom_union.union(fromstr('LINESTRING (%s %s, %s %s)' % extent, srid=srid))

            # Aggressive try/excepts done here for better reporting on the production servers
            if geom_union:
                logger.debug('Final geom_union = %s', geom_union)
            else:
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

            # Compute midpoint of extent for use in GeoViewpoint for Virtual Reality (WebVR) viewpoint setting
            lon_midpoint = (extent[0][0] + extent[1][0]) / 2.0
            lat_midpoint = (extent[0][1] + extent[1][1]) / 2.0
            qs = self.qs.aggregate(Max('maxdepth'), Min('mindepth'))
            depth_midpoint = (qs['mindepth__min'] + qs['maxdepth__max']) / 2.0
            if np.isnan(depth_midpoint):
                depth_midpoint = 0.0

            try:
                extent.transform(outputSRID)
            except:
                logger.exception('Cannot get transorm to %s for geomstr = %s, srid = %d', outputSRID, geomstr, srid)
        
            logger.debug('Returning from getExtent() with extent = %s', extent)

        return (extent, lon_midpoint, lat_midpoint, depth_midpoint)

