__author__    = 'Mike McCann'
__copyright__ = '2012'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

MeasuredParameter Query class for managing aspects of building requests for MeasuredParameter datavalues.
Intended to be used by utils/STOQSQManager.py for preventing multiple traversals of qs_mp and by
views/__init__.py to support query by parameter value for the REST responses.

@undocumented: __doc__ parser
@status: production
@license: GPL
'''
from django.conf import settings
from django.db.models.query import REPR_OUTPUT_SIZE, RawQuerySet, ValuesQuerySet
from django.contrib.gis.db.models.query import GeoQuerySet
from django.db import DatabaseError
from datetime import datetime
from stoqs.models import MeasuredParameter, Parameter
from utils import postgresifySQL, getGet_Actual_Count
import logging
import pprint
import re
import locale
import time
import os
import tempfile
import sqlparse

logger = logging.getLogger(__name__)

ITER_HARD_LIMIT = 100000

class MPQuerySet(object):
    '''
    A class to simulate a GeoQuerySet that's suitable for use everywhere a GeoQuerySet may be used.
    This special class supports adapting MeasuredParameter RawQuerySets to make them look like regular
    GeoQuerySets.  See: http://ramenlabs.com/2010/12/08/how-to-quack-like-a-queryset/.  (I looked at Google
    again to see if self-joins are possible in Django, and confirmed that they are probably not.  
    See: http://stackoverflow.com/questions/1578362/self-join-with-django-orm.)
    '''
    rest_columns = [ 'parameter__name',
                     'parameter__standard_name',
                     'measurement__depth',
                     'measurement__geom',
                     'measurement__instantpoint__timevalue', 
                     'measurement__instantpoint__activity__name',
                     'measurement__instantpoint__activity__platform__name',
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
    def __init__(self, query, values_list, qs_mp=None):
        '''
        Initialize MPQuerySet with either raw SQL in @query or a QuerySet in @qs_mp.
        Use @values_list to request just the fields (columns) needed.  The class variables
        rest_colums and kml_columns are typical value_lists.  Note: specifying a values_list
        appears to break the correct serialization of geometry types in the json response.
        Called by stoqs/views/__init__.py when MeasuredParameter REST requests are made.
        '''
        if query is None and qs_mp is not None:
            logger.debug('query is None and qs_mp is not None')
            self.query = postgresifySQL(str(qs_mp.query))
            self.mp_query = qs_mp
        elif query is not None and qs_mp is None:
            logger.debug('query is not None and qs_mp is None')
            self.query = query
            self.mp_query = MeasuredParameter.objects.raw(query)
        else:
            raise Exception('Either query or qs_mp must be not None and the other be None.')

        self.values_list = values_list
        self.ordering = ('id',)
 
    def __iter__(self):
        '''
        Main way to access data that is used by interators in templates, etc.
        Simulate behavior of regular GeoQuerySets.  Modify & format output as needed.
        '''
        minimal_values_list = False
        for item in self.rest_columns:
            if item not in self.values_list:
                minimal_values_list = True
                break
        logger.debug('minimal_values_list = %s', minimal_values_list)

        logger.debug('self.query = %s', self.query)
        logger.debug('type(self.mp_query) = %s', type(self.mp_query))

        if isinstance(self.mp_query, ValuesQuerySet):
            logger.debug('self.mp_query is ValuesQuerySet')
        if isinstance(self.mp_query, GeoQuerySet):
            logger.debug('self.mp_query is GeoQuerySet')
        if isinstance(self.mp_query, RawQuerySet):
            logger.debug('self.mp_query is RawQuerySet')

        # Must have model instance objects for JSON serialization of geometry fields to work right
        if minimal_values_list:
            # Likely for Flot contour plot
            try:
                # Dictionaries
                for mp in self.mp_query[:ITER_HARD_LIMIT]:
                    row = { 'measurement__depth': mp['measurement__depth'],
                            'measurement__instantpoint__timevalue': mp['measurement__instantpoint__timevalue'],
                            'measurement__instantpoint__activity__name': mp['measurement__instantpoint__activity__name'],
                            'datavalue': mp['datavalue'],
                          }
                    yield row

            except TypeError:
                # Model instances
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

            except TypeError:
                # Model instances
                for mp in self.mp_query[:ITER_HARD_LIMIT]:
                    row = { 
                            'measurement__depth': mp.measurement.depth,
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
        if not isinstance(k, (slice, int, long)):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0))
                or (isinstance(k, slice) and (k.start is None or k.start >= 0)
                    and (k.stop is None or k.stop >= 0))), \
                "Negative indexing is not supported."
 
        if isinstance(k, slice):
            return self.mp_query[k]

    def count(self):
        logger.debug('Counting records in self.mp_query which is of type = %s', type(self.mp_query))
        # self.mp_query should contain no 'ORDER BY' as ensured by the routine that calls .count()
        try:
            c = self.mp_query.count()
            logger.debug('c = %d as retreived from self.mp_query.count()', c)
        except AttributeError:
            try:
                c = sum(1 for mp in self.mp_query)
                logger.debug('c = %d as retreived from sum(1 for mp in self.mp_query)', c)
            except DatabaseError:
                return 0
        return c
 
    def all(self):
        return self._clone()
 
    def filter(self, *args, **kwargs):
        qs = self._clone()
        logger.debug('type(qs) = %s', type(qs))
        qs.mp_query = qs.mp_query.filter(*args, **kwargs)
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
        qs = MPQuerySet(self.query, self.values_list)
        qs.mp_query = self.mp_query._clone()
        return qs 
 

class MPQuery(object):
    '''
    This class is designed to handle building and managing queries against the MeasuredParameter table of the STOQS database.
    Special tooling is needed to perform parameter value queries which require building raw sql statements in order to
    execute the self joins needed on the measuredparameter table.  The structure of RawQuerySet returned is harmonized
    with the normal GeoQuerySet returned through regular .filter() operations by using the MPQuerySet "adapter".
    '''
    rest_select_items = '''stoqs_parameter.name as parameter__name,
                         stoqs_parameter.standard_name as parameter__standard_name,
                         stoqs_measurement.depth as measurement__depth,
                         stoqs_measurement.geom as measurement__geom,
                         stoqs_instantpoint.timevalue as measurement__instantpoint__timevalue, 
                         stoqs_platform.name as measurement__instantpoint__activity__platform__name,
                         stoqs_measuredparameter.datavalue as datavalue,
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
        self.sql = None
        self._count = None
        self._MProws = []
        self.parameterID = None
        
    def buildMPQuerySet(self, *args, **kwargs):
        '''
        Build the query set based on selections from the UI. For the first time through kwargs will be empty 
        and self.qs_mp will have no constraints and will be all of the MeasuredParameters in the database.
        This is called by utils/STOQSQueryManagery.py.
        '''

        if self.qs_mp is None:
            self.kwargs = kwargs
            if 'parameterplot' in self.kwargs:
                if self.kwargs['parameterplot'][0]:
                    self.parameterID = self.kwargs['parameterplot'][0]

            logger.debug('self.parameterID = %s', self.parameterID)
            
            self.qs_mp = self.getMeasuredParametersQS()
            if self.kwargs['showparameterplatformdata']:
                logger.debug('Building qs_mp_no_order with values_list = %s', MPQuerySet.ui_timedepth_columns)
                self.qs_mp_no_order = self.getMeasuredParametersQS(MPQuerySet.ui_timedepth_columns, orderedFlag=False)
            else:
                self.qs_mp_no_order = self.getMeasuredParametersQS(orderedFlag=False)
            self.sql = self.getMeasuredParametersPostgreSQL()

    def _getQueryParms(self):
        '''
        Extract constraints from the querystring kwargs to construct a dictionary of query parameters
        that can be used as a filter for MeasuredParameters.  Handles all constraints except parameter
        value constraints.
        '''
        qparams = {}

        ##logger.info('self.kwargs = %s', pprint.pformat(self.kwargs))
        if self.kwargs.has_key('measuredparametersgroup'):
            if self.kwargs['measuredparametersgroup']:
                qparams['parameter__name__in'] = self.kwargs['measuredparametersgroup']
        if self.kwargs.has_key('parameterstandardname'):
            if self.kwargs['parameterstandardname']:
                qparams['parameter__standard_name__in'] = self.kwargs['parameterstandardname']
        
        if self.kwargs.has_key('platforms'):
            if self.kwargs['platforms']:
                qparams['measurement__instantpoint__activity__platform__name__in'] = self.kwargs['platforms']
        if self.kwargs.has_key('time'):
            if self.kwargs['time'][0] is not None:
                qparams['measurement__instantpoint__timevalue__gte'] = self.kwargs['time'][0]
            if self.kwargs['time'][1] is not None:
                qparams['measurement__instantpoint__timevalue__lte'] = self.kwargs['time'][1]
        if self.kwargs.has_key('depth'):
            if self.kwargs['depth'][0] is not None:
                qparams['measurement__depth__gte'] = self.kwargs['depth'][0]
            if self.kwargs['depth'][1] is not None:
                qparams['measurement__depth__lte'] = self.kwargs['depth'][1]

        if getGet_Actual_Count(self.kwargs):
            # Make sure that we have at least time so that the instantpoint table is included
            if not qparams.has_key('measurement__instantpoint__timevalue__gte'):
                qparams['measurement__instantpoint__pk__isnull'] = False

        logger.debug('qparams = %s', pprint.pformat(qparams))

        return qparams

    def getMeasuredParametersQS(self, values_list=[], orderedFlag=True):
        '''
        Return query set of MeasuremedParameters given the current constraints.  If no parameter is selected return None.
        @values_list can be assigned with additional columns that are supported by MPQuerySet(). Note that specificiation
        of a values_list will break the JSON serialization of geometry types. @orderedFlag may be set to False to reduce
        memory and time taken for queries that don't need ordered values.  If parameterID is not none then that parameter
        is added to the filter - used for parameterPlatformPNG generation.
        '''
        qparams = self._getQueryParms()
        logger.debug('Building qs_mp...')
        if values_list == []:
            # If no .values(...) added to QS then items returned by iteration on qs_mp are model objects, not out wanted dictionaries
            qs_mp = MeasuredParameter.objects.using(self.request.META['dbAlias']).filter(**qparams).values(*MPQuerySet.rest_columns)
        else:
            qs_mp = MeasuredParameter.objects.using(self.request.META['dbAlias']).select_related(depth=2).filter(**qparams).values(*values_list)

        if self.parameterID:
            logger.debug('Adding parameter__id=%d filter to qs_mp', int(self.parameterID))
            qs_mp = qs_mp.filter(parameter__id=int(self.parameterID))

        if orderedFlag:
            qs_mp = qs_mp.order_by('measurement__instantpoint__activity__name', 'measurement__instantpoint__timevalue')

        # Wrap MPQuerySet around either RawQuerySet or GeoQuerySet to control the __iter__() items for lat/lon etc.
        if self.kwargs.has_key('parametervalues'):
            if self.kwargs['parametervalues']:
                # A depth of 4 is needed in order to see Platform
                qs_mp = MeasuredParameter.objects.using(self.request.META['dbAlias']).select_related(depth=4).filter(**qparams)
                if orderedFlag:
                    qs_mp = qs_mp.order_by('measurement__instantpoint__activity__name', 'measurement__instantpoint__timevalue')
                sql = postgresifySQL(str(qs_mp.query))
                logger.debug('\n\nsql before query = %s\n\n', sql)
                sql = self.addParameterValuesSelfJoins(sql, self.kwargs['parametervalues'], select_items=self.rest_select_items)
                logger.debug('\n\nsql after parametervalue query = %s\n\n', sql)
                qs_mpq = MPQuerySet(sql, values_list)
            else:
                logger.debug('Building MPQuerySet...')
                qs_mpq = MPQuerySet(None, values_list, qs_mp=qs_mp)
        else:
            logger.debug('Building MPQuerySet...')
            qs_mpq = MPQuerySet(None, values_list, qs_mp=qs_mp)

        if qs_mpq is None:
            logger.debug('qs_mpq.query = %s', str(qs_mpq.query))
        else:
            logger.debug("No queryset returned for qparams = %s", pprint.pformat(qparams))

        return qs_mpq

    def getMPCount(self):
        '''
        Get the actual count of measured parameters giving the exising query.  If private _count
        member variable exist return that, otherwise expand the query set as necessary to get and
        return the count.
        '''
        if not self._count:
            logger.debug('Calling self.qs_mp_no_order.count()...')
            self._count = self.qs_mp_no_order.count()

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
                sql = '\c %s\n' % settings.DATABASES[self.request.META['dbAlias']]['NAME']
                logger.debug('type(self.qs_mp) = %s', type(self.qs_mp))
                sql +=  str(self.qs_mp.query) + ';'
                sql = sqlparse.format(sql, reindent=True, keyword_case='upper')
                # Fix up the formatting
                sql = sql.replace('INNER JOIN', '     INNER JOIN')
                sql = sql.replace(' WHERE', '\nWHERE ')
                p = re.compile('\s+AND')
                sql = p.sub('\n      AND', sql)
                logger.debug('sql = %s', sql)

        return sql

    def addParameterValuesSelfJoins(self, query, pvDict, select_items= '''stoqs_instantpoint.timevalue as measurement__instantpoint__timevalue, 
                                                                          stoqs_measurement.depth as measurement__depth,
                                                                          stoqs_measurement.geom as measurement__geom,
                                                                          stoqs_measuredparameter.datavalue as datavalue'''):
        '''
        Given a Postgresified MeasuredParameter query string @query' modify it to add the MP self joins needed 
        to restrict the data selection to the ParameterValues specified in @pvDict.  Add to the required
        measuredparameter.id the select items in the comma separeated value string @select_items.
        Return a Postgresified query string that can be used by Django's Manage.raw().
        select_items can be altered as needed, examples:
            For Flot contour plot we need just depth and time.
            For KML output we need in addition: latitude, longitude, parameter name, and platform name
            For REST we need about everything
        '''
        # Example original Postgresified SQL
        #SELECT
        #    stoqs_measuredparameter.id,
        #    stoqs_measuredparameter.measurement_id,
        #    stoqs_measuredparameter.parameter_id,
        #    stoqs_measuredparameter.datavalue 
        #FROM
        #    stoqs_measuredparameter 
        #        INNER JOIN stoqs_measurement 
        #        ON (stoqs_measuredparameter.measurement_id = stoqs_measurement.id) 
        #            INNER JOIN stoqs_instantpoint 
        #            ON (stoqs_measurement.instantpoint_id = stoqs_instantpoint.id) 
        #                INNER JOIN stoqs_parameter 
        #                ON (stoqs_measuredparameter.parameter_id = stoqs_parameter.id) 
        #                    INNER JOIN stoqs_activity 
        #                    ON (stoqs_instantpoint.activity_id = stoqs_activity.id) 
        #                        INNER JOIN stoqs_platform 
        #                        ON (stoqs_activity.platform_id = stoqs_platform.id) 
        #WHERE
        #    (stoqs_instantpoint.timevalue <= '2012-09-13 18:19:04' AND
        #    stoqs_instantpoint.timevalue >= '2012-09-13 05:16:48' AND
        #    stoqs_parameter.name IN ('temperature') AND
        #    stoqs_measurement.depth >= -5.66 AND
        #    stoqs_platform.name IN ('dorado') AND
        #    stoqs_measurement.depth <= 153.85 )

        # Example Self-join SQL to insert into the string
        #select
        #    stoqs_measuredparameter.datavalue,
        #    stoqs_parameter_1.name              as name_1,
        #    stoqs_measuredparameter_1.datavalue as datavalue_1,
        #    stoqs_measuredparameter_1.datavalue as datavalue_1b,
        #    stoqs_parameter.name 
        #from
        #    stoqs_measuredparameter stoqs_measuredparameter_1 
        #        inner join stoqs_parameter stoqs_parameter_1 
        #        on stoqs_measuredparameter_1.parameter_id = stoqs_parameter_1.id 
        #            inner join stoqs_measuredparameter 
        #            stoqs_measuredparameter 
        #            on stoqs_measuredparameter_1.measurement_id = 
        #            stoqs_measuredparameter.measurement_id 
        #                inner join stoqs_parameter stoqs_parameter 
        #                on stoqs_parameter.id = stoqs_measuredparameter.
        #                parameter_id 
        #where
        #    (stoqs_parameter_1.name ='sea_water_sigma_t') and
        #    (stoqs_measuredparameter_1.datavalue >24.5) and
        #    (stoqs_measuredparameter_1.datavalue <25.0) and
        #    (stoqs_parameter.name ='temperature')

        # Used by getParameterPlatformDatavaluePNG(): 'measurement__instantpoint__timevalue', 'measurement__depth', 'datavalue
        # Used by REST requests in stoqs/views/__init__(): stoqs_parameter.name, stoqs_parameter.standard_name, stoqs_measurement.depth, stoqs_measurement.geom, stoqs_instantpoint.timevalue, stoqs_platform.name, stoqs_measuredparameter.datavalue, stoqs_parameter.units

        select_items = 'stoqs_measuredparameter.id, ' + select_items
        add_to_from = ''
        from_sql = '' 
        where_sql = '' 
        i = 0
        for pminmax in pvDict:
            i = i + 1
            add_to_from = add_to_from + 'stoqs_parameter p' + str(i) + ', '
            from_sql = from_sql + 'INNER JOIN stoqs_measuredparameter mp' + str(i) + ' '
            from_sql = from_sql + 'on mp' + str(i) + '.measurement_id = stoqs_measuredparameter.measurement_id '
            for k,v in pminmax.iteritems():
                # Prevent SQL injection attacks
                if k in Parameter.objects.using(self.request.META['dbAlias']).values_list('name', flat=True):
                    p = re.compile("[';]")
                    if p.search(v[0]) or p.search(v[1]):
                        raise Exception('Invalid ParameterValue constraint expression: %s, %s' % (k, v))
                    where_sql = where_sql + "(p" + str(i) + ".name = '" + k + "') AND "
                    if v[0]:
                        where_sql = where_sql + "(mp" + str(i) + ".datavalue > " + str(v[0]) + ") AND "
                    if v[1]:
                        where_sql = where_sql + "(mp" + str(i) + ".datavalue < " + str(v[1]) + ") AND "
                    where_sql = where_sql + "(mp" + str(i) + ".parameter_id = p" + str(i) + ".id) AND "

        q = query
        p = re.compile('SELECT .+ FROM')
        q = p.sub('SELECT ' + select_items + ' FROM', q)
        q = q.replace('SELECT FROM stoqs_measuredparameter', 'FROM ' + add_to_from + 'stoqs_measuredparameter')
        q = q.replace('FROM stoqs_measuredparameter', 'FROM ' + add_to_from + 'stoqs_measuredparameter')
        q = q.replace('WHERE', from_sql + ' WHERE ' + where_sql)

        return q


    def addParameterParameterSelfJoins(self, query, pDict):
        '''
        Given a Postgresified MeasuredParameter query string @query modify it to add the MP self joins needed 
        to return up to 4 parameter data values from the same measurements. The Parameter ids are specified
        by the integer values in @pList.  The original @query string may be one that is modified by 
        self.addParameterValuesSelfJoins() or not.  
        Return a Postgresified query string that can be used by Django's Manage.raw().
        Written for use by utils.Viz.ParamaterParameter()
        '''
        logger.debug('query = %s', query)
    
        select_items = 'stoqs_measuredparameter.id, '
        select_order = ('x', 'y', 'z', 'c')

        add_to_from = ''
        where_sql = '' 

        for axis in select_order:
            if pDict.has_key(axis):
                if pDict[axis]:
                    select_items = select_items + 'mp_' + axis + '.datavalue as ' + axis + ', '

        for axis, pid in pDict.iteritems():
            if pid:
                logger.debug('axis, pid = %s, %s', axis, pid)

                add_to_from = add_to_from + 'INNER JOIN stoqs_measuredparameter mp_' + axis + ' '
                add_to_from = add_to_from + 'on mp_' + axis + '.measurement_id = stoqs_measurement.id '
                add_to_from = add_to_from + 'INNER JOIN stoqs_parameter p_' + axis + ' '
                add_to_from = add_to_from + 'on mp_' + axis + '.parameter_id = p_' + axis + '.id '

                where_sql = where_sql + '(p_' + axis + '.id = ' + str(pid) + ') AND '

        q = query
        select_items = select_items[:-2] + ' '
        logger.debug('select_items = %s', select_items)
        q = 'SELECT ' + select_items + q[q.find('FROM'):]
        logger.debug('add_to_from = %s', add_to_from)

        if q.find('WHERE') == -1:
            q = q +  add_to_from + ' WHERE ' + where_sql
        else:
            q = q.replace(' WHERE ', add_to_from + ' WHERE ' + where_sql)

        logger.debug('q = %s', q)
        return q

