'''
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
from django.http import HttpResponse, Http404
from django.conf import settings
from django.core import serializers

import json
import stoqs.models as mod
import csv
import logging 
import tempfile
from utils.utils import postgresifySQL
from utils.MPQuery import MPQuery, MPQuerySet
from utils.PQuery import PQuery
from utils import encoders
from utils.Viz.KML import KML

logger = logging.getLogger(__name__)


class EmptyQuerySetException(Exception):
    pass


class BaseOutputer(object):
    '''
    Base methods for supported responses for all STOQS objects: csv, json, kml, html, etc.
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

    def __init__(self, request, fmt, query_set, stoqs_object=None):
        '''
        @query_set is the Query Set without any values assigned, qs is the Query set with values assigned.
        '''
        self.request = request
        self.format = fmt
        self.query_set = query_set.using(self.request.META['dbAlias'])
        self.stoqs_object = stoqs_object
        self.stoqs_object_name = stoqs_object._meta.verbose_name.lower().replace(' ', '_')
        self.html_template = '%s_tmpl.html' % self.stoqs_object_name

        # This file must be writable by the server running this Django app, wherever tempfile puts it should work.
        # /tmp should occasionally be scrubbed of old tempfiles by a cron(1) job.
        self.html_tmpl_path = tempfile.NamedTemporaryFile(dir='/tmp', prefix=self.stoqs_object_name+'_', suffix='.html').name

        # May be overridden by classes that provide other responses, such as '.png' in an overridden process_request() method
        self.responses = ['.help', '.html', '.json', '.csv', '.tsv', '.xml', '.count']

    def build_html_template(self):
        '''
        Build template for stoqs_object using generic html template with a column for each attribute
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

    def parameterValueConstraints(self):
        '''
        Look for any parameter _MIN & _MAX input from the Query String.   Return a dictionary of (min, max) tuples
        keyed by parameter name.  Unlike pvConstraints in the QueryUI, here we allow unbounded constraints; 
        either pmin or pmax may be None.
        '''
        pmin = {}
        pmax = {}
        for key, _ in self.request.GET.iteritems():
            if key.endswith('_MIN'):        
                name = key.split('_MIN')[0]
                try:
                    pmin[name] = self.request.GET.getlist(name + '_MIN')[0]
                except Exception:
                    logger.exception('Could not get min parameter value even though ' + key + ' ends with _MIN')
            if key.endswith('_MAX'):        
                name = key.split('_MAX')[0]
                try:
                    pmax[name] = self.request.GET.getlist(name + '_MAX')[0]
                except Exception:
                    logger.exception('Could not get max parameter value even though ' + key + ' ends with _MAX')

        pvDicts = []
        for name in set(pmin.keys() + pmax.keys()):         # set() uniquifies the keys from each dictionary
            if name in mod.Parameter.objects.using(self.request.META['dbAlias']).values_list('name', flat=True):
                try:
                    pn = pmin[name]
                except KeyError:
                    pn = None
                try:
                    px = pmax[name]
                except KeyError:
                    px = None
                pvDicts.append({name: (pn, px)})

        logger.debug('parametervalues =  %s', pvDicts)

        return pvDicts

    def applyQueryParams(self, fields):
        '''
        Apply any constraints specified in the query string with ammened Django field lookups
        '''
        qparams = {}    
        logger.debug(self.request.GET)
        for f in self.ammendFields(fields):
            ##logger.debug(f)
            if self.request.GET.getlist(f):
                ##logger.debug('len(self.request.GET.getlist(f)) = %d', len(self.request.GET.getlist(f)))
                if len(self.request.GET.getlist(f)) == 1:
                    qparams[f] = self.request.GET.getlist(f)[0]
                else:
                    qparams[f + '__in'] = self.request.GET.getlist(f)

        if self.request.GET.get('mplabels', []):
            # Special addition for labeled data constraint
            qparams['measurement__id__in'] = mod.MeasuredParameterResource.objects.filter(resource__id__in=[self.request.GET.get('mplabels')]
                                                                                ).values_list('measuredparameter__measurement__id', flat=True)

        self.qparams = qparams
        logger.debug(qparams)
        self.query_set = self.query_set.filter(**qparams)

    def assign_qs(self):
        '''
        Assign the processed query string 'qs' with query parameters and fields. May be overridden to restructure response as needed.
        Creates self.qs which is self.query_string with values added.
        '''
        fields = self.getFields()
        logger.debug(fields)
        self.applyQueryParams(fields)
        self.qs = self.query_set
        self.qs = self.qs.values(*fields)


    def process_request(self):
        '''
        Default request processing: Apply any query parameters and get fields for the values.  Respond with requested format.
        '''
        fields = self.getFields()
        geomFields = self.getGeomFields()
        try:
            self.assign_qs()
        except EmptyQuerySetException:
            raise Http404

        if self.stoqs_object_name == 'measured_parameter':
            # Check if the query contains parametervalue constraints, in which case we need to wrap RawQuerySet in an MPQuerySet
            pvConstraints = self.parameterValueConstraints()
            if pvConstraints:
                pq = PQuery(self.request)
                sql = postgresifySQL(str(self.qs.query))
                sql = pq.addParameterValuesSelfJoins(sql, pvConstraints, select_items=MPQuery.rest_select_items)
                self.qs = MPQuerySet(self.request.META['dbAlias'], sql, MPQuerySet.rest_columns)
            else:
                self.qs = MPQuerySet(self.request.META['dbAlias'], None, MPQuerySet.rest_columns, qs_mp=self.qs)

        # Process request based on format requested
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
            return HttpResponse(json.dumps(self.qs, cls=encoders.STOQSJSONEncoder), 'application/json')

        elif self.format == 'kml':
            kml = KML(self.request, self.qs, self.qparams, self.stoqs_object_name)
            return kml.kmlResponse()

        elif self.format == 'kmln':
            kml = KML(self.request, self.qs, self.qparams, self.stoqs_object_name, withTimeStamps=False, withLineStrings=False, withFullIconURL=False)
            return kml.kmlResponse()

        elif self.format == 'count':
            count = self.qs.count()
            logger.debug('count = %d', count)
            return HttpResponse('%d' % count, content_type='text/plain')

        elif self.format == 'help':
            helpText = 'Fields: %s\n\nField Lookups: %s' % (fields, self.fieldLookups)
            if geomFields:
                helpText += '\n\nSpatial and distance Lookups that may be appended to: %s\n\n%s\n\n%s' % (geomFields, 
                            self.distanceLookups, self.spatialLookups)
            helpText += '\n\nResponses: %s' % (self.responses,)
            response = HttpResponse(helpText, content_type="text/plain")
            return response

        else:
            self.build_html_template()
            try:
                response = render_to_response(self.html_tmpl_file, {'cols': fields, 
                                                'google_analytics_code': settings.GOOGLE_ANALYTICS_CODE },
                                                context_instance = RequestContext(self.request))
            except AttributeError:
                response = render_to_response(self.html_tmpl_file, {'cols': fields}, 
                                                context_instance = RequestContext(self.request))
            fh = open(self.html_tmpl_path, 'w')
            for line in response:
                fh.write(line)
            fh.close()
            return render_to_response(self.html_tmpl_path, {'list': self.qs})


def showSample(request, fmt='html'):
    stoqs_object = mod.Sample
    query_set = stoqs_object.objects.all().order_by('instantpoint__timevalue')

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    o.fields = ['instantpoint__activity__name', 'name', 'instantpoint__timevalue', 'depth', 'geom', 
                'sampledparameter__parameter__name', 'sampledparameter__datavalue',
                'sampletype__name', 'samplepurpose__name',
                'volume', 'filterdiameter', 'filterporesize', 'laboratory', 'researcher']
    return o.process_request()

def showInstantPoint(request, fmt='html'):
    stoqs_object = mod.InstantPoint
    query_set = stoqs_object.objects.all().order_by('timevalue')

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    return o.process_request()

def showMeasurement(request, fmt='html'):
    stoqs_object = mod.Measurement
    query_set = stoqs_object.objects.all()

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    return o.process_request()

def showMeasuredParameter(request, fmt='html'):
    stoqs_object = mod.MeasuredParameter
    query_set = stoqs_object.objects.all()

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    return o.process_request()

def showPlatform(request, fmt='html'):
    stoqs_object = mod.Platform
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    return o.process_request()

def showPlatformType(request, fmt='html'):
    stoqs_object = mod.PlatformType
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    return o.process_request()

def showParameterGroupParameter(request, fmt='html'):
    stoqs_object = mod.ParameterGroupParameter
    query_set = stoqs_object.objects.all().order_by('parametergroup', 'parameter')

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    o.fields = ['id', 'uuid', 'parametergroup_id', 'parameter_id', 'parametergroup__name', 'parameter__name']
    return o.process_request()

def showParameterGroup(request, fmt='html'):
    stoqs_object = mod.ParameterGroup
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    return o.process_request()

def showParameterResource(request, fmt='html'):
    stoqs_object = mod.ParameterResource
    query_set = stoqs_object.objects.all()

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    o.fields = ['id', 'uuid', 'parameter_id', 'resource_id', 'parameter__name', 'resource__name', 'resource__value']
    return o.process_request()

def showMeasuredParameterResource(request, fmt='html'):
    stoqs_object = mod.MeasuredParameterResource
    query_set = stoqs_object.objects.all()

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    o.fields = ['id', 'measuredparameter__id', 'resource_id', 'measuredparameter__parameter__name', 
                'measuredparameter__datavalue', 'resource__name', 'resource__value', 'resource__resourcetype__name']
    return o.process_request()

def showResourceResource(request, fmt='html'):
    stoqs_object = mod.ResourceResource
    query_set = stoqs_object.objects.all()

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    o.fields = ['id', 'fromresource__id', 'fromresource__name', 'fromresource__value', 'fromresource__resourcetype__name', 
                'toresource__id', 'toresource__name', 'toresource__value', 'toresource__resourcetype__name']
    return o.process_request()

def showPlatformResource(request, fmt='html'):
    stoqs_object = mod.PlatformResource
    query_set = stoqs_object.objects.all()

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    o.fields = ['id', 'uuid', 'platform_id', 'resource_id', 'platform__name', 'resource__name', 
            'resource__value', 'resource__uristring', 'resource__resourcetype__name']
    return o.process_request()

def showParameter(request, fmt='html'):
    stoqs_object = mod.Parameter
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    return o.process_request()

def showSampleType(request, fmt='html'):
    stoqs_object = mod.SampleType
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    return o.process_request()

def showSamplePurpose(request, fmt='html'):
    stoqs_object = mod.SamplePurpose
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    return o.process_request()

def showAnalysisMethod(request, fmt='html'):
    stoqs_object = mod.AnalysisMethod
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    return o.process_request()

def showActivity(request, fmt='html'):
    stoqs_object = mod.Activity
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    return o.process_request()

def showActivityType(request, fmt='html'):
    stoqs_object = mod.ActivityType
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    return o.process_request()

def showCampaign(request, fmt='html'):
    stoqs_object = mod.Campaign
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    return o.process_request()

def showCampaignResource(request, fmt='html'):
    stoqs_object = mod.CampaignResource
    query_set = stoqs_object.objects.all().order_by('resource__name')

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    o.fields = ['id', 'uuid', 'campaign__name', 'resource__name', 'resource__value', 'resource__uristring']
    return o.process_request()

def showResource(request, fmt='html'):
    stoqs_object = mod.Resource
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    o.fields = ['id', 'name', 'value', 'uristring', 'resourcetype__name', 'resourcetype__description']
    return o.process_request()

def showResourceType(request, fmt='html'):
    stoqs_object = mod.ResourceType
    query_set = stoqs_object.objects.all().order_by('name')

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    return o.process_request()

def showActivityResource(request, fmt='html'):
    stoqs_object = mod.ActivityResource
    query_set = stoqs_object.objects.all()

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    o.fields = ['id', 'uuid', 'activity__name', 'resource__name', 'resource__value', 'resource__uristring']
    return o.process_request()

def showActivityParameter(request, fmt='html'):
    stoqs_object = mod.ActivityParameter
    query_set = stoqs_object.objects.all()

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    o.fields = ['id', 'activity__name', 'parameter__name', 'number', 'min', 'max', 'mean', 
                'median', 'mode', 'p025', 'p975', 'p010', 'p990']
    return o.process_request()

def showSimpleDepthTime(request, fmt='html'):
    stoqs_object = mod.SimpleDepthTime
    query_set = stoqs_object.objects.all()

    o = BaseOutputer(request, fmt, query_set, stoqs_object)
    o.fields = ['id', 'activity__name', 'nominallocation', 'instantpoint__timevalue', 'epochmilliseconds', 'depth']
    return o.process_request()

