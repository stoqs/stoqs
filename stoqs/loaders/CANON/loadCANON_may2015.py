#!/usr/bin/env python
__author__    = 'Mike McCann,Duane Edgington,Reiko Michisaki'
__copyright__ = '2015'
__license__   = 'GPL v3'
__contact__   = 'duane at mbari.org'

__doc__ = '''

Master loader for all CANON activities in May 2015

Mike McCann and Duane Edgington
MBARI 11 May 2015

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
import urllib.request, urllib.error, urllib.parse

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
from thredds_crawler.crawl import Crawl
import timing

cl = CANONLoader('stoqs_canon_may2015', 'CANON-ECOHAB - May 2015',
                    description = 'Spring 2015 Experiment in Monterey Bay',
                    x3dTerrains = {
                                    'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                                        'position': '-2822317.31255 -4438600.53640 3786150.85474',
                                        'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                                        'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                                        'VerticalExaggeration': '10',
                                        'speed': '0.1',
                                    }
                    },
                    grdTerrain = os.path.join(parentDir, 'Monterey25.grd')
                  )

# Set start and end dates for all loads from sources that contain data 
# beyond the temporal bounds of the campaign
startdate = datetime.datetime(2015, 5, 6)                 # Fixed start
enddate = datetime.datetime(2015, 6, 11)                  # Fixed end

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'

#####################################################################
#  DORADO 
#####################################################################
# special location for dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2015/netcdf/'
cl.dorado_files = [
                   'Dorado389_2015_132_04_132_04_decim.nc',
                   'Dorado389_2015_148_01_148_01_decim.nc',
                   'Dorado389_2015_156_00_156_00_decim.nc',
                                   ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                    'fl700_uncorr', 'salinity', 'biolume', 'rhodamine', 
                    'sepCountList', 'mepCountList',
                    'roll', 'pitch', 'yaw',
                  ]

######################################################################
#  GLIDERS
######################################################################
# Glider data files from CeNCOOS thredds server
# L_662
# cl.l_662_base = 'http://www.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_files = [ 'OS_Glider_L_662_20150427_TS.nc' ]
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = startdate
cl.l_662_endDatetime = enddate

# NPS_29
#cl.nps29_base = 'http://www.cencoos.org/thredds/dodsC/gliders/Line66/'
#cl.nps29_files = [ 'OS_Glider_NPS_G29_20140930_TS.nc' ]
#cl.nps29_parms = ['TEMP', 'PSAL']
#cl.nps29_startDatetime = startdate
#cl.nps29_endDatetime = enddate

# slocum_294  also known as UCSC294
cl.slocum_294_base = 'http://data.ioos.us/gliders/thredds/dodsC/deployments/mbari/UCSC294-20150430T2218/'
cl.slocum_294_files = [ 'UCSC294-20150430T2218.nc3.nc' ]
cl.slocum_294_parms = ['temperature', 'salinity']
cl.slocum_294_startDatetime = startdate
cl.slocum_294_endDatetime = enddate

# slocum_260 also known as UCSC160
cl.slocum_260_base = 'http://data.ioos.us/gliders//thredds/dodsC/deployments/mbari/UCSC260-20150520T0000/'
cl.slocum_260_files = [ 'UCSC260-20150520T0000.nc3.nc'  ]
cl.slocum_260_parms = ['temperature', 'salinity']
cl.slocum_260_startDatetime = startdate
cl.slocum_260_endDatetime = enddate

# slocum_nemesis



######################################################################
# Wavegliders
######################################################################
# WG Tex - All instruments combined into one file - one time coordinate
#cl.wg_tex_base = cl.dodsBase + 'CANON/2015_May/Platforms/Waveglider/SV3_Tiny/'
#cl.wg_tex_files = [ 'SV3_20150501_QC.nc' ]
#cl.wg_tex_parms = [ 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal',  'bb_470', 'bb_650', 'chl',
#                    'beta_470', 'beta_650', 'pCO2_water', 'pCO2_air', 'pH', 'O2_conc' ]
#cl.wg_tex_startDatetime = startdate
#cl.wg_tex_endDatetime = enddate

# WG Tiny - All instruments combined into one file - one time coordinate
cl.wg_Tiny_base = cl.dodsBase + 'CANON/2015_May/Platforms/Waveglider/SV3_Tiny/'
cl.wg_Tiny_files = [ 'SV3_20150501_QC.nc' ]
cl.wg_Tiny_parms = [ 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal',  'bb_470', 'bb_650', 'chl',
                    'beta_470', 'beta_650', 'pCO2_water', 'pCO2_air', 'pH', 'O2_conc' ]
cl.wg_Tiny_startDatetime = startdate
cl.wg_Tiny_endDatetime = enddate

# WG OA - All instruments combined into one file - one time coordinate
##cl.wg_oa_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/WG_OA/final/'
##cl.wg_oa_files = [ 'Sept_2013_OAWaveglider_final.nc' ]
##cl.wg_oa_parms = [ 'distance', 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal', 'O2_conc',
##                   'O2_sat', 'beta_470', 'bb_470', 'beta_700', 'bb_700', 'chl', 'pCO2_water', 'pCO2_air', 'pH' ]
##cl.wg_oa_startDatetime = startdate
##cl.wg_oa_endDatetime = enddate

######################################################################
#  WESTERN FLYER: not in this cruise
######################################################################
# UCTD
cl.wfuctd_base = cl.dodsBase + 'CANON/2015_May/Platforms/Ships/Western_Flyer/uctd/'
cl.wfuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.wfuctd_files = [
 
                  ]

# PCTD
cl.wfpctd_base = cl.dodsBase + 'CANON/2014_Sep/Platforms/Ships/Western_Flyer/pctd/'
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl' , 'oxygen']
cl.wfpctd_files = [
                  ]

######################################################################
#  RACHEL CARSON: May 2015 -- 
######################################################################
# UCTD
cl.rcuctd_base = cl.dodsBase + 'CANON/2015_May/Platforms/Ships/Rachel_Carson/uctd/'
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.rcuctd_files = [
                  '13115plm01.nc',
                  '13215plm01.nc',
                  '14115plm01.nc',
                  '14815plm01.nc',
                  '15515plm01.nc',
                  '15615plm01.nc',    
                  ]

# PCTD
cl.rcpctd_base = cl.dodsBase + 'CANON/2015_May/Platforms/Ships/Rachel_Carson/pctd/'
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.rcpctd_files = [
                  '13115c01.nc', '13115c02.nc', '13115c03.nc',
                  '13215c01.nc', '13215c02.nc', '13215c03.nc', '13215c04.nc', '13215c05.nc',
                  '14115c01.nc', '14115c02.nc', '14115c03.nc', '14115c04.nc',
                  '14815c01.nc', '14815c02.nc', '14815c03.nc', '14815c04.nc', '14815c05.nc', '14815c06.nc',
                  '15515c01.nc', '15515c02.nc', '15515c03.nc',
                  '15615c01.nc', '15615c02.nc', '15615c03.nc', '15615c04.nc', 
                  ]

#####################################################################
# JOHN MARTIN
#####################################################################
cl.JMpctd_base = cl.dodsBase + 'CANON/2015_May/Platforms/Ships/Martin/pctd/' 
cl.JMpctd_parms = ['TEMP', 'PSAL', 'xmiss', 'wetstar', 'oxygen' ]
cl.JMpctd_files = [
                    'EH15_18.nc', 'EH15_19.nc', 'EH15_20.nc', 'EH15_21.nc', 'EH15_22.nc', 'EH15_24.nc', 
                    'EH15_25.nc', 'EH15_26.nc', 'EH15_27.nc', 'EH15_28a.nc', 'EH15_29a.nc', 'EH15_29b.nc', 
                    'EH15_29.nc', 'EH15_30.nc', 'EH15_31.nc', 'EH15_Sta10a.nc', 'EH15_Sta11.nc', 'EH15_Sta12a.nc', 
                    'EH15_Sta12.nc', 'EH15_Sta13.nc', 'EH15_Sta14.nc', 'EH15_Sta15.nc', 'EH15_Sta16.nc', 'EH15_Sta17.nc', 
                    'EH15_Sta8b.nc', 'EH15_Sta9.nc', 
                  ]

######################################################################
#  MOORINGS May 2015
######################################################################
# Mooring M1 Combined file produced by DPforSSDS processing - for just the duration of the campaign
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/201407/'
cl.m1_files = [
                'OS_M1_20140716hourly_CMSTV.nc',
              ]
cl.m1_parms = [ 'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
                'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
                'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR',
              ]
cl.m1_startDatetime = startdate
cl.m1_endDatetime = enddate

# Mooring 0A1
cl.oa1_base = cl.dodsBase + 'CANON/2015_May/Platforms/Moorings/OA1/'
cl.oa1_files = [
               'OA1_Canon2015_May.nc'
               ]
cl.oa1_parms = [
               'wind_dir', 'avg_wind_spd', 'atm_press', 'air_temp', 'water_temp',
               'sal', 'O2_conc', 'chl', 'pCO2_water', 'pCO2_air', 'pH',
              ]
cl.oa1_startDatetime = startdate
cl.oa1_endDatetime = enddate

# Mooring 0A2
cl.oa2_base = cl.dodsBase + 'CANON/2015_May/Platforms/Moorings/OA2/'
cl.oa2_files = [
               'OA2_Canon2015_May.nc'
               ]
cl.oa2_parms = [
               'wind_dir', 'avg_wind_spd', 'atm_press', 'air_temp', 'water_temp',
               'sal', 'O2_conc', 'chl', 'pCO2_water', 'pCO2_air', 'pH',
               ]
cl.oa2_startDatetime = startdate
cl.oa2_endDatetime = enddate


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
#                                   13115 13215 14115 14815 15515 15615
#   copied to local BOG_Data/CANON_May2105 dir
###################################################################################################
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data/CANON_May2015/')
cl.subsample_csv_files = [
## these are loaded OK:

   'STOQS_13115_CARBON_GFF.csv', 'STOQS_13115_CHL_1U.csv', 'STOQS_13115_CHL_5U.csv', 'STOQS_13115_CHL_GFF.csv', 
   'STOQS_13115_CHLA.csv', 'STOQS_13115_NO2.csv', 'STOQS_13115_NO3.csv', 'STOQS_13115_PHAEO_1U.csv',
   'STOQS_13115_PHAEO_5U.csv', 'STOQS_13115_PHAEO_GFF.csv', 'STOQS_13115_PO4.csv', 'STOQS_13115_SIO4.csv',

   'STOQS_13215_CARBON_GFF.csv',

## error  no data
## 'STOQS_13215_CHL_1U.csv', ## error  no data
## 'STOQS_13215_CHL_5U.csv', ## error  no data

   'STOQS_13215_CHL_GFF.csv','STOQS_13215_CHLA.csv', 'STOQS_13215_NO2.csv', 'STOQS_13215_NO3.csv',

## error  no data
## 'STOQS_13215_PHAEO_1U.csv', ## error no data
## 'STOQS_13215_PHAEO_5U.csv', ## error no data

   'STOQS_13215_PHAEO_GFF.csv', 'STOQS_13215_PO4.csv', 'STOQS_13215_SIO4.csv',

   'STOQS_14115_CARBON_GFF.csv', 'STOQS_14115_CHL_1U.csv', 'STOQS_14115_CHL_5U.csv', 'STOQS_14115_CHL_GFF.csv', 
   'STOQS_14115_CHLA.csv', 'STOQS_14115_NO2.csv', 'STOQS_14115_NO3.csv', 'STOQS_14115_PHAEO_1U.csv',
   'STOQS_14115_PHAEO_5U.csv', 'STOQS_14115_PHAEO_GFF.csv', 'STOQS_14115_PO4.csv', 'STOQS_14115_SIO4.csv',
 
   'STOQS_14815_CARBON_GFF.csv', 'STOQS_14815_CHL_1U.csv', 'STOQS_14815_CHL_5U.csv', 'STOQS_14815_CHL_GFF.csv',
   'STOQS_14815_CHLA.csv', 'STOQS_14815_NO2.csv', 'STOQS_14815_NO3.csv', 'STOQS_14815_PHAEO_1U.csv',
   'STOQS_14815_PHAEO_5U.csv', 'STOQS_14815_PHAEO_GFF.csv', 'STOQS_14815_PO4.csv', 'STOQS_14815_SIO4.csv',
 
   'STOQS_15515_CARBON_GFF.csv', 'STOQS_15515_CHL_1U.csv', 'STOQS_15515_CHL_5U.csv', 'STOQS_15515_CHL_GFF.csv',
   'STOQS_15515_CHLA.csv', 'STOQS_15515_NO2.csv', 'STOQS_15515_NO3.csv', 'STOQS_15515_PHAEO_1U.csv',
   'STOQS_15515_PHAEO_5U.csv', 'STOQS_15515_PHAEO_GFF.csv', 'STOQS_15515_PO4.csv', 'STOQS_15515_SIO4.csv',                       

   'STOQS_15615_CARBON_GFF.csv', 'STOQS_15615_CHL_1U.csv', 'STOQS_15615_CHL_5U.csv', 'STOQS_15615_CHL_GFF.csv',
   'STOQS_15615_CHLA.csv', 'STOQS_15615_NO2.csv', 'STOQS_15615_NO3.csv', 'STOQS_15615_PHAEO_1U.csv',
   'STOQS_15615_PHAEO_5U.csv', 'STOQS_15615_PHAEO_GFF.csv', 'STOQS_15615_PO4.csv', 'STOQS_15615_SIO4.csv',

                       ]


###################################################################################################################

# Execute the load 
cl.process_command_line()

if cl.args.test:

    cl.loadL_662(stride=100) 
    ##cl.load_NPS29(stride=10)  ## not in this campaign
    ##cl.load_slocum_294(stride=10) ## waiting for STOQS enhancement to load slocum_294
    ##cl.load_slocum_260(stride=10) ## waiting for STOQS enhancement to load slocum_294

    ##cl.load_wg_tex(stride=10) ## not in this campaign
    cl.load_wg_Tiny(stride=10)
    ##cl.load_wg_oa(stride=10)  ## waiting for data to be formated for loading

    cl.loadDorado(stride=100)

    cl.loadRCuctd(stride=10)
    cl.loadRCpctd(stride=10)
    ##cl.loadJMuctd(stride=10) ## waiting for data to be formated for loading
    cl.loadJMpctd(stride=10)
    ##cl.loadWFuctd(stride=10) ## not in this campaign   
    ##cl.loadWFpctd(stride=10) ## not in this campaign

    cl.loadM1(stride=10)

    ##cl.loadBruceMoor(stride=10) ## waiting for data to be formated for loading
    ##cl.loadMackMoor(stride=10) ## waiting for data to be formated for loading

    cl.loadSubSamples() ## need to populate local directory /loaders/CANON/BOG_Data/CANON_May2015/ with sample files 

elif cl.args.optimal_stride:

    cl.loadL_662(stride=2)
    ##cl.load_NPS29(stride=2)  ## not in this campaign
    ##cl.load_slocum_294(stride=2) ## waiting for STOQS enhancement to load slocum_294
    ##cl.load_slocum_260(stride=2) ## waiting for STOQS enhancement to load slocum_294

    ##cl.load_wg_tex(stride=2) ## not in this campaign
    cl.load_wg_Tiny(stride=2)
    ##cl.load_wg_oa(stride=2)  ## waiting for data to be formated for loading

    cl.loadDorado(stride=2)

    cl.loadRCuctd(stride=2)
    cl.loadRCpctd(stride=2)
    ##cl.loadJMuctd(stride=2) ## waiting for data to be formated for loading
    cl.loadJMpctd(stride=2)
    ##cl.loadWFuctd(stride=2) ## not in this campaign   
    ##cl.loadWFpctd(stride=2) ## not in this campaign

    cl.loadM1(stride=1)

    ##cl.loadBruceMoor(stride=2) ## waiting for data to be formated for loading
    ##cl.loadMackMoor(stride=2) ## waiting for data to be formated for loading

    cl.loadSubSamples() ## need to populate local directory /loaders/CANON/BOG_Data/CANON_May2015/ with sample files 

else:
    cl.stride = cl.args.stride

    cl.loadL_662()
    ##cl.load_NPS29()  ## not in this campaign
    ##cl.load_slocum_294() ## waiting for STOQS enhancement to load slocum_294
    ##cl.load_slocum_260() ## waiting for STOQS enhancement to load slocum_294

    ##cl.load_wg_tex() ## not in this campaign
    cl.load_wg_Tiny()
    ##cl.load_wg_oa()  ## waiting for data to be formated for loading

    cl.loadDorado()

    cl.loadRCuctd()
    cl.loadRCpctd()
    ##cl.loadJMuctd() ## waiting for data to be formated for loading
    cl.loadJMpctd()
    ##cl.loadWFuctd() ## not in this campaign   
    ##cl.loadWFpctd() ## not in this campaign

    cl.loadM1()
    cl.load_oa1()
    cl.load_oa2()


    ##cl.loadBruceMoor() ## waiting for data to be formated for loading
    ##cl.loadMackMoor() ## waiting for data to be formated for loading

    cl.loadSubSamples() ## need to populate local directory /loaders/CANON/BOG_Data/CANON_May2015/ with sample files 

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")


