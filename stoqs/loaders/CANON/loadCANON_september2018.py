#!/usr/bin/env python
__author__ = 'Mike McCann,Duane Edgington,Danelle Cline'
__copyright__ = '2018'
__license__ = 'GPL v3'
__contact__ = 'duane at mbari.org'

__doc__ = '''

Master loader for all CANON May-June Campaign 2018

Mike McCann, Duane Edgington, Danelle Cline
MBARI 15 May 2018

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

cl = CANONLoader('stoqs_canon_september2018', 'CANON - September 2018',
                 description='September 2018 campaign observations in Monterey Bay',
                 x3dTerrains={
                   'http://dods.mbari.org/terrain/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                     'position': '-2822317.31255 -4438600.53640 3786150.85474',
                     'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                     'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                     'VerticalExaggeration': '10',
                   },
                   'http://stoqs.mbari.org/x3d/Monterey25_1x/Monterey25_1x_src_scene.x3d': {
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
startdate = datetime.datetime(2018, 8, 24)  # Fixed start. Aug 30, 2018
enddate = datetime.datetime(2018, 9, 11)  # Fixed end. September 12, 2018.

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
cl.l_662a_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662a_files = [
                   'OS_Glider_L_662_20180816_TS.nc',
                  ]
cl.l_662a_parms = ['temperature', 'salinity', 'fluorescence','oxygen']
cl.l_662a_startDatetime = startdate
cl.l_662a_endDatetime = enddate

# NPS_34a updated parameter names in netCDF file
## The following loads decimated subset of data telemetered during deployment
cl.nps34a_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.nps34a_files = [ 'OS_Glider_NPS_G34_20180514_TS.nc' ]
cl.nps34a_parms = ['temperature', 'salinity','fluorescence']
cl.nps34a_startDatetime = startdate
cl.nps34a_endDatetime = enddate

# Slocum Teledyne nemesis Glider
## from ioos site ## these files proved to be not compatible with python loader
## cl.slocum_nemesis_base = 'https://data.ioos.us/gliders/thredds/dodsC/deployments/mbari/Nemesis-20170412T0000/'
## cl.slocum_nemesis_files = [ 'Nemesis-20170412T0000.nc3.nc' ]
##   from cencoos directory, single non-aggregated files
cl.slocum_nemesis_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/Nemesis/nemesis_201808/'

cl.slocum_nemesis_files = [

         'nemesis_20180906T194104_rt0.nc',
         'nemesis_20180906T191353_rt0.nc',
         'nemesis_20180906T184751_rt0.nc',
         'nemesis_20180906T183125_rt0.nc',
         'nemesis_20180906T170845_rt0.nc',
         'nemesis_20180906T163337_rt0.nc',
         'nemesis_20180906T160624_rt0.nc',
         'nemesis_20180906T155057_rt0.nc',
         'nemesis_20180906T142411_rt0.nc',
         'nemesis_20180906T132259_rt0.nc',
         'nemesis_20180906T121934_rt0.nc',
         'nemesis_20180906T114304_rt0.nc',
         'nemesis_20180906T093549_rt0.nc',
         'nemesis_20180906T082101_rt0.nc',
         'nemesis_20180906T070454_rt0.nc',
         'nemesis_20180906T062520_rt0.nc',
         'nemesis_20180906T043332_rt0.nc',
         'nemesis_20180906T004133_rt0.nc',
         'nemesis_20180905T221127_rt0.nc',
         'nemesis_20180905T204648_rt0.nc',
         'nemesis_20180905T164044_rt0.nc',
         'nemesis_20180905T141618_rt0.nc',
         'nemesis_20180905T131740_rt0.nc',
         'nemesis_20180905T103520_rt0.nc',
         'nemesis_20180905T085220_rt0.nc',
         'nemesis_20180905T072705_rt0.nc',
         'nemesis_20180905T063533_rt0.nc',
         'nemesis_20180905T044811_rt0.nc',
         'nemesis_20180905T035047_rt0.nc',
         'nemesis_20180905T030553_rt0.nc',
         'nemesis_20180905T023824_rt0.nc',
         'nemesis_20180905T012807_rt0.nc',
         'nemesis_20180905T010124_rt0.nc',
         'nemesis_20180905T003511_rt0.nc',
         'nemesis_20180905T002147_rt0.nc',
         'nemesis_20180904T233809_rt0.nc',
         'nemesis_20180904T231858_rt0.nc',
         'nemesis_20180904T230057_rt0.nc',
         'nemesis_20180904T224854_rt0.nc',
         'nemesis_20180904T220535_rt0.nc',
         'nemesis_20180904T214559_rt0.nc',
         'nemesis_20180904T212349_rt0.nc',
         'nemesis_20180904T211423_rt0.nc',
         'nemesis_20180904T202654_rt0.nc',
         'nemesis_20180904T200740_rt0.nc',
         'nemesis_20180904T194928_rt0.nc',
         'nemesis_20180904T193953_rt0.nc',
         'nemesis_20180904T185444_rt0.nc',
         'nemesis_20180904T183426_rt0.nc',
         'nemesis_20180904T181411_rt0.nc',
         'nemesis_20180904T180248_rt0.nc',
         'nemesis_20180904T053305_rt0.nc',
         'nemesis_20180904T051734_rt0.nc',
         'nemesis_20180904T041451_rt0.nc',
         'nemesis_20180904T035923_rt0.nc',
         'nemesis_20180904T025751_rt0.nc',
         'nemesis_20180904T023922_rt0.nc',
         'nemesis_20180904T013522_rt0.nc',
         'nemesis_20180904T011945_rt0.nc',
         'nemesis_20180904T001131_rt0.nc',
         'nemesis_20180903T235045_rt0.nc',
         'nemesis_20180903T223804_rt0.nc',
         'nemesis_20180903T221335_rt0.nc',
         'nemesis_20180903T211025_rt0.nc',
         'nemesis_20180903T205158_rt0.nc',
         'nemesis_20180903T190806_rt0.nc',
         'nemesis_20180903T183434_rt0.nc',
         'nemesis_20180903T163518_rt0.nc',
         'nemesis_20180903T155349_rt0.nc',
         'nemesis_20180903T141247_rt0.nc',
         'nemesis_20180903T133012_rt0.nc',
         'nemesis_20180903T110322_rt0.nc',
         'nemesis_20180903T102235_rt0.nc',
         'nemesis_20180903T072941_rt0.nc',
         'nemesis_20180903T063313_rt0.nc',
         'nemesis_20180903T024854_rt0.nc',
         'nemesis_20180903T004614_rt0.nc',
         'nemesis_20180902T204804_rt0.nc',
         'nemesis_20180902T192818_rt0.nc',
         'nemesis_20180902T153257_rt0.nc',
         'nemesis_20180902T135908_rt0.nc',
         'nemesis_20180902T093735_rt0.nc',
         'nemesis_20180902T080955_rt0.nc',
         'nemesis_20180902T033631_rt0.nc',
         'nemesis_20180902T020151_rt0.nc',
         'nemesis_20180901T205733_rt0.nc',
         'nemesis_20180901T191749_rt0.nc',
         'nemesis_20180901T143158_rt0.nc',
         'nemesis_20180901T120156_rt0.nc',
         'nemesis_20180901T071045_rt0.nc',
         'nemesis_20180901T052010_rt0.nc',
         'nemesis_20180901T010207_rt0.nc',
         'nemesis_20180831T233506_rt0.nc',
         'nemesis_20180831T184219_rt0.nc',
         'nemesis_20180831T165959_rt0.nc',
         'nemesis_20180831T123532_rt0.nc',
         'nemesis_20180831T112705_rt0.nc',
         'nemesis_20180831T083007_rt0.nc',
         'nemesis_20180831T073614_rt0.nc',
         'nemesis_20180831T044257_rt0.nc',
         'nemesis_20180831T032140_rt0.nc',
         'nemesis_20180830T213315_rt0.nc',
         'nemesis_20180830T192141_rt0.nc',
         'nemesis_20180830T163630_rt0.nc',
         'nemesis_20180830T154539_rt0.nc',
         'nemesis_20180830T122311_rt0.nc',
         'nemesis_20180830T100646_rt0.nc',
         'nemesis_20180830T081925_rt0.nc',
         'nemesis_20180830T063446_rt0.nc',
         'nemesis_20180830T041540_rt0.nc',
         'nemesis_20180830T032214_rt0.nc',
         'nemesis_20180830T014419_rt0.nc',
         'nemesis_20180830T011732_rt0.nc',
         'nemesis_20180830T000305_rt0.nc',
         'nemesis_20180829T234500_rt0.nc',
         'nemesis_20180829T225042_rt0.nc',
         'nemesis_20180829T215529_rt0.nc',

                          ]
cl.slocum_nemesis_parms = [ 'temperature', 'salinity', 'u', 'v' ] #'oxygen', 'cdom', 'opbs', 'fluorescence' not populated
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

# WG Sparky - All instruments combined into one file - one time coordinate
cl.wg_Sparky_base = 'http://dods.mbari.org/opendap/data/waveglider/deployment_data/'
cl.wg_Sparky_files = [
                      'wgSparky/20180821/realTime/20180821.nc',
                     ]

cl.wg_Sparky_parms = [ 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp_float', 'sal_float',  'water_temp_sub', 
                     'sal_sub', 'bb_470', 'bb_650', 'chl', 'beta_470', 'beta_650', 'pH', 'O2_conc' ] # two ctds (_float, _sub), no CO2
cl.wg_Sparky_depths = [ 0 ]
cl.wg_Sparky_startDatetime = startdate
cl.wg_Sparky_endDatetime = enddate

# WG Tiny - All instruments combined into one file - one time coordinate
cl.wg_Tiny_base = 'http://dods.mbari.org/opendap/data/waveglider/deployment_data/'
cl.wg_Tiny_files = [
                      'wgTiny/20180730/realTime/20180730.nc',
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
cl.oa1_base = 'http://dods.mbari.org/opendap/data/oa_moorings/deployment_data/OA1/201607/realTime/'
cl.oa1_files = [
               'OA1_201607.nc'
               ]
cl.oa1_parms = [
               'wind_dir', 'avg_wind_spd', 'atm_press', 'air_temp', 'water_temp',
               'sal', 'O2_conc', 'chl', 'pCO2_water', 'pCO2_air', 'pH',
               ]
cl.oa1_startDatetime = startdate
cl.oa1_endDatetime = enddate

# Mooring 0A2
cl.oa2_base = 'http://dods.mbari.org/opendap/data/oa_moorings/deployment_data/OA2/201609/'
cl.oa2_files = [
               'realTime/OA2_201609.nc'
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
#                  '03917plm01.nc',
                  ]

# PCTD
cl.rcpctd_base = cl.dodsBase + 'Other/routine/Platforms/Ships/RachelCarson/pctd/'
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.rcpctd_files = [
#                  '00917c01.nc', '00917c02.nc', '00917c03.nc',
#                  '03917c01.nc', '03917c02.nc', '03917c03.nc',
                  ]

######################################################################
#  WESTERN FLYER: Apr 2017 --
######################################################################
# UCTD
cl.wfuctd_base = cl.dodsBase + 'Other/routine/Platforms/Ships/WesternFlyer/uctd/'
cl.wfuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.wfuctd_files = [
                  'canon17sm01.nc',
                  ]

# PCTD
cl.wfpctd_base = cl.dodsBase + 'Other/routine/Platforms/Ships/WesternFlyer/pctd/'
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.wfpctd_files = [
                  'canon17sc01.nc',
                  ]

###################################################################################################
# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/
#   copied to local BOG_Data/CANON_OS2107 dir
###################################################################################################
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data/CANON_OS2017/bctd/')
cl.subsample_csv_files = [
##   'STOQS_00917_OXY_PS.csv',
##   'STOQS_00917_CARBON_GFF.csv',
##   'STOQS_00917_CHL_1U.csv',    'STOQS_00917_FLUOR.csv',
##   'STOQS_00917_CHL_5U.csv', 'STOQS_00917_NH4.csv', 'STOQS_00917_PHAEO_1U.csv',
##   'STOQS_00917_CHLA.csv', 'STOQS_00917_O2.csv', 'STOQS_00917_PHAEO_5U.csv',
##   'STOQS_00917_CHL_GFF.csv',
##   'STOQS_00917_PHAEO_GFF.csv',
                       ]

# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.stride = 100
elif cl.args.stride:
    cl.stride = cl.args.stride

cl.loadM1()  
cl.loadL_662a()
cl.load_NPS34a() 
cl.load_slocum_nemesis() 
cl.load_wg_Tiny()
cl.load_wg_Sparky()
cl.load_oa1()
cl.load_oa2()
cl.loadDorado(startdate, enddate, build_attrs=True)
cl.loadLRAUV('daphne', startdate, enddate)
cl.loadLRAUV('makai', startdate, enddate)
##cl.loadRCuctd()  ## not in this campaign
##cl.loadRCpctd()  ## not in this campaign
##cl.loadWFuctd()
##cl.loadWFpctd()

#cl.loadSubSamples() ## no subSamples yet...

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

