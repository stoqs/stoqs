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

from django.shortcuts import render
from django.template import RequestContext
from django.conf import settings
from django.db import DatabaseError
from django.http import HttpResponse
from utils import encoders
import stoqs.models as mod
from datetime import datetime, timedelta
from stoqs import tasks
import socket
import logging
import json
import sys

logger = logging.getLogger(__name__)

def deleteActivity(request, activityId):
    '''Do a cascade delete of an activity given the `activityId`.  This will delete everything that has a foreign
    key pointing to the activity which will result in removal of all the measurements and measured_parameters
    associated with the activity.
    '''
    
    tasks.delete_activity.delay(request.META['dbAlias'], activityId)
    return render(request, 'deletion.html', context={'dbAlias': request.META['dbAlias'], 'activityId': activityId})
    
    
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

    return render(request, 'management.html', context=
                {'dbAlias': request.META['dbAlias'], 
                 'actList': actList,
                 'pList': pList,
                 }
                ) 
    
    # End showDatabase()


def showCampaigns(request,format=None):
    '''
    Present list of Campaigns from scanning the DATABASES dictionary from settings.
    '''

    dbAliases = list(settings.DATABASES.keys())
    logger.debug("DATABASES")
    logger.debug(settings.DATABASES)
    logger.debug("DATABASES.keys()")
    logger.debug(list(settings.DATABASES.keys()))
  
    # Data structure hash of lists.  Possible to have multiple campaigns in a database
    cHash = {}
    rHash = {}
    for dbAlias in list(settings.DATABASES.keys()):
        # Initialize Campaign and Resource hash lists
        cHash[dbAlias] = []
        rHash[dbAlias] = []

    for dbAlias in list(settings.DATABASES.keys()):
        try:
            logger.debug("Getting Campaign from dbAlias = %s", dbAlias)
            cqs = mod.Campaign.objects.using(dbAlias).all()
            for c in cqs:
                logger.debug("Appending campaign name = %s to cHash with key (dbAlias) = %s", c.name, dbAlias)
                cHash[dbAlias].append(c)
                r = {}
                for cr in mod.CampaignResource.objects.using(dbAlias).filter(campaign=c):
                    r[cr.resource.name] = cr.resource.value
                rHash[dbAlias].append(r)
        except mod.Campaign.DoesNotExist:
            logger.warn("Database alias %s does not exist", dbAlias)
            continue
        except DatabaseError:
            # Will happen if database defined in privateSettings does not exist yet
            logger.warn("Database alias %s returns django.db.DatabaseError", dbAlias)
            continue

        # Close the database connection, before connecting to the next database
        # TODO: Check for how Django1.7+ does this
        ##close_connection()

    # Create a hash keyed by startdate of the dbAliases and campaigns so that we display a time sorted list of campaigns
    timeSortHash = {}
    dummyTime = datetime(1970,1,1)
    for k in list(cHash.keys()):
        logger.debug('k = %s', k)
        for c,r in zip(cHash[k], rHash[k]):
            logger.debug('c.name = %s', c.name)
            # Use combination of dbAlias and startdate as different dbAlias's can have the same startdate
            if c.startdate:
                key = str(c.startdate) + '_' + c.name
                timeSortHash[key] = {k: (c, r)}
                logger.debug("Set timeSortHash['%s'] = %s", key, {k: (c, r)})
            else:
                # Put in a dummy time, and increment it
                key = str(dummyTime) + '_' + c.name
                timeSortHash[key] = {k: (c, r)}
                logger.debug("Set timeSortHash['%s'] = %s", key, {k: (c, r)})
                dummyTime += timedelta(seconds=1)
                logger.debug('dummyTime = %s', dummyTime)

    # Build list of hashes to pass to the campaigns.html template
    camList = []
    for d in sorted(list(timeSortHash.keys()), reverse=True):
        logger.debug("d = %s, timeSortHash[d] = %s", d, timeSortHash[d])
        for k,(c, r) in list(timeSortHash[d].items()):
            logger.debug(k)
            logger.debug(c)
            description = ''
            startdate = ''
            enddate = ''
            if c.description:
                description = c.description
            if c.startdate: 
                startdate = c.startdate.strftime('%d %b %Y')
            if c.enddate:
                enddate = c.enddate.strftime('%d %b %Y')
            camList.append({'name': c.name, 'dbAlias': k, 'description': description,
                            'startdate': startdate, 'enddate': enddate,
                            'MeasuredParameter_count': r.get('MeasuredParameter_count', ''),
                            'SampledParameter_count': r.get('SampledParameter_count', ''),
                            'Parameter_count': r.get('Parameter_count', ''),
                            'Platform_count': r.get('Platform_count', ''),
                            'Activity_count': r.get('Activity_count', ''),
                            'minutes_to_load': r.get('minutes_to_load', ''),
                            'loadlog': r.get('load_logfile', '')})

    logger.debug("camList = %s", camList)
    if format == 'json':
        return HttpResponse(json.dumps(camList, cls=encoders.STOQSJSONEncoder), 'application/json')
    elif format == 'count':
        return HttpResponse(len(camList), mimetype='text/plain')
    else:
        return render(request, 'campaigns.html', context={'cList': camList })

def showActivitiesMBARICustom(request):
    '''Present list of Activities in the database.  Unlike showDatabase(), show show the Activities and their
    local attributes, no counts, or delete link.  This is so that it will display more quickly.
    
    '''

    aList = mod.Activity.objects.all().order_by('-startdate')       # Reverse order so that they pop off list in order

    # Construct our own Act activity list with an enhanced comment
    actList = []
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

    return render(request, 'activities.html', context={'aList': actList, 'dbAlias': request.META['dbAlias']})
    
    # End showActivities()



