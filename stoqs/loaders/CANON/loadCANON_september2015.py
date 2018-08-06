#!/usr/bin/env python
__author__    = 'Mike McCann,Duane Edgington,Reiko Michisaki'
__copyright__ = '2015'
__license__   = 'GPL v3'
__contact__   = 'duane at mbari.org'

__doc__ = '''

Master loader for all CANON activities in September 2015

Mike McCann and Duane Edgington
MBARI 23 September 2015

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime  # needed for glider data
import time      # for startdate, enddate args

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
import timing

 
cl = CANONLoader('stoqs_canon_september2015', 'CANON - September-October 2015',
                    description = 'Fall 2015 Front Identification in northern Monterey Bay',
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

# Set start and end dates for all loads from sources that contain data 
# beyond the temporal bounds of the campaign
startdate = datetime.datetime(2015, 9, 8)                 # Changed to 8th to include pre CANON LRAUV test data
enddate = datetime.datetime(2015, 10, 16)                 # Fixed end two days after end of CANON cruises

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'

#####################################################################
#  DORADO 
#####################################################################
# special location for dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2015/netcdf/'
cl.dorado_files = [
                    'Dorado389_2015_265_03_265_03_decim.nc',
                    'Dorado389_2015_267_01_267_01_decim.nc',
                    'Dorado389_2015_285_00_285_00_decim.nc',
                    'Dorado389_2015_286_00_286_00_decim.nc', 
                    'Dorado389_2015_287_00_287_00_decim.nc',
                  ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                    'fl700_uncorr', 'salinity', 'biolume', 'rhodamine',
                    'roll', 'pitch', 'yaw',
                    'sepCountList', 'mepCountList' ]

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
cl.l_662_files = [ 'OS_Glider_L_662_20150813_TS.nc' ]
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = startdate
cl.l_662_endDatetime = enddate


######################################################################
# Wavegliders
######################################################################
# WG Tiny - All instruments combined into one file - one time coordinate
cl.wg_Tiny_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Waveglider/wgTiny/'
cl.wg_Tiny_files = [ 'wgTiny_Canon2015_Sep.nc'  ]
cl.wg_Tiny_parms = [ 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal',  'bb_470', 'bb_650', 'chl',
                    'beta_470', 'beta_650', 'pCO2_water', 'pCO2_air', 'pH', 'O2_conc' ]
cl.wg_Tiny_startDatetime = startdate
cl.wg_Tiny_endDatetime = enddate

# WG OA - All instruments combined into one file - one time coordinate
cl.wg_oa_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Waveglider/wgOA/'
cl.wg_oa_files = [ 'wgOA_Canon2015_Sep.nc'  ]
cl.wg_oa_parms = [ 'distance', 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal', 'O2_conc',
                   'O2_sat', 'beta_470', 'bb_470', 'beta_700', 'bb_700', 'chl', 'pCO2_water', 'pCO2_air', 'pH' ]
cl.wg_oa_startDatetime = startdate
cl.wg_oa_endDatetime = enddate

######################################################################
#  WESTERN FLYER: September 29 - Oct 5 (7 days)
######################################################################
# UCTD
cl.wfuctd_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Ships/Western_Flyer/uctd/'
cl.wfuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.wfuctd_files = [
                  'canon15m01.nc', 'canon15m02.nc',   
                  'canon15m03.nc', 'canon15m04.nc',   
                  'canon15m05.nc', 'canon15m06.nc', 'canon15m07.nc', 'canon15m08.nc', 'canon15m09.nc', 'canon15m10.nc',
                  'canon15m11.nc', 'canon15m12.nc',  
                  ]

# PCTD
cl.wfpctd_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Ships/Western_Flyer/pctd/'
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl' , 'oxygen']
cl.wfpctd_files = [
                  'canon15c01.nc', 'canon15c02.nc', 'canon15c03.nc', 'canon15c04.nc',  
                  'canon15c05.nc', 'canon15c06.nc', 'canon15c07.nc', 'canon15c08.nc',  
                  'canon15c09.nc', 'canon15c10.nc', 'canon15c11.nc', 'canon15c12.nc',  
                  'canon15c13.nc', 'canon15c14.nc', 'canon15c15.nc', 'canon15c16.nc',  
                  'canon15c17.nc', 'canon15c18.nc', 'canon15c19.nc', 'canon15c20.nc',  
                  'canon15c21.nc', 'canon15c22.nc', 'canon15c23.nc', 'canon15c24.nc',  
                  'canon15c25.nc',  
                  'canon15c26.nc', 'canon15c27.nc', 'canon15c28.nc', 'canon15c29.nc', 'canon15c30.nc',
                  'canon15c31.nc', 'canon15c32.nc', 'canon15c33.nc', 'canon15c34.nc', 'canon15c35.nc', 
                  'canon15c36.nc', 'canon15c37.nc', 'canon15c38.nc', 'canon15c39.nc', 'canon15c40.nc', 
                  'canon15c41.nc', 'canon15c42.nc', 'canon15c43.nc', 'canon15c44.nc', 'canon15c45.nc', 
                  'canon15c46.nc', 'canon15c47.nc', 'canon15c48.nc', 'canon15c49.nc', 'canon15c50.nc', 
                  'canon15c51.nc', 'canon15c52.nc', 'canon15c53.nc', 'canon15c54.nc', 'canon15c55.nc',
                  'canon15c56.nc', 'canon15c57.nc',   
                  ]

######################################################################
#  RACHEL CARSON: September 22-24 (265-xxx) Oct 12 - Oct 14
######################################################################
# UCTD
cl.rcuctd_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Ships/Rachel_Carson/uctd/'
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.rcuctd_files = [
                  '26515plm01.nc', '26615plm01.nc', '26715plm01.nc', 
                  '28215plm01.nc', '28515plm01.nc', '28615plm01.nc', '28715plm01.nc', 
                  ]

# PCTD
cl.rcpctd_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Ships/Rachel_Carson/pctd/'
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.rcpctd_files = [
                  '26515c01.nc', '26515c02.nc', '26515c03.nc',
                  '26615c01.nc', '26615c02.nc',
                  '26715c01.nc', '26715c02.nc', 
                  '28215c01.nc', '28215c02.nc', '28215c03.nc',
                  '28515c01.nc', '28515c02.nc',
                  '28615c01.nc', '28615c02.nc',
                  '28715c01.nc', '28715c02.nc', '28715c04.nc', ## note there is no 28715c03.nc
                  ]

#####################################################################
# JOHN MARTIN
#####################################################################
##cl.JMuctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Ships/Martin/uctd/' 
##cl.JMuctd_parms = ['TEMP', 'PSAL', 'turb_scufa', 'fl_scufa' ]
##cl.JMuctd_files = [ 'jhmudas_2013101.nc', 'jhmudas_2013102.nc', 'jhmudas_2013103.nc', 'jhmudas_2013911.nc', 'jhmudas_2013913.nc', 
##                    'jhmudas_2013916.nc', 'jhmudas_2013917.nc', 'jhmudas_2013919.nc', 'jhmudas_2013923.nc', 'jhmudas_2013930.nc', ]

##cl.JMpctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Ships/Martin/pctd/' 
##cl.JMpctd_parms = ['TEMP', 'PSAL', 'xmiss', 'wetstar', 'oxygen' ]
##cl.JMpctd_files = [ 
##                    '25613JMC01.nc', '25613JMC02.nc', '25613JMC03.nc', '25613JMC04.nc', '25613JMC05.nc', 
##                    '26013JMC01.nc', '26013JMC02.nc', '26013JMC03.nc', '26013JMC04.nc', 
##                    '26213JMC01.nc', '26213JMC02.nc', '26213JMC03.nc', '26213JMC04.nc', '26213JMC05.nc', '26613JMC01.nc',
##                    '26613JMC02i1.nc', '26613JMC02.nc', '26613JMC03.nc', '27513JMC01.nc', '27513JMC02.nc', '27513JMC03.nc', 
##                    '27513JMC04.nc', '27513JMC05.nc', '27613JMC01.nc', '27613JMC02.nc', '27613JMC03.nc', '27613JMC04.nc',
##                  ]

######################################################################
#  MOORINGS
######################################################################
# Mooring M1 Combined file produced by DPforSSDS processing - for just the duration of the campaign
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/201507/'
cl.m1_files = [
#                'OS_M1_20150729hourly_CMSTV.nc', ## no such file exists
                'OS_M1_20150730hourly_CMSTV.nc',
                'm1_hs2_20150730.nc',
              ]
cl.m1_parms = [
                'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
                'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
                'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR', 
                'bb470', 'bb676', 'fl676',
              ]
cl.m1_startDatetime = startdate
cl.m1_endDatetime = enddate

# Mooring 0A1
cl.oa1_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Moorings/OA1/'
cl.oa1_files = [
               'OA1_Canon2015_Sep.nc'
               ]
cl.oa1_parms = [
               'wind_dir', 'avg_wind_spd', 'atm_press', 'air_temp', 'water_temp',
               'sal', 'O2_conc', 'chl', 'pCO2_water', 'pCO2_air', 'pH',
              ]
cl.oa1_startDatetime = startdate
cl.oa1_endDatetime = enddate

# Mooring 0A2
cl.oa2_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Moorings/OA2/'
cl.oa2_files = [
               'OA2_Canon2015_Sep.nc'
               ]
cl.oa2_parms = [
               'wind_dir', 'avg_wind_spd', 'atm_press', 'air_temp', 'water_temp',
               'sal', 'O2_conc', 'chl', 'pCO2_water', 'pCO2_air', 'pH',
               ]
cl.oa2_startDatetime = startdate
cl.oa2_endDatetime = enddate

# ESP MOORINGS

#######################################################################################

###################################################################################################
# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/ 
#                                   
#   copied to local CANONSep2015 dir
###################################################################################################
##cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data/CANONSep2013')
##cl.subsample_csv_files = [
##'STOQS_CANON13_CARBON_GFF.csv', 'STOQS_CANON13_CHL_1U.csv', 'STOQS_CANON13_CHL_5U.csv', 'STOQS_CANON13_CHLA.csv',
##'STOQS_CANON13_CHL_GFF.csv', 'STOQS_CANON13_NO2.csv', 'STOQS_CANON13_NO3.csv', 'STOQS_CANON13_PHAEO_1U.csv',
##'STOQS_CANON13_PHAEO_5U.csv', 'STOQS_CANON13_PHAEO_GFF.csv', 'STOQS_CANON13_PO4.csv', 'STOQS_CANON13_SIO4.csv',

##'STOQS_25913RC_CHL_1U.csv', 'STOQS_25913RC_CHL_5U.csv', 'STOQS_25913RC_CHLA.csv', 'STOQS_25913RC_CHL_GFF.csv',
##'STOQS_25913RC_NO2.csv', 'STOQS_25913RC_NO3.csv', 'STOQS_25913RC_PHAEO_1U.csv', 'STOQS_25913RC_PHAEO_5U.csv',
##'STOQS_25913RC_PHAEO_GFF.csv', 'STOQS_25913RC_PO4.csv', 'STOQS_25913RC_SIO4.csv',

##'STOQS_26013RC_CHL_1U.csv', 'STOQS_26013RC_CHL_5U.csv', 'STOQS_26013RC_CHLA.csv', 'STOQS_26013RC_CHL_GFF.csv',
##'STOQS_26013RC_NO2.csv', 'STOQS_26013RC_NO3.csv', 'STOQS_26013RC_PHAEO_1U.csv', 'STOQS_26013RC_PHAEO_5U.csv',
##'STOQS_26013RC_PHAEO_GFF.csv', 'STOQS_26013RC_PO4.csv', 'STOQS_26013RC_SIO4.csv',

##'STOQS_26113RC_CHL_1U.csv', 'STOQS_26113RC_CHL_5U.csv', 'STOQS_26113RC_CHLA.csv', 'STOQS_26113RC_CHL_GFF.csv',
##'STOQS_26113RC_NO2.csv', 'STOQS_26113RC_NO3.csv', 'STOQS_26113RC_PHAEO_1U.csv', 'STOQS_26113RC_PHAEO_5U.csv',
##'STOQS_26113RC_PHAEO_GFF.csv', 'STOQS_26113RC_PO4.csv', 'STOQS_26113RC_SIO4.csv',

##'STOQS_27313RC_CHLA.csv',

##'STOQS_27413RC_CHLA.csv',

##'STOQS_27513RC_CHLA.csv', 'STOQS_27513RC_CHL_GFF.csv', 'STOQS_27513RC_NO2.csv', 'STOQS_27513RC_NO3.csv',
##'STOQS_27513RC_PHAEO_GFF.csv', 'STOQS_27513RC_PO4.csv', 'STOQS_27513RC_SIO4.csv',

##'STOQS_27613RC_CHLA.csv',
##                         ]


###################################################################################################################

# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.stride = 100
else:
    cl.stride = cl.args.stride

cl.loadL_662()
cl.load_wg_Tiny() 
##cl.load_wg_tex()  ## no waveglider Tex in this campaign
cl.load_wg_oa()
cl.loadM1()
cl.load_oa1()   
cl.load_oa2()  
cl.loadDorado()
cl.loadLRAUV('tethys', startdate, enddate)
cl.loadLRAUV('daphne', startdate, enddate)
cl.loadLRAUV('makai', startdate, enddate)
cl.loadRCuctd()
cl.loadRCpctd() 
cl.loadWFuctd()   
cl.loadWFpctd()

##cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")
