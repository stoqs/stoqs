#!/usr/bin/env python
__author__ = 'Mike McCann,Duane Edgington,Danelle Cline'
__copyright__ = '2018'
__license__ = 'GPL v3'
__contact__ = 'duane at mbari.org'

__doc__ = '''

Master loader for all CANON off season activities in 2018

Mike McCann, Duane Edgington, Danelle Cline
MBARI 17 January 2018

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

cl = CANONLoader('stoqs_os2018', 'CANON - Off Season 2018',
                 description='Off Season 2018 observations in Monterey Bay and LRAUVs in Hawaii',
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
                   'https://stoqs.mbari.org/x3d/Globe_1m_bath_10x/Globe_1m_bath_10x_scene.x3d': {
                     'position': '14051448.48336 -15407886.51486 6184041.22775',
                     'orientation': '0.83940 0.33030 0.43164 1.44880',
                     'centerOfRotation': '0 0 0',
                     'VerticalExaggeration': '10',
                   },
                 },
                 grdTerrain=os.path.join(parentDir, 'Monterey25.grd')
                 )

# Set start and end dates for all loads from sources that contain data
# beyond the temporal bounds of the campaign
#
startdate = datetime.datetime(2018, 1, 1)  # Fixed start. January 1, 2018
enddate = datetime.datetime(2018, 5, 15)    # When stoqs_canon_may2018 starts 

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'


#####################################################################
#  DORADO
#####################################################################
# special location for dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2018/netcdf/'
cl.dorado_files = [
                   'Dorado389_2018_030_00_030_00_decim.nc',
                   'Dorado389_2018_059_00_059_00_decim.nc', 
                   'Dorado389_2018_079_00_079_00_decim.nc',
                   'Dorado389_2018_099_00_099_00_decim.nc',
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
# L_662a updated parameter names in netCDF file
cl.l_662a_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662a_files = [
                   'OS_Glider_L_662_20171012_TS.nc',
                   'OS_Glider_L_662_20180117_TS.nc',
                  ]
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
cl.nps34a_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.nps34a_files = [ 'OS_Glider_NPS_G34_20170405_TS.nc' ]
cl.nps34a_parms = ['temperature', 'salinity','fluorescence']
cl.nps34a_startDatetime = startdate
cl.nps34a_endDatetime = enddate

# Slocum Teledyne nemesis Glider
## from ioos site ## these files proved to be not compatible with python loader
## cl.slocum_nemesis_base = 'https://data.ioos.us/gliders/thredds/dodsC/deployments/mbari/Nemesis-20170412T0000/'
## cl.slocum_nemesis_files = [ 'Nemesis-20170412T0000.nc3.nc' ]
##   from cencoos directory, single non-aggregated files
cl.slocum_nemesis_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/Nemesis/nemesis_201705/'
cl.slocum_nemesis_files = [
         'nemesis_20170802T164114_rt0.nc',
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
                      'wgTiny/20171212/realTime/20171212.nc',
                      'wgTiny/20180116/realTime/20180116.nc',
                      'wgTiny/20180208/realTime/20180208.nc',
                      'wgTiny/20180323/realTime/20180323.nc',
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
  '201708/OS_M1_20170808hourly_CMSTV.nc',]
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
cl.loadL_662a()
##cl.load_NPS34()  ## not in this campaign
##cl.load_NPS34a() ## not in this campaign
##cl.load_slocum_nemesis()  ## not in this campaign
##cl.load_SG621(stride=2) ## KISS glider
##cl.load_SG539(stride=2) ## KISS glider
cl.load_wg_Tiny()
cl.load_oa1()
cl.load_oa2()
cl.loadDorado()
##cl.loadRCuctd()  ## not in this campaign
##cl.loadRCpctd()  ## not in this campaign
##cl.loadWFuctd()  ## not in this campaign
##cl.loadWFpctd()  ## not in this campaign

#cl.loadSubSamples() ## no subSamples yet...

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

