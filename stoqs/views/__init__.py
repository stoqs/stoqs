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

    def process_request(self):
        logger.debug("format = %s", self.format)
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

class SampleOutputer(BaseOutputer):
    '''
    Do special things for Sample responses, such as add Activity name and expand the Instantpoit timevalue.
    '''

    def process_request(self):
        logger.debug("format = %s", self.format)
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

        return super(SampleOutputer, self).process_request


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

def showSample(request, format = 'html'):
    stoqs_object = mod.Sample
    query_set = stoqs_object.objects.all().order_by('instantpoint__timevalue')

    s = SampleOutputer(request, format, query_set, stoqs_object)
    return s.process_request()

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

