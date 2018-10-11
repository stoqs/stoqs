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
from django.db.models.query import REPR_OUTPUT_SIZE, RawQuerySet, QuerySet
from django.db import DatabaseError
from datetime import datetime
from stoqs.models import MeasuredParameter, Parameter, ParameterGroupParameter, MeasuredParameterResource
from .utils import postgresifySQL, getGet_Actual_Count, EPOCH_STRING
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
    A class to simulate a QuerySet that's suitable for use everywhere a QuerySet may be used.
    This special class supports adapting MeasuredParameter RawQuerySets to make them look like regular
    QuerySets.  See: http://ramenlabs.com/2010/12/08/how-to-quack-like-a-queryset/.  (I looked at Google
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
        if qs_mp is None:
            self.mp_query = MeasuredParameter.objects.raw(query)
        else:
            if qs_mp.exists():
                self.mp_query = qs_mp
            else:
                self.mp_query = MeasuredParameter.objects.raw(query)
 
    def __iter__(self): # pragma: no cover
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

        if isinstance(self.mp_query, QuerySet):
            logger.debug('self.mp_query is QuerySet')
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
 
    def __getitem__(self, k): # pragma: no cover
        '''
        Boiler plate copied from http://ramenlabs.com/2010/12/08/how-to-quack-like-a-queryset/.  Does not seem to be used
        by Django templates and other uses of this class, which seem to mainly use __iter__().
        '''
        if not isinstance(k, (slice, int)):
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
    with the normal QuerySet returned through regular .filter() operations by using the PQuerySet "adapter".
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
        Return True if id is a Sampled Parameter. Where id can be the primary key or the name.
        '''
        value = id in ParameterGroupParameter.objects.using(self.request.META['dbAlias']
                        ).filter(parametergroup__name=SAMPLED).values_list('parameter__id', flat=True)
        if not value:
            value = id in ParameterGroupParameter.objects.using(self.request.META['dbAlias']
                            ).filter(parametergroup__name=SAMPLED).values_list('parameter__name', flat=True)
            
        return value
        
    def isParameterMeasured(self, id):
        '''
        Return True if id is a Measured Parameter. Where id can be the primary key or the name.
        '''
        value = id in ParameterGroupParameter.objects.using(self.request.META['dbAlias']
                        ).filter(parametergroup__name=MEASUREDINSITU).values_list('parameter__id', flat=True)
        if not value:
            value = id in ParameterGroupParameter.objects.using(self.request.META['dbAlias']
                            ).filter(parametergroup__name=MEASUREDINSITU).values_list('parameter__name', flat=True)
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

        if 'measuredparametersgroup' in self.kwargs:
            if self.kwargs['measuredparametersgroup']:
                qparams['parameter__id__in'] = self.kwargs['measuredparametersgroup']
        if 'sampledparametersgroup' in self.kwargs:
            if self.kwargs['sampledparametersgroup']:
                qparams['parameter__id__in'] = self.kwargs['sampledparametersgroup']
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

        if 'mplabels'  in self.kwargs:
            if self.kwargs['mplabels' ]:
                qparams['id__in'] = MeasuredParameterResource.objects.using(self.request.META['dbAlias']).filter(
                                    resource__id__in=self.kwargs['mplabels' ]).values_list('measuredparameter__id', flat=True)

        if getGet_Actual_Count(self.kwargs):
            # Make sure that we have at least time so that the instantpoint table is included
            if 'measurement__instantpoint__timevalue__gte' not in qparams:
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
            qs_mp = MeasuredParameter.objects.using(self.request.META['dbAlias']
                    ).filter(**qparams).values(*values_list)
        else:
            qs_mp = MeasuredParameter.objects.using(self.request.META['dbAlias']).filter(**qparams)

        # Wrap PQuerySet around either RawQuerySet or QuerySet to control the __iter__() items for lat/lon etc.
        qs_mpq = PQuerySet(None, values_list, qs_mp=qs_mp)
        if 'parametervalues' in self.kwargs:
            if self.kwargs['parametervalues'] != [{}]:
                # A depth of 4 is needed in order to see Platform
                qs_mp = MeasuredParameter.objects.using(
                        self.request.META['dbAlias']).select_related(
                                'measurement__instantpoint__activity__platform'
                                ).filter(**qparams)
                sql = postgresifySQL(str(qs_mp.query))
                self.logger.debug('\n\nsql before query = %s\n\n', sql)
                sql = self.addParameterValuesSelfJoins(sql, self.kwargs['parametervalues'], select_items=self.rest_select_items)
                self.logger.debug('\n\nsql after parametervalue query = %s\n\n', sql)
                qs_mpq = PQuerySet(sql, values_list)

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
        Given a list dictionary @pvDict of [{parameter: (pmin, pmax)}] return SQL fragments for the FROM and WHERE portions
        of a query. Deal with both Measured Parameters and Sampled Paramters.
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

            for k,v in list(pminmax.items()):
                if k in Parameter.objects.using(self.request.META['dbAlias']).values_list('name', flat=True):
                    p = re.compile("[';]")
                    if p.search(v[0]) or p.search(v[1]):
                        # Prevent SQL injection attacks
                        raise Exception('Invalid ParameterValue constraint expression: %s, %s' % (k, v))

                    if self.isParameterMeasured(k):
                        from_sql += 'INNER JOIN stoqs_measurement m' + str(i) + ' '
                        from_sql += 'on m' + str(i) + '.instantpoint_id = stoqs_instantpoint.id '
                        from_sql += 'INNER JOIN stoqs_measuredparameter mp' + str(i) + ' '
                        from_sql += 'on mp' + str(i) + '.measurement_id = m' + str(i) + '.id '
                        from_sql += 'INNER JOIN stoqs_parameter p' + str(i) + ' '
                        from_sql += 'on mp' + str(i) + '.parameter_id = p' + str(i) + '.id '

                        where_sql += "(p" + str(i) + ".name = '" + k + "') AND "
                        if v[0]:
                            where_sql += "(mp" + str(i) + ".datavalue > " + str(v[0]) + ") AND "
                        if v[1]:
                            where_sql += "(mp" + str(i) + ".datavalue < " + str(v[1]) + ") AND "
                        where_sql += "(mp" + str(i) + ".parameter_id = p" + str(i) + ".id) AND "

                    elif self.isParameterSampled(k): # pragma: no cover
                        from_sql += 'INNER JOIN stoqs_sample s' + str(i) + ' '
                        from_sql += 'on s' + str(i) + '.instantpoint_id = stoqs_instantpoint.id '
                        from_sql += 'INNER JOIN stoqs_sampledparameter sp' + str(i) + ' '
                        from_sql += 'on sp' + str(i) + '.sample_id = s' + str(i) + '.id '
                        from_sql += 'INNER JOIN stoqs_parameter p' + str(i) + ' '
                        from_sql += 'on sp' + str(i) + '.parameter_id = p' + str(i) + '.id '

                        where_sql += "(p" + str(i) + ".name = '" + k + "') AND "
                        if v[0]:
                            where_sql += "(sp" + str(i) + ".datavalue > " + str(v[0]) + ") AND "
                        if v[1]:
                            where_sql += "(sp" + str(i) + ".datavalue < " + str(v[1]) + ") AND "
                        where_sql += "(sp" + str(i) + ".parameter_id = p" + str(i) + ".id) AND "

        return add_to_from, from_sql, where_sql

    def _getContainsFlags(self, select_order, pDict):
        '''
        Return flags indicating if the query set contains MeasuredParameters and SampledParameters
        '''
        # Peek at selections to set Sample and Measurement flags
        containsSampleFlag = False
        containsMeasuredFlag = False
        for axis in select_order:
            if axis in pDict:
                if pDict[axis]:
                    try:
                        if self.isParameterMeasured(int(pDict[axis])):
                            containsMeasuredFlag = True
                        elif self.isParameterSampled(int(pDict[axis])):
                            containsSampleFlag = True
                    except ValueError as e:
                        pass
   
        return containsMeasuredFlag, containsSampleFlag 

    def addParameterValuesSelfJoins(self, query, pvDict, select_items= '''stoqs_instantpoint.timevalue as measurement__instantpoint__timevalue, 
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

        q = query

        add_to_from, from_sql, where_sql = self._pvSQLfragments(pvDict)

        select_items = select_items.replace('stoqs_parameter', 'p1')
        if add_to_from or from_sql or where_sql:
            # Raw query must include the primary key
            if q.find('FROM stoqs_sampledparameter') != -1:
                select_items = 'stoqs_sampledparameter.id, ' + select_items
            else:
                select_items = 'stoqs_measuredparameter.id, ' + select_items
   
            p = re.compile('SELECT .+? FROM')
            q = p.sub('SELECT ' + select_items + ' FROM', q, count=1)
            q = q.replace('SELECT FROM stoqs_measuredparameter', 'FROM ' + add_to_from + 'stoqs_measuredparameter')
            q = q.replace('FROM stoqs_measuredparameter', 'FROM ' + add_to_from + 'stoqs_measuredparameter')
            if q.find('WHERE') != -1:
                q = q.replace('WHERE', from_sql + ' WHERE ' + where_sql, 1)
            else:
                q += from_sql + ' WHERE ' + where_sql
                q = q[:-4]                              # Remove last 'AND '

        return q

    def addParameterParameterSelfJoins(self, query, pDict):
        '''
        Given a Postgresified MeasuredParameter query string @query modify it to add the P self joins needed 
        to return up to 4 parameter data values from the same measurements. The Parameter ids are specified
        by the integer values in @pList.  The original @query string may be one that is modified by 
        self.addParameterValuesSelfJoins() or not.  
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

        select_order = ('x', 'y', 'z', 'c')
        containsMeasuredFlag, containsSampleFlag = self._getContainsFlags(select_order, pDict)

        # Construct SELECT strings, must be in proper order, include depth for possible sigma-t calculation
        xyzc_items = ''
        for axis in select_order:
            if axis in pDict:
                if pDict[axis]:
                    try:
                        if self.isParameterMeasured(int(pDict[axis])):
                            xyzc_items = xyzc_items + 'mp_' + axis + '.datavalue as ' + axis + ', '
                        elif self.isParameterSampled(int(pDict[axis])):
                            xyzc_items = xyzc_items + 'sp_' + axis + '.datavalue as ' + axis + ', '
                        else:
                            # Default is to assume mp - supports legacy databases w/o the ParameterGroup assignment
                            xyzc_items = xyzc_items + 'mp_' + axis + '.datavalue as ' + axis + ', '
                    except ValueError as e:
                        if pDict[axis] == 'longitude':
                            if containsSampleFlag and not containsMeasuredFlag:
                                xyzc_items = xyzc_items + 'ST_X(stoqs_sample.geom) as ' + axis + ', '
                            else:
                                xyzc_items = xyzc_items + 'ST_X(stoqs_measurement.geom) as ' + axis + ', '
                        elif pDict[axis] == 'latitude':
                            if containsSampleFlag and not containsMeasuredFlag:
                                xyzc_items = xyzc_items + 'ST_Y(stoqs_sample.geom) as ' + axis + ', '
                            else:
                                xyzc_items = xyzc_items + 'ST_Y(stoqs_measurement.geom) as ' + axis + ', '
                        elif pDict[axis] == 'depth':
                            if containsSampleFlag and not containsMeasuredFlag:
                                xyzc_items = xyzc_items + 'stoqs_sample.depth as ' + axis + ', '
                            else:
                                xyzc_items = xyzc_items + 'stoqs_measurement.depth as ' + axis + ', '
                        elif pDict[axis] == 'time':
                            xyzc_items += "(DATE_PART('day', stoqs_instantpoint.timevalue - timestamp '%s') * 86400 + " % EPOCH_STRING
                            xyzc_items += "DATE_PART('hour', stoqs_instantpoint.timevalue - timestamp '%s') * 3600 + " % EPOCH_STRING
                            xyzc_items += "DATE_PART('minute', stoqs_instantpoint.timevalue - timestamp '%s') * 60 + " % EPOCH_STRING
                            xyzc_items += "DATE_PART('second', stoqs_instantpoint.timevalue - timestamp '%s') ) / 86400 " % EPOCH_STRING
                            xyzc_items += ' as ' + axis + ', '  
                        else:
                            logger.error('%s, but axis = %s is not a coordinate', e, pDict[axis])

        # Identify the appropriate depth for the SELECT
        if containsSampleFlag and not containsMeasuredFlag:
            # Only Sampled
            depth_item = 'DISTINCT stoqs_sample.depth, '
        else:
            # Only Measured -or- Sampled and Measured
            depth_item = 'DISTINCT stoqs_measurement.depth, '

        add_to_from = ''
        select_items = depth_item + xyzc_items

        # Construct INNER JOINS and WHERE sql for Sampled and Measured Parameter selections
        # Use aliases for joins on each axis
        where_sql = '' 
        for axis, pid in list(pDict.items()):
            if pid:
                self.logger.debug('axis, pid = %s, %s', axis, pid)
                add_to_from += '\n'
                try:
                    if self.isParameterMeasured(int(pid)):
                        add_to_from += '\nINNER JOIN stoqs_measurement m_' + axis + ' '
                        add_to_from += '\non m_' + axis + '.instantpoint_id = stoqs_instantpoint.id'
                        add_to_from += '\nINNER JOIN stoqs_measuredparameter mp_' + axis + ' '
                        add_to_from += '\non mp_' + axis + '.measurement_id = m_' + axis + '.id '
                        add_to_from += '\nINNER JOIN stoqs_parameter p_' + axis + ' '
                        add_to_from += '\non mp_' + axis + '.parameter_id = p_' + axis + '.id '
                    elif self.isParameterSampled(int(pid)):
                        add_to_from += '\nINNER JOIN stoqs_sample s_' + axis + ' '
                        add_to_from += '\non s_' + axis + '.instantpoint_id = stoqs_instantpoint.id'
                        add_to_from += '\nINNER JOIN stoqs_sampledparameter sp_' + axis + ' '
                        add_to_from += '\non sp_' + axis + '.sample_id = s_' + axis + '.id '
                        add_to_from += '\nINNER JOIN stoqs_parameter p_' + axis + ' '
                        add_to_from += '\non sp_' + axis + '.parameter_id = p_' + axis + '.id '
                    else:
                        self.logger.warn('Encountered parameter (id=%s) that is not in the Measured nor in the Sampled ParameterGroup', pid)
                    where_sql = where_sql + '(p_' + axis + '.id = ' + str(pid) + ') AND '
                except ValueError:
                    # pid likely a coordinate, ignore
                    pass

        # Modify original SQL with new joins and where sql - almost a total rewrite
        # - Need to preserve subqueries with their own FROM and WHERE words
        q = query
        select_items = select_items[:-2] + ' '                      # Remove ', '
        q = 'SELECT ' + select_items + q[q.find('FROM'):]           # Override original select items, finds first FROM which is what we want

        if q.find('WHERE') == -1 and where_sql:
            # Case where no filters applied from UI - no selections and no WHERE clause, add ours
            q += ' WHERE ' + where_sql[:-4]                         # Remove last 'AND '
        else:
            # Insert our WHERE clause into the filters that are in the original query
            self.logger.debug('q = %s', q)
            q = q.replace(' WHERE ', ' WHERE ' + where_sql, 1)      # Replace only first occurance to preserve subquery

        # Brute-force fixup of query string to deal with Sample-only query
        if containsSampleFlag and not containsMeasuredFlag:
            q = q.replace('FROM stoqs_measuredparameter', 'FROM stoqs_sampledparameter')
            q = q.replace('INNER JOIN stoqs_measurement ON (stoqs_measuredparameter.measurement_id = stoqs_measurement.id)', 
                          'INNER JOIN stoqs_sample ON (stoqs_sampledparameter.sample_id = stoqs_sample.id)')
            q = q.replace('INNER JOIN stoqs_instantpoint ON (stoqs_measurement.instantpoint_id = stoqs_instantpoint.id)',
                          'INNER JOIN stoqs_instantpoint ON (stoqs_sample.instantpoint_id = stoqs_instantpoint.id)')
            q = q.replace('INNER JOIN stoqs_parameter ON (stoqs_measuredparameter.parameter_id = stoqs_parameter.id)',
                          'INNER JOIN stoqs_parameter ON (stoqs_sampledparameter.parameter_id = stoqs_parameter.id)')
            q = q.replace('AND stoqs_measurement.depth', 'AND stoqs_sample.depth')

        # Add stoqs_measurement inner join if missing and needed for the select
        if select_items.find('stoqs_measurement') != -1:
            p = re.compile('FROM stoqs_measuredparameter.* stoqs_measurement')
            if not p.search(q):
                put_before = ' inner join stoqs_measurement on stoqs_measurement.id = stoqs_measuredparameter.measurement_id '
                put_before += ' inner join stoqs_instantpoint on stoqs_measurement.instantpoint_id = stoqs_instantpoint.id ' 
                add_to_from = put_before + add_to_from
    
        # Add stoqs_sample inner join if missing and needed for the select
        if select_items.find('stoqs_sample') != -1:
            p = re.compile('FROM stoqs_sampledparameter.* stoqs_sample')
            if not p.search(q):
                put_before = ' inner join stoqs_sample on stoqs_sample.id = stoqs_sampledparameter.sample_id '
                put_before += ' inner join stoqs_instantpoint on stoqs_sample.instantpoint_id = stoqs_instantpoint.id ' 
                add_to_from = put_before + add_to_from

        if q.lower().find('where') == -1:
            q += add_to_from
        else:
            q = q.replace(' WHERE ', add_to_from + ' WHERE ', 1)    # Replace only first occurance to preserve subquery

        self.logger.debug('q = %s', q)
        q = sqlparse.format(q, reindent=True, keyword_case='upper')

        return q

    def addSampleConstraint(self, query):
        '''
        Modify query to get sample informtation
        '''
        # Modified to return just depth, x, y points for places where there are samples (new SQL is all lower case):
        # 
        # SELECT DISTINCT stoqs_measurement.depth,
        #                 mp_x.datavalue AS x,
        #                 mp_y.datavalue AS y
        # FROM stoqs_activity
        # INNER JOIN stoqs_platform ON stoqs_platform.id = stoqs_activity.platform_id
        # INNER JOIN stoqs_instantpoint ON stoqs_instantpoint.activity_id = stoqs_activity.id
        # INNER JOIN stoqs_measurement ON stoqs_measurement.instantpoint_id = stoqs_instantpoint.id
        # INNER JOIN stoqs_measurement m_y ON m_y.instantpoint_id = stoqs_instantpoint.id
        # INNER JOIN stoqs_measuredparameter mp_y ON mp_y.measurement_id = m_y.id
        # INNER JOIN stoqs_parameter p_y ON mp_y.parameter_id = p_y.id
        # INNER JOIN stoqs_measurement m_x ON m_x.instantpoint_id = stoqs_instantpoint.id
        # INNER JOIN stoqs_measuredparameter mp_x ON mp_x.measurement_id = m_x.id
        # INNER JOIN stoqs_parameter p_x ON mp_x.parameter_id = p_x.id
        # 
        # inner join stoqs_sample on stoqs_sample.instantpoint_id = stoqs_instantpoint.id
        # 
        # WHERE (p_y.id = 8)
        #   AND (p_x.id = 6)
        # 
        #   and stoqs_sample.id is not null;
        # 
        #        depth       |          x          |          y           
        # -------------------+---------------------+----------------------
        #  -0.85070807630861 |  0.0150373139209564 | 0.000853291921996732
        #   20.8333460743087 | 0.00611123921903796 | 0.000356326309018604
        #   47.0254516097659 |  0.0166342378584501 | 0.000125864557424297
        #   41.0084011951115 |  0.0106893958691858 | 0.000111319997500448
        #   20.7215864415311 |  0.0027162356341817 |  0.00029715946267329
        #   9.18344644259678 | 0.00478679339998439 | 0.000845079474062416
        # (6 rows)

        q = query

        # Remove any color and z selections
        p = re.compile(',\s.+datavalue AS c')
        q = p.sub(' ', q)
        p = re.compile(',\s.+datavalue AS z')
        q = p.sub(' ', q)

        # Add sample name to SELECT for labeling the Parameter-Parameter plot
        q = q.replace('FROM', ', stoqs_sample.name FROM', 1)                # Replace just first occurance

        # Make sure we are getting stoqs_sample in our query - warning: very hackish
        if q.find('FROM stoqs_measuredparameter') != -1:
            if q.lower().find('inner join stoqs_sample on') == -1 :
                add_to_from = ''
                if q.lower().find('inner join stoqs_measurement on ') == -1:
                    add_to_from += ' inner join stoqs_measurement on stoqs_measurement.instantpoint_id = stoqs_instantpoint.id'
                add_to_from += ' inner join stoqs_sample on stoqs_sample.instantpoint_id = stoqs_instantpoint.id'
                if q.lower().find('where') == -1:
                    # No where clause, so add the inner joins we need - a bit of a hack
                    q += add_to_from + ' WHERE'
                else:
                    q = q.replace('WHERE', add_to_from + ' WHERE', 1)       # Replace just first occurance

            if not q.strip().lower().endswith('where'):
                q += ' and '
    
            q += ' stoqs_sample.id is not null'

        self.logger.debug('q = %s', q)
        q = sqlparse.format(q, reindent=True, keyword_case='upper')

        return q

    @staticmethod
    def addPrimaryKey(query, table='stoqs_measuredparameter'):
        '''
        Django 1.7 gives InvalidQuery: Raw query must include the primary key if 'id' not in select list
        '''
        q = query
        p = re.compile('SELECT (.+?) FROM')
        m = p.match(q.replace('\n',''))
        if 'id' not in [item.strip() for item in m.group(1).split(',')]:
            q = p.sub('SELECT ' + table + '.id, ' + m.group(1) + ' FROM', q, count=1)

        return q

