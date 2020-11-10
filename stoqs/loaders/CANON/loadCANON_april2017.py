#!/usr/bin/env python
__author__ = 'Mike McCann,Duane Edgington,Reiko Michisaki,Danelle Cline'
__copyright__ = '2017'
__license__ = 'GPL v3'
__contact__ = 'duane at mbari.org'

__doc__ = '''

Master loader for all KISS/CANON April season activities in 2017

Mike McCann, Duane Edgington, Danelle Cline
MBARI 7 April 2017

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

cl = CANONLoader('stoqs_canon_april2017', 'KISS CANON Spring 2017',
                 description='KISS CANON Spring 2017 Experiment in Monterey Bay',
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
startdate = datetime.datetime(2017, 4, 7)  # Fixed start. April 7, 2017
enddate = datetime.datetime(2017, 5, 15)  # Fixed end. May 15, 2017

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'


#####################################################################
#  DORADO 
#####################################################################
# special location for dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2017/netcdf/'
cl.dorado_files = [
                   'Dorado389_2017_108_01_108_01_decim.nc',
                   'Dorado389_2017_121_00_121_00_decim.nc',    
                   'Dorado389_2017_124_00_124_00_decim.nc',
                                    ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                    'fl700_uncorr', 'salinity', 'biolume',
                    'sepCountList', 'mepCountList',
                    'roll', 'pitch', 'yaw',
                  ]

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
# L_662
cl.l_662_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line67/'
cl.l_662_files = [
                   'OS_Glider_L_662_20170328_TS.nc'  ] 
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = startdate
cl.l_662_endDatetime = enddate

# Glider data files from CeNCOOS thredds server
# L_662a updated parameter names in netCDF file
cl.l_662a_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line67/'
cl.l_662a_files = [
                   'OS_Glider_L_662_20170328_TS.nc'  ]
cl.l_662a_parms = ['temperature', 'salinity', 'fluorescence','oxygen']
cl.l_662a_startDatetime = startdate
cl.l_662a_endDatetime = enddate

# SG_539 ## KISS glider from Caltech/JPL
cl.sg539_base = cl.dodsBase + 'Activity/canon/2017_Apr/Platforms/Gliders/SG539/'
cl.sg539_files = ['p539{:04d}.nc'.format(i) for i in range(1,291)] ## index needs to be 1 higher than terminal file name
cl.sg539_parms = ['temperature', 'salinity']
cl.sg539_startDatetime = startdate
cl.sg539_endDatetime = enddate

# SG_621 ## KISS glider from Caltech/JPL
cl.sg621_base = cl.dodsBase + 'Activity/canon/2017_Apr/Platforms/Gliders/SG621/'
cl.sg621_files = ['p621{:04d}.nc'.format(i) for i in range(1,291)] ## index needs to be 1 higher than terminal file name
cl.sg621_parms = ['temperature', 'salinity'] # 'aanderaa4330_dissolved_oxygen' throws DAPloader KeyError
cl.sg621_startDatetime = startdate
cl.sg621_endDatetime = enddate


# NPS_34a updated parameter names in netCDF file
## The following loads decimated subset of data telemetered during deployment
cl.nps34a_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/MBARI/'
cl.nps34a_files = [ 'OS_Glider_NPS_G34_20170405_TS.nc' ]
cl.nps34a_parms = ['temperature', 'salinity','fluorescence']
cl.nps34a_startDatetime = startdate
cl.nps34a_endDatetime = enddate

# Slocum Teledyne nemesis Glider
## from ioos site ## these files proved to be not compatible with python loader
## cl.slocum_nemesis_base = 'https://data.ioos.us/gliders/thredds/dodsC/deployments/mbari/Nemesis-20170412T0000/'
## cl.slocum_nemesis_files = [ 'Nemesis-20170412T0000.nc3.nc' ]
##   from cencoos directory, single non-aggregated files
cl.slocum_nemesis_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/line66/nemesis_201704/'
cl.slocum_nemesis_files = [
       'nemesis_20170426T233417_rt0.nc',
       'nemesis_20170426T193433_rt0.nc',
       'nemesis_20170426T175101_rt0.nc',
       'nemesis_20170426T135031_rt0.nc', 
       'nemesis_20170426T101456_rt0.nc',
       'nemesis_20170426T065328_rt0.nc',
       'nemesis_20170426T025437_rt0.nc',
       'nemesis_20170425T225257_rt0.nc',
       'nemesis_20170425T181501_rt0.nc',
       'nemesis_20170425T155145_rt0.nc',
       'nemesis_20170425T112030_rt0.nc', 
       'nemesis_20170425T065720_rt0.nc',
       'nemesis_20170425T023329_rt0.nc',
       'nemesis_20170425T012718_rt0.nc',
       'nemesis_20170424T183523_rt0.nc',
       'nemesis_20170424T163853_rt0.nc',  
       'nemesis_20170424T101051_rt0.nc',  
       'nemesis_20170424T082924_rt0.nc',  
       'nemesis_20170424T024219_rt0.nc',  
        'nemesis_20170424T004146_rt0.nc',  
        'nemesis_20170423T183602_rt0.nc',  
        'nemesis_20170423T170338_rt0.nc',  
        'nemesis_20170423T110527_rt0.nc',  
        'nemesis_20170423T090902_rt0.nc',  
        'nemesis_20170423T022952_rt0.nc',  
        'nemesis_20170423T003332_rt0.nc',  
        'nemesis_20170422T174553_rt0.nc',  
        'nemesis_20170422T154625_rt0.nc',  
        'nemesis_20170422T100914_rt0.nc',  
        'nemesis_20170422T082446_rt0.nc',
        'nemesis_20170422T023332_rt0.nc',
        'nemesis_20170422T003714_rt0.nc',
        'nemesis_20170421T191814_rt0.nc',
        'nemesis_20170421T173951_rt0.nc',
    'nemesis_20170421T104922_rt0.nc',
    'nemesis_20170421T084951_rt0.nc',
    'nemesis_20170421T020423_rt0.nc',
    'nemesis_20170421T000452_rt0.nc',
    'nemesis_20170420T175634_rt0.nc',
    'nemesis_20170420T163615_rt0.nc', 
    'nemesis_20170420T125233_rt0.nc',
    'nemesis_20170420T081202_rt0.nc',
    'nemesis_20170420T033108_rt0.nc',
    'nemesis_20170419T225941_rt0.nc',
    'nemesis_20170419T183219_rt0.nc',
    'nemesis_20170419T125701_rt0.nc',
    'nemesis_20170419T085215_rt0.nc',
    'nemesis_20170419T042720_rt0.nc',
    'nemesis_20170418T234312_rt0.nc',
    'nemesis_20170418T221752_rt0.nc',
    'nemesis_20170418T212940_rt0.nc',
    'nemesis_20170418T210333_rt0.nc',
    'nemesis_20170418T194024_rt0.nc',
    'nemesis_20170418T185432_rt0.nc',
    'nemesis_20170418T183124_rt0.nc',
    'nemesis_20170418T172154_rt0.nc',
    'nemesis_20170418T164352_rt0.nc',
    'nemesis_20170418T162547_rt0.nc',
    'nemesis_20170418T132214_rt0.nc',
    'nemesis_20170418T101901_rt0.nc',
    'nemesis_20170418T054425_rt0.nc',
    'nemesis_20170418T041209_rt0.nc',
    'nemesis_20170417T233719_rt0.nc',
    'nemesis_20170417T215856_rt0.nc',
    'nemesis_20170417T184524_rt0.nc',
    'nemesis_20170417T162824_rt0.nc',
    'nemesis_20170417T101213_rt0.nc',
    'nemesis_20170417T075255_rt0.nc',
    'nemesis_20170417T042017_rt0.nc',
    'nemesis_20170417T030853_rt0.nc',
    'nemesis_20170417T003843_rt0.nc',
    'nemesis_20170416T221424_rt0.nc',
    'nemesis_20170416T193428_rt0.nc',
    'nemesis_20170416T170011_rt0.nc',
    'nemesis_20170416T142835_rt0.nc',
    'nemesis_20170416T074059_rt0.nc',
    'nemesis_20170416T062946_rt0.nc',
    'nemesis_20170415T234216_rt0.nc',
    'nemesis_20170415T223406_rt0.nc',
    'nemesis_20170415T181901_rt0.nc',
    'nemesis_20170415T142326_rt0.nc',
    'nemesis_20170414T211726_rt0.nc',
    'nemesis_20170414T204237_rt0.nc',
    'nemesis_20170414T200204_rt0.nc',
    'nemesis_20170414T191127_rt0.nc',
    'nemesis_20170414T183517_rt0.nc',
    'nemesis_20170414T175658_rt0.nc',
    'nemesis_20170414T170838_rt0.nc',
    'nemesis_20170414T163826_rt0.nc',
    'nemesis_20170414T160550_rt0.nc',
    'nemesis_20170414T153128_rt0.nc',
    'nemesis_20170414T144546_rt0.nc',
    'nemesis_20170414T141553_rt0.nc',
    'nemesis_20170414T134419_rt0.nc',
    'nemesis_20170414T125048_rt0.nc',
    'nemesis_20170414T121126_rt0.nc',
    'nemesis_20170414T113140_rt0.nc',
    'nemesis_20170414T104022_rt0.nc',
    'nemesis_20170414T100220_rt0.nc',
    'nemesis_20170414T092320_rt0.nc',
    'nemesis_20170414T083639_rt0.nc',
    'nemesis_20170414T080001_rt0.nc',
    'nemesis_20170414T072333_rt0.nc',
    'nemesis_20170414T060450_rt0.nc',
    'nemesis_20170414T052723_rt0.nc',
    'nemesis_20170414T045256_rt0.nc',
    'nemesis_20170414T001407_rt0.nc',
    'nemesis_20170413T224113_rt0.nc',
    'nemesis_20170413T175449_rt0.nc',
    'nemesis_20170413T161622_rt0.nc',
    'nemesis_20170413T143646_rt0.nc',
    'nemesis_20170413T130648_rt0.nc',
    'nemesis_20170413T112821_rt0.nc',
    'nemesis_20170413T095841_rt0.nc',
    'nemesis_20170413T074545_rt0.nc',
    'nemesis_20170413T055613_rt0.nc',
    'nemesis_20170413T040950_rt0.nc',
    'nemesis_20170413T021706_rt0.nc',
    'nemesis_20170413T004402_rt0.nc',
    'nemesis_20170412T234033_rt0.nc',
    'nemesis_20170412T223941_rt0.nc',
    'nemesis_20170412T221251_rt0.nc',
    'nemesis_20170412T214343_rt0.nc',
    'nemesis_20170412T212116_rt0.nc',
    'nemesis_20170412T205615_rt0.nc',
    'nemesis_20170412T203242_rt0.nc',
    'nemesis_20170412T195346_rt0.nc',
    'nemesis_20170412T192201_rt0.nc',
    'nemesis_20170412T182659_rt0.nc',
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

# WG Tiny - All instruments combined into one file - one time coordinate
cl.wg_Tiny_base = 'http://dods.mbari.org/opendap/data/waveglider/deployment_data/'
cl.wg_Tiny_files = [
                     'wgTiny/20170412/QC/20170412_QC.nc',
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
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/201608/'
cl.m1_files = [
  'OS_M1_20160829hourly_CMSTV.nc'
]
cl.m1_parms = [
  'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
  'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
  'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR'
]

cl.m1_startDatetime = startdate
cl.m1_endDatetime = enddate

# Mooring 0A1
#cl.oa1_base = 'http://dods.mbari.org/opendap/data/oa_moorings/deployment_data/OA1/201401/'
#cl.oa1_files = [
#               'OA1_201401.nc'
#               ]
cl.oa1_base = 'http://dods.mbari.org/opendap/data/oa_moorings/deployment_data/OA1/201607/realTime/'
cl.oa1_files = [
               'OA1_201607.nc'  ## new deployment
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
                  'canon17sm02.nc',
                  'canon17sm03.nc',
                  'canon17sm04.nc',
                  'canon17sm05.nc',
                  'canon17sm06.nc',
                  'canon17sm07.nc',                                                                             
                  'canon17sm08.nc',                                                        
                  'canon17sm09.nc',                                                  
                  'canon17sm10.nc',                                                               
                  'canon17sm11.nc',                                                                  
                  'canon17sm12.nc',                                                                                        
                  'canon17sm13.nc',                                         
                  'canon17sm14.nc',                                                                    
                  'canon17sm1.nc', 
                  'canon17sm15.nc', 'canon17sm16.nc', 'canon17sm17.nc',
                  'canon17sm18.nc',
                  'canon17sm19.nc', 'canon17sm20.nc', 'canon17sm21.nc',
                  'canon17sm22.nc',
                  'canon17sm23.nc', 'canon17sm24.nc', 'canon17sm25.nc',
                  ]

# PCTD
cl.wfpctd_base = cl.dodsBase + 'Other/routine/Platforms/Ships/WesternFlyer/pctd/'
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.wfpctd_files = [
                  'canon17sc01.nc',  
                  'canon17sc03.nc',
                  'canon17sc04.nc',                                                                      
                  'canon17sc05.nc',
                  'canon17sc06.nc',
                  'canon17sc07.nc',
                  'canon17sc08.nc',
                  'canon17sc09.nc',
                  'canon17sc10.nc',
                  'canon17sc11.nc',
                  'canon17sc12.nc',
                  'canon17sc13.nc',
                  'canon17sc14.nc',
                  'canon17sc15.nc', 'canon17sc16.nc', 'canon17sc17.nc',
                  'canon17sc18.nc', 'canon17sc19.nc', 'canon17sc20.nc',
                  'canon17sc21.nc', 'canon17sc22.nc', 'canon17sc23.nc',
                  'canon17sc24.nc', 'canon17sc25.nc', 'canon17sc26.nc',
                  'canon17sc27.nc', 'canon17sc28.nc',
                  'canon17sc29.nc', 'canon17sc30.nc', 'canon17sc31.nc', 'canon17sc32.nc',
                  'canon17sc33.nc', 'canon17sc34.nc', 'canon17sc35.nc', 'canon17sc36.nc',
                  'canon17sc37.nc', 'canon17sc38.nc', 
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
    cl.stride = 1000
elif cl.args.optimal_stride:
    cl.stride = 2
else:
    cl.stride = cl.args.stride

cl.loadM1()
cl.loadLRAUV('tethys', startdate, enddate)
cl.loadLRAUV('aku', startdate, enddate)
cl.loadLRAUV('ahi', startdate, enddate)
cl.loadLRAUV('opah', startdate, enddate)
cl.loadLRAUV('daphne', startdate, enddate)
##cl.loadL_662()  ## not in this campaign
cl.loadL_662a()
##cl.load_NPS34()  ## not in this campaign
cl.load_NPS34a()
cl.load_slocum_nemesis()
cl.load_SG621(stride=2) ## KISS glider
cl.load_SG539(stride=2) ## KISS glider
cl.load_wg_Tiny()
cl.load_oa1()
cl.load_oa2()
cl.loadDorado()
##cl.loadRCuctd()  ## not in this campaign
##cl.loadRCpctd()  ## not in this campaign
cl.loadWFuctd()
cl.loadWFpctd()

#cl.loadSubSamples() ## no subSamples yet...

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

