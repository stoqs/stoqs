#!/usr/bin/env python
'''
Load all long time series MBARI OASIS Mooring data

Mike McCann
MBARI 4 October 2018
'''

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
import django
django.setup()

from loaders.CANON import CANONLoader
import timing

# Create loader with mesh globe for Spatial->3D view
cl = CANONLoader('stoqs_oasis', 'MBARI OASIS Moorings',
                        description = 'Quality Controlled data from MBARI Moorings M0, M1, M2, M3, and M4',
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
cl.startDatetime = None
cl.endDatetime = None


cl.m1_base = 'http://dods.mbari.org:80/opendap/data/OASISdata/netcdf/'
cl.m1_files = [ 'dailyAveragedM1.nc' ]
cl.m1_parms = [
 'AIR_PRESS_DAY',
 'AIR_TEMPERATURE_DAY',
 'CONDUCTIVITY_DAY',
 'ECHO_INTENSITY_BEAM1_DAY',
 'ECHO_INTENSITY_BEAM2_DAY',
 'ECHO_INTENSITY_BEAM3_DAY',
 'ECHO_INTENSITY_BEAM4_DAY',
 'GPS_LATITUDE_DAY',
 'GPS_LONGITUDE_DAY',
 'PRESSURE_DAY',
 'RELATIVE_HUMIDITY_DAY',
 'SALINITY_DAY',
 'TEMPERATURE_DAY',
 'U_COMPONENT_DAY',
 'U_COMPONENT_UNCORR_DAY',
 'V_COMPONENT_DAY',
 'V_COMPONENT_UNCORR_DAY',
 'WIND_U_COMPONENT_DAY',
 'WIND_V_COMPONENT_DAY',
]


# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.stride = 100
elif cl.args.stride:
    cl.stride = cl.args.stride

cl.loadM1()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

