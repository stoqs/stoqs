#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Loader for IOOS Glider DAC

Mike McCann
MBARI 22 April 2014

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that IOOS and DAPloaders are found

import logging 
import datetime
from IOOS import IOOSLoader
from DAPloaders import runGliderLoader
from thredds_crawler.crawl import Crawl
import timing

logger = logging.getLogger('__main__')

il = IOOSLoader('stoqs_ioos_gliders', 'IOOS Gliders',
                        description = 'Glider data from the Integrated Ocean Observing System Glider DAC',
                        x3dTerrains = {
                            'https://stoqs.mbari.org/x3d/Globe_1m_bath_10x/Globe_1m_bath_10x_scene.x3d': {
                                'position': '14051448.48336 -15407886.51486 6184041.22775',
                                'orientation': '0.83940 0.33030 0.43164 1.44880',
                                'centerOfRotation': '0 0 0',
                                'VerticalExaggeration': '10',
                            }
                        },
                        grdTerrain = os.path.join(parentDir, 'Globe_1m_bath.grd')
               )

il.parms = ['temperature', 'salinity', 'density']

# Start and end dates of None will load entire archive
il.startDatetime = None
il.endDatetime = None

def loadGliders(loader, stride=1):
    '''
    Crawl the IOOS Glider TDS for OPeNDAP links of mbari files and load into STOQS
    '''

    glider_dac_url = 'https://data.ioos.us/gliders/thredds/catalog/catalog.xml'
    logger.info(f'Crawling {glider_dac_url}')
    c = Crawl(glider_dac_url, select=[".*mbari.*"], debug=il.args.verbose)
    urls = [s.get("url") for d in c.datasets for s in d.services if s.get("service").lower() == "opendap"]
    colors = list(loader.colors.values())

    for url in urls:
        aName = url.split('/')[-1].split('.')[0]
        pName = aName.replace('_Time', '')
        if pName.find('-') != -1:
            logger.warn("Replacing '-' characters in platform name %s with '_'s", pName)
            pName = pName.replace('-', '_')

        logger.info("Executing runGliderLoader with url = %s", url)
        try:
            runGliderLoader(url, loader.campaignName, il.campaignDescription, aName, pName, colors.pop(), 'glider', 'Glider Mission', 
                            loader.parms, loader.dbAlias, stride, loader.startDatetime, loader.endDatetime, il.grdTerrain)
        except Exception as e:
            logger.error('%s. Skipping this dataset.', e)


# Execute the load
il.process_command_line()

if il.args.test:
    loadGliders(il, stride=100)

elif il.args.optimal_stride:
    loadGliders(il, stride=10)

else:
    loadGliders(il, stride=il.args.stride)

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
il.addTerrainResources()

print("All Done.")

