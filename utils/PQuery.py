__author__    = 'Mike McCann'
__copyright__ = '2012'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Parameter Query class for managing aspects of building requests for Measured and Sampled Parameter datavalues.
Intended to be used by utils/STOQSQManager.py for building ParameterValue and ParameterParameter queries.
The class hides the complexities of getting datavalues from both MeasuredParameter and SampledParameter.

@undocumented: __doc__ parser
@status: production
@license: GPL
'''
from django.conf import settings
from django.db.models.query import REPR_OUTPUT_SIZE, RawQuerySet, ValuesQuerySet
from django.contrib.gis.db.models.query import GeoQuerySet
from django.db import DatabaseError
from datetime import datetime
from stoqs.models import MeasuredParameter, Parameter, ParameterGroupParameter
from utils import postgresifySQL, getGet_Actual_Count
from loaders.SampleLoaders import SAMPLED
from loaders import MEASUREDINSITU
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

class PQuerySet(object):
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
    def __init__(self, query, values_list, qs_mp=None):
        '''
        Initialize PQuerySet with either raw SQL in @query or a QuerySet in @qs_mp.
        Use @values_list to request just the fields (columns) needed.  The class variables
        rest_colums and kml_columns are typical value_lists.  Note: specifying a values_list
        appears to break the correct serialization of geometry types in the json response.
        Called by stoqs/views/__init__.py when MeasuredParameter REST requests are made.
        '''
        self.query = query or postgresifySQL(str(qs_mp.query))
        self.values_list = values_list
        self.ordering = ('timevalue,')
        if qs_mp:
            self.mp_query = qs_mp
        else:
            self.mp_query = MeasuredParameter.objects.raw(query)
 
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
                            'datavalue': mp['datavalue'],
                          }
                    yield row

            except TypeError:
                # Model instances
                for mp in self.mp_query[:ITER_HARD_LIMIT]:
                    row = { 'measurement__depth': mp.measurement.depth,
                            'measurement__instantpoint__timevalue': mp.measurement.instantpoint.timevalue,
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
        Boiler plate copied from http://ramenlabs.com/2010/12/08/how-to-quack-like-a-queryset/.  Does not seem to be used
        by Django templates and other uses of this class, which seem to mainly use __iter__().
        '''
        if not isinstance(k, (slice, int, long)):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0))
                or (isinstance(k, slice) and (k.start is None or k.start >= 0)
                    and (k.stop is None or k.stop >= 0))), \
                "Negative indexing is not supported."
 
        if isinstance(k, slice):
            ordering = tuple(field.lstrip('-') for field in self.ordering)
            reverse = (ordering != self.ordering)
            ##if reverse:
                ##assert (sum(1 for field in self.ordering
                ##            if field.startswith('-')) == len(ordering)), \
                ##        "Mixed sort directions not supported."


            mpq = self.mp_query
 
            if k.stop is not None:
                mpq = mpq[:k.stop]
 
            rows = ([row + (MeasuredParameter,)
                     for row in mpq.values_list(*(ordering + ('pk',)))])
 
            rows.sort()
            if reverse:
                rows.reverse()
            rows = rows[k]
 
            pk_idx = len(ordering)
            klass_idx = pk_idx + 1
            mp_pks = [row[pk_idx] for row in rows
                            if row[klass_idx] is MeasuredParameter]
            mps = MeasuredParameter.objects.in_bulk(mp_pks)
 
            results = []
            for row in rows:
                pk = row[-2]
                klass = row[-1]
                if klass is MeasuredParameter:
                    mps[pk].type = 'measuredparameter'
                    results.append(mps[pk])
            return results
        else:
            return self[k:k+1][0]

    def count(self):
        logger.debug('Counting records in self.mp_query which is of type = %s', type(self.mp_query))
        try:
            c = self.mp_query.count()
        except AttributeError:
            try:
                c = sum(1 for mp in self.mp_query)
            except DatabaseError:
                return 0
        return c
 
    def all(self):
        return self._clone()
 
    def filter(self, *args, **kwargs):
        qs = self._clone()
        logger.debug('type(qs) = %s', type(qs))
        qs.mp_query = qs.mp_query.filter(*args, **kwargs)
        return qs
 
    def exclude(self, *args, **kwargs):
        qs = self._clone()
        qs.mp_query = qs.mp_query.exclude(*args, **kwargs)
        return qs
 
    def order_by(self, *ordering):
        qs = self._clone()
        qs.mp_query = qs.mp_query.order_by(*ordering)
        qs.ordering = ordering
        return qs
 
    def _clone(self):
        qs = PQuerySet(self.query, self.values_list)
        qs.mp_query = self.mp_query._clone()
        return qs 


 

class PQuery(object):
    '''
    This class is designed to handle building and managing queries against the MeasuredParameter
    or the SampledParameter tables of the STOQS database.  Special tooling is needed to perform 
    parameter value and parameter-parameter queries which require building raw sql statements in order to
    execute the self joins needed on the tables.  The structure of RawQuerySet returned is harmonized
    with the normal GeoQuerySet returned through regular .filter() operations by using the PQuerySet "adapter".
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
    logger = logging.getLogger(__name__)

    def __init__(self, request):
        '''
        This object saves instances of the QuerySet and count so that get_() methods work like a singleton to 
        return the value for the object.  PQuery objects are meant to be instantiated by the STOQSQManager 
        buildQuerySet() method and are unique for each AJAX request.  After buildPQuerySet() is executed
        the member values below can be accessed.
        '''
        self.request = request
        self.qs_mp = None
        self.sql = None
        self._count = None
        self._Prows = []

    def isParameterSampled(self, id):
        '''
        Return True Parameter @id is a Sampled Parameter
        '''
        value = id in ParameterGroupParameter.objects.using(self.request.META['dbAlias']
                        ).filter(parametergroup__name=SAMPLED).values_list('parameter__id', flat=True)
        return value
        
    def isParameterMeasured(self, id):
        '''
        Return True Parameter @id is a Measured Parameter
        '''
        value = id in ParameterGroupParameter.objects.using(self.request.META['dbAlias']
                        ).filter(parametergroup__name=MEASUREDINSITU).values_list('parameter__id', flat=True)
        return value

    def buildPQuerySet(self, *args, **kwargs):
        '''
        Build the query set based on selections from the UI. For the first time through kwargs will be empty 
        and self.qs_mp will have no constraints and will be all of the MeasuredParameters in the database.
        This is called by utils/STOQSQueryManagery.py.
        '''

        if self.qs_mp is None:
            self.kwargs = kwargs
            self.qs_mp = self.getMeasuredParametersQS()
            self.sql = self.getMeasuredParametersPostgreSQL()

    def _getQueryParms(self):
        '''
        Extract constraints from the querystring kwargs to construct a dictionary of query parameters
        that can be used as a filter for MeasuredParameters.  Handles all constraints except parameter
        value constraints.
        '''
        qparams = {}

        self.logger.info('self.kwargs = %s', pprint.pformat(self.kwargs))
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

        self.logger.debug('qparams = %s', pprint.pformat(qparams))

        return qparams

    def getMeasuredParametersQS(self, values_list=[]):
        '''
        Return query set of MeasuremedParameters given the current constraints.  If no parameter is selected return None.
        @values_list can be assigned with additional columns that are supported by PQuerySet(). Note that specificiation
        of a values_list will break the JSON serialization of geometry types.
        '''
        qparams = self._getQueryParms()
        if values_list:
            qs_mp = MeasuredParameter.objects.using(self.request.META['dbAlias']).select_related(depth=2).filter(**qparams).values(*values_list)
        else:
            qs_mp = MeasuredParameter.objects.using(self.request.META['dbAlias']).filter(**qparams)

        # Wrap PQuerySet around either RawQuerySet or GeoQuerySet to control the __iter__() items for lat/lon etc.
        if self.kwargs.has_key('parametervalues'):
            if self.kwargs['parametervalues']:
                # A depth of 4 is needed in order to see Platform
                qs_mp = MeasuredParameter.objects.using(self.request.META['dbAlias']).select_related(depth=4).filter(**qparams)
                sql = postgresifySQL(str(qs_mp.query))
                self.logger.debug('\n\nsql before query = %s\n\n', sql)
                sql = self.addMeasuredParameterValuesSelfJoins(sql, self.kwargs['parametervalues'], select_items=self.rest_select_items)
                self.logger.debug('\n\nsql after parametervalue query = %s\n\n', sql)
                qs_mpq = PQuerySet(sql, values_list)
            else:
                qs_mpq = PQuerySet(None, values_list, qs_mp=qs_mp)
        else:
            qs_mpq = PQuerySet(None, values_list, qs_mp=qs_mp)

        if qs_mpq:
            self.logger.debug('qs_mpq.query = %s', str(qs_mpq.query))
            
        else:
            self.logger.debug("No queryset returned for qparams = %s", pprint.pformat(qparams))
        return qs_mpq

    def getPCount(self):
        '''
        Get the actual count of measured parameters giving the exising query.  If private _count
        member variable exist return that, otherwise expand the query set as necessary to get and
        return the count.
        '''
        if not self._count:
            self.logger.debug('Calling self.qs_mp.count()...')
            self._count = self.qs_mp.count()

        self.logger.debug('self._count = %d', self._count)
        return int(self._count)

    def getLocalizedPCount(self):
        '''
        Apply commas to the count number and return as a string
        '''
        locale.setlocale(locale.LC_ALL, 'en_US')
        return locale.format("%d", self.getPCount(), grouping=True)

    def getMeasuredParametersPostgreSQL(self):
        '''
        Return SQL string that can be executed against the postgres database
        '''
        sql = 'Check "Get actual count" checkbox to see the SQL for your data selection'
        if self._count:
            self.qs_mp = self.getMeasuredParametersQS(PQuerySet.rest_columns)
            if self.qs_mp:
                sql = '\c %s\n' % settings.DATABASES[self.request.META['dbAlias']]['NAME']
                self.logger.debug('type(self.qs_mp) = %s', type(self.qs_mp))
                sql +=  str(self.qs_mp.query) + ';'
                sql = sqlparse.format(sql, reindent=True, keyword_case='upper')
                # Fix up the formatting
                sql = sql.replace('INNER JOIN', '     INNER JOIN')
                sql = sql.replace(' WHERE', '\nWHERE ')
                p = re.compile('\s+AND')
                sql = p.sub('\n      AND', sql)

        return sql

    def _pvSQLfragments(self, pvDict):
        '''
        Given a dictionary @pvDict of {parameter: (pmin, pmax)} return SQL fragments for the FROM and WHERE portions
        of a query
        '''
        add_to_from = ''
        from_sql = '' 
        where_sql = '' 
        i = 0
        for pminmax in pvDict:
            i = i + 1

            # Experimenting in Aqua Data Studio, need to add SQL that looks like:
            #    INNER JOIN stoqs_measurement m1 
            #    ON m1.instantpoint_id = stoqs_instantpoint.id 
            #        INNER JOIN stoqs_measuredparameter mp1 
            #        ON mp1.measurement_id = m1.id 
            #            INNER JOIN stoqs_parameter p1 
            #            ON mp1.parameter_id = p1.id

            from_sql = from_sql + 'INNER JOIN stoqs_measurement m' + str(i) + ' '
            from_sql = from_sql + 'on m' + str(i) + '.instantpoint_id = stoqs_instantpoint.id '
            from_sql = from_sql + 'INNER JOIN stoqs_measuredparameter mp' + str(i) + ' '
            from_sql = from_sql + 'on mp' + str(i) + '.measurement_id = m' + str(i) + '.id '
            from_sql = from_sql + 'INNER JOIN stoqs_parameter p' + str(i) + ' '
            from_sql = from_sql + 'on mp' + str(i) + '.parameter_id = p' + str(i) + '.id '

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

        return add_to_from, from_sql, where_sql

    def addMeasuredParameterValuesSelfJoins(self, query, pvDict, select_items= '''stoqs_instantpoint.timevalue as measurement__instantpoint__timevalue, 
                                                                          stoqs_measurement.depth as measurement__depth,
                                                                          stoqs_measurement.geom as measurement__geom,
                                                                          stoqs_measuredparameter.datavalue as datavalue'''):
        '''
        Given a Postgresified MeasuredParameter query string @query' modify it to add the P self joins needed 
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

        add_to_from, from_sql, where_sql = self._pvSQLfragments(pvDict)

        q = query
        p = re.compile('SELECT .+ FROM')
        q = p.sub('SELECT ' + select_items + ' FROM', q)
        q = q.replace('SELECT FROM stoqs_measuredparameter', 'FROM ' + add_to_from + 'stoqs_measuredparameter')
        q = q.replace('FROM stoqs_measuredparameter', 'FROM ' + add_to_from + 'stoqs_measuredparameter')
        q = q.replace('WHERE', from_sql + ' WHERE ' + where_sql)

        return q


    def addParameterParameterSelfJoins(self, query, pDict):
        '''
        Given a Postgresified MeasuredParameter query string @query modify it to add the P self joins needed 
        to return up to 4 parameter data values from the same measurements. The Parameter ids are specified
        by the integer values in @pList.  The original @query string may be one that is modified by 
        self.addMeasuredParameterValuesSelfJoins() or not.  
        Return a Postgresified query string that can be used by Django's Manage.raw().
        Written for use by utils.Viz.ParamaterParameter()

    Example query to emulate (designed in Aqua Data Studio Query Builder and Query Analyzer):

SELECT
    mp_x.datavalue AS x,
    sp_y.datavalue AS y, 
    mp_c.datavalue AS c
FROM
    stoqs_sample 
        INNER JOIN stoqs_instantpoint 
        ON stoqs_sample.instantpoint_id = stoqs_instantpoint.id 
            INNER JOIN stoqs_measurement 
            ON stoqs_instantpoint.id = stoqs_measurement.instantpoint_id 
                INNER JOIN stoqs_activity 
                ON stoqs_instantpoint.activity_id = stoqs_activity.id 
                    INNER JOIN stoqs_platform 
                    ON stoqs_activity.platform_id = stoqs_platform.id 

                        INNER JOIN stoqs_sampledparameter sp_y
                        ON sp_y.sample_id = stoqs_sample.id 
                            INNER JOIN stoqs_parameter p_y 
                            ON sp_y.parameter_id = p_y.id 

                                INNER JOIN stoqs_measuredparameter mp_x
                                ON mp_x.measurement_id = stoqs_measurement.id 
                                    INNER JOIN stoqs_parameter p_x
                                    ON mp_x.parameter_id = p_x.id 

                                        INNER JOIN stoqs_measuredparameter mp_c 
                                        ON mp_c.measurement_id = stoqs_measurement.id 
                                            INNER JOIN stoqs_parameter p_c
                                            ON mp_c.parameter_id = p_c.id 
WHERE
    ("stoqs_platform"."name" ='dorado') AND
    (p_x.id =6) AND
    (p_c.id =7) AND
    (p_y.id =57)


For sampledparameter to sampledparamter query an example is:

  SELECT DISTINCT s_x.depth, sp_x.datavalue as x, sp_y.datavalue as y, p_x.id as px, p_y.id as py FROM stoqs_activity
    INNER JOIN stoqs_instantpoint ip
      on ip.activity_id = stoqs_activity.id
      INNER JOIN stoqs_sample s_x
        on s_x.instantpoint_id = ip.id
          INNER JOIN stoqs_sample s_y
            on s_y.instantpoint_id = ip.id
              INNER JOIN stoqs_sampledparameter sp_y
                on sp_y.sample_id = s_y.id
                  INNER JOIN stoqs_parameter p_y
                    on sp_y.parameter_id = p_y.id
                      INNER JOIN stoqs_sampledparameter sp_x
                        on sp_x.sample_id = s_x.id
                          INNER JOIN stoqs_parameter p_x
                            on sp_x.parameter_id = p_x.id
    WHERE (p_y.id = 10) AND (p_x.id = 8);

        '''

        self.logger.debug('initial query = %s', query)
    
        # Construct SELECT strings, must be in proper order, include depth for possible sigma-t calculation
        select_order = ('x', 'y', 'z', 'c')
        containsSampleFlag = False
        containsMeasuredFlag = False
        xyzc_items = ''
        for axis in select_order:
            if pDict.has_key(axis):
                if pDict[axis]:
                    try:
                        if self.isParameterMeasured(int(pDict[axis])):
                            xyzc_items = xyzc_items + 'mp_' + axis + '.datavalue as ' + axis + ', '
                            containsMeasuredFlag = True
                        elif self.isParameterSampled(int(pDict[axis])):
                            containsSampleFlag = True
                            xyzc_items = xyzc_items + 'sp_' + axis + '.datavalue as ' + axis + ', '
                        else:
                            # Default is to assume mp - supports legacy databases w/o the ParameterGroup assignment
                            xyzc_items = xyzc_items + 'mp_' + axis + '.datavalue as ' + axis + ', '
                    except ValueError, e:
                        if pDict[axis] == 'longitude':
                            xyzc_items = xyzc_items + 'ST_X(stoqs_measurement.geom) as ' + axis + ', '
                        elif pDict[axis] == 'latitude':
                            xyzc_items = xyzc_items + 'ST_Y(stoqs_measurement.geom) as ' + axis + ', '
                        elif pDict[axis] == 'depth':
                            xyzc_items = xyzc_items + 'stoqs_measurement.depth as ' + axis + ', '
                        elif pDict[axis] == 'time':
                            xyzc_items += "(DATE_PART('day', stoqs_instantpoint.timevalue - timestamp '1950-01-01') * 86400 + "
                            xyzc_items += "DATE_PART('hour', stoqs_instantpoint.timevalue - timestamp '1950-01-01') * 3600 + "
                            xyzc_items += "DATE_PART('minute', stoqs_instantpoint.timevalue - timestamp '1950-01-01') * 60 + "
                            xyzc_items += "DATE_PART('second', stoqs_instantpoint.timevalue - timestamp '1950-01-01') ) / 86400 "
                            xyzc_items += ' as ' + axis + ', '  
                        logger.error('%s, but axis is not a coordinate', e)


        # Include all joins that are possible from the selectors in the UI: time, depth, parameter, platform
        # Cannot use aliases because where clause from UI selectors don't use them
        replace_from = '''stoqs_activity
            INNER JOIN stoqs_platform 
              on stoqs_platform.id = stoqs_activity.platform_id
            INNER JOIN stoqs_instantpoint 
              on stoqs_instantpoint.activity_id = stoqs_activity.id
        '''
        if containsSampleFlag and not containsMeasuredFlag:
            # Only Sampled
            depth_item = 'DISTINCT stoqs_sample.depth, '
            replace_from = replace_from + '''
            INNER JOIN stoqs_sample 
              on stoqs_sample.instantpoint_id = stoqs_instantpoint.id
            '''
        elif containsSampleFlag and containsMeasuredFlag:
            # Sampled and Measured
            depth_item = 'DISTINCT stoqs_measurement.depth, '
            replace_from = replace_from + '''
            INNER JOIN stoqs_measurement 
              on stoqs_measurement.instantpoint_id = stoqs_instantpoint.id
            INNER JOIN stoqs_sample 
              on stoqs_sample.instantpoint_id = stoqs_instantpoint.id
            '''
        else:
            # Only Measured
            depth_item = 'DISTINCT stoqs_measurement.depth, '
            replace_from = replace_from + '''
            INNER JOIN stoqs_measurement 
              on stoqs_measurement.instantpoint_id = stoqs_instantpoint.id
            '''

        select_items = depth_item + xyzc_items

        # Construct INNER JOINS and WHERE sql for Sampled and Measured Parameter selections
        # Use aliases for joins on each axis
        where_sql = '' 
        for axis, pid in pDict.iteritems():
            if pid:
                self.logger.debug('axis, pid = %s, %s', axis, pid)
                replace_from = replace_from + '\n'
                try:
                    if self.isParameterMeasured(int(pid)):
                        replace_from = replace_from + '\nINNER JOIN stoqs_measurement m_' + axis + ' '
                        replace_from = replace_from + '\non m_' + axis + '.instantpoint_id = stoqs_instantpoint.id'
                        replace_from = replace_from + '\nINNER JOIN stoqs_measuredparameter mp_' + axis + ' '
                        replace_from = replace_from + '\non mp_' + axis + '.measurement_id = m_' + axis + '.id '
                        replace_from = replace_from + '\nINNER JOIN stoqs_parameter p_' + axis + ' '
                        replace_from = replace_from + '\non mp_' + axis + '.parameter_id = p_' + axis + '.id '
                    elif self.isParameterSampled(int(pid)):
                        replace_from = replace_from + '\nINNER JOIN stoqs_sample s_' + axis + ' '
                        replace_from = replace_from + '\non s_' + axis + '.instantpoint_id = stoqs_instantpoint.id'
                        replace_from = replace_from + '\nINNER JOIN stoqs_sampledparameter sp_' + axis + ' '
                        replace_from = replace_from + '\non sp_' + axis + '.sample_id = s_' + axis + '.id '
                        replace_from = replace_from + '\nINNER JOIN stoqs_parameter p_' + axis + ' '
                        replace_from = replace_from + '\non sp_' + axis + '.parameter_id = p_' + axis + '.id '
                    else:
                        self.logger.warn('Encountered parameter (id=%s) that is not in the Measured nor in the Sampled ParameterGroup', pid)
                    where_sql = where_sql + '(p_' + axis + '.id = ' + str(pid) + ') AND '
                except ValueError:
                    # pid likely a coordinate, ignore
                    pass


        # Modify original SQL with new joins and where sql - almost a total rewrite
        q = query
        select_items = select_items[:-2] + ' '                      # Remove ', '
        q = 'SELECT ' + select_items + q[q.find('FROM'):]           # Override original select items

        if q.find('WHERE') == -1:
            # Case where no filters applied from UI - no selections and no WHERE clause, add ours
            q = q + ' WHERE ' + where_sql[:-4]                      # Remove last 'AND '
        else:
            # Insert our WHERE clause into the filters that are in the original query
            self.logger.debug('q = %s', q)
            if containsSampleFlag and not containsMeasuredFlag:
                q = q.replace('stoqs_measurement', 'stoqs_sample')
            q = q.replace(' WHERE ', ' WHERE ' + where_sql)

        # Completely replace the whole FROM clause
        p = re.compile('FROM.+WHERE')
        q = p.sub('FROM ' + replace_from + ' WHERE', q)

        # Check for ParameterValues and add to the SQL
        if self.kwargs['parametervalues']:
            # Add SQL fragments for any Parameter Value selections
            pv_add_to_from, pv_from_sql, pv_where_sql = self._pvSQLfragments(self.kwargs['parametervalues'])
            q = q.replace('FROM stoqs_sample', 'FROM ' + pv_add_to_from + 'stoqs_sample')
            q = q.replace('FROM stoqs_instantpoint', 'FROM ' + pv_add_to_from + 'stoqs_instantpoint')
            q = q.replace('WHERE', pv_from_sql + ' WHERE ' + pv_where_sql)

        self.logger.debug('q = %s', q)
        q = sqlparse.format(q, reindent=True, keyword_case='upper')

        return q

