#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''
Master loader for all CANON activities in September 2010

Mike McCann
MBARI 22 April 2012
'''

import os
import sys
parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found
from CANON import CANONLoader
from datetime import datetime
import timing

# Assign input data sources
cl = CANONLoader('stoqs_september2010', 'CANON - September 2010',
                    description = 'ESP Drift with Dorado circling outside Monterey Bay',
                    x3dTerrains = {
                        'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                            'position': '-2822317.31255 -4438600.53640 3786150.85474',
                            'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                            'centerOfRotation': '-2711557.94 -4331414.32 3801353.46',
                            'VerticalExaggeration': '10',
                            'speed': '.1',
                        }
                    },
                    grdTerrain = os.path.join(parentDir, 'Monterey25.grd')
                )

# AUV
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
cl.dorado_files = [ 'Dorado389_2010_257_01_258_04_decim.nc',
                    'Dorado389_2010_258_05_258_08_decim.nc',
                    'Dorado389_2010_259_00_259_03_decim.nc',
                    'Dorado389_2010_260_00_260_00_decim.nc',
                    'Dorado389_2010_261_00_261_00_decim.nc',
                  ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                    'fl700_uncorr', 'salinity', 'biolume',
                    'sepCountList', 'mepCountList',
                    'roll', 'pitch', 'yaw',
                  ]
# Moorings
cl.m1_startDatetime = datetime(2010, 9, 8)
cl.m1_endDatetime = datetime(2010, 9, 21)
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/200910/'
cl.m1_files = [ 
                'OS_M1_20091020hourly_CMSTV.nc',
                'm1_hs2_20091020.nc',
                ] 
cl.m1_parms = [
                'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
                'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
                'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR',
                'bb470', 'bb676', 'fl676'
              ]

cl.m2_startDatetime = datetime(2010, 9, 8)
cl.m2_endDatetime = datetime(2010, 9, 21)
cl.m2_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m2/201004/'
cl.m2_files = [ 
                'OS_M2_20100402hourly_CMSTV.nc',
                'm2_hs2_20100402.nc',
                ] 

cl.m2_parms = [ # No ADCP data from M2 in September 2010
                'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
                'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR',
                'bb470', 'bb676', 'fl676'
              ]


# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadDorado(stride=100)
    cl.loadM1(stride=10)
    cl.loadM2(stride=10)

elif cl.args.optimal_stride:
    cl.loadDorado(stride=2)
    cl.loadM1(stride=2)
    cl.loadM2(stride=2)

else:
    cl.stride = cl.args.stride 
    cl.loadDorado()
    cl.loadM1()
    cl.loadM2()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

