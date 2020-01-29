#!/usr/bin/env python
'''
Loader for data from OceanSITES GDAC

Mike McCann
MBARI 28 October 2014
'''

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
import django
django.setup()

from loaders.OceanSITES import OSLoader
from thredds_crawler.crawl import Crawl

# Monkey-patch coards functions to accept non-standard time units
import coards
from coards import parse_units, parse_date
import timing

coards.parse_units = lambda units: parse_units(units.lower())
coards.parse_date = lambda date: parse_date(date.upper())

# Create loader with mesh globe for Spatial->3D view
osl = OSLoader('stoqs_oceansites', 'OS Moorings',
                        description = 'Mooring data from the OceanSITES GDAC',
                        x3dTerrains = {
                            'https://stoqs.mbari.org/x3d/Globe_1m_bath_10x/Globe_1m_bath_10x_scene.x3d': {
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
# Each tuple contains: <catalog>, <select_list>, <optimal_stride>
osl.dataSets = [
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/MBARI/catalog.html', ['.*M1.*_TS.nc$', '.*M2.*_TS.nc$'], 144),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/WHOTS/catalog.html', ['.*OS_WHOTS_2012_D_TS4631m.nc$'], 20),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/PAPA/catalog.html', ['.*OS_PAPA_2009PA003_D_CTD_10min.nc$'], 144),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/PAPA/catalog.html', ['.*OS_PAPA_2009PA003_D_PSAL_1hr.nc$'], 24),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/SOTS/catalog.html', ['.*OS_SOTS_SAZ-15-2012_D_microcat-4422m.nc$'], 12),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/MOVE1/catalog.html', ['.*D_MICROCAT-PART.*$'], 288),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/MOVE2/catalog.html', ['.*D_MICROCAT-PART.*$'], 288),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/MOVE3/catalog.html', ['.*D_MICROCAT-PART.*$'], 288),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/MOVE4/catalog.html', ['.*D_MICROCAT-PART.*$'], 288),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/MOVE5/catalog.html', ['.*D_MICROCAT-PART.*$'], 288),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/NOG/catalog.html', ['.*OS_NOG-1_201211_P_deepTS.nc$'], 10),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/IMOS-EAC/catalog.html', ['.*D_RDI-WORKHORSE-ADCP-615-m.nc$'], 10),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/IMOS-EAC/catalog.html', ['.*D_RDI-WORKHORSE-ADCP-422-m.nc$'], 10),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/IMOS-EAC/catalog.html', ['.*D_RDI-WORKHORSE-ADCP-83-m.nc$'], 10),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA_GRIDDED/PIRATA/catalog.html', ['.*_TVSM_dy.nc$'], 10),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/CCE1/catalog.html', ['.*_MICROCAT.nc$', '.*_SEACAT.nc$'], 50),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/CCE2/catalog.html', ['.*_MICROCAT.nc$', '.*_SEACAT.nc$'], 50),
    #('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/Stratus/catalog.html', ['.*_TS.nc$', '.*_M.nc$', '.*TS2000m.nc$'], 50),
    ('http://dods.ndbc.noaa.gov/thredds/catalog/oceansites/DATA/Stratus/catalog.html', ['.*_TS.nc$'], 50),  # Only _TS.nc are of GridType
    
               ]

# Execute the load
osl.process_command_line()

if osl.args.test:
    # Doubles the stide in the dataSets list
    osl.loadStationData()

elif osl.args.optimal_stride:
    # Third item in dataSets tuple will be used for the stride
    osl.loadStationData()

else:
    osl.loadStationData(stride=osl.args.stride)

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
osl.addTerrainResources()

print("All Done.")

