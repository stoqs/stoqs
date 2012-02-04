#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__credits__ = ["Chander Ganesan, Open Technology Group"]
__license__ = "GPL"
__version__ = "$Revision: 12294 $".split()[1]
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

View functions that are related to managing the stoqs databases.

Mike McCann
MBARI Jan 9, 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.conf import settings
from django.db import DatabaseError
import stoqs.models as mod
from stoqs import tasks
import socket
import logging
import sys

# Set up logging
log_level = logging.INFO
logger = logging.getLogger('STOQS_views_management')
logger.setLevel(log_level)
handler = logging.StreamHandler(sys.stderr)
handler.setLevel(log_level)
formatter = logging.Formatter('%(levelname)s %(name)s %(asctime)s %(lineno)d: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def deleteActivity(request, activityId):
    '''Do a cascade delete of an activity given the `activityId`.  This will delete everything that has a foreign
    key pointing to the activity which will result in removal of all the measurements and measured_parameters
    associated with the activity.
    '''
    
    tasks.delete_activity.delay(request.META['dbName'], activityId)
    return render_to_response('deletion.html', {'dbName': request.META['dbName'], 'activityId': activityId})
    
    
class Act():
    '''A tiny class to hold all the information for an Activity that includes perhaps additional data from other
    parts of the model. The types are simple things (characters and numbers) that can appear in a web page.
    '''

    m_query = ''
    mp_query = ''
    id = 0
    campaign = ''
    platform = ''
    activitytype = ''
    name = ''
    comment = ''
    platformName = ''
    startdate = None
    enddate = None

    mCount = 0
    mpCount = 0
    parameters = ''
    links = ''


def showDatabase(request):
    '''Present summary view of the database. Show list of Activities, number of measured_paramaters, parameter names, platforms, etc.
    Offer ability to delete Activities.
    '''

    aList = mod.Activity.objects.all().order_by('startdate')
    
    actList = []
    for a in aList:
        qs_m = mod.Measurement.objects.filter(instantpoint__activity__id = a.id)
        qs_mp = mod.MeasuredParameter.objects.filter(measurement__instantpoint__activity__id = a.id)
        act = Act()
        if a.campaign:
            act.campaignName = a.campaign.name
        if a.platform:
            act.platformName = a.platform.name
        if a.activitytype:
            act.activityTypeName = a.activitytype.name

        act.m_query = str(qs_m.query)
        act.mp_query = str(qs_mp.query)
        act.id = a.id
        act.name = a.name
        act.comment = a.comment
        act.startdate = a.startdate
        act.isostartdate = a.startdate.strftime('%Y%m%dT%H%M%S')
        if a.enddate:
            act.enddate = a.enddate
            act.isoenddate = a.enddate.strftime('%Y%m%dT%H%M%S')

        act.mCount = qs_m.count()
        act.mpCount = qs_mp.count()
        act.parameters = ''
        actList.append(act)

    pList = mod.Parameter.objects.all().order_by('name')    

    return render_to_response('management.html', 
                {'dbName': request.META['dbName'], 
                 'actList': actList,
                 'pList': pList,
                 }
                ) 
    
    # End showDatabase()


def showCampaigns(request):
    '''Present list of Campaigns from scanning the DATABASES dictionary from settings.
    '''

    dbAliases = settings.DATABASES.keys()
    logger.debug("DATABASES")
    logger.debug(settings.DATABASES)
    logger.debug("DATABASES.keys()")
    logger.debug(settings.DATABASES.keys())
  
    # Data structure hash of lists.  Possible to have multiple campaigns in a database
    cHash = {}
    for dbName in settings.DATABASES.keys():
        # Initialize Campaign hassh list
        cHash[dbName] = []

    for dbName in settings.DATABASES.keys():
        try:
            logger.debug("Getting Campaign from dbName = %s", dbName)
            cqs = mod.Campaign.objects.using(dbName).all()
            for c in cqs:
                logger.debug("Appending campaign name = %s to cHash with key (dbName) = %s", c.name, dbName)
                cHash[dbName].append(c)
        except mod.Campaign.DoesNotExist:
            logger.warn("Database %s does not exist", dbName)
            continue
        except DatabaseError:
            # Will happen if database defined in privateSettings does not exist yet
            logger.warn("Database %s returns django.db.DatabaseError", dbName)
            continue

    # Preprocess hash for template (basically, flatten it)
    cList = []
    class Cam(object):
        pass
    for k in cHash.keys():
        for c in cHash[k]:
	    cam = Cam()
            cam.dbName = k
            cam.name = c.name
            cam.description = c.description
            cam.startdate = c.startdate
            cam.enddate = c.enddate
            logger.debug("Appending to cList cam with dbName = %s and name = %s", cam.dbName, cam.name)
            cList.append(cam)

    logger.debug("cList = %s", cList)

    return render_to_response('campaigns.html', {'cList': cList } ) 

def showActivities(request):
    '''Present list of Activities in the database.  Unlike showDatabase(), show show the Activities and their
    local attributes, no counts, or delete link.  This is so that it will display more quickly.
    
    '''

    aList = mod.Activity.objects.all().order_by('-startdate')       # Reverse order so that they pop off list in order

    # Construct our own Act activity list with an enhanced comment
    actList = []
    hostname = socket.gethostbyaddr(socket.gethostname())[0]
    for a in aList:
        act = Act()

        if a.campaign:
            act.campaignName = a.campaign.name
        if a.platform:
            act.platformName = a.platform.name
        if a.activitytype:
            act.activityTypeName = a.activitytype.name
        act.id = a.id
        act.name = a.name
        act.startdate = a.startdate
        act.isostartdate = a.startdate.strftime('%Y%m%dT%H%M%S')
        if a.enddate:
            act.enddate = a.enddate
            act.isoenddate = a.enddate.strftime('%Y%m%dT%H%M%S')

        # Pull out information from initial comment to construct preview links to the data - uses 'syntactic surgar' and knowlegde of the comment that DAPloader creates
        # It's probably better to do this in the template file - but I know how to do it this way
        try:
            mparms = a.comment.split(':')[1].split('.')[0].split(' ')
        except IndexError:
            # Empty comment, append Activity and continue
            actList.append(act)
            continue

        # Note:  This is really bad form: mixing html style here...
        #        We'd like this information, and it should probably be added to the model...
        ##commStr = '<b>' + a.comment.split(':')[0] + '</b>'
        commStr = ''
        depthQuery = 'depth/0/300'
        commStr += '<b>Parameters</b> (Sample links here are for /%s)\n<table border="0">' % depthQuery
        for mp in mparms:
            if not mp:
                continue
            commStr += '\n<tr><td><p class="smallerText">%s:</p></td>' % mp
            parmURL = "measurement/%s/between/%s/%s/%s" % (mp, a.startdate.strftime('%Y%m%dT%H%M%S'), a.enddate.strftime('%Y%m%dT%H%M%S'), depthQuery)
            for type in ['count', 'data.html', 'data.csv', 'data.kml', 'perf.kml']:
                commStr += '<td><p class="smallerText"><a href="%s/%s">%s</a> | </p>' % (parmURL, type, type)
            commStr = commStr[:-2] + '</td>'        # Remove last '|' , close cell
        commStr += '</tr>\n</table>\n'            # Close inner table, add new line
        commStr += a.comment.split(':')[0] + a.comment.split('.')[1].split('.')[0] + ' GMT'
        act.comment = commStr

        # Construct some useful links to the original activity for display on the activities page
        # It's probably better to do this in the template file - but I know how to do it this way
        tethysLogBase = 'http://aosn.mbari.org/TethysLogs'
        doradoSurveyBase = 'http://dods.mbari.org/data/auvctd/surveys/'
        if act.platformName == 'tethys':
            if a.name.split('/')[1] < '20110422T001932':
                tMap = 'mapplot.jpg'
                tSec = 'section.jpg'
            else:
                tMap = 'mapplot.png'
                tSec = 'section.png'
            linkStr = '<a href="%(base)s/%(Y)s/%(Y)s%(M)s/%(tMiss)s"><img src="%(base)s/%(Y)s/%(Y)s%(M)s/%(tMiss)s/%(tMap)s" width="144" height="108"></a>' % {'base': tethysLogBase, 
                        'Y': a.startdate.strftime('%Y'), 'M':  a.startdate.strftime('%m'), 'tMiss': a.name.split('/')[1], 'tMap': tMap}
            linkStr += '<a href="%(base)s/%(Y)s/%(Y)s%(M)s/%(tMiss)s"><img src="%(base)s/%(Y)s/%(Y)s%(M)s/%(tMiss)s/%(tSec)s" width="144" height="108"></a>' % {'base': tethysLogBase, 
                        'Y': a.startdate.strftime('%Y'), 'M':  a.startdate.strftime('%m'), 'tMiss': a.name.split('/')[1], 'tSec': tSec}
        elif act.platformName == 'dorado':
            # Thumbnail image is a resize of the original with a factor of 1/7.
            linkStr = '<a href="%(base)s/%(Y)s/images/%(dSurv)s_2column.png"><img src="%(base)s/%(Y)s/images/%(dSurv)s_2column.png" width="293" height="170"></a>' % {'base': doradoSurveyBase, 
                        'Y': a.startdate.strftime('%Y'), 'dSurv': a.name.split('_decim')[0]}
        else:
            linkStr = ''
        act.links = linkStr

        actList.append(act)

    return render_to_response('activities.html', 
                {'aList': actList, 'dbName': request.META['dbName']},
                context_instance=RequestContext(request)
                ) 
    
    # End showActivities()



