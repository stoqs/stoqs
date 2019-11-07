__author__    = 'Mike McCann'
__copyright__ = '2012'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

MeasuredParameter Query class for managing aspects of building requests for MeasuredParameter datavalues.
Intended to be used by utils/STOQSQManager.py for preventing multiple traversals of qs_mp and by
views/__init__.py to support query by parameter value for the REST responses.

This module (though called MPQuery) also contains and SPQuerySet class to handle the Sample portion of 
the STOQS data model. Sample and Measurment are almost synonomous, expecially with their relationships
to InstantPoint and SampledParameter/MeasuredParameter.  The MPQuery class has a lot of machinery that
for which checks are made on which ParameterGroup the Parameter belongs to execute to proper code for
a Sample or a Measurement.

@undocumented: __doc__ parser
@status: production
@license: GPL
'''
from django.conf import settings
from django.db.models.query import REPR_OUTPUT_SIZE, RawQuerySet, QuerySet
from django.db import DatabaseError
from datetime import datetime
from stoqs.models import MeasuredParameter, Parameter, SampledParameter, ParameterGroupParameter, MeasuredParameterResource
from .utils import postgresifySQL, getGet_Actual_Count, getParameterGroups
from loaders import MEASUREDINSITU
from loaders.SampleLoaders import SAMPLED
from .PQuery import PQuery
import logging
import pprint
import re
import locale
import time
import os
import tempfile
import sqlparse

logger = logging.getLogger(__name__)

ITER_HARD_LIMIT = 1000000

class MPQuerySet(object):
    '''
    A class to simulate a QuerySet that's suitable for use everywhere a QuerySet may be used.
    This special class supports adapting MeasuredParameter RawQuerySets to make them look like regular
    QuerySets.  See: http://ramenlabs.com/2010/12/08/how-to-quack-like-a-queryset/.  (I looked at Google
    again to see if self-joins are possible in Django, and confirmed that they are probably not.  
    See: http://stackoverflow.com/questions/1578362/self-join-with-django-orm.)
    '''
    rest_columns = [ 'parameter__id',
                     'parameter__name',
                     'parameter__standard_name',
                     'measurement__depth',
                     'measurement__geom',
                     'measurement__instantpoint__timevalue', 
                     'measurement__instantpoint__activity__name',
                     'measurement__instantpoint__activity__platform__name',
                     'measurement__nominallocation__depth', 
                     'datavalue',
                     'parameter__units'
                   ]
    kml_columns = [  'parameter__name',
                     'parameter__standard_name',
                     'measurement__depth',
                     'measurement__geom',
                     'measurement__instantpoint__timevalue', 
                     'measurement__instantpoint__activity__platform__name',
                     'datavalue',
                   ]
    ui_timedepth_columns = [  
                     'measurement__depth',
                     'measurement__instantpoint__timevalue', 
                     'measurement__instantpoint__activity__name',
                     'datavalue',
                   ]

    def __init__(self, dbAlias, query, values_list, qs_mp=None):
        '''
        Initialize MPQuerySet with either raw SQL in @query or a QuerySet in @qs_mp.
        Use @values_list to request just the fields (columns) needed.  The class variables
        rest_colums and kml_columns are typical value_lists.  Note: specifying a values_list
        appears to break the correct serialization of geometry types in the json response.
        Called by stoqs/views/__init__.py when MeasuredParameter REST requests are made.
        '''
        self.isRawQuerySet = False
        if query is None and qs_mp is not None:
            logger.debug('query is None and qs_mp is not None')
            self.query = postgresifySQL(str(qs_mp.query))
            self.mp_query = qs_mp
        elif query is not None and qs_mp is None:
            logger.debug('query is not None and qs_mp is None')
            self.query = query
            query = PQuery.addPrimaryKey(query)
            self.mp_query = MeasuredParameter.objects.using(dbAlias).raw(query)
            self.isRawQuerySet = True
        else:
            raise Exception('Either query or qs_mp must be not None and the other be None.')

        self.dbAlias = dbAlias
        self.values_list = values_list
        self.ordering = ('id',)
        self._count = None

    def __iter__(self):
        '''
        Main way to access data that is used by interators in templates, etc.
        Simulate behavior of regular QuerySets.  Modify & format output as needed.
        '''
        minimal_values_list = False
        for item in self.rest_columns:
            if item not in self.values_list:
                minimal_values_list = True
                break
        logger.debug('minimal_values_list = %s', minimal_values_list)

        logger.debug('self.query = %s', self.query)
        logger.debug('type(self.mp_query) = %s', type(self.mp_query))

        # Must have model instance objects for JSON serialization of geometry fields to work right
        if minimal_values_list:
            # Likely for Flot contour plot
            try:
                # Dictionaries
                for mp in self.mp_query[:ITER_HARD_LIMIT]:
                    # TODO: Fix this to make it a more performant generator - making row takes time
                    row = { 'measurement__depth': mp['measurement__depth'],
                            'measurement__instantpoint__timevalue': mp['measurement__instantpoint__timevalue'],
                            'measurement__instantpoint__activity__name': mp['measurement__instantpoint__activity__name'],
                            'datavalue': mp['datavalue'],
                          }
                    yield row

            except TypeError:
                for mp in self.mp_query[:ITER_HARD_LIMIT]:
                    row = { 'measurement__depth': mp.measurement.depth,
                            'measurement__instantpoint__timevalue': mp.measurement.instantpoint.timevalue,
                            'measurement__instantpoint__activity__name': mp.measurement.instantpoint.activity.name,
                            'datavalue': mp.datavalue,
                          }
                    yield row

        else:
            # Likely for building a REST or KML response
            logger.debug('type(self.mp_query) = %s', type(self.mp_query))
            try:
                # Dictionaries
                for mp in self.mp_query[:ITER_HARD_LIMIT]:
                    row = { 
                            'measurement__depth': mp['measurement__depth'],
                            'parameter__id': mp['parameter__id'],
                            'parameter__name': mp['parameter__name'],
                            'datavalue': mp['datavalue'],
                            'measurement__instantpoint__timevalue': mp['measurement__instantpoint__timevalue'],
                            'parameter__standard_name': mp['parameter__standard_name'],
                            'measurement__instantpoint__activity__name': mp['measurement__instantpoint__activity__name'],
                            'measurement__instantpoint__activity__platform__name': mp['measurement__instantpoint__activity__platform__name'],
                            # If .values(...) are requested in the query string then json serialization of the point geometry does not work right
                            'measurement__geom': mp['measurement__geom'],
                            'parameter__units': mp['parameter__units'],
                          }
                    yield row

            except (TypeError, AttributeError):
                # Model objects
                for mp in self.mp_query[:ITER_HARD_LIMIT]:
                    row = { 
                            'measurement__depth': mp.measurement.depth,
                            'parameter__id': mp.parameter__id,
                            'parameter__name': mp.parameter__name,
                            'datavalue': mp.datavalue,
                            'measurement__instantpoint__timevalue': mp.measurement.instantpoint.timevalue,
                            'parameter__standard_name': mp.parameter.standard_name,
                            'measurement__instantpoint__activity__name': mp.measurement.instantpoint.activity.name,
                            'measurement__instantpoint__activity__platform__name': mp.measurement.instantpoint.activity.platform.name,
                            'measurement__geom': mp.measurement.geom,
                            'parameter__units': mp.parameter.units,
                          }
                    yield row
 
    def __repr__(self):
        data = list(self[:REPR_OUTPUT_SIZE + 1])
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."
        return repr(data)
 
    def __getitem__(self, k):
        '''
        Boiler plate copied from http://ramenlabs.com/2010/12/08/how-to-quack-like-a-queryset/.  
        Is used for slicing data, e.g. for subsampling data for sensortracks
        '''
        if not isinstance(k, (slice, int)):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0))
                or (isinstance(k, slice) and (k.start is None or k.start >= 0)
                    and (k.stop is None or k.stop >= 0))), \
                "Negative indexing is not supported."
 
        if isinstance(k, slice):
            return self.mp_query[k]

    def count(self):
        # self.mp_query should contain no 'ORDER BY' as ensured by the routine that calls .count()
        if self._count is not None:
            return self._count

        try:
            logger.debug('Counting records in self.mp_query which is of type = %s', type(self.mp_query))
            self._count = self.mp_query.count()
            logger.debug('self._count = %d as retreived from self.mp_query.count()', self._count)
        except AttributeError:
            try:
                self._count = sum(1 for mp in self.mp_query)
                logger.debug('self._count = %d as retreived from sum(1 for mp in self.mp_query)', self._count)
            except DatabaseError:
                return 0
        return self._count
 
    def all(self):
        return self._clone()
 
    def filter(self, *args, **kwargs):
        qs = self._clone()
        try:
            qs.mp_query = qs.mp_query.filter(*args, **kwargs)
        except AttributeError as e:
            logger.warn(str(e))

        return qs.mp_query
 
    def exclude(self, *args, **kwargs):
        qs = self._clone()
        qs.mp_query = qs.mp_query.exclude(*args, **kwargs)
        return qs.mp_query
 
    def order_by(self, *args, **kwargs):
        qs = self._clone()
        qs.mp_query = qs.mp_query.order_by(*args, **kwargs)
        return qs.mp_query
 
    def _clone(self):
        qs = MPQuerySet(self.dbAlias, self.query, self.values_list)
        try:
            qs.mp_query = self.mp_query._clone()
        except AttributeError as e:
            logger.warn(str(e))

        return qs 
 



class SPQuerySet(object):
    '''
    A class to simulate a QuerySet that's suitable for use everywhere a QuerySet may be used.
    This special class supports adapting SampledParameter RawQuerySets to make them look like regular
    QuerySets.  See: http://ramenlabs.com/2010/12/08/how-to-quack-like-a-queryset/.  (I looked at Google
    again to see if self-joins are possible in Django, and confirmed that they are probably not.  
    See: http://stackoverflow.com/questions/1578362/self-join-with-django-orm.)
    '''
    rest_columns = [ 'parameter__id',
                     'parameter__name',
                     'parameter__standard_name',
                     'sample__depth',
                     'sample__geom',
                     'sample__instantpoint__timevalue', 
                     'sample__instantpoint__activity__name',
                     'sample__instantpoint__activity__platform__name',
                     'sample__instantpoint__activity__startdate',
                     'sample__instantpoint__activity__enddate',
                     'sample__instantpoint__activity__mindepth',
                     'sample__instantpoint__activity__maxdepth',
                     'datavalue',
                     'parameter__units'
                   ]
    kml_columns = [  'parameter__name',
                     'parameter__standard_name',
                     'sample__depth',
                     'sample__geom',
                     'sample__instantpoint__timevalue', 
                     'sample__instantpoint__activity__platform__name',
                     'datavalue',
                   ]
    ui_timedepth_columns = [  
                     'sample__depth',
                     'sample__instantpoint__timevalue', 
                     'sample__instantpoint__activity__name',
                     'sample__instantpoint__activity__startdate',
                     'sample__instantpoint__activity__enddate',
                     'sample__instantpoint__activity__mindepth',
                     'sample__instantpoint__activity__maxdepth',
                     'datavalue',
                   ]

    def __init__(self, dbAlias, query, values_list, qs_sp=None):
        '''
        Initialize SPQuerySet with either raw SQL in @query or a QuerySet in @qs_sp.
        Use @values_list to request just the fields (columns) needed.  The class variables
        rest_colums and kml_columns are typical value_lists.  Note: specifying a values_list
        appears to break the correct serialization of geometry types in the json response.
        Called by stoqs/views/__init__.py when SampledParameter REST requests are made.
        '''
        if query is None and qs_sp is not None:
            logger.debug('query is None and qs_sp is not None')
            self.query = postgresifySQL(str(qs_sp.query))
            self.sp_query = qs_sp
        elif query is not None and qs_sp is None:
            logger.debug('query is not None and qs_sp is None')
            self.query = query
            self.sp_query = SampledParameter.objects.using(dbAlias).raw(query)
        else:
            raise Exception('Either query or qs_sp must be not None and the other be None.')

        self.dbAlias = dbAlias
        self.values_list = values_list
        self.ordering = ('id',)
 
    def __iter__(self):
        '''
        Main way to access data that is used by interators in templates, etc.
        Simulate behavior of regular QuerySets.  Modify & format output as needed.
        '''
        minimal_values_list = False
        for item in self.rest_columns:
            if item not in self.values_list:
                minimal_values_list = True
                break
        logger.debug('minimal_values_list = %s', minimal_values_list)

        logger.debug('self.query = %s', self.query)
        logger.debug('type(self.sp_query) = %s', type(self.sp_query))

        if isinstance(self.sp_query, QuerySet):
            logger.debug('self.sp_query is QuerySet')
        if isinstance(self.sp_query, RawQuerySet):
            logger.debug('self.sp_query is RawQuerySet')

        # Must have model instance objects for JSON serialization of geometry fields to work right
        if minimal_values_list:
            # Likely for Flot contour plot
            try:
                # Dictionaries
                for mp in self.sp_query[:ITER_HARD_LIMIT]:
                    row = { 'sample__depth': mp['sample__depth'],
                            'sample__instantpoint__timevalue': mp['sample__instantpoint__timevalue'],
                            'sample__instantpoint__activity__name': mp['sample__instantpoint__activity__name'],
                            'datavalue': mp['datavalue'],
                          }
                    yield row

            except TypeError:
                # Model instances
                for mp in self.sp_query[:ITER_HARD_LIMIT]:
                    row = { 'sample__depth': mp.sample.depth,
                            'sample__instantpoint__timevalue': mp.sample.instantpoint.timevalue,
                            'sample__instantpoint__activity__name': mp.sample.instantpoint.activity.name,
                            'datavalue': mp.datavalue,
                          }
                    yield row

        else:
            # Likely for building a REST or KML response
            logger.debug('type(self.sp_query) = %s', type(self.sp_query))
            try:
                # Dictionaries
                for mp in self.sp_query[:ITER_HARD_LIMIT]:
                    row = { 
                            'sample__depth': mp['sample__depth'],
                            'parameter__id': mp['parameter__id'],
                            'parameter__name': mp['parameter__name'],
                            'datavalue': mp['datavalue'],
                            'sample__instantpoint__timevalue': mp['sample__instantpoint__timevalue'],
                            'parameter__standard_name': mp['parameter__standard_name'],
                            'sample__instantpoint__activity__name': mp['sample__instantpoint__activity__name'],
                            'sample__instantpoint__activity__platform__name': mp['sample__instantpoint__activity__platform__name'],
                            # If .values(...) are requested in the query string then json serialization of the point geometry does not work right
                            'sample__geom': mp['sample__geom'],
                            'parameter__units': mp['parameter__units'],
                          }
                    yield row

            except TypeError:
                # Model instances
                for mp in self.sp_query[:ITER_HARD_LIMIT]:
                    row = { 
                            'sample__depth': mp.sample.depth,
                            'parameter__id': mp.parameter__id,
                            'parameter__name': mp.parameter__name,
                            'datavalue': mp.datavalue,
                            'sample__instantpoint__timevalue': mp.sample.instantpoint.timevalue,
                            'parameter__standard_name': mp.parameter.standard_name,
                            'sample__instantpoint__activity__name': mp.sample.instantpoint.activity.name,
                            'sample__instantpoint__activity__platform__name': mp.sample.instantpoint.activity.platform.name,
                            'sample__geom': mp.sample.geom,
                            'parameter__units': mp.parameter.units,
                          }
                    yield row
 
    def __repr__(self):
        data = list(self[:REPR_OUTPUT_SIZE + 1])
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."
        return repr(data)
 
    def __getitem__(self, k):
        '''
        Boiler plate copied from http://ramenlabs.com/2010/12/08/how-to-quack-like-a-queryset/.  
        Is used for slicing data, e.g. for subsampling data for sensortracks
        '''
        if not isinstance(k, (slice, int)):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0))
                or (isinstance(k, slice) and (k.start is None or k.start >= 0)
                    and (k.stop is None or k.stop >= 0))), \
                "Negative indexing is not supported."
 
        if isinstance(k, slice):
            return self.sp_query[k]

    def count(self):
        logger.debug('Counting records in self.sp_query which is of type = %s', type(self.sp_query))
        # self.sp_query should contain no 'ORDER BY' as ensured by the routine that calls .count()
        try:
            c = self.sp_query.count()
            logger.debug('c = %d as retreived from self.sp_query.count()', c)
        except AttributeError:
            try:
                c = sum(1 for mp in self.sp_query)
                logger.debug('c = %d as retreived from sum(1 for mp in self.sp_query)', c)
            except DatabaseError:
                return 0
        return c
 
    def all(self):
        return self._clone()
 
    def filter(self, *args, **kwargs):
        qs = self._clone()
        logger.debug('type(qs) = %s', type(qs))
        qs.sp_query = qs.sp_query.filter(*args, **kwargs)
        return qs.sp_query
 
    def exclude(self, *args, **kwargs):
        qs = self._clone()
        qs.sp_query = qs.sp_query.exclude(*args, **kwargs)
        return qs.sp_query
 
    def order_by(self, *args, **kwargs):
        qs = self._clone()
        qs.sp_query = qs.sp_query.order_by(*args, **kwargs)
        return qs.sp_query
 
    def _clone(self):
        qs = SPQuerySet(self.dbAlias, self.query, self.values_list)
        qs.sp_query = self.sp_query._clone()
        return qs 



class MPQuery(object):
    '''
    This class is designed to handle building and managing queries against the MeasuredParameter table of the STOQS database.
    Special tooling is needed to perform parameter value queries which require building raw sql statements in order to
    execute the self joins needed on the measuredparameter table.  The structure of RawQuerySet returned is harmonized
    with the normal QuerySet returned through regular .filter() operations by using the MPQuerySet "adapter".
    '''
    rest_select_items = '''stoqs_parameter.id as parameter__id,
                         stoqs_parameter.name as parameter__name,
                         stoqs_parameter.standard_name as parameter__standard_name,
                         stoqs_measurement.depth as measurement__depth,
                         stoqs_measurement.geom as measurement__geom,
                         stoqs_instantpoint.timevalue as measurement__instantpoint__timevalue, 
                         stoqs_platform.name as measurement__instantpoint__activity__platform__name,
                         stoqs_measuredparameter.datavalue as datavalue,
                         stoqs_parameter.units as parameter__units'''
    sampled_rest_select_items = '''stoqs_parameter.id as parameter__id,
                         stoqs_parameter.name as parameter__name,
                         stoqs_parameter.standard_name as parameter__standard_name,
                         stoqs_sample.depth as sample__depth,
                         stoqs_sample.geom as sample__geom,
                         stoqs_instantpoint.timevalue as sample__instantpoint__timevalue, 
                         stoqs_platform.name as sample__instantpoint__activity__platform__name,
                         stoqs_sampledparameter.datavalue as datavalue,
                         stoqs_parameter.units as parameter__units'''


    kml_select_items = ''
    contour_select_items = ''

    def __init__(self, request):
        '''
        This object saves instances of the QuerySet and count so that get_() methods work like a singleton to 
        return the value for the object.  MPQuery objects are meant to be instantiated by the STOQSQManager 
        buildQuerySet() method and are unique for each AJAX request.  After buildMPQuerySet() is executed
        the member values below can be accessed.
        '''
        self.request = request
        self.qs_mp = None
        self.qs_mp_no_order = None
        self.qs_sp = None
        self.qs_sp_no_order = None
        self.sql = None
        self._count = None
        self._MProws = []
        self.parameterID = None
        self.initialQuery = False
        
    def buildMPQuerySet(self, *args, **kwargs):
        '''
        Build the query set based on selections from the UI. For the first time through kwargs will be empty 
        and self.qs_mp will have no constraints and will be all of the MeasuredParameters in the database.
        This is called by utils/STOQSQueryManagery.py.  On successful completion one or more member query
        sets will be available: qs_sp, qs_mp, qs_sp_no_order, qs_mp_no_order, with coresponding SQL
        strings: sql_sp, sql_mp.
        '''
        if self.qs_mp is None:
            parameterGroups = [MEASUREDINSITU]
            self.kwargs = kwargs
            if 'parameterplot' in self.kwargs:
                if self.kwargs['parameterplot'][0]:
                    self.parameterID = self.kwargs['parameterplot'][0]
            if 'parameterplot_id' in self.kwargs:
                if self.kwargs['parameterplot_id'] is not None:
                    # Override UI selected parameterplot so as to resuse this code for parametercontourplot
                    self.parameterID = self.kwargs['parameterplot_id']
            if self.parameterID is not None:
                logger.debug('self.parameterID = %s', self.parameterID)
                parameter = Parameter.objects.using(self.request.META['dbAlias']).get(id=self.parameterID)
                parameterGroups = getParameterGroups(self.request.META['dbAlias'], parameter)

            if SAMPLED in parameterGroups:
                self.qs_sp = self.getSampledParametersQS()
                if self.kwargs['showparameterplatformdata']:
                    logger.debug('Building qs_sp_no_order with values_list = %s', SPQuerySet.ui_timedepth_columns)
                    self.qs_sp_no_order = self.getSampledParametersQS(SPQuerySet.ui_timedepth_columns, orderedFlag=False)
                else:
                    self.qs_sp_no_order = self.getSampledParametersQS(orderedFlag=False)
                self.sql_sp = self.getSampledParametersPostgreSQL()
            else:
                # The default is to consider the Parameter MEASUREDINSITU if it's not SAMPLED
                self.qs_mp = self.getMeasuredParametersQS()
                if self.kwargs['showparameterplatformdata']:
                    logger.debug('Building qs_mp_no_order with values_list = %s', MPQuerySet.ui_timedepth_columns)
                    self.qs_mp_no_order = self.getMeasuredParametersQS(MPQuerySet.ui_timedepth_columns, orderedFlag=False)
                else:
                    self.qs_mp_no_order = self.getMeasuredParametersQS(orderedFlag=False)
                self.sql = self.getMeasuredParametersPostgreSQL()

    def _getQueryParms(self, group=MEASUREDINSITU):
        '''
        Extract constraints from the querystring kwargs to construct a dictionary of query parameters
        that can be used as a filter for MeasuredParameters.  Handles all constraints except parameter
        value constraints.
        '''
        qparams = {}

        ##logger.debug('self.kwargs = %s', pprint.pformat(self.kwargs))
        logger.debug('group = %s', group)
        if group == SAMPLED:
            if 'sampledparametersgroup' in self.kwargs:
                if self.kwargs['sampledparametersgroup']:
                    qparams['parameter__id__in'] = self.kwargs['sampledparametersgroup']
            if 'parameterstandardname' in self.kwargs:
                if self.kwargs['parameterstandardname']:
                    qparams['parameter__standard_name__in'] = self.kwargs['parameterstandardname']
            
            if 'platforms' in self.kwargs:
                if self.kwargs['platforms']:
                    qparams['sample__instantpoint__activity__platform__name__in'] = self.kwargs['platforms']
            if 'time' in self.kwargs:
                if self.kwargs['time'][0] is not None:
                    qparams['sample__instantpoint__timevalue__gte'] = self.kwargs['time'][0]
                if self.kwargs['time'][1] is not None:
                    qparams['sample__instantpoint__timevalue__lte'] = self.kwargs['time'][1]
            if 'depth' in self.kwargs:
                if self.kwargs['depth'][0] is not None:
                    qparams['sample__depth__gte'] = self.kwargs['depth'][0]
                if self.kwargs['depth'][1] is not None:
                    qparams['sample__depth__lte'] = self.kwargs['depth'][1]
            if 'activitynames' in self.kwargs:
                if self.kwargs['activitynames']:
                    qparams['sample__instantpoint__activity__name__in'] = self.kwargs['activitynames']
    
            if getGet_Actual_Count(self.kwargs):
                # Make sure that we have at least time so that the instantpoint table is included
                if not 'sample__instantpoint__timevalue__gte' in qparams:
                    qparams['sample__instantpoint__pk__isnull'] = False

        else: 
            if 'measuredparametersgroup' in self.kwargs:
                if self.kwargs['measuredparametersgroup']:
                    qparams['parameter__id__in'] = self.kwargs['measuredparametersgroup']
            if 'parameterstandardname' in self.kwargs:
                if self.kwargs['parameterstandardname']:
                    qparams['parameter__standard_name__in'] = self.kwargs['parameterstandardname']
            
            if 'platforms' in self.kwargs:
                if self.kwargs['platforms']:
                    qparams['measurement__instantpoint__activity__platform__name__in'] = self.kwargs['platforms']
            if 'time' in self.kwargs:
                if self.kwargs['time'][0] is not None:
                    qparams['measurement__instantpoint__timevalue__gte'] = self.kwargs['time'][0]
                if self.kwargs['time'][1] is not None:
                    qparams['measurement__instantpoint__timevalue__lte'] = self.kwargs['time'][1]
            if 'depth' in self.kwargs:
                if self.kwargs['depth'][0] is not None:
                    qparams['measurement__depth__gte'] = self.kwargs['depth'][0]
                if self.kwargs['depth'][1] is not None:
                    qparams['measurement__depth__lte'] = self.kwargs['depth'][1]
            if 'activitynames' in self.kwargs:
                if self.kwargs['activitynames']:
                    qparams['measurement__instantpoint__activity__name__in'] = self.kwargs['activitynames']
                    logger.debug(f"qparams['measurement__instantpoint__activity__name__in'] = {qparams['measurement__instantpoint__activity__name__in']}")

            if 'mplabels'  in self.kwargs:
                if self.kwargs['mplabels' ]:
                    qparams['measurement__id__in'] = MeasuredParameterResource.objects.using(self.request.META['dbAlias']).filter(
                                        resource__id__in=self.kwargs['mplabels' ]).values_list('measuredparameter__measurement__id', flat=True)

            if getGet_Actual_Count(self.kwargs):
                # Make sure that we have at least time so that the instantpoint table is included
                if 'measurement__instantpoint__timevalue__gte' not in qparams:
                    qparams['measurement__instantpoint__pk__isnull'] = False

        logger.debug('Strings may be split on spaces in the following "pretty print"')
        logger.debug('qparams = %s', pprint.pformat(qparams))

        return qparams

    def getMeasuredParametersQS(self, values_list=[], orderedFlag=True):
        '''
        Return query set of MeasureedParameters given the current constraints.  If no parameter is selected return None.
        @values_list can be assigned with additional columns that are supported by MPQuerySet(). Note that specificiation
        of a values_list will break the JSON serialization of geometry types. @orderedFlag may be set to False to reduce
        memory and time taken for queries that don't need ordered values.  If parameterID is not none then that parameter
        is added to the filter - used for parameterPlatformPNG generation.
        '''
        qparams = self._getQueryParms()
        logger.debug('Building qs_mp...')
        if values_list == []:
            # If no .values(...) added to QS then items returned by iteration on qs_mp are model objects, not out wanted dictionaries
            logger.debug('... with values_list = []; using default rest_columns')
            qs_mp = MeasuredParameter.objects.using(self.request.META['dbAlias']).filter(**qparams).values(*MPQuerySet.rest_columns)
        else:
            logger.debug('... with values_list = %s', values_list)
            # May need select_related(...)
            qs_mp = MeasuredParameter.objects.using(self.request.META['dbAlias']).filter(**qparams).values(*values_list)

        if orderedFlag:
            qs_mp = qs_mp.order_by('measurement__instantpoint__activity__name', 'measurement__instantpoint__timevalue', 'parameter__name')

        # Save ordered queryset with no parameter in the filter for X3D display to get roll, pitch, and yaw
        self.qs_mp_no_parm = qs_mp

        # If the parametertimeplotid is selected from the UI then we need to have that filter in the QuerySet
        # before doing any raw SQL construction.  Use the qs_mp_no_parm member for QuerySets that shouldn't
        # be filtered by the parametertimeplotid, e.g. parametertime, 3D animation, etc.
        if self.parameterID:
            logger.debug('Adding parameter__id=%d filter to qs_mp', int(self.parameterID))
            qs_mp = qs_mp.filter(parameter__id=int(self.parameterID))

        # Wrap MPQuerySet around either RawQuerySet or QuerySet to control the __iter__() items for lat/lon etc.
        if 'parametervalues' in self.kwargs:
            if self.kwargs['parametervalues']:
                # Start with fresh qs_mp without .values()
                qs_mp = MeasuredParameter.objects.using(self.request.META['dbAlias']).select_related(
                            'measurement__instantpoint__activity__platform').filter(**qparams)
                if self.parameterID:
                    qs_mp = qs_mp.filter(parameter__id=int(self.parameterID))

                if orderedFlag:
                    qs_mp = qs_mp.order_by('measurement__instantpoint__activity__name', 'measurement__instantpoint__timevalue', 'parameter__name')

                sql = postgresifySQL(str(qs_mp.query))
                logger.debug('\n\nsql before query = %s\n\n', sql)
                pq = PQuery(self.request)
                sql = pq.addParameterValuesSelfJoins(sql, self.kwargs['parametervalues'], select_items=self.rest_select_items)
                logger.debug('\n\nsql after parametervalue query = %s\n\n', sql)
                qs_mpq = MPQuerySet(self.request.META['dbAlias'], sql, values_list)
            else:
                logger.debug('Building MPQuerySet with qs_mpquery = %s', str(qs_mp.query))
                qs_mpq = MPQuerySet(self.request.META['dbAlias'], None, values_list, qs_mp=qs_mp)
        else:
            logger.debug('Building MPQuerySet with qs_mpquery = %s', str(qs_mp.query))
            qs_mpq = MPQuerySet(self.request.META['dbAlias'], None, values_list, qs_mp=qs_mp)

        if qs_mpq is None:
            logger.debug('qs_mpq.query = %s', str(qs_mpq.query))
        else:
            logger.debug('Strings may be split on spaces in the following "pretty print"')
            logger.debug("No queryset returned for qparams = %s", pprint.pformat(qparams))

        return qs_mpq

    def getSampledParametersQS(self, values_list=[], orderedFlag=True):
        '''
        Return query set of SampledParameters given the current constraints.  If no parameter is selected return None.
        @values_list can be assigned with additional columns that are supported by SPQuerySet(). Note that specificiation
        of a values_list will break the JSON serialization of geometry types. @orderedFlag may be set to False to reduce
        memory and time taken for queries that don't need ordered values.  If parameterID is not none then that parameter
        is added to the filter - used for parameterPlatformPNG generation.
        '''
        qparams = self._getQueryParms(group=SAMPLED)
        logger.debug('Building qs_sp...')
        if values_list == []:
            # If no .values(...) added to QS then items returned by iteration on qs_sp are model objects, not out wanted dictionaries
            values_list = SPQuerySet.rest_columns
            qs_sp = SampledParameter.objects.using(self.request.META['dbAlias']).filter(**qparams).values(*values_list)
        else:
            # May need select_related(...)
            qs_sp = SampledParameter.objects.using(self.request.META['dbAlias']).filter(**qparams).values(*values_list)

        # Save ordered queryset with no parameter in the filter for X3D display to get roll, pitch, and yaw
        self.qs_sp_no_parm = qs_sp

        # If the parametertimeplotid is selected from the UI then we need to have that filter in the QuerySet
        # before doing the raw SQL construction.  Use the qs_mp_no_parm member for QuerySets that shouldn't
        # be filtered by the parametertimeplotid, e.g. parametertime, 3D animation, etc
        if self.parameterID:
            logger.debug('Adding parameter__id=%d filter to qs_sp', int(self.parameterID))
            qs_sp = qs_sp.filter(parameter__id=int(self.parameterID))

        if orderedFlag:
            qs_sp = qs_sp.order_by('sample__instantpoint__activity__name', 'sample__instantpoint__timevalue', 'parameter__name')

        # Wrap SPQuerySet around either RawQuerySet or QuerySet to control the __iter__() items for lat/lon etc.
        if 'parametervalues' in self.kwargs:
            if self.kwargs['parametervalues']:
                # A depth of 4 is needed in order to see Platform
                qs_sp = SampledParameter.objects.using(self.request.META['dbAlias']).select_related(
                            'sample__instantpoint__activity__platform').filter(**qparams)
                if orderedFlag:
                    qs_sp = qs_sp.order_by('sample__instantpoint__activity__name', 'sample__instantpoint__timevalue', 'parameter__name')
                sql = postgresifySQL(str(qs_sp.query))
                logger.debug('\n\nsql before query = %s\n\n', sql)
                pq = PQuery(self.request)
                sql = pq.addParameterValuesSelfJoins(sql, self.kwargs['parametervalues'], select_items=self.sampled_rest_select_items)
                logger.debug('\n\nsql after parametervalue query = %s\n\n', sql)
                qs_spq = SPQuerySet(self.request.META['dbAlias'], sql, values_list)
            else:
                logger.debug('Building SPQuerySet for SampledParameter...')
                qs_spq = SPQuerySet(self.request.META['dbAlias'], None, values_list, qs_sp=qs_sp)
        else:
            logger.debug('Building SPQuerySet for SampledParameter...')
            qs_spq = SPQuerySet(self.request.META['dbAlias'], None, values_list, qs_sp=qs_sp)

        if qs_spq is None:
            logger.debug('qs_spq.query = %s', str(qs_spq.query))
        else:
            logger.debug('Strings may be split on spaces in the following "pretty print"')
            logger.debug("No queryset returned for qparams = %s", pprint.pformat(qparams))

        return qs_spq

    def getMPCount(self):
        '''
        Get the actual count of measured parameters giving the existing query.  If private _count
        member variable exist return that, otherwise expand the query set as necessary to get and
        return the count.
        '''
        if not self._count:
            logger.debug('self._count does not exist, getting count...')
            if self.initialQuery:
                logger.debug('... getting initialCount from simple QuerySet')
                self._count = MeasuredParameter.objects.using(self.request.META['dbAlias']).count()
            else:
                try:
                    self._count = self.qs_mp_no_order.count()
                except AttributeError as e:
                    raise Exception('Could not get Measured Parameter count: %s' % e)

        logger.debug('self._count = %d', self._count)
        return int(self._count)

    def getLocalizedMPCount(self):
        '''
        Apply commas to the count number and return as a string
        '''
        locale.setlocale(locale.LC_ALL, 'en_US')
        return locale.format("%d", self.getMPCount(), grouping=True)

    def getMeasuredParametersPostgreSQL(self):
        '''
        Return SQL string that can be executed against the postgres database
        '''
        sql = 'Check "Get actual count" checkbox to see the SQL for your data selection'
        if not self._count:
            logger.debug('Calling self.getMPCount()...')
            self._count = self.getMPCount()
        if self._count:
            self.qs_mp = self.getMeasuredParametersQS(MPQuerySet.rest_columns)
            if self.qs_mp:
                logger.debug('type(self.qs_mp) = %s', type(self.qs_mp))
                sql =  str(self.qs_mp.query)
                sql = sqlparse.format(sql, reindent=True, keyword_case='upper')
                # Fix up the formatting
                sql = sql.replace('INNER JOIN', '     INNER JOIN')
                sql = sql.replace(' WHERE', '\nWHERE ')
                p = re.compile('\s+AND')
                sql = p.sub('\n      AND', sql)
                logger.debug('sql = %s', sql)

        return sql

    def getSampledParametersPostgreSQL(self):
        '''
        Return SQL string that can be executed against the postgres database
        '''
        self.qs_sp = self.getSampledParametersQS(SPQuerySet.rest_columns)
        if self.qs_sp:
            logger.debug('type(self.qs_sp) = %s', type(self.qs_sp))
            sql =  str(self.qs_sp.query)
            sql = sqlparse.format(sql, reindent=True, keyword_case='upper')
            # Fix up the formatting
            sql = sql.replace('INNER JOIN', '     INNER JOIN')
            sql = sql.replace(' WHERE', '\nWHERE ')
            p = re.compile('\s+AND')
            sql = p.sub('\n      AND', sql)
            logger.debug('sql = %s', sql)

        return sql

