#!/usr/bin/env python
'''
LRAUV and other deployments during ECOHAB April 2023 in Monterey Bay

Mike McCann, Duane Edgington, Danelle Cline
MBARI 31 March 2023
'''

import os
import sys

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
from datetime import datetime
import timing

cl = CANONLoader('stoqs_ecohab_april2023', 'ECOHAB - April 2023',
                    description = 'Harmful Algal Bloom (HAB) ecology research in Monterey Bay',
                    x3dTerrains = {
                       'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                         'position': '-2822317.31255 -4438600.53640 3786150.85474',
                         'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                         'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                         'VerticalExaggeration': '10',
                       },
                       'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_e10_lat_rev.glb': {
                         'name': 'Monterey25_e10',
                         'position': '-2709340.15630 3838759.47032 -4315928.63232',
                         'orientation': '-0.92531 0.16085 0.34340 1.48161',
                         'centerOfRotation': '-2698376.20956 3816324.15548 -4328209.99402',
                         'zNear': '10000.0',
                         'zFar': '30000000.0',
                         'VerticalExaggeration': '10',
                       },
                    },
                    grdTerrain = os.path.join(parentDir, 'Monterey25.grd')
                 )

# Overall Campaign times used for LRAUV loads
sdate = datetime(2023, 4, 3)
edate = datetime(2023, 4, 30)

# M1 Mooring
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/'
cl.m1_files = [
    '202207/OS_M1_20220718hourly_CMSTV.nc',
    '202207/m1_hs2_1m_20220718.nc',
              ]
cl.m1_parms = [
    'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
    'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
    'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR',
    'bb470', 'bb676', 'fl676',
]
cl.m1_startDatetime = datetime(2023, 3, 31)
cl.m1_endDatetime = datetime(2023, 4, 25)

# WG Tiny - All instruments combined into one file - one time coordinate
# Liquid Robotics changed their data portal - usual data products not available as of 11 April 2023
cl.wg_Tiny_base = 'http://dods.mbari.org/opendap/data/waveglider/deployment_data/'
cl.wg_Tiny_files = [
                      'wgTiny/20230302/realTime/20230302.nc',
                   ]


cl.wg_Tiny_parms = [ 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal',  'bb_470', 'bb_650', 'chl',
                    'beta_470', 'beta_650', 'pCO2_water', 'pCO2_air', 'pH', 'O2_conc' ]
cl.wg_Tiny_depths = [ 0 ]
cl.wg_Tiny_startDatetime = datetime(2023, 3, 10)
cl.wg_Tiny_endDatetime = edate


cl.process_command_line()

if cl.args.test:
    cl.stride = 100
elif cl.args.stride:
    cl.stride = cl.args.stride
else:
    cl.stride = 1

cl.loadM1()
##cl.load_wg_Tiny()

# For testing a specific file
##cl.daphne_base = 'http://dods.mbari.org/thredds/dodsC/LRAUV/daphne/realtime/sbdlogs/2023/'
##cl.daphne_files = ['202304/20230403T164827/shore_i.nc', ]
##cl.daphne_parms = ['bin_median_sea_water_salinity', 'bin_median_sea_water_temperature', 'bin_median_mass_concentration_of_chlorophyll_in_sea_water']
##cl.loadLRAUV('daphne', sdate, edate, critSimpleDepthTime=0.1, sbd_logs=True, build_attrs=False)

# brizo/missionlogs/2023/20230411_20230420/20230411T192116/syslog, resp.status_code = 404
##cl.brizo_base = 'http://dods.mbari.org/thredds/dodsC/LRAUV/brizo/missionlogs/2023/20230411_20230420/20230411T192116/'
##cl.brizo_files = ['202304111921_202304112324_2S_scieng.nc', ]
##cl.brizo_parms = ['temperature']
##cl.loadLRAUV('brizo', sdate, edate, critSimpleDepthTime=0.1, build_attrs=False)
for lrauv in ('galene', 'pontus', 'daphne', 'makai', 'brizo'):
    # Realtime
    cl.loadLRAUV(lrauv, sdate, edate, critSimpleDepthTime=0.1, sbd_logs=True)
    # Delayed mode
    cl.loadLRAUV(lrauv, sdate, edate, critSimpleDepthTime=0.1)

##cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

