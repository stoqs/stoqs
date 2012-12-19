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
from django.db.models.query import RawQuerySet
from datetime import datetime
from stoqs import models
from utils import postgresifySQL
import logging
import pprint
import re
import locale
import time
import os
import tempfile

logger = logging.getLogger(__name__)

class MPQuery(object):
    '''
    This class is designed to handle building and managing queries against the MeasuredParameter table of the STOQS database.
    '''
    def __init__(self, request):
        '''
        This object saves instances of the QuerySet and count so that get_() methods work like a singleton to 
        return the value for the object.  MPQuery objects are meant to be instantiated by the STOQSQManager 
        buildQuerySet() method and are unique for each AJAX request.  After buildMPQuerySet() is executed
        the member values below can be accessed.
        '''
        self.request = request
        self.qs_mp = None
        self.sql = None
        self._count = None
        self._MProws = []
        
    def buildMPQuerySet(self, *args, **kwargs):
        '''
        Build the query set based on selections from the UI. For the first time through kwargs will be empty 
        and self.qs_mp will have no constraints and will be all of the MeasuredParameters in the database.
        '''

        if self.qs_mp is None:
            self.kwargs = kwargs
            self.qs_mp = self.getMeasuredParametersQS()
            self.sql = self.getMeasuredParametersPostgreSQL()

    def getQueryParms(self):
        '''
        Extract constraints from the querystring kwargs to construct a dictionary of query parameters
        that can be used as a filter for MeasuredParameters.  Handles all constraints except parameter
        value constraints.
        '''
        qparams = {}

        logger.info('self.kwargs = %s', pprint.pformat(self.kwargs))
        if self.kwargs.has_key('parametername'):
            if self.kwargs['parametername']:
                qparams['parameter__name__in'] = self.kwargs['parametername']
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

        logger.debug('qparams = %s', pprint.pformat(qparams))

        return qparams

    def getMeasuredParametersQS(self):
        '''
        Return query set of MeasuremedParameters given the current constraints.  If no parameter is selected return None.

        What KML generation expects:
            data = [(mp.measurement.instantpoint.timevalue, mp.measurement.geom.x, mp.measurement.geom.y,
                     mp.measurement.depth, pName, mp.datavalue, mp.measurement.instantpoint.activity.platform.name)
                     for mp in qs_mp]

        What Viz.py expects:
            if type(qs_mp) == RawQuerySet:
                # Most likely because it is a RawQuerySet from a ParameterValues query
                for mp in qs_mp:
                    ##logger.debug('mp = %s, %s, %s', mp.timevalue, mp.depth, mp.datavalue)
                    x.append(time.mktime(mp.timevalue.timetuple()) / scale_factor)
                    y.append(mp.depth)
                    z.append(mp.datavalue)
            else:
                for mp in qs_mp.values('measurement__instantpoint__timevalue', 'measurement__depth', 'datavalue'):
                    x.append(time.mktime(mp['measurement__instantpoint__timevalue'].timetuple()) / scale_factor)
                    y.append(mp['measurement__depth'])
                    z.append(mp['datavalue'])
        '''

        logger.debug('dbalias = %s', self.request.META['dbAlias'])

        qparams = self.getQueryParms()

        qs_mp = models.MeasuredParameter.objects.using(self.request.META['dbAlias']).filter(**qparams)
        qs_mp = qs_mp.values('measurement__instantpoint__timevalue', 'measurement__geom')

        if self.kwargs.has_key('parametervalues'):
            if self.kwargs['parametervalues']:
                sql = postgresifySQL(str(qs_mp.query))
                logger.debug('\n\nsql before query = %s\n\n', sql)
                # Modify sql to do a self-join on MeasuredParameter selecting on data values
                sql_pv = self.addParameterValuesSelfJoins(sql, self.kwargs['parametervalues'])
                logger.debug('\n\nsql_pv for parametervalue query = %s\n\n', sql_pv)
                qs_mp = models.MeasuredParameter.objects.raw(sql_pv)

        if qs_mp:
            logger.debug('type(qs_mp) = %s', type(qs_mp))
            logger.debug(pprint.pformat(str(qs_mp.query)))
        else:
            logger.debug("No queryset returned for qparams = %s", pprint.pformat(qparams))
        return qs_mp

    def getMPCount(self):
        '''
        Get the actual count of measured parameters giving the exising query.  If private _count
        member variable exist return that, otherwise expand the query set as necessary to get and
        return the count.
        '''
        if not self._count:
            logger.debug('Counting MPs from qs_mp = %s', str(self.qs_mp))
            if type(self.qs_mp) == RawQuerySet:
                # Most likely a RawQuerySet from a ParameterValues selection
                self._count = sum(1 for mp in self.qs_mp)
            else:
                self._count = self.qs_mp.count()

        logger.debug('self._count = %d', self._count)
        return int(self._count)

    def getMProws(self):
        '''
        Return a list of dictionaries of Measured Parameter data loaded from the current Query Set.
        Clients should request data from this method rather than iterating through the Query Set returned
        by getMeasuredParametersQS() as getMProws() returns consistently formatted data whether we have
        a GeoQuerySet or a RawQuerySet.

        For Flot contour plot we need just depth and time.
        For KML output we need in addition: latitude, longitude, parameter name, and platform name
        '''
        if not self._MProws:
            if type(self.qs_mp) == RawQuerySet:
                for mp in qs_mp:
                    self._MProws.append(  { 'timevalue': mp.timevalue,
                                            'depth': mp.depth,
                                            'lon': mp.geom.x,
                                            'lat': mp.geom.y,
                                            'datavalue': mp.datavalue
                                           })
            else:
                for mp in qs_mp.values( 'parameter__name', 'measurement__instantpoint__activity__platform.name',
                                        'measurement__instantpoint__timevalue', 'measurement__depth', 
                                        'mp.measurement.geom.x', 'mp.measurement.geom.y', 'datavalue'):
                    self._MProws.append(  { 
                                            'parametername': mp.parameter.name,
                                            'platformname': mp.measurement.instantpoint.activity.platform.name,
                                            'timevalue': mp.measurement.instantpoint.timevalue,
                                            'depth': mp.measurement.depth,
                                            'lon': mp.mp.measurement.geom.x,
                                            'lat': mp.mp.measurement.geom.y,
                                            'datavalue': mp.datavalue
                                           })

        return self._MProws
            

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
        if self._count:
            qs_mp = self.qs_mp

            if type(qs_mp) == RawQuerySet:
                # Most likely becase its a RawQuerySet from a ParameterValues selection
                sql = postgresifySQL(str(qs_mp.query)) + ';'
                sql = self.addParameterValuesSelfJoins(sql, self.kwargs['parametervalues'])
                sql = '\c %s\n' % settings.DATABASES[self.request.META['dbAlias']]['NAME'] + sql
            else:
                qs_mp = qs_mp.values(   'measurement__instantpoint__activity__platform__name', 'measurement__instantpoint__timevalue', 
                                        'measurement__geom', 'parameter__name', 'datavalue')
                if qs_mp:
                    sql = '\c %s\n' % settings.DATABASES[self.request.META['dbAlias']]['NAME']
                    sql +=  postgresifySQL(str(qs_mp.query)) + ';'

        return sql

    def addParameterValuesSelfJoins(self, query, pvDict, select_items='stoqs_instantpoint.timevalue, stoqs_measurement.depth, stoqs_measuredparameter.datavalue'):
        '''
        Given a Postgresified MeasuredParameter query string @query' modify it to add the MP self joins needed 
        to restrict the data selection to the ParameterValues specified in @pvDict.  Add to the required
        measuredparameter.id the select items in the comma separeated value string @select_items.
        Return a Postgresified query string that can be used by Django's Manage.raw().
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
                p = re.compile("[';]")
                if p.search(k) or p.search(v[0]) or p.search(v[1]):
                    raise Exception('Invalid ParameterValue constraint expression: %s, %s' % (k, v))
                where_sql = where_sql + "(p" + str(i) + ".name = '" + k + "') AND "
                where_sql = where_sql + "(mp" + str(i) + ".datavalue > " + str(v[0]) + ") AND "
                where_sql = where_sql + "(mp" + str(i) + ".datavalue < " + str(v[1]) + ") AND "
                where_sql = where_sql + "(mp" + str(i) + ".parameter_id = p" + str(i) + ".id) AND "

        q = query
        p = re.compile('SELECT .+ FROM')
        q = p.sub('SELECT ' + select_items + ' FROM', q)
        q = q.replace('SELECT FROM stoqs_measuredparameter', 'FROM ' + add_to_from + 'stoqs_measuredparameter')
        q = q.replace('FROM stoqs_measuredparameter', 'FROM ' + add_to_from + 'stoqs_measuredparameter')
        q = q.replace('WHERE', from_sql + ' WHERE' + where_sql)

        return q


