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
    # Django's additional field lookups - applicable to all fields
    fieldLookups = ('exact', 'iexact', 'contains', 'icontains', 'in', 'gt', 'gte', 'lt', 'lte', 'startswith', 'istartswith',
                    'endswith', 'iendswith', 'range', 'year', 'month', 'day', 'week_day', 'isnull', 'search', 'regex', 'iregex')
    # GeoDjango's field lookups for geometry fields
    distanceLookups = ('distance_lt', 'distance_lte', 'distance_gt', 'distance_gte', 'dwithin') 

    spatialLookups = ('bbcontains', 'bboverlaps', 'contained', 'contains', 'contains_properly', 'coveredby', 'covers', 'crosses', 
                      'disjoint', 'distance_gt', 'distance_gte', 'distance_lt', 'distance_lte', 'dwithin', 'equals', 'exact', 
                      'intersects', 'overlaps', 'relate', 'same_as', 'touches', 'within', 'left', 'right', 'overlaps_left', 
                      'overlaps_right', 'overlaps_above', 'overlaps_below', 'strictly_above', 'strictly_below')
    fields = []
    geomFields = []

    def __init__(self, request, format, query_set, stoqs_object=None):
        self.request = request
        self.format = format
        self.query_set = query_set
        self.stoqs_object = stoqs_object
        self.stoqs_object_name = stoqs_object._meta.verbose_name.lower().replace(' ', '_')
        self.html_template = '%s_tmpl.html' % self.stoqs_object_name
        # This file must be writable by the server running this Django app, wherever tempfile puts it should work.
        # /tmp should occasionally be scrubbed of old tempfiles by a cron(1) job.
        self.html_tmpl_path = tempfile.NamedTemporaryFile(dir='/tmp', prefix=self.stoqs_object_name+'_', suffix='.html').name
        # May be overridden by classes that provide other responses, such as '.png' in an overridden process_request() method
        self.responses = ['.help', '.html', '.json', '.csv', '.tsv', '.xml', '.count']

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
        Default fields for model class retreived by introspection.  Override fields in subclasses to add other fields from joined tables.
        '''
        if self.fields:
            return self.fields
        else:
            fields = []
            for f in self.stoqs_object._meta.fields:
                fields.append(f.name)
            self.fields = fields
            return fields

    def getGeomFields(self):
        '''
        Return list of any Geometry Field Types in the class - useful for knowing if we can append distanceLookups and spatialLookups.
        '''
        geomTypes = ('GeometryField', 'PointField', 'LineStringField', 'PolygonField', 'MultiPointField', 'MultiLineStringField', 
                     'MultiPolygonField', 'GeometryCollectionField') 
        if self.geomFields:
            return self.geomFields
        else:
            geomFields = []
            for f in self.stoqs_object._meta.fields:
                if f.get_internal_type() in geomTypes:
                    geomFields.append(f.name)
                self.geomFields = geomFields
            return geomFields

    def ammendFields(self, fields):

        # Append Django field lookups to the field names, see: https://docs.djangoproject.com/en/dev/ref/models/querysets/#field-lookups
        # and https://docs.djangoproject.com/en/dev/ref/contrib/gis/db-api/ for the distance and spatial lookups
        ammendedFields = []
        ammendedFields.extend(fields)
        for addition in self.fieldLookups:
            for f in fields:
                ammendedFields.append('%s__%s' % (f, addition, ))

        for addition in self.distanceLookups:
            for f in self.geomFields:
                ammendedFields.append('%s__%s' % (f, addition, ))

        for addition in self.spatialLookups:
            for f in self.geomFields:
                ammendedFields.append('%s__%s' % (f, addition, ))

        return ammendedFields

    def applyQueryParams(self, fields):
        '''
        Apply any constraints specified in the query string with ammened Django field lookups
        '''
        qparams = {}    
        logger.debug(self.request.GET)
        for f in self.ammendFields(fields):
            ##logger.debug(f)
            if self.request.GET.getlist(f):
                qparams[f] = self.request.GET.getlist(f)[0]     # Get's just first element, will need to change for multiple params

        logger.debug(qparams)
        self.query_set = self.query_set.filter(**qparams)

    def assign_qs(self):
        '''
        Assign the processed query string 'qs' with query parameters and fields. May be overridden to restructure response as needed.
        '''
        fields = self.getFields()
        geomFields = self.getGeomFields()
        logger.debug(fields)
        self.applyQueryParams(self.ammendFields(fields))
        self.qs = self.query_set
        self.qs = self.qs.values(*fields)


    def process_request(self):
        '''
        Default request processing: Apply any query parameters and get fields for the values.  Respond with requested format.
        '''
        fields = self.getFields()
        geomFields = self.getGeomFields()
        self.assign_qs()

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
            for obj in self.qs:
                writer.writerow([obj[f] for f in fields])

            return response
        elif self.format == 'xml':
            return HttpResponse(serializers.serialize('xml', self.query_set), 'application/xml')

        elif self.format == 'json':
            return HttpResponse(simplejson.dumps(self.qs, cls=encoders.STOQSJSONEncoder), 'application/json')

        elif self.format == 'count':
            count = self.qs.count()
            logger.debug('count = %d', count)
            return HttpResponse('%d' % count, mimetype='text/plain')

        elif self.format == 'help':
            helpText = 'Fields: %s\n\nField Lookups: %s' % (self.fields, self.fieldLookups)
            if geomFields:
                helpText += '\n\nSpatial and distance Lookups that may be appended to: %s\n\n%s\n\n%s' % (geomFields, 
                            self.distanceLookups, self.spatialLookups)
            helpText += '\n\nResponses: %s' % (self.responses,)
            response = HttpResponse(helpText, mimetype="text/plain")
            return response

        else:
            self.build_html_template()
            response = render_to_response(self.html_tmpl_file, {'cols': fields, 'google_analytics_code': settings.GOOGLE_ANALYTICS_CODE },
                                          context_instance = RequestContext(self.request))
            fh = open(self.html_tmpl_path, 'w')
            for line in response:
                fh.write(line)
            fh.close()
            return render_to_response(self.html_tmpl_path, {'list': self.qs})


class SampleOutputer(BaseOutputer):
    '''
    Add Activity name and Instantpoint timevalue to the default fields
    '''
    fields = [  'uuid', 'depth', 'geom', 'name', 'sampletype__name', 'samplepurpose__name', 
                'volume', 'filterdiameter', 'filterporesize', 'laboratory', 'researcher',
                'instantpoint__timevalue', 'instantpoint__activity__name']

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

def showMeasurement(request, format = 'html'):
    stoqs_object = mod.Measurement
    query_set = stoqs_object.objects.all()

    o = BaseOutputer(request, format, query_set, stoqs_object)
    return o.process_request()

def showMeasuredParameter(request, format = 'html'):
    stoqs_object = mod.MeasuredParameter
    query_set = stoqs_object.objects.all()

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

def showSimpleDepthTime(request, format = 'html'):
    stoqs_object = mod.SimpleDepthTime
    query_set = stoqs_object.objects.all()

    o = BaseOutputer(request, format, query_set, stoqs_object)
    return o.process_request()

