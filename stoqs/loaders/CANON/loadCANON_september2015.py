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
import csv
import urllib2

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
       
cl = CANONLoader('stoqs_canon_september2015', 'CANON - September-October 2015',
                    description = 'Fall 2015 Front Identification in northern Monterey Bay',
                    x3dTerrains = {
                            '/static/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
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
startdate = datetime.datetime(2015, 9, 17)                 # Fixed start Thursday Sep 17 2015 per F. Chavez
enddate = datetime.datetime(2015, 10, 16)                  # Fixed end two days after end of CANON cruises

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
				   ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                    'fl700_uncorr', 'salinity', 'biolume', 'rhodamine',
                    'roll', 'pitch', 'yaw',
                    'sepCountList', 'mepCountList' ]

#####################################################################
#  LRAUV 
#####################################################################
# NetCDF files produced (binned, etc.) by John Ryan
##cl.tethys_base = cl.dodsBase + 'CANON_september2013/Platforms/AUVs/Tethys/NetCDF/'
##cl.tethys_files = ['Tethys_CANON_Fall2013.nc']
##cl.tethys_parms = ['temperature', 'salinity', 'chlorophyll', 'bb470', 'bb650']

##cl.daphne_base = cl.dodsBase + 'CANON_september2013/Platforms/AUVs/Daphne/NetCDF/'
##cl.daphne_files = ['Daphne_CANON_Fall2013.nc']
##cl.daphne_parms = ['temperature', 'chlorophyll', 'bb470', 'bb650']


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
cl.wg_Tiny_files = [  ]
cl.wg_Tiny_parms = [ 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal',  'bb_470', 'bb_650', 'chl',
                    'beta_470', 'beta_650', 'pCO2_water', 'pCO2_air', 'pH', 'O2_conc' ]
cl.wg_Tiny_startDatetime = startdate
cl.wg_Tiny_endDatetime = enddate

# WG OA - All instruments combined into one file - one time coordinate
##cl.wg_oa_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Waveglider/wgOA/'
##cl.wg_oa_files = [  ]
##cl.wg_oa_parms = [ 'distance', 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal', 'O2_conc',
##                   'O2_sat', 'beta_470', 'bb_470', 'beta_700', 'bb_700', 'chl', 'pCO2_water', 'pCO2_air', 'pH' ]
##cl.wg_oa_startDatetime = startdate
##cl.wg_oa_endDatetime = enddate

######################################################################
#  WESTERN FLYER: September 27 - Oct 3
######################################################################
# UCTD
cl.wfuctd_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Ships/Western_Flyer/uctd/'
cl.wfuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.wfuctd_files = [
                  ]

# PCTD
cl.wfpctd_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Ships/Western_Flyer/pctd/'
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl' , 'oxygen']
cl.wfpctd_files = [
                  ]

######################################################################
#  RACHEL CARSON: September 22-26 (265-xxx) Oct 6 - Oct 10
######################################################################
# UCTD
cl.rcuctd_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Ships/Rachel_Carson/uctd/'
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.rcuctd_files = [ 
                  ]

# PCTD
cl.rcpctd_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Ships/Rachel_Carson/pctd/'
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.rcpctd_files = [ 
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
                'OS_M1_20150729hourly_CMSTV.nc',
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

 
#######################################################################################
# ESP MOORINGS
#######################################################################################
##cl.bruce_moor_base = cl.dodsBase + 'CANON_september2013/Platforms/Moorings/ESP_Bruce/NetCDF/'
##cl.bruce_moor_files = ['Bruce_ctd.nc']
##cl.bruce_moor_parms = [ 'TEMP','PSAL','chl','xmiss','oxygen','beamc',
##                   ]
##cl.bruce_moor_startDatetime = startdate
##cl.bruce_moor_endDatetime = enddate

##cl.mack_moor_base = cl.dodsBase + 'CANON_september2013/Platforms/Moorings/ESP_Mack/NetCDF/'
##cl.mack_moor_files = ['Mack_ctd.nc']
##cl.mack_moor_parms = [ 'TEMP','PSAL','chl','xmiss','oxygen','beamc',
##                   ]
##cl.mack_moor_startDatetime = startdate
##cl.mack_moor_endDatetime = enddate

###################################################################################################
# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/ 
#                                   CANON13 25913RC 25913RC 26113RC 27313RC 27413RC 27513RC 27613RC
#   copied to local CANON2013 dir
###################################################################################################
##cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data/CANON2013')
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
    cl.loadL_662(stride=100) 

    ##cl.load_wg_tex(stride=10)
    ##cl.load_wg_oa(stride=10) 

    cl.loadDorado(stride=100)
    ##cl.loadDaphne(stride=100)
    ##cl.loadTethys(stride=100)

    ##cl.loadRCuctd(stride=10)
    ##cl.loadRCpctd(stride=10)
    ##cl.loadJMuctd(stride=10)
    ##cl.loadJMpctd(stride=10)
    ##cl.loadWFuctd(stride=10)   
    ##cl.loadWFpctd(stride=10)

    cl.loadM1(stride=10)

    ##cl.loadBruceMoor(stride=10)
    ##cl.loadMackMoor(stride=10)

    ##cl.loadSubSamples()

elif cl.args.optimal_stride:

    cl.loadL_662(stride=2)
    cl.loadM1(stride=1)
    #cl.loadDorado(stride=2)
    #cl.loadRCuctd(stride=2)
    #cl.loadRCpctd(stride=2)

    ##cl.loadSubSamples()

else:
    cl.stride = cl.args.stride

    #cl.loadL_662() 
    #cl.loadM1()
    cl.loadDorado()
    #cl.loadRCuctd()
    #cl.loadRCpctd() 
    #cl.loadWFuctd()   
    #cl.loadWFpctd()

    ##cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print "All Done."

