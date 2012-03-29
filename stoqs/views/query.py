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
from utils.STOQSQManager import STOQSQManager
from utils import encoders


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
    Return a response that is a KML represenation of the existing MeasuredParameter query tat is in qm
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

    folderName = "%s_%.1f_%.1f" % (pName, qm.getDepth()[0], qm.getDepth()[1])
    descr = request.get_full_path().replace('&', '&amp;')
    logger.debug(descr)
    kml = KML.makeKML(dataHash, pName, folderName, descr, qm.getTime()[0], qm.getTime()[1])
    response['Content-Type'] = 'application/vnd.google-earth.kml+xml'
    response.write(kml)
    return response

def queryData(request, format=None):
    '''
    Process data requests from the main query web page.  Returns both summary Activity and actual MeasuredParameter data
    as retreived from STOQSQManager.
    '''
    response = HttpResponse()
    query_parms = {'parameters': 'parameters', # This should be specified once in the query string for each parameter.
                   'time': ('start_time','end_time'), # Single values
                   'depth': ('min_depth', 'max_depth'), # Single values
                   'platforms': 'platforms', # Specified once in the query string for each platform.
                   }
    params = {}
    for key, value in query_parms.iteritems():
        if type(value) in (list, tuple):
            params[key] = [request.GET.get(p, None) for p in value]
        else:
            params[key] = request.GET.getlist(key)
   
    # 'mappath' should be in the session from the call to queryUI() set it here in case it's not set by queryUI() 
    if request.session.has_key('mappath'):
        logger.info("Reusing request.session['mappath'] = %s", request.session['mappath'])
    else:
        request.session['mappath'] = NamedTemporaryFile(dir='/dev/shm', prefix=__name__, suffix='.map').name
        logger.info("Setting new request.session['mappath'] = %s", request.session['mappath'])

    qm = STOQSQManager(request, response, request.META['dbAlias'])
    qm.buildQuerySet(**params)
    
    av = ActivityView(request, [], qm.getMapfileDataStatement())
    av.generateActivityMapFile(template='stoqsquery.map')
    logger.info("av.mappath = %s", av.mappath)

    if not format: # here we export in a given format, or just provide summary data if no format is given.
        response['Content-Type'] = 'text/json'
        response.write(simplejson.dumps(qm.generateOptions(),
                                        cls=encoders.STOQSJSONEncoder))
                                        # use_decimal=True) # After json v2.1.0 this can be used instead of the custom encoder class.
    elif format == 'json':
        response['Content-Type'] = 'text/json'
        response.write(serializers.serialize('json', qm.qs))

    elif format == 'csv':
        logger.info('csv output')
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

    ##formats={'csv': 'Comma-Separated Values (CSV)',
    ##         'dap': 'OPeNDAP Format',
    ##         'kml': 'KML (Google Earth)'}
    formats={'kml': 'KML (Google Earth)'}
    return render_to_response('stoqsquery.html', {'site_uri': request.build_absolute_uri('/')[:-1],
                                                  'formats': formats,
                                                  'mapserver_host': settings.MAPSERVER_HOST,
                                                  'mappath': request.session['mappath'],
                                                 }, 
                            context_instance=RequestContext(request))

