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
from DAPloaders import runMooringLoader
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

osl.parms = ['TEMP', 'PSAL']

# Start and end dates of None will load entire archive
osl.startDatetime = None
osl.endDatetime = None

def loadMoorings(loader, stride=1):
    '''
    Crawl the OceanSITES Mooring data TDS for OPeNDAP links and load into STOQS
    '''

    # http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/catalog.html
    ##c = Crawl("http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/catalog.html", select=[".*_TS.nc$"])
    c = Crawl("http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/MBARI/catalog.html", select=[".*_TS.nc$"])
    urls = [s.get("url") for d in c.datasets for s in d.services if s.get("service").lower() == "opendap"]
    # TODO: Replace with HSV rotation values
    colors = loader.colors.values()

    for url in urls:
        print url
        aName = url.split('/')[-1].split('.')[0]
        pName = aName.replace('_Time', '')
        if pName.find('-') != -1:
            logger.warn("Replacing '-' characters in platform name %s with '_'s", pName)
            pName = pName.replace('-', '_')

        logger.info("Executing runMooringLoader with url = %s", url)
        try:
            runMooringLoader(url, loader.campaignName, osl.campaignDescription, aName, pName, colors.pop(), 'mooring', 'Mooring Deployment', 
                            loader.parms, loader.dbAlias, stride, loader.startDatetime, loader.endDatetime, osl.grdTerrain)
        ##except Exception, e:
        except KeyError as e:
            logger.error('%s. Skipping this dataset.', e)


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

