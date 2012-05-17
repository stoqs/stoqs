__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

The view functions for the stoqsdb_* database web app.  These functions are called after successful matching
from the patterns in urls.py.  They query the database and format the output for the response.

Most responses return the positions in time order.  The exceptions are if the 'last' option is specified, or
if 'stride' is specified.  In these cases the results are returned in reverse time order so as to always return
the most recent position reports.

This web app derives from the MBARItracking web app.  I addition to delivering platform names, types, and
positions, it also delivers measured_paramaters based on various common query criteria.

@undocumented: __doc__ parser
@status: production
@license: GPL
'''

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse
from django.conf import settings
from django.db import connection
from django.db.models import Q
from django.utils import simplejson
from django.core import serializers

from datetime import datetime, timedelta
import time
import stoqs.models as mod
import csv
import sys
import logging 
import os
from random import randint
import tempfile
from utils.STOQSQManager import STOQSQManager
from utils import encoders

logger = logging.getLogger(__name__)

class BaseOutputer(object):
    '''Base methods for supported responses for all STOQS objects: csv, json, kml, html, etc.
    '''
    html_tmpl_file = 'html_template.html'

    def __init__(self, request, format, query_set, stoqs_object=None):
        self.request = request
        self.format = format
        self.query_set = query_set
        self.stoqs_object = stoqs_object
        self.stoqs_object_name = stoqs_object._meta.verbose_name.lower().replace(' ', '_')
        self.html_template = '%s_tmpl.html' % self.stoqs_object_name
        # This file must be writable by the server running this Django app, whereever tempfile puts it should work.
        # /tmp should be occasionally be scrubbed of old tempfiles by a cron(1) job.
        self.html_tmpl_path = tempfile.NamedTemporaryFile(dir='/tmp', prefix=self.stoqs_object_name+'_', suffix='.html').name

    def build_html_template(self):
        '''Build template for stoqs_object using generic html template with a column for each attribute
        '''
        response = render_to_response(self.html_tmpl_file, {'cols': [field.name for field in self.stoqs_object._meta.fields] },
                                         context_instance = RequestContext(self.request))

        logger.debug("Writing template: %s", self.html_tmpl_path)

        fh = open(self.html_tmpl_path, 'w')
        for line in response:
            fh.write(line)
        fh.close()

    def getFields(self):
        '''
        Default fields for model class retreived by introspection.  Override to add other fields from joined tables.
        '''
        fields = []
        for f in self.stoqs_object._meta.fields:
            fields.append(f.name)

        return fields

    def ammendFields(self, fields):

        # Append Django field lookups to the field names, see: https://docs.djangoproject.com/en/dev/ref/models/querysets/#field-lookups
        fieldLookups = ('exact', 'iexact', 'contains', 'icontains', 'in', 'gt', 'gte', 'lt', 'lte', 'startswith', 'istartswith',
                        'endswith', 'iendswith', 'range', 'year', 'month', 'day', 'week_day', 'isnull', 'search', 'regex', 'iregex')
        ammendedFields = []
        ammendedFields.extend(fields)
        for addition in fieldLookups:
            for f in fields:
                ammendedFields.append('%s__%s' % (f, addition, ))

        return ammendedFields

    def applyQueryParams(self, fields):
        '''
        Apply any constraints specified in the query string with ammened Django field lookups
        '''
        qparams = {}    
        logger.debug(self.request.GET)
        for f in self.ammendFields(fields):
            logger.debug(f)
            if self.request.GET.getlist(f):
                qparams[f] = self.request.GET.getlist(f)[0]     # Get's just first element, will need to change for multiple params

        logger.debug(qparams)
        self.query_set = self.query_set.filter(**qparams)

    def process_request(self):
        '''
        Default request processing: Apply any query parameters and get fields for the values.  Respond with requested format.
        '''
        fields = self.getFields()
        self.applyQueryParams(self.ammendFields(fields))
        qs = self.query_set
        qs = qs.values(*fields)

        if self.format == 'csv' or self.format == 'tsv':
            response = HttpResponse()
            if self.format == 'tsv':
                response['Content-type'] = 'text/tab-separated-values'
                response['Content-Disposition'] = 'attachment; filename=%s.tsv' % self.stoqs_object_name
                writer = csv.writer(response, delimiter='\t')
            else:
                response['Content-type'] = 'text/csv'
                response['Content-Disposition'] = 'attachment; filename=%s.csv' % self.stoqs_object_name
                writer = csv.writer(response)
            writer.writerow(fields)
            for obj in qs:
                writer.writerow([obj[f] for f in fields])

            return response
        elif self.format == 'xml':
            return HttpResponse(serializers.serialize('xml', qs), 'application/xml')

        elif self.format == 'json':
            return HttpResponse(simplejson.dumps(qs, cls=encoders.STOQSJSONEncoder), 'application/json')

        else:
            self.build_html_template()
            return render_to_response(self.html_tmpl_path, {'list': qs})

class SampleOutputer(BaseOutputer):
    '''
    Do special things for Sample responses: Add Activity name and Instantpoint timevalue
    '''

    def getFields(self):
        '''
        Joins needed to get time and activity name
        '''
        fields = [  'uuid', 'depth', 'geom', 'name', 'sampletype__name', 'samplepurpose__name', 
                    'volume', 'filterdiameter', 'filterporesize', 'laboratory', 'researcher',
                    'instantpoint__timevalue', 'instantpoint__activity__name']
        return fields


def showSample(request, format = 'html'):
    stoqs_object = mod.Sample
    query_set = stoqs_object.objects.all().order_by('instantpoint__timevalue')

    s = SampleOutputer(request, format, query_set, stoqs_object)
    return s.process_request()

def showInstantPoint(request, format = 'html'):
    stoqs_object = mod.InstantPoint
    query_set = stoqs_object.objects.all().order_by('timevalue')

    o = BaseOutputer(request, format, query_set, stoqs_object)
    return o.process_request()

def showPlatform(request, format = 'html'):
    stoqs_object = mod.Platform
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, format, query_set, stoqs_object)
    return o.process_request()

def showPlatformType(request, format = 'html'):
    stoqs_object = mod.PlatformType
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, format, query_set, stoqs_object)
    return o.process_request()

def showParameter(request, format = 'html'):
    stoqs_object = mod.Parameter
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, format, query_set, stoqs_object)
    return o.process_request()

def showSampleType(request, format = 'html'):
    stoqs_object = mod.SampleType
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, format, query_set, stoqs_object)
    return o.process_request()

def showAnalysisMethod(request, format = 'html'):
    stoqs_object = mod.AnalysisMethod
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, format, query_set, stoqs_object)
    return o.process_request()

# --------------------------------------------------------------------------------------------------------
# Work in progress: adding Q object building for Activity requests following the pattern in STOQSQManager.py
# with the intention of applying the same method in a similar way to the other STOQS model objects.

def _platformsQ(platforms):
    '''
    Build a Q object to be added to the current queryset as a filter.
    '''
    q = Q()
    if platforms is None:
        return q
    else:
        q = Q(platform__name__in=platforms)
    return q

def showActivity(request, format = 'html', order = 'startdate'):
    '''
    Other potential order fields: name, startdate, enddate, loadeddate
    '''
    response = HttpResponse()
    query_parms = {'platform__name': 'platform__name', 
                    # Can add additional query parms, which may be multi-valued, e.g. start & end times
                   }
    params = {}
    for key, value in query_parms.iteritems():
        if type(value) in (list, tuple):
            params[key] = [request.GET.get(p, None) for p in value]
        else:
            qlist = request.GET.getlist(key)
            if qlist:
                params[key] = list

    stoqs_object = mod.Activity
    qs = stoqs_object.objects.all().order_by(order)


    # Calling this will execute a measuredparameter count, which can take several seconds with a multi-million measurement database
    # This is a work in progress to support arbitrary query strings for Acvivity responses
    ##qm = STOQSQManager(request, response, request.META['dbAlias'])
    ##qm.buildQuerySet(qs, **params)
    ##options = simplejson.dumps(qm.generateOptions(),
    ##                           cls=encoders.STOQSJSONEncoder)
    ##                           # use_decimal=True) # After json v2.1.0 this can be used instead of the custom encoder class.

    if params:
        for k,v in params.iteritems():
            logger.debug('k = %s, v = %s', k, str(v))
            qs = qs.filter(_platformsQ(params['platform__name']))
    
    logger.debug('qs = %s', qs )
    o = BaseOutputer(request, format, qs, stoqs_object)
    return o.process_request()

#---------------------------------------------------------------------------------------------------------------------


def showActivityType(request, format = 'html'):
    stoqs_object = mod.ActivityType
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, format, query_set, stoqs_object)
    return o.process_request()

def showCampaign(request, format = 'html'):
    stoqs_object = mod.Campaign
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, format, query_set, stoqs_object)
    return o.process_request()

def showResource(request, format = 'html'):
    stoqs_object = mod.Resource
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, format, query_set, stoqs_object)
    return o.process_request()

def showResourceType(request, format = 'html'):
    stoqs_object = mod.ResourceType
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, format, query_set, stoqs_object)
    return o.process_request()

def showActivityResource(request, format = 'html'):
    stoqs_object = mod.ActivityResource
    query_set = stoqs_object.objects.all()

    o = BaseOutputer(request, format, query_set, stoqs_object)
    return o.process_request()

def showActivityParameter(request, format = 'html'):
    stoqs_object = mod.ActivityParameter
    query_set = stoqs_object.objects.all()

    o = BaseOutputer(request, format, query_set, stoqs_object)
    return o.process_request()

def showSimpleDepthTime(request, format = 'html'):
    stoqs_object = mod.SimpleDepthTime
    query_set = stoqs_object.objects.all()

    o = BaseOutputer(request, format, query_set, stoqs_object)
    return o.process_request()

