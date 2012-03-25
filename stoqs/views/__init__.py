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
from django.utils import simplejson
from django.core import serializers
from utils.STOQSQManager import STOQSQManager
from utils import encoders

from datetime import datetime, timedelta
import time
import stoqs.models as mod
import csv
import sys
import logging 
import os
from random import randint
import tempfile

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
        # The tmpfile  must be writable by the server running this Django app, whereever tempfile puts it should work
        # (Watch for issues (file ownership) when transitioning to production.)
        self.html_tmpl_tmpfile = tempfile.NamedTemporaryFile(prefix=self.stoqs_object_name+'_', suffix='.html')
        self.html_tmpl_path = self.html_tmpl_tmpfile.name

    def build_html_template(self):
        '''Build template for stoqs_object using generic html template with a column for each attribute
        '''
        response = render_to_response(self.html_tmpl_file, {'cols': [field.name for field in self.stoqs_object._meta.fields] },
                                         context_instance = RequestContext(self.request))

        logger.debug("Writing template: %s", self.html_tmpl_path)

        fh = open(self.html_tmpl_path, 'w')
        for line in response:
            fh.write(line)

    def process_request(self):
        logger.debug("format = %s", self.format)
        if self.format == 'csv':
            response = HttpResponse(mimetype='text/csv')
            response['Content-Disposition'] = 'attachment; filename=%s.csv' % self.stoqs_object_name
            writer = csv.writer(response)
            logger.debug('instance._meta.fields = %s', self.stoqs_object._meta.fields)
            writer.writerow([field.name for field in self.stoqs_object._meta.fields])
            for rec in self.query_set:
                row = []
                for field in self.stoqs_object._meta.fields:
                    row.append(getattr(rec, field.name))
                logger.debug('row = %s', row)
                writer.writerow(row)
            return response
        elif self.format == 'xml':
            return HttpResponse(serializers.serialize('xml', self.query_set), 'application/xml')
        elif self.format == 'json':
            return HttpResponse(serializers.serialize('json', self.query_set), 'application/json')
        else:
            self.build_html_template()
            return render_to_response(self.html_tmpl_path, {'list': self.query_set})


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

def showActivity(request, format = 'html'):
    stoqs_object = mod.Activity
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, format, query_set, stoqs_object)
    return o.process_request()

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


def queryData(request, format=None):
    response=HttpResponse()
    query_parms={'parameters': 'parameters', # This should be specified once in the query string for each parameter.
                 'time': ('start_time','end_time'), # Single values
                 'depth': ('min_depth', 'max_depth'), # Single values
                 'platforms': 'platforms', # Specified once in the query string for each platform.
                 }
    params={}
    for key, value in query_parms.iteritems():
        if type(value) in (list, tuple):
            params[key]=[request.GET.get(p, None) for p in value]
        else:
            params[key]=request.GET.getlist(key)
    
    qm=STOQSQManager(request, response, request.META['dbAlias'])
    qm.buildQuerySet(**params)
    
    if not format: # here we export in a given format, or just provide summary data if no format is given.
        response['Content-Type']='text/json'
        response.write(simplejson.dumps(qm.generateOptions(),
                                        cls=encoders.STOQSJSONEncoder))
                                        # use_decimal=True) # After json v2.1.0 this can be used instead of the custom encoder class.
    elif format == 'json':
        response['Content-Type']='text/json'
        response.write(serializers.serialize('json', qm.qs))
    return response
    
def queryUI(request):
    formats={'csv': 'Comma-Separated Values (CSV)',
             'DAP': 'OPeNDAP Format',
             'KML': 'KML (Google Earth)'}
    return render_to_response('stoqsquery.html', {'site_uri': request.build_absolute_uri('/')[:-1],
                                                  'formats': formats,}, 
                            context_instance=RequestContext(request))

