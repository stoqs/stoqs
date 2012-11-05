__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

View functions to supoprt the main query web page

@undocumented: __doc__ parser
@status: production
@license: GPL
'''

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse
from django.utils import simplejson
from django.conf import settings
from django.core import serializers
from django.db.models import Q
from utils.STOQSQManager import STOQSQManager
from utils import encoders
import json
import pprint
import csv


import logging 
import KML
from wms import ActivityView
from tempfile import NamedTemporaryFile

logger = logging.getLogger(__name__)

class InvalidMeasuredParameterQueryException(Exception):
    pass

class NoParameterSelectedException(Exception):
    pass

def kmlResponse(request, qm, response):
    '''
    Return a response that is a KML represenation of the existing MeasuredParameter query that is in qm
    '''
    qs_mp = qm.getMeasuredParametersQS()
    if qs_mp is None:
        raise InvalidMeasuredParameterQueryException

    try:
        pName = qm.getParameters()[0][0]
        logger.info("pName = %s", pName)
    except IndexError:
        raise NoParameterSelectedException

    data = [(mp.measurement.instantpoint.timevalue, mp.measurement.geom.x, mp.measurement.geom.y,
                 mp.measurement.depth, pName, mp.datavalue, mp.measurement.instantpoint.activity.platform.name)
                 for mp in qs_mp]
    dataHash = {}
    for d in data:
        try:
            dataHash[d[6]].append(d)
        except KeyError:
            dataHash[d[6]] = []
            dataHash[d[6]].append(d)

    folderName = "%s_%.1f_%.1f" % (pName, float(qm.getDepth()[0]), float(qm.getDepth()[1]))
    descr = request.get_full_path().replace('&', '&amp;')
    logger.debug(descr)
    kml = KML.makeKML(  request.META['dbAlias'], dataHash, pName, folderName, descr, qm.getTime()[0], qm.getTime()[1], 
                        request.GET.get('cmin', None), request.GET.get('cmax', None))
    response['Content-Type'] = 'application/vnd.google-earth.kml+xml'
    response.write(kml)
    return response

def csvResponse(request, qm, response):
    '''
    Return a response that is a Comma Separated Value represenation of the existing MeasuredParameter query that is in qm
    '''
    qs_mp = qm.getMeasuredParametersQS()
    if qs_mp is None:
        raise InvalidMeasuredParameterQueryException

    try:
        pName = qm.getParameters()[0][0]
        logger.info("pName = %s", pName)
    except IndexError:
        raise NoParameterSelectedException

    fields = ['platformName', 'time', 'longitude', 'latitude', 'depth', pName, 'units']

     
    data = [
            (   
                mp.measurement.instantpoint.activity.platform.name, 
                mp.measurement.instantpoint.timevalue, mp.measurement.geom.x, mp.measurement.geom.y,
                mp.measurement.depth, mp.datavalue, mp.parameter.units
            )
                 for mp in qs_mp]

    response = HttpResponse()
    response['Content-type'] = 'text/csv'
    response['Content-Disposition'] = 'attachment; filename=%s.csv' % pName

    writer = csv.writer(response)
    writer.writerow(fields)
    for d in data:
        writer.writerow(d)
    return response

    
def buildMapFile(request, qm, options):
    # 'mappath' should be in the session from the call to queryUI() set it here in case it's not set by queryUI() 
    if request.session.has_key('mappath'):
        logger.info("Reusing request.session['mappath'] = %s", request.session['mappath'])
    else:
        request.session['mappath'] = NamedTemporaryFile(dir='/dev/shm', prefix=__name__, suffix='.map').name
        logger.info("Setting new request.session['mappath'] = %s", request.session['mappath'])

    # A rudumentary class of items for passing a list of them to the activity.map template
    class Item(object):
        def __repr__(self):
            return '%s %s %s %s' % (self.id, self.name, self.color, self.geo_query,)

    # Add an item (a mapfile layer) for each platform - unioned up
    item_list = []      # Replicates queryset from an Activity query (needs name & id) with added geo_query & color attrbutes
    union_layer_string = ''
    for p in json.loads(options)['platforms']:
        item = Item()
        item.id = p[1]
        item.name = p[0]
        union_layer_string += str(item.name) + ','
        item.color = '"#%s"' % p[2]
        item.type = 'line'
        item.geo_query = qm.getActivityGeoQuery(Q(platform__name='%s' % p[0]))
        item.extra_style = ''
        item_list.append(item)

    # Add an item for the samples for the existing query - do not add it to the union, it's a different type
    item = Item()
    item.id = 'sample_points'
    item.name = 'sample_points'
    item.color = '255 255 255'
    item.type = 'point'
    item.geo_query = qm.getSampleGeoQuery()
    item.extra_style = 'SYMBOL "circle"\n        SIZE 7.0\n        OUTLINECOLOR 0 0 0 '
    item_list.append(item)
    
    union_layer_string = union_layer_string[:-1]

    ##logger.debug('item_list = %s', pprint.pformat(item_list))        
    logger.debug('union_layer_string = %s', union_layer_string)
    av = ActivityView(request, item_list, union_layer_string)
    av.generateActivityMapFile()

def queryData(request, format=None):
    '''
    Process data requests from the main query web page.  Returns both summary Activity and actual MeasuredParameter data
    as retreived from STOQSQManager.
    '''
    response = HttpResponse()
    query_parms = {'parameters': 'parameters',              # For queryUI, contains list of (name, standard_name) tuples
                   'parametername': 'parametername',        # For data queries
                   'parameterstandardname': 'parameterstandardname',        # For data queries
                   'parameterminmax': 'parameterminmax',    # Array of name, min, max
                   'time': ('start_time','end_time'),       # Single values
                   'depth': ('min_depth', 'max_depth'),     # Single values
                   'simpledepthtime': [],                   # List of x,y values
                   'platforms': 'platforms',                # Specified once in the query string for each platform.
                   'get_actual_count': 'get_actual_count',  # Flag value from checkbox
                   'show_all_parameter_values': 'show_all_parameter_values',  # Flag value from checkbox
                   }
    params = {}
    for key, value in query_parms.iteritems():
        if type(value) in (list, tuple):
            params[key] = [request.GET.get(p, None) for p in value]
        else:
            params[key] = request.GET.getlist(key)
   
    qm = STOQSQManager(request, response, request.META['dbAlias'])
    qm.buildQuerySet(**params)
    options = simplejson.dumps(qm.generateOptions(),
                               cls=encoders.STOQSJSONEncoder)
                               # use_decimal=True) # After json v2.1.0 this can be used instead of the custom encoder class.
    ##logger.debug('options = %s', pprint.pformat(options))
    ##logger.debug('len(simpledepthtime) = %d', len(json.loads(options)['simpledepthtime']))
    buildMapFile(request, qm, options)

    if not format: # here we export in a given format, or just provide summary data if no format is given.
        response['Content-Type'] = 'text/json'
        response.write(options)
    elif format == 'json':
        response['Content-Type'] = 'text/json'
        response.write(serializers.serialize('json', qm.qs))
    elif format == 'csv-simple':
        logger.info('csv output')
        return csvResponse(request, qm, response)
    elif format == 'dap':
        logger.info('dap output')
    elif format == 'kml':
        return kmlResponse(request, qm, response)

    return response
    
def queryUI(request):
    '''
    Build and return main query web page
    '''

    ##request.session.flush()
    if request.session.has_key('mappath'):
        logger.info("Reusing request.session['mappath'] = %s", request.session['mappath'])
    else:
        request.session['mappath'] = NamedTemporaryFile(dir='/dev/shm', prefix=__name__, suffix='.map').name
        logger.info("Setting new request.session['mappath'] = %s", request.session['mappath'])

    # Use list of tuples to preserve order
    formats=[('kml', 'Keyhole Markup Language - click on icon to view in Google Earth', ),
             ('sql', 'Structured Query Language for PostGIS', ),
             ('stoqstoolbox', 'stoqstoolbox - work with the data in Matlab', ),
             ('json', 'JavaScript Object Notation', ),
             ('csv', 'Comma Separated Values', ),
             ('tsv', 'Tabbed Separated Values', ),
             ('html', 'Hyper Text Markup Language table', ),
             ('csv-simple', 'Comma Separated Values - simplified header', ),
            ]
    logger.debug(formats)
    return render_to_response('stoqsquery.html', {'site_uri': request.build_absolute_uri('/')[:-1],
                                                  'formats': formats,
                                                  'mapserver_host': settings.MAPSERVER_HOST,
                                                  'mappath': request.session['mappath'],
                                                  'google_analytics_code': settings.GOOGLE_ANALYTICS_CODE,
                                                 }, 
                            context_instance=RequestContext(request))

def queryActivityResource(request):
    '''
    Build and return main Activity Resource web page
    '''

    formats={'kml': 'KML (Google Earth)'}
    return render_to_response('stoqsquery.html', {'site_uri': request.build_absolute_uri('/')[:-1],
                                                  'formats': formats,
                                                  'mapserver_host': settings.MAPSERVER_HOST,
                                                  'mappath': request.session['mappath'],
                                                 }, 
                            context_instance=RequestContext(request))

