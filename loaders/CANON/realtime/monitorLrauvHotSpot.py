#!/usr/bin/env python
__author__    = 'Mike McCann, Danelle Cline'
__version__ = '$Revision: $'.split()[1]
__date__ = '$Date: $'.split()[1]
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'
__doc__ = '''

Monitor the dods web site for new realtime hotspot data from Tethys and use
DAPloaders.py to load new data into the stoqs database.

Mike McCann
MBARI 12 March 2014

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
sys.path.insert(0, "/home/stoqsadm/dev/stoqs/loaders/CANON/toNetCDF")
sys.path.insert(0, "/home/stoqsadm/dev/stoqs/loaders")
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import DAPloaders
import logging
import lrauvNc4ToNetcdf
from datetime import datetime, timedelta
import urllib2
import time
import csv
import re
from stoqs import models as mod
from BeautifulSoup import BeautifulSoup as soup
import socket
import pydap.client 
import pdb

# Set up global variables for logging output to STDOUT
logger = logging.getLogger('monitorTethysHotSpotLogger')
fh = logging.StreamHandler()
f = logging.Formatter("%(levelname)s %(asctime)sZ %(filename)s %(funcName)s():%(lineno)d %(message)s")
fh.setFormatter(f)
logger.addHandler(fh)
logger.setLevel(logging.DEBUG)

class NoNewHotspotData(Exception):
    pass

class NcFileMissing(Exception):
    def __init__(self, value):
        self.nc4FileUrl = value
    def __str__(self):
        return repr(self.nc4FileUrl)
  
def getNcStartEnd(url, useTds):
    '''Find the lines in the html with the .nc file, then open it and read the start/end times
    return url to the .nc  and start/end as datetime objects.
    '''
    startDatetime = None
    endDatetime = None
    urlNcDap    = None
    urlNc4Dap   = None

    if useTds is True:
        htmlToScan = 'catalog.html'
    else:
        htmlToScan = 'index.html'

    socket = urllib2.urlopen(url + '/' + htmlToScan)
    htmlPage = socket.read()
    socket.close()
    html = soup(htmlPage)

    links = html.findAll('a', attrs={'href': re.compile(".*.nc")})

    for link in links:
        #logger.debug("=============>link = %s" % (link['href']))
        match = re.match('.+/(hotspot-Normal_.+.nc)',link['href'])
        if match:
            #Open the url and get the time     
            #logger.debug("=================>match = %s" % match.group(1))
            u   = url + '/' + match.group(1)

            if useTds is True:
                urlNcDap = u.replace('catalog', 'dodsC')
            else:
                urlNcDap = u #untested

            try:
                df = pydap.client.open_url(urlNcDap)
                v = df['time']
                startDatetime = datetime.utcfromtimestamp(v[1])
                endDatetime = datetime.utcfromtimestamp(v[-1])
                logger.info("Datetime of first data in %s is %s" % (url, startDatetime))
                logger.info("Datetime of last data in %s is %s" % (url, endDatetime))
                return (match.group(1), startDatetime, endDatetime)  
            except:
                # Nc file can't be open; find the .nc4 file and throw exception to 
                # flag nc file is missing
                match = re.match('.+/(hotspot.+.nc4)',link['href'])
                if match:
                    #logger.debug("=================>match = %s" % match.group(1))
                    u = url + '/' + match.group(1)
                
                    if useTds is True:
                        urlNc4Dap = u.replace('catalog', 'dodsC')
                    else:
                        urlNc4Dap = u #untested

                    raise NcFileMissing(urlNc4Dap)

    return (None, startDatetime, endDatetime)

def getDatetime(url, outDir, useTds, lastDatetime):
    '''
    Scrape lrauv web site for first .nc file newer than lastDatetime.
    '''
    folderName = []
    filename = []
    startDatetime = None
    endDatetime = None

    # Get directory list from sites
    logger.info("Scanning for start and end times in %s" % (url))
  
    if useTds is True:
        htmlToScan = 'catalog.html'
    else:
        htmlToScan = 'index.html'

    socket = urllib2.urlopen(url + '/' + htmlToScan)
    htmlPage = socket.read()
    socket.close()
    html = soup(htmlPage)

    links = html.findAll('a', attrs={'href': re.compile("^(\d+T\d+)")})

    # look in reverse time order - oldest to newest
    for link in reversed(links):
        try:
            #logger.debug("=============>link = %s" % (link['href']))
            match = re.match('^(\d+T\d+)', link['href'] )
            folderName = match.group(1)       
            folderDatetime = datetime(*time.strptime(folderName, '%Y%m%dT%H%M%S')[:6])
            if folderDatetime > lastDatetime:
                (filename, startDatetime, endDatetime) = getNcStartEnd(url + folderName, useTds)
                if startDatetime and endDatetime and filename:
                    return (folderName, filename, startDatetime, endDatetime)
        except NcFileMissing,(instance):
            # Run the conversion if the nc file is missing and place in the 
            # appropriate directory behind an opendap/thredds server somewhere
            pw = lrauvNc4ToNetcdf.InterpolatorWriter()
            # Formulate new filename from the url. Should be the same name as the .nc4 specified in the url
            # with _i.nc appended to indicate it has interpolated data in .nc format
            nc4f = instance.nc4FileUrl.rsplit('/',1)[1]
            outFile = outDir + folderName + '/' + '.'.join(nc4f.split('.')[:-1]) + '_i.nc'
            # Only create if it doesn't already exists
            if not os.path.isfile(outFile):
                try:
                    pw.process(instance.nc4FileUrl, outFile)
                except Exception,e:
                    logger.info('Error creating %s: %s' % (outFile, e))
            continue

    raise NoNewHotspotData

def process_command_line():
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n\n'
        examples += sys.argv[0] + " -d  'Daphe hotspot data from April 2014 ECOHAB experiment' \
        -o '/LRAUV/daphne/realtime/hotspotlogs/' -u 'http://dods.mbari.org/opendap/hyrax/data/lrauv/daphne/realtime/hotspotlogs/' -b 'stoqs_march2014' -c 'CANON-ECOHAB - March 2014'\n"    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Read lRAUV data transferred over hotstpot and .nc file in \
                                         compatible CF1-6 Discrete Sampling Geometry forat for loading into STOQS',
                                         epilog=examples)
                                             
        parser.add_argument('-u', '--inUrl',action='store', help='url where hotspot logs are', default='.',required=True)   
        parser.add_argument('-b', '--database',action='store', help='name of database to load hotspot data to', default='.',required=True)  
        parser.add_argument('-c', '--campaign',action='store', help='name of campaign', default='.',required=True)    
        parser.add_argument('-o', '--outDir', action='store', help='output directory to store .nc file', default='.',required=True)   
        parser.add_argument('-d', '--description', action='store', help='Brief description of experiment', default='',required=True)
        parser.add_argument('-v', '--verbose', action='store_true', help='Turn on verbose output')
   
        args = parser.parse_args()    
	return args

if __name__ == '__main__':
    colors = {  'tethys':       'fed976',
                'daphne':       'feb24c'}
  
    useTds = None
    
    args = process_command_line()

    platformName = None; 

    # Base url for logs indicates what vehicle logs are being monitored 
    d = re.match(r'.*tethys*',args.inUrl) 
    if d:
        platformName = 'tethys'
    d = re.match(r'.*daphne*',args.inUrl)
    if d:
        platformName = 'daphne'

    # Determine if using thredds from url 
    d = re.match(r'.*thredds*',args.inUrl) 
    if d:
        useTds = True
        htmlToScan = 'catalog.html'
    else:
        useTds = False
        htmlToScan = 'index.html'

    if platformName is None:
        raise Exception('cannot find platformName from url %s' % args.inUrl)

    activityBaseName = platformName + ' hotspot - '

    # Start back a week from now to load in old data
    lastDatetime = datetime.utcnow() - timedelta(days=7)
    
    while True: 
        'Loop until we run out of new lrauv data'
        logger.info("-----------------------------------------------------------------------------------------------------------------")
        logger.info("Checking %s" % args.inUrl)
        logger.info("Last lrauv %s data in %s is from %s" % (platformName, args.database, lastDatetime))

        try:
            (folderName, filename, startDatetime, endDatetime) = getDatetime(args.inUrl, args.outDir, useTds, lastDatetime)
            lastDatetime = endDatetime
        except NoNewHotspotData:
            logger.info("No new %s data.  Exiting." % platformName )
            sys.exit(1)

        if len(filename) > 0:
            logger.info("Received new %s data ending at %s in folder %s filename %s" % (platformName, endDatetime, folderName, filename))
            u = '%s%s/%s' % (args.inUrl, folderName, filename)
        
            if useTds is True:
                newURL = u.replace('catalog', 'dodsC')
            else:
                newURL = u #untested
         
            aName = activityBaseName + folderName

            # If we have any activities with the same enddate whose name matches the activity name
            alist = mod.Activity.objects.filter(name = aName)

            if aName in [a.name for a in alist]:
                logger.info("Found activity name = %s" % aName)
            else:
                try:
                    parms = ['sea_water_temperature', 'sea_water_salinity', 'mass_concentration_of_chlorophyll_in_sea_water', 'downwelling_photosynthetic_photon_flux_in_sea_water']
                    logger.debug("Instantiating Lrauv_Loader for url = %s", newURL)
                    lrauvLoad = DAPloaders.runLrauvLoader(aName = aName,
                                                      aTypeName = '',
                                                      pName = platformName,
                                                      pTypeName = 'auv',
                                                      pColor = colors[platformName],
                                                      url = newURL,
                                                      parmList = parms,
                                                      cName = args.campaign,
                                                      dbAlias = args.database,
                                                      stride = 1,
                                                      startDatetime = startDatetime,
                                                      endDatetime = endDatetime)
                except DAPloaders.NoValidData:
                    logger.info("No measurements in this log set. Activity was not created as there was nothing to load.")

