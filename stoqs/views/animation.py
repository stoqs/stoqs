#!/usr/bin/env python

__author__ = "Danelle Cline"
__copyright__ = "Copyright 2012, MBARI" 
__license__ = "GPL"
__version__ = "$Revision: 12294 $".split()[1]
__maintainer__ = "Danelle Cline"
__email__ = "dcline at mbari.org"
__status__ = "Development"
__doc__ = '''

Test animation that creates animation based on gifs

Danelle Cline
MBARI Feb 16, 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.http import QueryDict
from datetime import datetime
from datetime import timedelta
from urlparse import urlparse
from shutil import copyfile
from django.conf import settings

import shutil
import time
import logging 
import os
import json
import urllib2 
import random

logger = logging.getLogger(__name__)
webUrl = 'http://localhost/media/'
cacheDir = '/tmp/media/'
  
def createAnimation(request, startDate, endDate, deltaMinutes, format, rangeFlag):  
    
    'parse time into datetime object and initialize query'
    timeFormat = '%Y%m%dT%H%M%S'
    startdt = datetime.strptime(startDate, timeFormat)
    enddt = datetime.strptime(endDate, timeFormat)    
    querydt = startdt
    delta = timedelta(minutes=int(deltaMinutes))         
    
    'generate randomly generated scratch directory to dump images to and create directory'
    r = random.randint(1, 10000)
    tmpDir = "%s%d%s" % ('/tmp/animate', r, '/')    
    os.mkdir(tmpDir)
    animateFinal = "%s%d%s" % ('animate', r, '.gif')
    animate = tmpDir + animateFinal    

    if not os.path.exists(cacheDir) :
        os.mkdir(cacheDir)
         
    'get tiles and overall width/height of final animated GIF'
    mapWidth = int(request.GET.get('width',''))
    mapHeight = int(request.GET.get('height',''))    
    bgSize="%dx%d" % (mapWidth, mapHeight)            
    numRows = int(request.GET.get('rows',''))  
    numCols = int(request.GET.get('cols',''))
    tilesjson = request.GET.get('tiles','')  
    tiles = json.loads(tilesjson)    
     
    'define file names'
    canvas = tmpDir + 'canvas.gif'
    tileCanvas = tmpDir + 'tilecanvas.gif' 
    foregroundAlpha = tmpDir + 'foreground_alpha.gif' 
    rootFinal = 'flat'
    gifFiles = tmpDir + rootFinal + '*.gif'
    
    'create transparent canvas to write tiles to'
    runCmd("%s%d%s%d%s" % ('convert -size ', mapWidth,'x',mapHeight,' xc:transparent ' + canvas)  )
  
    'create a tile canvas'
    runCmd("%s%d%s%d%s" % ('convert -size ', mapWidth,'x',mapHeight,' xc:transparent ' + tileCanvas) )
  
    j = 0
    r = 0
    c = 0 
         
    while querydt <= enddt:          
  
        flat = "%s%d%s" % (tmpDir + rootFinal, j, '.gif' )          
         
        j = j + 1        
        
        for tile in tiles:   
            
            'parse url key/value pairs into dictionary with DJango QueryDict'
            url = tile.get('url','') 
            logger.debug("URL: " + url)
            b = urlparse(url)

            if not b.query :
                continue

            logger.debug("URL query: " + b.query)       
            q = QueryDict(b.query, mutable=True)  

            'replace time query in dictionary according to the format specified by the layer'     
            if (querydt + delta) <= enddt:
                qstart = querydt.strftime(  q['TIMEFORMAT']  )
                qend = (querydt + delta).strftime( q['TIMEFORMAT']  )
                qstartPretty = querydt.strftime('%d %b %Y %H:%M GMT')
                qendPretty = (querydt + delta).strftime('%d %b %Y %H:%M GMT')
            else:
                qstart = querydt.strftime(  q['TIMEFORMAT']  )
                qend = enddt.strftime( q['TIMEFORMAT']  )
                qstartPretty = querydt.strftime('%d %b %Y %H:%M GMT')
                qendPretty = enddt.strftime('%d %b %Y %H:%M GMT')
                
            if rangeFlag:
                qrange = qstart + '/' + qend 
                qrangePretty = qstartPretty + '/' + qendPretty
                q['TIME'] = qrange
            else:
                q['TIME'] = qstart
                qrangePretty = qstartPretty

            logger.debug("QUERY" + qrangePretty)
            
            'parse the url and replace with updated time'
            b = urlparse(url)
            url = b.scheme + "://" + b.netloc + b.path + "?" + q.urlencode()    
            
            logger.debug("URL new query: " + url)
            
            'read tile and write to disk'
            tileRaw = "tile.gif"
            f = open(tileRaw, 'w') 
            data = urllib2.urlopen(url).read()             
            f.write(data)
            f.close()  
                
            'create tile to add to the tile canvas'
            x = int(tile.get('x',''))
            y = int(tile.get('y',''))
            tileW = int(tile.get('tileSizeW','')) 
            tileH = int(tile.get('tileSizeH',''))
            tileSize="%dx%d" % (tileW, tileH)            
            tileOffset = "%+d%+d" % (x, y)  
            runCmd("convert " + tileCanvas +  " " +   tileRaw +  " -geometry " + tileSize + tileOffset + " -composite " + tileCanvas )
            
            if r == numRows - 1 &  c == numCols - 1:
                c = 0
                r = 0              
                
                'change alpha channel to match that defined in the layer'
                opacity =  int(tile.get('opacity',''))        
                runCmd("%s%d%s" % ("convert " + tileCanvas + " -channel Alpha -evaluate set ", opacity,"% " + foregroundAlpha) )
              
                'add to the canvas '
                runCmd("convert -size " + bgSize + " -composite -compose plus " + canvas + " " + foregroundAlpha + " -geometry " +  bgSize + "+0,+0  " + canvas) 
       
                'flatten the image and save'
                runCmd("convert " + canvas +  " -flatten " + flat)
                
                'add the date time, adjusting the point size to something reasonsable based on the map width'
                pointsize =  "%d" % (mapWidth/25)  
                size =  "%s%d%s%d" % ('-size ', mapWidth, 'x', 30)
                runCmd("convert " + flat + " -pointsize " + pointsize + " -fill yellow  -undercolor '#050505' -gravity South " + size + " -annotate +0+20 " + " '" +  qrangePretty + "' " + flat)
       
                'if increment zero, this will not create a time animation, so do not proceed from here'
                if deltaMinutes <= 0:
                    break  
    
                'create transparent canvas to write tiles to'
                runCmd("%s%d%s%d%s" % ('convert -size ', mapWidth,'x',mapHeight,' xc:transparent ' + canvas)  )
  
                'create a tile canvas'
                runCmd("%s%d%s%d%s" % ('convert -size ', mapWidth,'x',mapHeight,' xc:transparent ' + tileCanvas) )
  
            elif c == numCols - 1:
                r = r + 1
                c = 0 
            else:
                c = c + 1  
        querydt = querydt + delta
            
     
    'create animated gif, dump to cached file(optional), clean-up, then copy output to web dir '
    runCmd('convert -delay 250 -loop 0 -treedepth 4 -dispose Previous -transparent black ' + gifFiles + " " + animate)
     
    if format == 'url' :
        shutil.copy(animate , cacheDir)
  
    'get binary image'
    imageData = open(animate, 'rb').read()
    
    'clean up'
    shutil.rmtree(tmpDir)
    
    if format == 'url' :
        returnStr = webUrl + animateFinal
        return HttpResponse(returnStr)
    elif format == 'image' : 
        return HttpResponse(imageData, mimetype='image/gif')   
    
    return HttpResponse(imageData, mimetype='image/gif')   

            
def runCmd(cmd):
    logger.debug("Executing " + cmd)
    os.popen(cmd) 
   
