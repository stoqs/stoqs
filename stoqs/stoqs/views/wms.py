__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Support Classes and methods for mapserver mapfile generation for stoqs views.


@undocumented: __doc__ parser
@status: production
@license: GPL
'''

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.conf import settings 
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse
from django.conf import settings
from django.db import connection
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
import pprint
from tempfile import NamedTemporaryFile
from utils.utils import addAttributeToListItems

logger = logging.getLogger(__name__)
    
class Color(object):
    '''Simple color class to add to add as an attribute to items.  Initialize a nice grey color.
    '''
    r = 128
    g = 128
    b = 128

    def __str__(self):
        return "%i %i %i" % (self.r, self.g, self.b,)

class ActivityView(object):

    olWebPageTemplate = 'activitiesWMS.html'
    
    # For using the same colors
    itemColor_dict = {}

    def __init__(self, request, itemList, trajectory_union_layer_string, station_union_layer_string, url=olWebPageTemplate):
        '''Initialize activity object to support building of mapserver mapfiles and openlayers html files.

        @param request: Web server request object
        @param itemList: List objects with attributes that are used to add layers to the mapserver map, attributes include
                         for example:
                            item.id = 'sample_points'
                            item.name = 'sample_points'
                            item.color = '255 255 255'
                            item.type = 'point'
                            item.geo_query = qm.getSampleGeoQuery()
                            item.extra_style = 'SYMBOL "circle"\n        SIZE 7.0\n        OUTLINECOLOR 0 0 0 '

        @param trajectory_union_layer_string: A comma separated list of trajectory layer names that are grouped together by openlayers
        @param station_union_layer_string: A comma separated list of station layer names that are grouped together by openlayers
        @param geo_query: The SQL to be placed in the DATA directive.  It must return a geometry object and a gid for the filter.
        '''
        self.url = url
        self.request = request
        self.itemList = itemList 
        self.trajectory_union_layer_string = trajectory_union_layer_string
        self.station_union_layer_string = station_union_layer_string
        self.mappath = self.request.session['mappath']
    
        if settings.LOGGING['loggers']['stoqs']['level'] == 'DEBUG':
            self.map_debug_level = 5             # Mapserver debug level: [off|on|0|1|2|3|4|5]
            self.layer_debug_level = 2           # Mapserver debug level: [off|on|0|1|2|3|4|5]
        else:
            self.map_debug_level = 0 
            self.layer_debug_level = 0
            


    def generateActivityMapFile(self, template = 'activity.map'):
        '''Build mapfile for activity from template.  Write it to a location that mapserver can see it.
            The mapfile performs direct SQL queries, so we must pass all of the connection parameters for the dbAlias. 
        '''
        filename, ext = os.path.splitext(template)
        if self.request.session.has_key('mappath'):
            logger.info("Reusing request.session['mappath'] = %s", self.request.session['mappath'])
        else:
            self.request.session['mappath'] =  tempfile.NamedTemporaryFile(dir=settings.MAPFILE_DIR, prefix=filename + '_' , suffix=ext).name
            logger.info("Setting new request.session['mappath'] = %s", request.session['mappath'])

        # mapserver_host: Hostname where 'http://<mapserver_host>/cgi-bin/mapserv?file=<mappath>' works
        # With Apache RewriteBase rule this pattern also works for cleaner URLs:
        # Allow WMS requests to any file in /dev/shm by providing a URL like /wms/ADFASDFASDF (where /dev/shm/ADFASDFASDF.map is the name of the mapfile)
        # this means that the "?map=" need not be provided as part of the URL
        # <Location /wms>
        #    Options Indexes FollowSymLinks
        #    RewriteEngine On
        #    RewriteBase '/wms/'
        #    RewriteRule .*/(.*) /cgi-bin/mapserv?map=/dev/shm/$1.map [QSA]
        # </location>

        ##logger.debug(pprint.pformat(settings.DATABASES[self.request.META['dbAlias']]))
        response = render_to_response(template, {'mapserver_host': settings.MAPSERVER_HOST,
                            'list': self.itemList,
                            'trajectory_union_layer_string': self.trajectory_union_layer_string,
                            'station_union_layer_string': self.station_union_layer_string,
                            'wfs_title': 'WFS title for an Activity',
                            'map_debug_level': self.map_debug_level,
                            'layer_debug_level': self.layer_debug_level,
                            'copyright_string': 'MBARI %d' % datetime.today().year,
                            'dbconn': settings.DATABASES[self.request.META['dbAlias']],
                            'mappath': self.mappath,
                            'imagepath': settings.MAPFILE_DIR,
                            'STATIC_ROOT': settings.STATIC_ROOT},
                            context_instance = RequestContext(self.request))

        try:
            fh = open(self.mappath, 'w')    
        except IOError:
            # In case of accessed denied error, create a new mappath and store it in the session, and open that
            self.request.session['mappath'] = NamedTemporaryFile(dir=settings.MAPFILE_DIR, prefix=__name__, suffix='.map').name
            self.mappath = self.request.session['mappath']
            fh = open(self.mappath, 'w')
                
        for line in response:
            ##logger.debug(line)
            fh.write(line) 

    def getColorOfItem(self, item):
        '''Return color given name of item.  Returns value saved in class dictionary otherwise create new random color, save, and return it. 
        Check to see it item (could be Activity, Parameter, Platform, ...)
        '''
            
        if not self.itemColor_dict.has_key(item.id):
            logger.debug("Creating a random color for item with id = %d", item.id)
            c = Color()
            c.r = randint(100, 255)
            c.g = randint(100, 255)
            c.b = randint(50, 150)
            self.itemColor_dict[item.id] = c
        else:
            logger.debug("Returing saved color for item with id = %d", item.id)


        return self.itemColor_dict[item.id]

    def assignColors(self, list):
        '''For each item in list create a unique rgb color and add it as an attribute to the list'''

        newList = []
        for item in list:
            # If item has a color attribute, use it; otherwise get a color (perhaps already saved in a hash) and add it to the item
            try:
                getattr(item, 'color')
                logger.debug("Item.id %d has a color, it is = %s", item.id, item.color)
            except AttributeError:
                c = self.getColorOfItem(item)
                setattr(item, 'color', c)
                logger.debug("Item.id %d did not have a color, it now has item.color = %s", item.id, item.color)

            newList.append(item)

        self.list = newList

    def process_request(self, webPageTemplate='activitiesWMS.html', mapfile='activity.map'):
        '''Build mapfile and return corresponding OpenLayers-powered web page
        '''

        self.assignColors(self.itemList)
        self.generateActivityMapFile(mapfile)

        logger.debug("Building web page from pointing to mapserver at %s", settings.MAPSERVER_HOST)
    
        return render_to_response(webPageTemplate, {'mapserver_host': settings.MAPSERVER_HOST, 
                                    'list': self.itemList,
                                    'dbAlias': self.request.META['dbAlias'],
                                    'mappath': self.mappath},
                            context_instance=RequestContext(self.request))


def showActivityWMS(request):
    '''
    Fuller featured Activities view using bootstrap and ajax features of querystoqs.html.
    Displays Resources of activity along with tracks on the map and perhaps a get data button.
    Could be a useful results page from a search of the database.
    '''
    logger.debug("inside showActivityWMS")

    # This list could result from a collection of Q objects constructed similar to what STOQSQManager does
    qs = mod.Activity.objects.all().order_by('startdate')  
    geo_query = '''geom from (select a.maptrack as geom, a.id as gid, 
        a.name as name, a.comment as comment, a.startdate as startdate, a.enddate as enddate
        from stoqs_activity a)
        as subquery using unique gid using srid=4326'''
    av = ActivityView(request, list, geo_query)
    platform_string = ''
    for p in qs:
        platform_string += p.name + ','
    platform_string = platform_string[:-1]
   
    av = ActivityView(request, addAttributeToListItems(qs, 'geo_query', geo_query), platform_string)
    return av.process_request(webPageTemplate = 'activityWMS.html')


def showActivitiesWMS(request):
    '''Render Activities as WMS via mapserver'''

    list = mod.Activity.objects.all().order_by('startdate')  
    geo_query = '''geom from (select a.maptrack as geom, a.id as gid, 
        a.name as name, a.comment as comment, a.startdate as startdate, a.enddate as enddate
        from stoqs_activity a)
        as subquery using unique gid using srid=4326'''

    av = ActivityView(request, addAttributeToListItems(list, 'geo_query', geo_query),'')
    return av.process_request(webPageTemplate = 'activitiesWMS.html')


def showActivitiesWMSAnimate(request):
    '''Render Activities as WMS via mapserver'''

    list = mod.Activity.objects.all().order_by('startdate')  

    for a in list:
       a.isostartdate = a.startdate.strftime('%Y-%m-%dT%H:%M:%S')
       a.isoenddate = a.enddate.strftime('%Y-%m-%dT%H:%M:%S')

    geo_query = '''geom from (select m.geom as geom, ip.id as gid, ip.timevalue as timevalue 
                from stoqs_instantpoint ip
                inner join stoqs_measurement m on (m.instantpoint_id = ip.id) order by ip.timevalue )
                as subquery using unique gid using srid=4326'''                

    av = ActivityView(request, addAttributeToListItems(list, 'geo_query', geo_query), '', 'activitiesWMSAnimate.html')
    return av.process_request(webPageTemplate='activitiesWMSAnimate.html', mapfile='activitypoint.map')

def showActivitiesWMSAnimateCoastwatch(request):
    return render_to_response('testAnimateCoastwatch.html',
                    {'mapserver_host': settings.MAPSERVER_HOST,
                    },context_instance=RequestContext(request))


def showParametersWMS(request):
    '''Render Activities that have specified parameter as WMS via mapserver'''

    list = mod.Parameter.objects.all().order_by('name')  
    geo_query = '''geom from (select a.maptrack as geom, a.id as aid, p.id as gid,
        a.name as name, a.comment as comment, a.startdate as startdate, a.enddate as enddate
        from stoqs_activity a
        inner join stoqs_activityparameter ap on (a.id = ap.activity_id)
        inner join stoqs_parameter p on (ap.parameter_id = p.id)
        order by p.name)
        as subquery using unique gid using srid=4326'''

    av = ActivityView(request, list, geo_query)
    return av.process_request()


def showPlatformsWMS(request):
    '''Render Activities that have specified platform as WMS via mapserver'''

    list = mod.Platform.objects.all().order_by('name')  
    geo_query = '''geom from (select a.maptrack as geom, a.id as aid, p.id as gid,
        a.name as name, a.comment as comment, a.startdate as startdate, a.enddate as enddate
        from stoqs_activity a
        inner join stoqs_platform p on (a.platform_id = p.id)
        order by p.name)
        as subquery using unique gid using srid=4326'''

    av = ActivityView(request, list, geo_query)
    return av.process_request()

