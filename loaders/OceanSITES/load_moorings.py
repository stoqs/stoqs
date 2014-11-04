#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Loader for data from OceanSITES GDAC

Mike McCann
MBARI 28 October 2014

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that OS and DAPloaders are found

import logging 
import datetime
from OceanSITES import OSLoader
from DAPloaders import Mooring_Loader, NoValidData
from thredds_crawler.crawl import Crawl

logger = logging.getLogger('__main__')

osl = OSLoader('stoqs_oceansites', 'OS Moorings',
                        description = 'Mooring data from the OceanSITES GDAC',
                        x3dTerrains = {
                            'http://dods.mbari.org/terrain/x3d/Globe_1m_bath_10x/Globe_1m_bath_10x_scene.x3d': {
                                'position': '14051448.48336 -15407886.51486 6184041.22775',
                                'orientation': '0.83940 0.33030 0.43164 1.44880',
                                'centerOfRotation': '0 0 0',
                                'VerticalExaggeration': '10',
                            }
                        },
                        ##grdTerrain = os.path.join(parentDir, 'Globe_1m_bath.grd') - For some reason causes an error in coards/__init__.py
               )

osl.parmList = ['TEMP', 'PSAL']
##osl.parmList = ['TEMP']

# Start and end dates of None will load entire archive
osl.startDatetime = None
osl.endDatetime = None

# TODO Method that can be pulled into the base class
def loadMoorings(osl, stride=1):
    '''Crawl the OceanSITES Mooring data TDS for OPeNDAP links and load into STOQS
    '''

    # http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/catalog.html
    ##c = Crawl("http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/catalog.html", select=[".*_TS.nc$"])
    #c = Crawl("http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/MBARI/catalog.html", select=[".*_TS.nc$"])
    #c = Crawl("http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/WHOTS/catalog.html", select=[".*OS_WHOTS_2012_D_TS4631m.nc$"])
    #c = Crawl("http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/PAPA/catalog.html", select=[".*OS_PAPA_2009PA003_D_CTD_10min.nc$"])
    #c = Crawl("http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/PAPA/catalog.html", select=[".*OS_PAPA_2009PA003_D_PSAL_1hr.nc$"])
    c = Crawl("http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/SOTS/catalog.html", select=[".*OS_SOTS_SAZ-15-2012_D_microcat-4422m.nc$"])
    urls = [s.get("url") for d in c.datasets for s in d.services if s.get("service").lower() == "opendap"]

    # First pass through urls matching OceanSITES pattern to collect platform names to get colors
    # Use OceanSITES naming convention for platform "OS_<platformName>_xxx_R|D_<type>.nc"
    pNames = set()
    for url in urls:
        pNames.add(url.split('/')[-1].split('.')[0].split('_')[1])

    pColors = {}
    for pName, color in zip(sorted(pNames), osl.getColor(len(pNames))) :
        pColors[pName] = color

    # Now loop again, this time loading the data 
    for url in urls:
        logger.info("Executing runMooringLoader with url = %s", url)
        if stride > 1:
            aName = url.split('/')[-1].split('.')[0] + '(stride=%d)' % stride
        else:
            aName = url.split('/')[-1].split('.')[0]
        pName = aName.split('_')[1]

        logger.debug("Instantiating Mooring_Loader for url = %s", url)
        ml = Mooring_Loader(
                url = url,
                campaignName = osl.campaignName,
                campaignDescription = osl.campaignDescription,
                dbAlias = osl.dbAlias,
                activityName = aName,
                activitytypeName = 'Mooring Deployment',
                platformName = pName,
                platformColor = pColors[pName],
                platformTypeName = 'mooring',
                stride = stride,
                startDatetime = osl.startDatetime,
                dataStartDatetime = None,
                endDatetime = osl.endDatetime)

        if url.find('OS_PAPA_2009PA003_D_CTD_10min') != -1:
            ml.include_names = ['TEMP']
        elif url.find('OS_PAPA_2009PA003_D_PSAL_1hr') != -1:
            ml.include_names = ['PSAL']
        elif url.find('OS_SOTS') != -1:
            ml.include_names = ['TEMP', 'PSAL']
            # DEPTH_CN_PR_PS_TE coordinate missing standard_name attribute
            ml.auxCoords = {}
            for v in ml.include_names:
                ml.auxCoords[v] = {'time': 'TIME', 'latitude': 'LATITUDE', 'longitude': 'LONGITUDE', 'depth': 'DEPTH_CN_PR_PS_TE'}
            # Only global attribute is 'cdm_data_type: Time-series'; monkey-patch the method
            Mooring_Loader.getFeatureType = lambda self: 'timeseries'

        else:
            ml.include_names = ['TEMP', 'PSAL']

        try:
            (nMP, path, parmCountHash, mind, maxd) = ml.process_data()
            logger.debug("Loaded Activity with name = %s", aName)
        except NoValidData, e:
            logger.warning(e)




# Execute the load
osl.process_command_line()

if osl.args.test:
    loadMoorings(osl, stride=100)

elif osl.args.optimal_stride:
    loadMoorings(osl, stride=10)

else:
    loadMoorings(osl, stride=osl.args.stride)

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
osl.addTerrainResources()

print "All Done."

