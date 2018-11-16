#!/usr/bin/env python
__author__ = 'Mike McCann,Duane Edgington,Reiko Michisaki,Danelle Cline'
__copyright__ = '2017'
__license__ = 'GPL v3'
__contact__ = 'duane at mbari.org'

__doc__ = '''

Master loader for all CANON off season activities in 2017

Mike McCann, Duane Edgington, Danelle Cline
MBARI 4 January 2017

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime  # needed for glider data
import time  # for startdate, enddate args

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
import timing

cl = CANONLoader('stoqs_os2017', 'CANON - Off Season 2017',
                 description='CANON Off Season 2017 Experiment in Monterey Bay',
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
startdate = datetime.datetime(2017, 1, 1)  # Fixed start
enddate = datetime.datetime(2017, 12, 31)  # Fixed end. Extend "offseason" to end of year

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'


#####################################################################
#  DORADO 
#####################################################################
# special location for dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2017/netcdf/'
cl.dorado_files = [
                   'Dorado389_2017_044_00_044_00_decim.nc',
                   'Dorado389_2017_068_00_068_00_decim.nc',
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
cl.l_662_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_files = [
                   'OS_Glider_L_662_20161214_TS.nc',
                   'OS_Glider_L_662_20170328_TS.nc'  ] 
# Begining with OS_Glider_L_662_20170328_TS variable names became: 'temperature', 'salinity', 'fluorescence'
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2', 'temperature', 'salinity', 'fluorescence']
cl.l_662_startDatetime = startdate
cl.l_662_endDatetime = enddate

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
                     'wgTiny/20170109/QC/20170109_QC.nc',
                     'wgTiny/20170307/QC/20170307_QC.nc',
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
cl.rcuctd_base = cl.dodsBase + 'CANON/2017_OffSeason/Platforms/Ships/Rachel_Carson/uctd/'
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.rcuctd_files = [
                  '00917plm01.nc',
                  '03917plm01.nc',
                  ]

# PCTD
cl.rcpctd_base = cl.dodsBase + 'CANON/2017_OffSeason/Platforms/Ships/Rachel_Carson/pctd/'
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.rcpctd_files = [
                  '00917c01.nc', '00917c02.nc', '00917c03.nc',
                  '03917c01.nc', '03917c02.nc', '03917c03.nc',
                  ]

###################################################################################################
# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/
#   copied to local BOG_Data/CANON_OS2107 dir
###################################################################################################
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data/CANON_OS2017/bctd/')
cl.subsample_csv_files = [
   'STOQS_00917_OXY_PS.csv',
   'STOQS_00917_CARBON_GFF.csv', 
   'STOQS_00917_CHL_1U.csv',    'STOQS_00917_FLUOR.csv',
   'STOQS_00917_CHL_5U.csv', 'STOQS_00917_NH4.csv', 'STOQS_00917_PHAEO_1U.csv',
   'STOQS_00917_CHLA.csv', 'STOQS_00917_O2.csv', 'STOQS_00917_PHAEO_5U.csv',
   'STOQS_00917_CHL_GFF.csv',
   'STOQS_00917_PHAEO_GFF.csv', 

   'STOQS_03917_OXY_PS.csv',
   'STOQS_03917_CARBON_GFF.csv',
   'STOQS_03917_CHL_1U.csv',    'STOQS_03917_FLUOR.csv',
   'STOQS_03917_CHL_5U.csv', 'STOQS_03917_NH4.csv', 'STOQS_03917_PHAEO_1U.csv',
   'STOQS_03917_CHLA.csv', 'STOQS_03917_O2.csv', 'STOQS_03917_PHAEO_5U.csv',
   'STOQS_03917_CHL_GFF.csv',
   'STOQS_03917_PHAEO_GFF.csv',

                       ]

# Execute the load
cl.process_command_line()

if cl.args.test:

    cl.loadM1(stride=100)
    cl.loadLRAUV('tethys', startdate, enddate, stride=100)
    cl.loadLRAUV('aku', startdate, enddate, stride=100)
    cl.loadLRAUV('ahi', startdate, enddate, stride=100)
    cl.loadLRAUV('opah', startdate, enddate, stride=100)
    cl.loadL_662(stride=100)

elif cl.args.optimal_stride:

    cl.loadL_662(stride=2)
    ##cl.load_NPS29(stride=2)
    #cl.load_NPS34(stride=2)
    cl.load_wg_Tiny(stride=2)
    cl.load_oa1(stride=2)
    cl.load_oa2(stride=2)
    cl.loadM1(stride=2)
    ##cl.loadDorado(stride=2)
    cl.loadRCuctd(stride=2)
    cl.loadRCpctd(stride=2)

    cl.loadSubSamples()


else:
    cl.stride = cl.args.stride

    cl.loadM1()
    cl.loadLRAUV('tethys', startdate, enddate)
    cl.loadLRAUV('aku', startdate, enddate)
    cl.loadLRAUV('ahi', startdate, enddate)
    cl.loadLRAUV('opah', startdate, enddate)
    cl.loadL_662()
    ##cl.load_NPS29()
    ##cl.load_NPS34()
    ##cl.load_UCSC294()
    ##cl.load_UCSC260()
    cl.load_wg_Tiny()
    cl.load_oa1()
    cl.load_oa2()
    cl.loadDorado()
    cl.loadRCuctd()
    cl.loadRCpctd()
    ##cl.loadWFuctd()
    ##cl.loadWFpctd()

    cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")


