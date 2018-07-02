#!/usr/bin/env python

__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Contains class for common routines for loading all CANON data

Mike McCann
MBARI 22 April 2012

@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # settings.py is one dir up
import re

import DAPloaders
from thredds_crawler.crawl import Crawl
from loaders import LoadScript
from DAPloaders import Mooring_Loader, NoValidData
import logging
import colorsys

logger = logging.getLogger('__main__')

class OSLoader(LoadScript):
    '''
    Common routines for loading all CANON data
    '''
    def getColor(self, numColors):
        '''Rotate through numCOlors hues to return a next rgb color value
        '''
        for hue in range(numColors):
            hue = 1. * hue / numColors
            col = [int(x) for x in colorsys.hsv_to_rgb(hue, 1.0, 230)]
            yield "{0:02x}{1:02x}{2:02x}".format(*col)

    def loadStationData(self, stride=1):
        '''Crawl the OceanSITES Mooring data TDS for OPeNDAP links and load into STOQS
        '''
        urls = []
        strides = {}
        for dataSet in self.dataSets:
            c = Crawl(dataSet[0], select=dataSet[1], debug=self.args.verbose)
            dsUrls = [s.get("url") for d in c.datasets for s in d.services if s.get("service").lower() == "opendap"]
            for dsu in dsUrls:
                strides[dsu] = dataSet[2]
            urls += dsUrls

        # First pass through urls matching OceanSITES pattern to collect platform names to get colors
        # Use OceanSITES naming convention for platform "OS_<platformName>_xxx_R|D_<type>.nc"
        pNames = set()
        platfrormTypeNames = set()
        for url in urls:
            platfrormTypeNames.add(url.split('/')[-2])
            if url.find('MOVE1_') != -1:
                # Special hack for MOVE PlatformCode
                newUrl = url.replace('MOVE1_', 'MOVE1-')
                pNames.add(newUrl.split('/')[-1].split('.')[0].split('_')[1])
            else:
                pNames.add(url.split('/')[-1].split('.')[0].split('_')[1])

        # Assign colors by platformTypeName
        pColors = {}
        for ptName, color in zip(sorted(platfrormTypeNames), self.getColor(len(platfrormTypeNames))) :
            pColors[ptName] = color

        # Now loop again, this time loading the data 
        for url in urls:
            logger.info("Executing runMooringLoader with url = %s", url)
            if self.args.optimal_stride and strides[url]:
                stride = strides[url] 
            elif self.args.test:
                stride = strides[url] * 2

            fixedUrl = url
            if url.find('OS_IMOS-EAC_EAC') != -1:
                # Special fix to get platform name 
                fixedUrl = url.replace('OS_IMOS-EAC_EAC', 'OS_IMOS-EAC-EAC')

            if stride > 1:
                aName = fixedUrl.split('/')[-1].split('.')[0] + '(stride=%d)' % stride
            else:
                aName = fixedUrl.split('/')[-1].split('.')[0]

            pName = aName.split('_')[1]
            ptName = url.split('/')[-2]
   
            logger.debug("Instantiating Mooring_Loader for url = %s", url)
            try:
                ml = Mooring_Loader(
                    url = url,
                    campaignName = self.campaignName,
                    campaignDescription = self.campaignDescription,
                    dbAlias = self.dbAlias,
                    activityName = aName,
                    activitytypeName = 'Mooring Deployment',
                    platformName = pName,
                    platformColor = pColors[ptName],
                    platformTypeName = ptName,
                    stride = stride,
                    startDatetime = self.startDatetime,
                    dataStartDatetime = None,
                    endDatetime = self.endDatetime)
            except UnicodeDecodeError as e:
                logger.warn(str(e))
                logger.warn(f'Cannot read data from {url}')
                continue

            # Special fixes for non standard metadata and if files don't contain the standard TEMP and PSAL parameters
            if url.find('MBARI-') != -1:
                ml.include_names = ['TEMP', 'PSAL']
                ml.auxCoords = {}
                for v in ml.include_names:
                    ml.auxCoords[v] = {'time': 'TIME', 'latitude': 'LATITUDE', 'longitude': 'LONGITUDE', 'depth': 'DEPTH'}
            elif url.find('OS_PAPA_2009PA003_D_CTD_10min') != -1:
                ml.include_names = ['TEMP']
            elif url.find('OS_PAPA_2009PA003_D_PSAL_1hr') != -1:
                ml.include_names = ['PSAL']
            elif url.find('OS_SOTS_SAZ-15-2012_D_microcat-4422m') != -1:
                ml.include_names = ['TEMP', 'PSAL']
                # DEPTH_CN_PR_PS_TE coordinate missing standard_name attribute
                ml.auxCoords = {}
                for v in ml.include_names:
                    ml.auxCoords[v] = {'time': 'TIME', 'latitude': 'LATITUDE', 'longitude': 'LONGITUDE', 'depth': 'DEPTH_CN_PR_PS_TE'}
                # Only global attribute is 'cdm_data_type: Time-series'; monkey-patch the method
                Mooring_Loader.getFeatureType = lambda self: 'timeseries'
            elif url.find('D_MICROCAT-PART') != -1:
                ml.include_names = ['TEMP', 'PSAL']
                ml.auxCoords = {}
                for v in ml.include_names:
                    ml.auxCoords[v] = {'time': 'TIME', 'latitude': 'LATITUDE', 'longitude': 'LONGITUDE', 'depth': 'DEPTH'}
            elif url.find('D_RDI-WORKHORSE-ADCP-') != -1:
                ml.include_names = ['UCUR', 'VCUR', 'WCUR']
                ml.auxCoords = {}
                for v in ml.include_names:
                    ml.auxCoords[v] = {'time': 'TIME', 'latitude': 'LATITUDE', 'longitude': 'LONGITUDE', 'depth': 'HEIGHT_ABOVE_SENSOR'}
                # Metadata in file states 'timeseries', but it's really something different; monkey-patch the getFeatureType() method
                Mooring_Loader.getFeatureType = lambda self: 'trajectoryprofile'
            elif url.find('TVSM_dy.nc') != -1:
                ##ml.include_names = ['UCUR', 'VCUR', 'TEMP', 'PSAL', 'CSPD', 'CDIR']
                ml.include_names = ['TEMP', 'PSAL']
                ml.auxCoords = {}
                for v in ('UCUR', 'VCUR', 'CSPD', 'CDIR'):
                    ml.auxCoords[v] = {'time': 'TIME', 'latitude': 'LATITUDE', 'longitude': 'LONGITUDE', 'depth': 'DEPCUR'}
                for v in ('TEMP',):
                    ml.auxCoords[v] = {'time': 'TIME', 'latitude': 'LATITUDE', 'longitude': 'LONGITUDE', 'depth': 'DEPTH'}
                for v in ('PSAL',):
                    ml.auxCoords[v] = {'time': 'TIME', 'latitude': 'LATITUDE', 'longitude': 'LONGITUDE', 'depth': 'DEPPSAL'}
                # These PIRATA daily files are timeSeriesProfile which hsa no featureType attribute
                Mooring_Loader.getFeatureType = lambda self: 'timeseriesprofile'
            elif url.find('CCE') != -1:
                ml.include_names = ['TEMP', 'PSAL']
                ml.auxCoords = {}
                for v in ml.include_names:
                    ml.auxCoords[v] = {'time': 'TIME', 'latitude': 'LATITUDE', 'longitude': 'LONGITUDE', 'depth': 'DEPTH'}
            elif url.find('NOG') != -1:
                ml.include_names = ['TEMP', 'PSAL']
                Mooring_Loader.getFeatureType = lambda self: 'timeseries'
            elif url.find('Stratus') != -1:
                # Variable attrubute coordinates: TIME, DEPTH, LATITUDE, LONGITUDE; it should not contain commas
                ml.include_names = ['TEMP', 'PSAL']
                ml.auxCoords = {}
                for v in ml.include_names:
                    ml.auxCoords[v] = {'time': 'TIME', 'latitude': 'LATITUDE', 'longitude': 'LONGITUDE', 'depth': 'DEPTH'}
            else:
                ml.include_names = ['TEMP', 'PSAL']
    
            try:
                (nMP, path, parmCountHash) = ml.process_data()
                logger.debug("Loaded Activity with name = %s", aName)
            except NoValidData as e:
                logger.warning(e)
    
