#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__credits__ = ["Chander Ganesan, Open Technology Group"]
__license__ = "GPL"
__version__ = "$Revision: 12265 $".split()[1]
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

View functions related to providing parameter and measurement responses.

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
from django.http import HttpResponse
from django.conf import settings
from django.db import connection
from datetime import datetime, timedelta
import time
import sys
import csv
import stoqs.models as mod
import logging

from KML import makeKML

logger = logging.getLogger(__name__)

# Control util.CursorDebugWrapper - setting to True will cause all db queries to have their stack trace logged
##connection.use_debug_cursor = False

def showMeasurementsOfActivity(request, aName, aType, stride = '1', format = 'html', ofType = False, countFlag = False):
    '''Return measurements in specified format of specified Activity Name and Activity Type
    '''
    
    measList = []
    qs = mod.MeasuredParameter.objects.select_related().filter(measurement__instantpoint__activity__name = aName,
                                               measurement__instantpoint__activity__activitytype__name = aType)
    if countFlag:
        count = qs.count()
    else:
        mpList = qs.order_by('measurement__instantpoint__timevalue')[::int(stride)]
        if format == 'kml':
            title = "%s_%s_%s" % (pName, dmin, dmax)
            desc = 'Description'
            data = [(mp.measurement.instantpoint.timevalue, mp.measurement.geom.x, mp.measurement.geom.y, 
                 mp.measurement.depth, pName, mp.datavalue, mp.measurement.instantpoint.activity.platform.name)
                    for mp in mpList]
            kml = makeKML(data, pName, title, desc, startDate, endDate)
        else:
            measList.extend([ (mp.parameter.name, time.mktime(mp.measurement.instantpoint.timevalue.timetuple()), 
                        '%.6f' % mp.measurement.geom.x, '%.6f' %  mp.measurement.geom.y, '%.1f' %  mp.measurement.depth,
                        '%f' % mp.datavalue,
                        mp.measurement.instantpoint.timevalue.strftime('%Y-%m-%dT%H:%M:%SZ')) for mp in mpList ])

    if countFlag:
        response = HttpResponse("%d" % count, mimetype="text/plain")
        return response

    '''Deliver the response to the client of the data in the measList '''
    if format == 'csv':
        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = 'attachment; filename=measurementData_%s_between%s_%s.csv' % (pName, startDate, endDate)
        writer = csv.writer(response)
        writer.writerow(['parameter', 'epochSeconds', 'longitude', 'latitude', 'depth', 'datavalue', 'isoformat'])
        writer.writerows(measList)
        return response

    elif format == 'kml':
        response = HttpResponse(mimetype='application/vnd.google-earth.kml+xml')
        response['Content-Disposition'] = 'attachment; filename=%s_between_%s_%s_depth_%s_%s.kml' % (pName, startDate, endDate, dmin, dmax)
        ##response = HttpResponse(mimetype='text/plain')
        response.write(kml)
        return response

    else:
        'Default: render as html'
        return render_to_response('measurement.html', {'mList': measList})
    

def showBetweenMeasurements(request, pName, startDate, endDate, dmin, dmax, stride = '1', type = 'data', format = 'html', countFlag = False, snFlag = False):
    '''Return measurements in specified format from ISO8601 formatted startDate and endDate and depth range.  
    (There are no '-'s or ':'s in startDate -- they're not URL firendly.)  Depth min & max are in meters.
    '''
    # showBetweenMeasurements?pname=XXXX&stride=100
    ##pName = request.GET.get('pname', None)
    ##stride = request.GET.get('stride', 1)
    
    sDate = datetime(*time.strptime(startDate, '%Y%m%dT%H%M%S')[:6])
    eDate = datetime(*time.strptime(endDate, '%Y%m%dT%H%M%S')[:6])

    measList = []
    perfDict = {}
    if countFlag:
        if snFlag:
            count = mod.MeasuredParameter.objects.filter(parameter__standard_name = pName, measurement__instantpoint__timevalue__gte = sDate,
                                                measurement__instantpoint__timevalue__lte = eDate, measurement__depth__gte = dmin,
                                                measurement__depth__lte = dmax).count()
        else:
            qs = mod.MeasuredParameter.objects.filter(parameter__name = pName, measurement__instantpoint__timevalue__gte = sDate,
                                                measurement__instantpoint__timevalue__lte = eDate, measurement__depth__gte = dmin,
                                                measurement__depth__lte = dmax)
            logger.debug(qs.query)
            count = qs.count()                                    


    else:
        start = time.clock()
        if snFlag:
            qs = mod.MeasuredParameter.objects.select_related().filter(parameter__standard_name = pName, measurement__instantpoint__timevalue__gte = sDate, 
                        measurement__instantpoint__timevalue__lte = eDate, measurement__depth__gte = dmin, 
                        measurement__depth__lte = dmax).order_by('measurement__instantpoint__timevalue')
            logger.debug(qs.query)
            mpList = qs[::int(stride)]
            
        else:
            qs = mod.MeasuredParameter.objects.select_related().filter(parameter__name = pName, measurement__instantpoint__timevalue__gte = sDate, 
                        measurement__instantpoint__timevalue__lte = eDate, measurement__depth__gte = dmin, 
                        measurement__depth__lte = dmax).order_by('measurement__instantpoint__timevalue')

            logger.debug(qs.query)
            mpList = qs[::int(stride)]
            
            
        perfDict['get_mpListFromDB'] = time.clock() - start

        if format == 'kml':
            title = "%s_%s_%s" % (pName, dmin, dmax)
            desc = 'Description'
            start = time.clock()
            data = [(mp.measurement.instantpoint.timevalue, mp.measurement.geom.x, mp.measurement.geom.y, 
                 mp.measurement.depth, pName, mp.datavalue, mp.measurement.instantpoint.activity.platform.name)
                    for mp in list(mpList)]
            perfDict['makeDataListBuildTime'] = time.clock() - start

            dataHash = {}
            start = time.clock()
            for d in data:
                try:
                    dataHash[d[6]].append(d)
                except KeyError:
                    dataHash[d[6]] = []
                    dataHash[d[6]].append(d)
            perfDict['makeDataHashBuildTime'] = time.clock() - start
            logger.debug('makeDataHashBuildTime = %f seconds', (time.clock() - start))

            start = time.clock()
            kml = makeKML(dataHash, pName, title, desc, startDate, endDate)
            perfDict['makeKMLBuildTime'] = time.clock() - start
        else:
            start = time.clock()
            # This statement causes many SQL queries in order to look up all of the attributes


            measList.extend([ (mp.parameter.name, mp.measurement.instantpoint.activity.platform.name,
                        time.mktime(mp.measurement.instantpoint.timevalue.timetuple()), 
                        '%.6f' % mp.measurement.geom.x, '%.6f' %  mp.measurement.geom.y, '%.1f' %  mp.measurement.depth,
                        '%f' % mp.datavalue,
                        mp.measurement.instantpoint.timevalue.strftime('%Y-%m-%dT%H:%M:%SZ')) for mp in mpList[::] ])
            perfDict['measListBuildTime'] = time.clock() - start

    if countFlag:
        response = HttpResponse("%d" % count, mimetype="text/plain")
        return response

    if type == 'perf':
        pSum = 0
        for p in perfDict.values():
            pSum += p
        tSum = 0
        for t in connection.queries:
            tSum += float(t['time'])
        return render_to_response('performance.html', {'format': format, 'qList': connection.queries, 'tSum': tSum, 'pDict': perfDict, 'pSum': pSum})
        return response

    '''Deliver the response to the client of the data in the measList '''
    if format == 'csv':
        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = 'attachment; filename=measurementData_%s_between%s_%s.csv' % (pName, startDate, endDate)
        writer = csv.writer(response)
        writer.writerow(['parameter', 'platform', 'epochSeconds', 'longitude', 'latitude', 'depth', 'datavalue', 'isoformat'])
        writer.writerows(measList)
        return response

    elif format == 'kml':
        response = HttpResponse(mimetype='application/vnd.google-earth.kml+xml')
        response['Content-Disposition'] = 'attachment; filename=%s_between_%s_%s_depth_%s_%s.kml' % (pName, startDate, endDate, dmin, dmax)
        response.write(kml)
        return response

    else:
        'Default: render as html'
        return render_to_response('measurement.html', {'mList': measList})

