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

from OceanSITES import OSLoader
from thredds_crawler.crawl import Crawl

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
               )

# Start and end dates of None will load entire archive
osl.startDatetime = None
osl.endDatetime = None

# Look in each sub-catalog for the data files as it's faster than searching from the root catalog
osl.dataSets = [
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/MBARI/catalog.html', ['.*M1.*_TS.nc$', '.*M2.*_TS.nc$']),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/WHOTS/catalog.html', ['.*OS_WHOTS_2012_D_TS4631m.nc$']),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/PAPA/catalog.html', ['.*OS_PAPA_2009PA003_D_CTD_10min.nc$']),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/PAPA/catalog.html', ['.*OS_PAPA_2009PA003_D_PSAL_1hr.nc$']),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/SOTS/catalog.html', ['.*OS_SOTS_SAZ-15-2012_D_microcat-4422m.nc$']),
               ]

# Execute the load
osl.process_command_line()

if osl.args.test:
    osl.loadStationData(stride=100)

elif osl.args.optimal_stride:
    osl.loadStationData(stride=10)

else:
    osl.loadStationData(stride=osl.args.stride)

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
osl.addTerrainResources()

print "All Done."

