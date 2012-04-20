'''
'''
from django.conf import settings
from django.db import connections
from django.db.models import Q, Max, Min
from stoqs import models
import logging
import pprint
import re

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
        
    def buildQuerySet(self, *args, **kwargs):
        '''
        Build the query set based on any selections form the UI. For the first time through  kwargs will be empty 
        and self.qs will be built of a join of activities, parameters, and platforms with no constraints.

        Right now supported keyword arguments are the following:
            parameters - a list of parameter names to include
            platforms - a list of platform names to include
            time - a two-tuple consisting of a start and end time, if either is None, the assumption is no start (or end) time
            depth - a two-tuple consisting of a range (start/end depth, if either is None, the assumption is no start (or end) depth

        These are all called internally - so we'll assume that all the validation has been done in advance,
        and the calls to this method meet the requirements stated above.
        '''
        if 'qs' in args:
            logger.debug('Using query string passed in to make a non-activity based query')
            qs = args['qs']
        else:
            logger.debug('Making default activity based query')
            if (not kwargs):
                qs = models.Activity.objects.using(self.dbname).select_related(depth=3).filter( activityparameter__parameter__pk__isnull=False,
                                                                                                activityparameter__activity__pk__isnull=False,
                                                                                                simpledepthtime__pk__isnull=False,
                                                                                                platform__pk__isnull=False)
            else:
                qs = models.Activity.objects.using(self.dbname).select_related(depth=3).all()   # To receive filters constructed below from kwargs
    
        for k, v in kwargs.iteritems():
            '''
            Check to see if there is a "builder" for a Q object using the given parameters.
            '''
            if not v:
                continue
            if hasattr(self, '_%sQ' % (k,)):
                # Call the method if it exists, and add the resulting Q object to the filtered
                # queryset.
                q = getattr(self,'_%sQ' % (k,))(v)
                logger.debug('k = %s, v = %s, q = %s', k, v, q)
                qs = qs.filter(q)
        self.qs = qs.distinct()
        self.kwargs = kwargs
        
    def generateOptions(self, stoqs_object = None):
        '''
        Generate a dictionary of all the selectable parameters by executing each of the functions
        to generate those parameters.  In this case, we'll simply do it by defining the dictionary and it's associated
        function, then iterate over that dictionary calling the function(s) to get the value to be returned.
        Note that in the case of parameters and platforms the result is a list of 2-tuples, with the UUID
        and NAME of the associated element.  For time and depth, the result is a single 2-tuple with the
        min and max value (respectively.)  
        These objects are "simple" dictionaries using only Python's built-in types - so conversion to a
        corresponding JSON object should be trivial.
        '''
        if stoqs_object:
            stoqs_object_name = stoqs_object._meta.verbose_name.lower().replace(' ', '_')
            if stoqs_object_name == 'activity':
                options_functions={
                                   'platform_name': self.getPlatforms,
                                   }
        else:
            options_functions={'parameters': self.getParameters,
                               'platforms': self.getPlatforms,
                               'time': self.getTime,
                               'depth': self.getDepth,
                               'simpledepthtime': self.getSimpleDepthTime,
                               'count': self.getCount,
                               }
        
        results = {}
        for k,v in options_functions.iteritems():
            results[k] = v()
        
        logger.info('qs.query = %s', pprint.pformat(str(self.qs.query)))
        logger.info('results = %s', pprint.pformat(results))
        return results
    
    #
    # Methods that generate summary data, based on the current query criteria.
    #
        
    def getCount(self):
        '''
        Get the count of measured parameters giving the exising query
        '''
        qs_mp = self.getMeasuredParametersQS()
        if qs_mp:
            return qs_mp.count()
        else:
            return 0
        
    def getMeasuredParametersQS(self):
        '''
        Return query set of MeasuremedParameters given the current constraints.  If no parameter is selected return None.
        '''
        qparams = {}

        logger.info(pprint.pformat(self.kwargs))
        if self.kwargs.has_key('parameters'):
            if self.kwargs['parameters']:
                qparams['parameter__uuid__in'] = self.kwargs['parameters']
        if self.kwargs.has_key('platforms'):
            if self.kwargs['platforms']:
                qparams['measurement__instantpoint__activity__platform__uuid__in'] = self.kwargs['platforms']
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

        logger.debug(pprint.pformat(qparams))
        qs_mp = models.MeasuredParameter.objects.filter(**qparams)
        if qs_mp:
            logger.debug(pprint.pformat(str(qs_mp.query)))
        else:
            logger.debug("No queryset returned for qparams = %s", pprint.pformat(qparams))
        return qs_mp

    def getSampleQS(self):
        '''
        Return query set of Samples given the current constraints. 
        '''
        qparams = {}

        logger.info(pprint.pformat(self.kwargs))
        if self.kwargs.has_key('platforms'):
            if self.kwargs['platforms']:
                qparams['instantpoint__activity__platform__uuid__in'] = self.kwargs['platforms']
        if self.kwargs.has_key('time'):
            if self.kwargs['time'][0] is not None:
                qparams['instantpoint__timevalue__gte'] = self.kwargs['time'][0]
            if self.kwargs['time'][1] is not None:
                qparams['instantpoint__timevalue__lte'] = self.kwargs['time'][1]
        if self.kwargs.has_key('depth'):
            if self.kwargs['depth'][0] is not None:
                qparams['depth__gte'] = self.kwargs['depth'][0]
            if self.kwargs['depth'][1] is not None:
                qparams['depth__lte'] = self.kwargs['depth'][1]

        logger.debug(pprint.pformat(qparams))
        qs_sample = models.Sample.objects.filter(**qparams)
        if qs_sample:
            logger.debug(pprint.pformat(str(qs_sample.query)))
        else:
            logger.debug("No queryset returned for qparams = %s", pprint.pformat(qparams))
        return qs_sample

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

    def getParameters(self):
        '''
        Get a list of the unique parameters that are left based on the current query criteria.  Also
        return the UUID's of those, since we need to return those to perform the query later.
        Lastly, we assume here that the uuid's and name's have a 1:1 relationship - this should be enforced
        somewhere in the database hopefully.  If not, we'll return the duplicate name/uuid pairs as well.
        '''
        qs=self.qs.values('activityparameter__parameter__uuid','activityparameter__parameter__name').distinct()
        results=[]
        for row in qs:
            name=row['activityparameter__parameter__name']
            uuid=row['activityparameter__parameter__uuid']
            if name is not None and uuid is not None:
                results.append((name,uuid,))
        return results
    
    def getPlatforms(self):
        '''
        Get a list of the unique platforms that are left based on the current query criteria.  Also
        return the UUID's of those, since we need to return those to perform the query later.
        Lastly, we assume here that the uuid's and name's have a 1:1 relationship - this should be enforced
        somewhere in the database hopefully.  If not, we'll return the duplicate name/uuid pairs as well.
        '''
        qs=self.qs.values('platform__uuid', 'platform__name').distinct()
        results=[]
        for row in qs:
            name=row['platform__name']
            uuid=row['platform__uuid']
            if name is not None and uuid is not None:
                results.append((name,uuid,))
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
        return (qs['startdate__min'], qs['enddate__max'],)
    
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
        return (qs['mindepth__min'],qs['maxdepth__max'])
        
    def getSimpleDepthTime(self):
        '''
        Based on the current selected query criteria for activities, return the associated SimpleDepth time series
        values as a 2-tuple list for plotting by flot in the UI.
        '''
        return(self.qs.values_list( 'simpledepthtime__epochmilliseconds', 
                                    'simpledepthtime__depth').order_by('simpledepthtime__epochmilliseconds'))

    #
    # Methods that generate Q objects used to populate the query.
    #    
        
    def _parametersQ(self, parameters):
        '''
        Build a Q object to be added to the current queryset as a filter.  This should 
        ensure that our result doesn't contain any parameters that were not selected.
        '''
        q=Q()
        if parameters is None:
            return q
        else:
            q=Q(activityparameter__parameter__uuid__in=parameters)
        return q
    
    def _platformsQ(self, platforms):
        '''
        Build a Q object to be added to the current queryset as a filter.  This will ensure that we
        only generate the other values/sets for platforms that were selected.
        '''
        q=Q()
        if platforms is None:
            return q
        else:
            q=Q(platform__uuid__in=platforms)
        return q    
    
    def _timeQ(self, times):
        '''
        Build a Q object to be added to the current queryset as a filter.  This ensures that we limit
        things down based on the time range selected by the user.
        '''
        q=Q()
        if not times:
            return q
        if times[0] is not None:
            q=Q(enddate__gte=times[0])
        if times[1] is not None:
            q=q & Q(startdate__lte=times[1])
        return q
    
    def _depthQ(self, depth):
        '''
        Build a Q object to be added to the current queryset as a filter.  Once again, we want
        to make sure that we only generate the "leftover" components based on the selected depth
        range.
        '''
        q=Q()
        if not depth:
            return q
        if depth[0] is not None:
            q=Q(maxdepth__gte=depth[0])
        if depth[1] is not None:
            q=q & Q(mindepth__lte=depth[1])
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

    def postgresifySQL(self, query):
        '''
        Given a generic database agnostic Django query string modify it using regular expressions to work
        on a PostgreSQL server.
        '''
        # Get text of query to quotify for Postgresql
        q = str(query)

        # Remove double quotes from around all table and colum names
        q = q.replace('"', '')
        logger.debug('Before: %s', q)

        # Add aliases for geom and gid - Activity
        q = q.replace('stoqs_activity.id', 'stoqs_activity.id as gid', 1)
        q = q.replace('stoqs_activity.maptrack', 'stoqs_activity.maptrack as geom')
   
        # Add aliases for geom and gid - Activity
        q = q.replace('stoqs_sample.id', 'stoqs_sample.id as gid', 1)
        q = q.replace('stoqs_sample.geom', 'stoqs_sample.geom as geom')
   
        # Put quotes around any IN parameters:
        #  IN (a81563b5f2464a9ab2d5d7d78067c4d4)
        m = re.search( r' IN \(([\S^\)]+)\)', q)
        if m:
            logger.debug(m.group(1))
            q = re.sub( r' IN \([\S^\)]+\)', ' IN (\'' + m.group(1) + '\')', q)

        # Put quotes around the DATE TIME parameters, treat each one separately:
        #  >= 2010-10-27 07:12:10
        #  <= 2010-10-28 08:22:52
        m1 = re.search( r'>= (\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d)', q)
        if m1:
            logger.debug('>= %s', m1.group(1))
            q = re.sub( r'>= \d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d', '>= \'' + m1.group(1) + '\'', q)
        m2 = re.search( r'<= (\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d)', q)
        if m2:
            logger.debug('<= %s', m2.group(1))
            q = re.sub( r'<= \d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d', '<= \'' + m2.group(1) + '\'', q)

        # Put quotes around 'platform.name = ' parameters:
        #  stoqs_platform.name = dorado 
        m = re.search( r'stoqs_platform.name = (.+?) ', q)
        if m:
            logger.debug('stoqs_platform.name =  %s', m.group(1))
            q = re.sub( r'stoqs_platform.name = .+? ', 'stoqs_platform.name =  \'' + m.group(1) + '\'', q)

        logger.debug('After: %s', q)

        return q

    ##def getMapfileDataStatement(self, Q_object = None):
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
            as subquery using unique gid using srid=4326''' % self.postgresifySQL(qs.query)
        
        return geo_query


    def getSampleGeoQuery(self, Q_object = None):
        '''
        This method generates a string that can be put into a Mapserver mapfile DATA statment.
        It is for returning Samples.
        '''
        qs = self.getSampleQS()

        # Add any more filters (Q objects) if specified
        if Q_object:
            qs = qs.filter(Q_object)

        # Query for mapserver
        geo_query = '''geom from (%s)
            as subquery using unique gid using srid=4326''' % self.postgresifySQL(qs.query)
        
        return geo_query

