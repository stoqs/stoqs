#!/usr/bin/env python
__author__ = 'Mike McCann,Duane Edgington,Danelle Cline'
__copyright__ = '2018'
__license__ = 'GPL v3'
__contact__ = 'duane at mbari.org'

__doc__ = '''

Master loader for all CANON May-June Campaign 2019

Mike McCann, Duane Edgington, Danelle Cline
MBARI 22 May 2019

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime  # needed for glider data

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
import timing

cl = CANONLoader('stoqs_canon_may2019', 'CANON - May 2019',
                 description='May 2019 coordinated campaign observations in Monterey Bay',
                 x3dTerrains={
                   'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                     'position': '-2822317.31255 -4438600.53640 3786150.85474',
                     'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                     'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                     'VerticalExaggeration': '10',
                   },
                   'https://stoqs.mbari.org/x3d/Monterey25_1x/Monterey25_1x_src_scene.x3d': {
                     'name': 'Monterey25_1x',
                     'position': '-2822317.31255 -4438600.53640 3786150.85474',
                     'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                     'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                     'VerticalExaggeration': '1',
                   },
                 },
                 grdTerrain=os.path.join(parentDir, 'Monterey25.grd')
                 )

# Set start and end dates for all loads from sources that contain data
# beyond the temporal bounds of the campaign
#
startdate = datetime.datetime(2019, 5, 20)  # Fixed start.May 20, 2019
enddate = datetime.datetime(2019, 6, 8)  # Fixed end. June 8, 2019.

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'


#####################################################################
#  DORADO
#####################################################################

# Use the attributes built by loadDorad() using startdate and enddate


#####################################################################
#  LRAUV
#####################################################################

# Load netCDF files produced (binned, etc.) by Danelle Cline
# These binned files are created with the makeLRAUVNetCDFs.sh script in the
# toNetCDF directory. You must first edit and run that script once to produce
# the binned files before this will work

# Use the default parameters provided by loadLRAUV() calls below


######################################################################
#  GLIDERS
######################################################################
# Glider data files from CeNCOOS thredds server
# L_662a updated parameter names in netCDF file
cl.l_662a_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line67/'
cl.l_662a_files = [
                   'OS_Glider_L_662_20190328_TS.nc',
                  ]
cl.l_662a_parms = ['temperature', 'salinity', 'fluorescence','oxygen']
cl.l_662a_startDatetime = startdate
cl.l_662a_endDatetime = enddate

# NPS_34a updated parameter names in netCDF file
## The following loads decimated subset of data telemetered during deployment
cl.nps34a_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/MBARI/'
cl.nps34a_files = [ 'OS_Glider_NPS_G34_20180514_TS.nc' ]
cl.nps34a_parms = ['temperature', 'salinity','fluorescence']
cl.nps34a_startDatetime = startdate
cl.nps34a_endDatetime = enddate

# NPS_29 ##
cl.nps29_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/MBARI/'
cl.nps29_files = [ 'OS_Glider_NPS_G29_20190528_TS.nc' ]
cl.nps29_parms = ['TEMP', 'PSAL', 'FLU2', 'OXYG']
cl.nps29_startDatetime = startdate
cl.nps29_endDatetime = enddate

# Slocum Teledyne nemesis Glider
## from ioos site ## these files proved to be not compatible with python loader
## cl.slocum_nemesis_base = 'https://data.ioos.us/gliders/thredds/dodsC/deployments/mbari/Nemesis-20170412T0000/'
## cl.slocum_nemesis_files = [ 'Nemesis-20170412T0000.nc3.nc' ]
##   from cencoos directory, single non-aggregated files
cl.slocum_nemesis_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/MBARI/nemesis_201808/'

cl.slocum_nemesis_files = [
                           'nemesis_20180912T155836_rt0.nc', 
                          ] 
cl.slocum_nemesis_startDatetime = startdate
cl.slocum_nemesis_endDatetime = enddate


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
                   'wgHansen/20190522/realTime/20190522.nc',
                  ]

cl.wg_Hansen_parms = [ 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp_float', 'sal_float',  'water_temp_sub',
                     'sal_sub', 'bb_470', 'bb_650', 'chl', 'beta_470', 'beta_650', 'pH', 'O2_conc_float','O2_conc_sub' ] # two ctds (_float, _sub), no CO2
cl.wg_Hansen_depths = [ 0 ]
cl.wg_Hansen_startDatetime = startdate
cl.wg_Hansen_endDatetime = enddate


# WG Sparky - All instruments combined into one file - one time coordinate
cl.wg_Sparky_base = 'http://dods.mbari.org/opendap/data/waveglider/deployment_data/'
cl.wg_Sparky_files = [
                      'wgSparky/20180905/QC/20180905_QC.nc',
                     ]

cl.wg_Sparky_parms = [ 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp_float', 'sal_float',  'water_temp_sub', 
                     'sal_sub', 'bb_470', 'bb_650', 'chl', 'beta_470', 'beta_650', 'pH', 'O2_conc' ] # two ctds (_float, _sub), no CO2
cl.wg_Sparky_depths = [ 0 ]
cl.wg_Sparky_startDatetime = startdate
cl.wg_Sparky_endDatetime = enddate

# WG Tiny - All instruments combined into one file - one time coordinate
cl.wg_Tiny_base = 'http://dods.mbari.org/opendap/data/waveglider/deployment_data/'
cl.wg_Tiny_files = [
                      'wgTiny/20190513/realTime/20190513.nc',
                   ]


cl.wg_Tiny_parms = [ 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal',  'bb_470', 'bb_650', 'chl',
                    'beta_470', 'beta_650', 'pCO2_water', 'pCO2_air', 'pH', 'O2_conc' ]
cl.wg_Tiny_depths = [ 0 ]
cl.wg_Tiny_startDatetime = startdate
cl.wg_Tiny_endDatetime = enddate

# WG OA - All instruments combined into one file - one time coordinate
##cl.wg_oa_base = cl.dodsBase + 'CANON/2015_OffSeason/Platforms/Waveglider/wgOA/'
##cl.wg_oa_files = [ 'Sept_2013_OAWaveglider_final.nc' ]
##cl.wg_oa_parms = [ 'distance', 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal', 'O2_conc',
##                   'O2_sat', 'beta_470', 'bb_470', 'beta_700', 'bb_700', 'chl', 'pCO2_water', 'pCO2_air', 'pH' ]
##cl.wg_oa_startDatetime = startdate
##cl.wg_oa_endDatetime = enddate

######################################################################
#  MOORINGS
######################################################################
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/'
cl.m1_files = [
  '201808/OS_M1_20180806hourly_CMSTV.nc',]
cl.m1_parms = [
  'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
  'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
  'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR'
]

cl.m1_startDatetime = startdate
cl.m1_endDatetime = enddate

# Mooring 0A1
cl.oa1_base = 'http://dods.mbari.org/opendap/data/oa_moorings/deployment_data/OA1/201810/realTime/'
cl.oa1_files = [
               'OA1_201810.nc'
               ]
cl.oa1_parms = [
               'wind_dir', 'avg_wind_spd', 'atm_press', 'air_temp', 'water_temp',
               'sal', 'O2_conc', 'chl', 'pCO2_water', 'pCO2_air', 'pH',
               ]
cl.oa1_startDatetime = startdate
cl.oa1_endDatetime = enddate

# Mooring 0A2
cl.oa2_base = 'http://dods.mbari.org/opendap/data/oa_moorings/deployment_data/OA2/201812/'
cl.oa2_files = [
               'realTime/OA2_201812.nc'
               ]
cl.oa2_parms = [
               'wind_dir', 'avg_wind_spd', 'atm_press', 'air_temp', 'water_temp',
               'sal', 'O2_conc', 'chl', 'pCO2_water', 'pCO2_air', 'pH',
               ]
cl.oa2_startDatetime = startdate
cl.oa2_endDatetime = enddate


######################################################################
#  RACHEL CARSON: Jan 2017 --
######################################################################
# UCTD
cl.rcuctd_base = cl.dodsBase + 'Other/routine/Platforms/Ships/RachelCarson/uctd/'
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.rcuctd_files = [
#                  '00917plm01.nc',
                  ]

# PCTD
cl.rcpctd_base = cl.dodsBase + 'Other/routine/Platforms/Ships/RachelCarson/pctd/'
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.rcpctd_files = [
#                  '00917c01.nc', 
                  ]

######################################################################
#  WESTERN FLYER: Apr 2017 --
######################################################################
# UCTD
cl.wfuctd_base = cl.dodsBase + 'Other/routine/Platforms/Ships/WesternFlyer/uctd/'
cl.wfuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.wfuctd_files = [
                  'CN19SM01.nc',
                  'CN19SM02.nc',
                  'CN19SM03.nc',
                  'CN19SM04.nc',
                  'CN19SM05.nc',
                  'CN19SM06.nc',
                  ]

# PCTD
cl.wfpctd_base = cl.dodsBase + 'Other/routine/Platforms/Ships/WesternFlyer/pctd/'
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.wfpctd_files = [
                  'CN19SC01.nc',
                  'CN19SC02.nc',
                  'CN19SC03.nc',
                  'CN19SC04.nc',
                  'CN19SC05.nc',
                  'CN19SC06.nc',
                  'CN19SC07.nc',
                  'CN19SC08.nc',
                  'CN19SC09.nc',
                  'CN19SC10.nc',
                  'CN19SC11.nc',
                  'CN19SC12.nc',
                  'CN19SC13.nc',
                  'CN19SC14.nc',
                  'CN19SC15.nc',
                  'CN19SC16.nc',
                  'CN19SC17.nc',
                  'CN19SC18.nc',
                  'CN19SC19.nc',
                  'CN19SC20.nc',
                  'CN19SC21.nc',
                  'CN19SC22.nc',
                  'CN19SC23.nc',
                  'CN19SC24.nc',
                  'CN19SC25.nc',
                  'CN19SC26.nc',
                  'CN19SC27.nc',
                  'CN19SC28.nc',
                  'CN19SC29.nc',
                  'CN19SC30.nc',
                  'CN19SC31.nc',
                  'CN19SC32.nc',
                  'CN19SC33.nc',
                  'CN19SC34.nc',
                  'CN19SC35.nc',
                  'CN19SC36.nc',
                  'CN19SC37.nc',
                  'CN19SC38.nc',
                  'CN19SC39.nc',                  
                  ]

# DEIMOS
cl.deimos_base = cl.dodsBase + 'Other/routine/Platforms/DEIMOS/netcdf/'
cl.deimos_parms = [ 'Sv_mean' ]
cl.deimos_files = [ 'deimos-2019-CANON-Spring.nc' ]

###################################################################################################
# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/
#   copied to local BOG_Data/N18F
###################################################################################################
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data/CN18F/CN18F/')
cl.subsample_csv_files = [
                         'STOQS_CN19S_CARBON_GFF.csv',
                         'STOQS_CN19S_ALK.csv',
                         'STOQS_CN19S_TCO2.csv',
                         'STOQS_CN19S_TRANSBEAM.csv',
                         'STOQS_CN19S_COND2.csv',
                         'STOQS_CN19S_TEMP2.csv',
                         'STOQS_CN19S_SAL2.csv',
                         'STOQS_CN19S_OXY_PS.csv',
                         'STOQS_CN19S_OXY_ML.csv',
                         'STOQS_CN19S_NH4.csv',
                         'STOQS_CN19S_PHAEO_5U.csv',
                         'STOQS_CN19S_CHL_1U.csv',
                         'STOQS_CN19S_CHL_5U.csv',
                         'STOQS_CN19S_O2.csv',
                         'STOQS_CN19S_PHAEO_1U.csv',
                         'STOQS_CN19S_TRANSMISS.csv',
                         'STOQS_CN19S_CHLA.csv',
                         'STOQS_CN19S_FLUOR.csv',
                         'STOQS_CN19S_CONDUCT.csv',
                         'STOQS_CN19S_SIG_T.csv',
                         'STOQS_CN19S_SAL.csv',
                         'STOQS_CN19S_TMP.csv',
                         'STOQS_CN19S_PHAEO_GFF.csv',
                         'STOQS_CN19S_CHL_GFF.csv',                          
                         ]

# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.stride = 100
elif cl.args.stride:
    cl.stride = cl.args.stride


# Lot's of debugging in this Campaign - keep these lines here commented out (to be used if problems crop up)
##startdate = datetime.datetime(2019, 5, 23, 18)
##enddate = datetime.datetime(2019, 5, 24, 1)
##cl.daphne_base = 'http://dods.mbari.org/opendap/data/lrauv/daphne/missionlogs/2019/20190528_20190606/20190529T194310'
##cl.daphne_base = 'http://dods.mbari.org/opendap/data/lrauv/daphne/missionlogs/2019/20190528_20190606/20190529T194310'
##cl.daphne_base = 'http://dods.mbari.org/opendap/data/lrauv/daphne/missionlogs/2019/20190528_20190606/20190601T142912'
##cl.daphne_base = 'http://dods.mbari.org/opendap/data/lrauv/daphne/missionlogs/2019/20190528_20190606/20190602T025849'
##cl.daphne_base = 'http://dods.mbari.org/opendap/data/lrauv/daphne/missionlogs/2019/20190528_20190606/20190529T115150'
##cl.daphne_base = 'http://dods.mbari.org/opendap/data/lrauv/daphne/missionlogs/2019/20190528_20190606/20190604T233636'
##cl.daphne_base = 'http://dods.mbari.org/opendap/data/lrauv/daphne/missionlogs/2019/20190528_20190606/20190602T170120/'
##cl.daphne_files = ['201905291943_201905300048_2S_scieng.nc']
##cl.daphne_files = ['201905291943_201905300048_2S_scieng.nc']
##cl.daphne_files = ['201906011429_201906020258_2S_scieng.nc']
##cl.daphne_files = ['201906020259_201906021701_2S_scieng.nc']
##cl.daphne_files = ['201905291151_201905291713_2S_scieng.nc']
##cl.daphne_files = ['201906042336_201906052235_2S_scieng.nc']
##cl.daphne_files = ['201906021701_201906030901_2S_scieng.nc']
##cl.daphne_parms = ['temperature']
##cl.loadLRAUV('daphne', startdate, enddate, build_attrs=False)
##cl.makai_base = 'http://dods.mbari.org/opendap/data/lrauv/makai/missionlogs/2019/20190528_20190530/20190528T183638'
##cl.makai_base = 'http://dods.mbari.org/opendap/data/lrauv/makai/missionlogs/2019/20190528_20190530/20190529T081339'
##cl.makai_base = 'http://dods.mbari.org/opendap/data/lrauv/makai/missionlogs/2019/20190528_20190530/20190530T005113'
##cl.makai_files = ['201905281836_201905281946_2S_scieng.nc']
##cl.makai_files = ['201905290813_201905300051_2S_scieng.nc']
##cl.makai_files = ['201905300051_201905301829_2S_scieng.nc']
##cl.makai_parms = ['temperature']
##cl.loadLRAUV('makai', startdate, enddate, build_attrs=False)
##sys.exit()

cl.loadM1()  
cl.loadDEIMOS(startdate, enddate)
cl.loadL_662a()
cl.load_NPS29()   
##cl.load_NPS34a() ## not in this campaign
##cl.load_slocum_nemesis() ## not in this campaign
cl.load_wg_Tiny()
##cl.load_wg_Sparky() ## not in this campaign
cl.load_wg_Hansen() ## new for this campaign 
#cl.load_oa1()  ## no data during this campaign
cl.load_oa2() 
#cl.loadDorado(startdate, enddate, build_attrs=True) ## waiting for first data
cl.loadLRAUV('makai', startdate, enddate)
cl.loadLRAUV('daphne', startdate, enddate)
cl.loadLRAUV('tethys', startdate, enddate)
#cl.loadRCuctd() ## waiting for first data
#cl.loadRCpctd() ## waiting for first data
cl.loadWFuctd() 
cl.loadWFpctd() 

cl.loadSubSamples() 

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

