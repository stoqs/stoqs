#!/usr/bin/env python
'''
Master loader for CANON April (Spring) 2021 Campaign
'''

import os
import sys
from datetime import datetime

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)

from CANON import CANONLoader
import timing

cl = CANONLoader('stoqs_canon_october2022', 'CANON - October 2022',
                 description='October 2022 CANON campaign in Monterey Bay',
                 x3dTerrains={
                   'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                     'name': 'Monterey25_10x',
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
                 grdTerrain=os.path.join(parentDir, 'Monterey25.grd')
                 )

startdate = datetime(2022, 10, 7)
enddate = datetime(2022, 10, 20)

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'

######################################################################
#  GLIDERS
######################################################################
# Glider data files from CeNCOOS thredds server
# L_662a updated parameter names in netCDF file
cl.l_662a_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line67/'
cl.l_662a_files = [ 'OS_Glider_L_662_20220726_TS.nc', ]
cl.l_662a_parms = ['temperature', 'salinity', 'fluorescence','oxygen']
# Just the time period its in Monterey Bay
cl.l_662a_startDatetime = datetime(2022, 10, 9)
cl.l_662a_endDatetime = datetime(2022, 10, 15)

######################################################################
# Wavegliders
######################################################################
# WG Hansen - All instruments combined into one file - one time coordinate
cl.wg_Hansen_base = 'http://dods.mbari.org/opendap/data/waveglider/deployment_data/'
cl.wg_Hansen_files = [
                        'wgHansen/20210409/realTime/20210409.nc'
                     ]

cl.wg_Hansen_parms = [ 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp_float', 'sal_float',  'water_temp_sub',
                     'sal_sub', 'bb_470', 'bb_650', 'chl', 'beta_470', 'beta_650', 'pH', 'O2_conc_float','O2_conc_sub' ] # two ctds (_float, _sub), no CO2
cl.wg_Hansen_depths = [ 0 ]
cl.wg_Hansen_startDatetime = startdate
cl.wg_Hansen_endDatetime = enddate

# WG Tiny - All instruments combined into one file - one time coordinate
cl.wg_Tiny_base = 'http://dods.mbari.org/opendap/data/waveglider/deployment_data/'
cl.wg_Tiny_files = [
                      'wgTiny/20210408/realTime/20210408.nc'
                   ]


cl.wg_Tiny_parms = [ 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal',  'bb_470', 'bb_650', 'chl',
                    'beta_470', 'beta_650', 'pCO2_water', 'pCO2_air', 'pH', 'O2_conc' ]
cl.wg_Tiny_depths = [ 0 ]
cl.wg_Tiny_startDatetime = startdate
cl.wg_Tiny_endDatetime = enddate

######################################################################
#  MOORINGS
######################################################################
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/'
cl.m1_files = [
  '202207/OS_M1_20220718hourly_CMSTV.nc',
  '202207/m1_hs2_1m_20220718.nc' ]
cl.m1_parms = [
  'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
  'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
  'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR',
  'bb470', 'bb676', 'fl676'
]
cl.m1_startDatetime = startdate
cl.m1_endDatetime = enddate



# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.stride = 10
elif cl.args.stride:
    cl.stride = cl.args.stride

cl.loadL_662a()
##cl.loadLRAUV('makai', startdate, enddate, sbd_logs=True)
cl.loadLRAUV('makai', startdate, enddate)
##cl.loadLRAUV('daphne', startdate, enddate, sbd_logs=True)
cl.loadLRAUV('daphne', startdate, enddate)
cl.loadLRAUV('pontus', startdate, enddate, sbd_logs=True)
cl.loadLRAUV('pontus', startdate, enddate)
cl.loadM1()
#cl.load_wg_Tiny()
#cl.load_wg_Hansen()
cl.loadDorado(startdate, enddate, build_attrs=True)

##cl.loadSubSamples() 

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")
