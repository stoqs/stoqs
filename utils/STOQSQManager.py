'''
'''
from django.conf import settings
from django.db import connections
from django.db.models import Q, Max, Min
from stoqs import models
import re

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
        self.request=request
        self.dbname=dbname
        self.response=response
        
    def buildQuerySet(self, **kwargs):
        '''
        Right now supported keyword arguments are the following:
        parameters - a list of parameter names to include
        platforms - a list of platform names to include
        time - a two-tuple consisting of a start and end time, if either is None, the assumption is no start (or end) time
        depth - a two-tuple consisting of a range (start/end depth, if either is None, the assumption is no start (or end) depth
        These are all called internally - so we'll assume that all the validation has been done in advance,
        and the calls to this method meet the requirements stated above.
        '''
        if (not kwargs):
            qs=models.Activity.objects.using('stoqs_oct2010').select_related(depth=3).filter(activityparameter__parameter__pk__isnull=False,
                                                                                         activityparameter__activity__pk__isnull=False,
                                                                                         platform__pk__isnull=False,
                                                                                         instantpoint__measurement__pk__isnull=False)
        else:
            qs=models.Activity.objects.using('stoqs_oct2010').select_related(depth=3).all()
        for k, v in kwargs.iteritems():
            '''
            Check to see if there is a "builder" for a Q object using the given parameters.
            '''
            if not v:
                continue
            if hasattr(self, '_%sQ' % (k,)):
                # Call the method if it exists, and add the resulting Q object to the filtered
                # queryset.
                q=getattr(self,'_%sQ' % (k,))(v)
                qs=qs.filter(q)
        self.qs=qs.distinct()
        
    def generateOptions(self):
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
        options_functions={'parameters': self.getParameters,
                           'platforms': self.getPlatforms,
                           'time': self.getTime,
                           'depth': self.getDepth,
                           'count': self.getCount,
                           }
        
        results={}
        for k,v in options_functions.iteritems():
            results[k]=v()
        #results['parameters']=[('tet',"1"),('test',"2")]
        import pprint
        pprint.pprint(str(self.qs.query))
        pprint.pprint(results)
        return results
    
    #
    # Methods that generate summary data, based on the current query criteria.
    #
        
    def getCount(self):
        '''
        Get the count of rows to be returned if we ran this entire query.
        '''
        return self.qs.count()
        
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
        qs=self.qs.aggregate(Max('instantpoint__timevalue'), Min('instantpoint__timevalue'))
        return (qs['instantpoint__timevalue__min'], qs['instantpoint__timevalue__max'],)
    
    def getDepth(self):
        '''
        Based on the current selected query criteria, determine the available depth range.  That'll be
        returned as a 2-tuple as the min and max values that are selectable.
        '''
        qs=self.qs.aggregate(Max('instantpoint__measurement__depth'), Min('instantpoint__measurement__depth'))
        return (qs['instantpoint__measurement__depth__min'],qs['instantpoint__measurement__depth__max'])
        
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
            q=Q(instantpoint__timevalue__gte=times[0])
        if times[1] is not None:
            q=q & Q(instantpoint__timevalue__lte=times[1])
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
            q=Q(instantpoint__measurement__depth__gte=depth[0])
        if depth[1] is not None:
            q=q & Q(instantpoint__measurement__depth__lte=depth[1])
        return q
    
    #
    # Method to get the query used based on the current Q object.
    #
    def getSQLWhere(self):
        '''
        This method will generate a pseudo-query, and then normalize it to a standard SQL query.  While for
        PostgreSQL this is usually the actual query, we might need to massage it a bit to handle quoting
        issues and such.  The string representation of the querset's query attribute gives us the query.
        
        This is really useful when we want to generate a new mapfile based on the current query result.  We just want
        the WHERE clause of the query, since that's where the predicate exists.
        '''
        querystring=str(self.qs.query)
        
        return querystring
        
    