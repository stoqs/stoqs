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

cl = CANONLoader('stoqs_canon_april2021', 'CANON-ECOHAB - April 2021',
                 description='April 2021 CANON campaign in Monterey Bay (CN21S)',
                 x3dTerrains={
                   'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                     'name': 'Monterey25_10x',
                     'position': '-2822317.31255 -4438600.53640 3786150.85474',
                     'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                     'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                     'VerticalExaggeration': '10',
                   },
                 },
                 grdTerrain=os.path.join(parentDir, 'Monterey25.grd')
                 )

startdate = datetime(2021, 4, 8)
enddate = datetime(2021, 4, 29)

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'

######################################################################
#  GLIDERS
######################################################################
# Glider data files from CeNCOOS thredds server
# L_662a updated parameter names in netCDF file
cl.l_662a_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line67/'
cl.l_662a_files = [ 'OS_Glider_L_662_20200615_TS.nc', ]
cl.l_662a_parms = ['temperature', 'salinity', 'fluorescence','oxygen']
cl.l_662a_startDatetime = startdate
cl.l_662a_endDatetime = enddate

# NPS_34 ##
cl.nps34_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/MBARI/'
cl.nps34_files = [ 'OS_Glider_NPS_G34_20210414_TS.nc' ]
cl.nps34_parms = ['TEMP', 'PSAL', 'FLU2', 'OXYG']
cl.nps34_startDatetime = startdate
cl.nps34_endDatetime = enddate

# NPS_29 ##
cl.nps29_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/MBARI/'
cl.nps29_files = [ 'OS_Glider_NPS_G29_20210209_TS.nc' ]
cl.nps29_parms = ['TEMP', 'PSAL', 'FLU2', 'OXYG']
cl.nps29_startDatetime = startdate
cl.nps29_endDatetime = enddate

######################################################################
# Wavegliders
######################################################################
# WG Tex - All instruments combined into one file - one time coordinate
##cl.wg_tex_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/WG_Tex/final/'
##cl.wg_tex_files = [ 'WG_Tex_all_final.nc' ]
##cl.wg_tex_parms = [ 'wind_dir', 'wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal', 'density', 'bb_470', 'bb_650', 'chl' ]
##cl.wg_tex_startDatetime = startdate
##cl.wg_tex_endDatetime = enddate

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
  '202008/OS_M1_20200825hourly_CMSTV.nc', 
  '202008/m1_hs2_0m_20200825.nc' ]
cl.m1_parms = [
  'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
  'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
  'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR',
  'bb470', 'bb676', 'fl676'
]
cl.m1_startDatetime = startdate
cl.m1_endDatetime = enddate

# Mooring 0A1
cl.oa1_base = 'http://dods.mbari.org/opendap/data/oa_moorings/deployment_data/OA1/202010/'
cl.oa1_files = [
               'realTime/OA1_202010.nc'
               ]
cl.oa1_parms = [
               'wind_dir', 'avg_wind_spd', 'atm_press', 'air_temp', 'water_temp',
               'sal', 'O2_conc', 'chl', 'pCO2_water', 'pCO2_air', 'pH',
               ]
cl.oa1_startDatetime = startdate
cl.oa1_endDatetime = enddate

# Mooring 0A2
cl.oa2_base = 'http://dods.mbari.org/opendap/data/oa_moorings/deployment_data/OA2/201912/'
cl.oa2_files = [
               'realTime/OA2_201912.nc'
               ]
cl.oa2_parms = [
               'wind_dir', 'avg_wind_spd', 'atm_press', 'air_temp', 'water_temp',
               'sal', 'O2_conc', 'chl', 'pCO2_water', 'pCO2_air', 'pH',
               ]
cl.oa2_startDatetime = startdate
cl.oa2_endDatetime = enddate

######################################################################
#  WESTERN FLYER
######################################################################
# UCTD
cl.wfuctd_base = cl.dodsBase + 'Other/routine/Platforms/Ships/WesternFlyer/uctd/'
cl.wfuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.wfuctd_files = [
                  'CN21Sm01.nc',
                  'CN21Sm02.nc',
                  'CN21Sm03.nc',
                  'CN21Sm04.nc',
                  'CN21Sm05.nc',
                  'CN21Sm06.nc',
                  ]

# PCTD
cl.wfpctd_base = cl.dodsBase + 'Other/routine/Platforms/Ships/WesternFlyer/pctd/'
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.wfpctd_files = [
        'CN21SC01.nc',
        'CN21SC02.nc',
        'CN21SC03.nc',
        'CN21SC04.nc',
        'CN21SC05.nc',
        'CN21SC06.nc',
        'CN21SC07.nc',
        'CN21SC08.nc',
        'CN21SC09.nc',
        'CN21SC10.nc',
        'CN21SC11.nc',
        'CN21SC12.nc',
        'CN21SC13.nc',
        'CN21SC14.nc',
        'CN21SC15.nc',
        'CN21SC16.nc',
        'CN21SC17.nc',
        'CN21SC18.nc',
        'CN21SC19.nc',
        'CN21SC20.nc',
        'CN21SC21.nc',
        'CN21SC22.nc',
        'CN21SC23.nc',
        'CN21SC24.nc',
        'CN21SC25.nc',
        'CN21SC26.nc',
        'CN21SC27.nc',
        'CN21SC28.nc',
        'CN21SC29.nc',
                  ]

# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.stride = 10
elif cl.args.stride:
    cl.stride = cl.args.stride

# Test correction of Sample name for leaked ESP Cartridges and spare used
##cl.makai_base = ' http://dods.mbari.org/opendap/data/lrauv/makai/missionlogs/2021/20210420_20210426/20210421T033242'
##cl.makai_files = ['202104210332_202104211941_2S_scieng.nc']
##cl.makai_parms = ['temperature']
##cl.loadLRAUV('makai', startdate, enddate, build_attrs=False)
##sys.exit()

lrauv_start = datetime(2021, 4, 11)
lrauv_end = datetime(2021, 4, 29)
cl.loadLRAUV('brizo', lrauv_start, lrauv_end)
cl.loadLRAUV('pontus', lrauv_start, lrauv_end)
cl.loadLRAUV('makai', lrauv_start, lrauv_end)
cl.loadLRAUV('daphne', lrauv_start, lrauv_end)

cl.loadM1()
cl.load_oa1()
cl.load_oa2()
cl.load_NPS29()
cl.load_NPS34()
cl.load_wg_Tiny()
cl.load_wg_Hansen()

# Realtime LRAUV loads - to be executed during the Campaign
##lrauv_parms = ['chlorophyll', 'temperature']
##cl.loadLRAUV('brizo', lrauv_start, lrauv_end, critSimpleDepthTime=0.1, sbd_logs=True,
##             parameters=lrauv_parms)
##cl.loadLRAUV('pontus', lrauv_start, lrauv_end, critSimpleDepthTime=0.1, sbd_logs=True,
##             parameters=lrauv_parms)
##cl.loadLRAUV('makai', lrauv_start, lrauv_end, critSimpleDepthTime=0.1, sbd_logs=True,
##             parameters=lrauv_parms)
##cl.loadLRAUV('daphne', lrauv_start, lrauv_end, critSimpleDepthTime=0.1, sbd_logs=True,
##             parameters=lrauv_parms)

cl.loadDorado(startdate, enddate, build_attrs=True)

cl.loadWFuctd()
cl.loadWFpctd()

##cl.loadSubSamples() 

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")
