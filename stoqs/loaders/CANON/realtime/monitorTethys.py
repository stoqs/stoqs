#!/usr/bin/env python
'''
Monitor the aosn web site for new realtime data from Tethys and use
DAPloaders.py to load new data into the stoqs_realtime database.

Mike McCann
MBARI 17 May 2011
'''

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE']='config.settings.local'

import DAPloaders
import logging
from datetime import datetime, timedelta
import urllib.request, urllib.error, urllib.parse
import time
import csv
import re
from stoqs import models as mod
import socket

# Set up global variables for logging output to STDOUT
logger = logging.getLogger('monitorTethysLogger')
fh = logging.StreamHandler()
f = logging.Formatter("%(levelname)s %(asctime)sZ %(filename)s %(funcName)s():%(lineno)d %(message)s")
fh.setFormatter(f)
logger.addHandler(fh)
logger.setLevel(logging.DEBUG)

class NoMoreTethysLogSets(Exception):
    pass


def getLogSetStartAndEnd(url):
    '''Step though the lines of the html to pick out the start and end epoch sends of this LogSet in the url
    return start and end times as datetime objects.
    '''

    folderStart = None
    folderEnd = None

    for line in urllib.request.urlopen(url).read().split('\n'):
        ##logger.debug("line = %s" % line)
        d = re.match('.+var startTime=([\.\d]+)', line) # Get time of last data for this mission
        if d:
            folderStart = datetime.utcfromtimestamp(float(d.group(1)) / 1000.)
            logger.info("Datetime of first data in %s is %s", url, folderStart)
        d = re.match('.+var endTime=([\.\d]+)', line)   # Get time of last data for this mission
        if d:
            folderEnd = datetime.utcfromtimestamp(float(d.group(1)) / 1000.)
            logger.info("Datetime of last data in %s is %s", url, folderEnd)

        if folderStart and folderEnd:
            return (folderStart, folderEnd)



def getNewTethysDatetime(startFolder = None):
    '''
    Scrape AOSN TethysLog web site for the end time and mission directory name of the most recent data.
    Returns datetime object and string of the directory name as a tuple.  If startFolder is provided then
    start scanning following this folder.  This is so that the calling routine can skip over missions
    that have no measurements.
    '''

    previousFolderName = None
    previousFolderEndTime = None

    # Get directory list from aosn site
    url = 'http://aosn.mbari.org/TethysLogs/'
    logger.info("Scanning log sets and index.html start and end times in %s", url)
    if startFolder:
        logger.info("Starting at startFolder = %s", startFolder)
    for line in urllib.request.urlopen(url).read().split('\n'):
        # href="20110526T151722/"
        logger.debug("line = %s", line)
        f = re.match('.+href="(\d+T\d+)', line)
        if f:
            logger.debug("f.group(1) = %s", f.group(1))
            if startFolder:
                if f.group(1) < startFolder:
                    # Skip over folders that are before startFolder.  We need to revisit startFolder to set previous.. values
                    previousFolderName = f.group(1)
                    logger.debug("Skipping folder %s and it is earlier than startFolder = %s", previousFolderName, startFolder)
                    continue
            folderDatetime = datetime(*time.strptime(f.group(1), '%Y%m%dT%H%M%S')[:6])
            logger.debug("Going on to test whether folder %s has good data beyond lastTethysDatetime = %s", f.group(1), lastTethysDatetime)
    
            if folderDatetime > lastTethysDatetime:
                logger.info("Folder %s is newer than than last Tethys data in %s", f.group(1), stoqsDB)

                (folderStart, folderEnd) = getLogSetStartAndEnd(url + f.group(1))

                if folderStart and folderEnd:
                    return (f.group(1), folderStart, folderEnd, previousFolderName, previousFolderEndTime)
            else:
                previousFolderName = f.group(1)
                logger.debug("Folder %s contains data that have already been loaded in %s", f.group(1), stoqsDB)
                for line in urllib.request.urlopen(url + f.group(1)).read().split('\n'):
                    ##logger.debug("line = %s", line)
                    d = re.match('.+var endTime=([\.\d]+)', line)   # Get time of last data for this mission
                    if d:
                        previousFolderEndTime = datetime.utcfromtimestamp(float(d.group(1)) / 1000.)

    logger.info("Fell out of loop looking for new Folder with a startDate > lastTethysDatetime,"
                " checking for new data in previousFolderName = %s", previousFolderName)
    if previousFolderName is not None:
        (folderStart, folderEnd) = getLogSetStartAndEnd(url + previousFolderName)
        if (folderEnd - lastTethysDatetime) > timedelta(seconds = 1):
            logger.info("%s has new data that extends %s beyond what is in %s", previousFolderName, 
                                    (folderEnd - lastTethysDatetime), stoqsDB)
            # Return None for prebious values as there's no way we'll assign an end time in this situation
            return (previousFolderName, folderStart, folderEnd, None, None)


    raise NoMoreTethysLogSets


if __name__ == '__main__':

    # No arguments to parse.  Just look for new data and DAP load it.

    # Get time of last data item loaded
    stoqsDB = 'stoqsdb_realtime'
    hostname = socket.gethostbyaddr(socket.gethostname())[0]
    url = 'http://' + hostname + '/' + stoqsDB + '/position/tethys/last/1/data.csv'

    activityBaseName = 'Tethys realtime - '

    # When set to None getNewTethysDatetime() starts scanning from the beginning of the aosn index
    # If starting a new database then set to a value, e.g. '20110609T033428' to begin at that directory
    startFolderName = None

    while True: 
        # Loop until we run out of new Tethys data from aosn
        
        try:
            lastTethysEs = float(csv.DictReader(urllib.request.urlopen(url)).next()['epochSeconds'])
        except StopIteration:
            lastTethysEs = 0.0
        lastTethysDatetime = datetime.utcfromtimestamp(lastTethysEs)
        logger.info("-----------------------------------------------------------------------------------------------------------------")
        logger.info("Checking %s", url)
        logger.info("Last Tethys data in %s is from %s", stoqsDB, lastTethysDatetime)

        try:
            logger.debug("Calling getNewTethysDatetime with startFolderName = %s", startFolderName)
            (folderName, folderStart, folderEnd, previousFolderName, previousFolderEndTime) = getNewTethysDatetime(startFolderName);
            logger.debug("getNewTethysDatetime() returned previousFolderEndTime = %s", previousFolderEndTime)
        except NoMoreTethysLogSets:
            logger.info("No new Tethys data.  Exiting.")
            sys.exit(1)

        eval(input("Pause"))

        logger.info("Received new Tethys data ending at %s in folder %s", folderEnd, folderName)
        newTethysURL = 'http://beach.mbari.org:8080/thredds/dodsC/lrauv/tethys/%s/shore.nc' % folderName

        # The first time through the loop we need to get the last folder from the 'previous...' items returned by getNewTethysDatetime()
        # After that we'll remember the last folder from the last successful load done in this loop
        if not startFolderName and previousFolderName:
            lastAName = activityBaseName + previousFolderName
            lastAEndTime = previousFolderEndTime
        else:
            lastAName = None

        # If we have any activities with a null enddate whose name matches the last activity name then set the end date
        if lastAName:
            nullEndtimeActList =  mod.Activity.objects.filter(enddate__isnull = True)
            if lastAName in [a.name for a in nullEndtimeActList]:
                logger.info("Found Activity name = %s with null enddate", lastAName)

                # We have a new folderName, set the end time for the previous Activity and "close" that log set
                mod.Activity.objects.filter(name = lastAName).update(enddate = lastAEndTime)
                logger.info("Set endDatetime = %s for previous Activity.id = %s", a.enddate, a.id)

        # Tethys loads from TDS on beach - create with Null end time, we don't know the end until we have the next folder
        aName = activityBaseName + folderName
        ##newTethysDatetime = newTethysDatetime - timedelta(hours = 4)
        try:
            lrauvLoad = DAPloaders.Lrauv_Loader(activityName = aName,
                url = newTethysURL,
                startDatetime = folderStart,
                endDatetime = None,
                dataStartDatetime = lastTethysDatetime,
                platformName = 'tethys',
                stride = 1)
        except DAPloaders.NoValidData:
            # Make sure we don't visit this startFolder again - add 1 second to it
            startFolderName = (datetime(*time.strptime(folderName, '%Y%m%dT%H%M%S')[:6]) + timedelta(seconds = 1)).strftime('%Y%m%dT%H%M%S')
            logger.info("No measurements in this log set. Activity was not created as there was nothing to load.")
            if not previousFolderName:
                logger.info("previousFolderName = None, indicating that we are looking for valid data in the last folder")
                logger.info("Exiting now to prevent time consuming loop waiting for valid data in previousFolderName = %s", previousFolderName)
                sys.exit(1)

        else:
            logger.info("Loading data from %s into %s", newTethysURL, stoqsDB)
            nMeasurements = lrauvLoad.process_data()

            newComment = "%s loaded on %sZ" % (' '.join(lrauvLoad.varsLoaded), datetime.utcnow())
            logger.info("Updating comment with newComment = %s", newComment)
            mod.Activity.objects.filter(name = aName).update(comment = newComment)

            if not previousFolderName:
                logger.info("previousFolderName = None, indicating that we are looking for valid data in the last folder")
                logger.info("Exiting now to prevent time consuming loop waiting for valid data in previousFolderName = %s", previousFolderName)
                sys.exit(1)
            elif nMeasurements:
                # Make sure we don't visit this startFolder again - add 1 second to it
                startFolderName = (datetime(*time.strptime(folderName, '%Y%m%dT%H%M%S')[:6]) + timedelta(seconds = 1)).strftime('%Y%m%dT%H%M%S')
            else:
                startFolderName = folderName

            lastAName = aName
            lastAEndTime = folderEnd

