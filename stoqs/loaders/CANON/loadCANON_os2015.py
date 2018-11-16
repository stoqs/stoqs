#!/usr/bin/env python
__author__    = 'Mike McCann,Duane Edgington,Reiko Michisaki'
__copyright__ = '2015'
__license__   = 'GPL v3'
__contact__   = 'duane at mbari.org'

__doc__ = '''

Master loader for all CANON off season activities in 2015

Mike McCann, Duane Edgington, Danelle Cline
MBARI 4 August 2015

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
import urllib.parse
import requests

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
from thredds_crawler.crawl import Crawl
from lxml import etree
import timing

cl = CANONLoader('stoqs_os2015', 'CANON-ECOHAB - Off Season 2015',
                    description = 'CANON Off Season 2015 Experiment in Monterey Bay',
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
#
#startdate = datetime.datetime(2015, 7, 31)                 # Fixed start
startdate = datetime.datetime(2015, 6, 6)                 # Fixed start

#enddate = datetime.datetime(2015, 9, 30)                  # Fixed end
enddate = datetime.datetime(2015, 12, 31)                  # Fixed end. Extend "offseason" to end of year

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

#####################################################################
#  LRAUV 
#####################################################################

# Load netCDF files produced (binned, etc.) by Danelle Cline
# These binned files are created with the makeLRAUVNetCDFs.sh script in the
# toNetCDF directory. You must first edit and run that script once to produce
# the binned files before this will work

# TDS server is crawled and attributes are set in the loadLRAUV() calls below


######################################################################
#  GLIDERS
######################################################################
# Glider data files from CeNCOOS thredds server
# L_662
# cl.l_662_base = 'http://www.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_files = [ 'OS_Glider_L_662_20150813_TS.nc' ]
# OS_Glider_L_662_20150813_TS.nc most recent deployment
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = startdate
cl.l_662_endDatetime = enddate

# NPS_29
#cl.nps29_base = 'http://www.cencoos.org/thredds/dodsC/gliders/Line66/'
#cl.nps29_files = [ 'OS_Glider_NPS_G29_20140930_TS.nc' ]
cl.nps29_parms = ['TEMP', 'PSAL']
cl.nps29_startDatetime = startdate
cl.nps29_endDatetime = enddate

# UCSC_294
#cl.ucsc294_base = 'http://data.ioos.us/gliders/thredds/dodsC/deployments/mbari/UCSC294-20150430T2218/'
#cl.ucsc294_files = [ 'UCSC294-20150430T2218.nc3.nc' ]
#cl.ucsc294_parms = ['TEMP', 'PSAL']
#cl.ucsc294_startDatetime = startdate
#cl.ucsc294_endDatetime = enddate

# UCSC_260
#cl.ucsc260_base = 'http://data.ioos.us/gliders//thredds/dodsC/deployments/mbari/UCSC260-20150520T0000/'
#cl.ucsc260_files = [ 'UCSC260-20150520T0000.nc3.nc'  ]
#cl.ucsc260_parms = ['TEMP', 'PSAL']
#cl.ucsc260_startDatetime = startdate
#cl.ucsc260_endDatetime = enddate


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
cl.wg_Tiny_base = cl.dodsBase + 'CANON/2015_OffSeason/Platforms/Waveglider/wgTiny/'
cl.wg_Tiny_files = [ 
                     'SV3_20150611_QC.nc',
                     'SV3_20151019.nc',    # starts after end of Fall 2015 campaign
                   ]

cl.wg_Tiny_parms = [ 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal',  'bb_470', 'bb_650', 'chl',
                    'beta_470', 'beta_650', 'pCO2_water', 'pCO2_air', 'pH', 'O2_conc' ]
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
cl.rcuctd_base = cl.dodsBase + 'CANON/2015_OffSeason/Platforms/Ships/Rachel_Carson/uctd/'
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.rcuctd_files = [
                 '18815plm01.nc',
                 '21515plm01.nc',
                 '23715plm01.nc',
                  ]

# PCTD
cl.rcpctd_base = cl.dodsBase + 'CANON/2015_OffSeason/Platforms/Ships/Rachel_Carson/pctd/'
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.rcpctd_files = [
                  '18815c01.nc', '18815c02.nc', '18815c03.nc',
                  '21515c01.nc', '21515c02.nc', '21515c03.nc', 
                  '23715c01.nc', '23715c02.nc', '23715c03.nc',
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
#  MOORINGS May 2015
######################################################################
# Mooring M1 Combined file produced by DPforSSDS processing - for just the duration of the campaign
# M1 had a turnaround on July 29, 2015
# http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/201507/OS_M1_20150729hourly_CMSTV.nc
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/201507/'
cl.m1_files = [
#                'OS_M1_20150729hourly_CMSTV.nc'
                 'OS_M1_20150730hourly_CMSTV.nc'
              ]
cl.m1_parms = [
                'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
                'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
                'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR'
              ]

cl.m1_startDatetime = startdate
cl.m1_endDatetime = enddate

# Mooring 0A1
cl.oa1_base = cl.dodsBase + 'CANON/2015_OffSeason/Platforms/Moorings/OA1/'
cl.oa1_files = [
               'OA1_Canon2015_OffSeason.nc'
               ]
cl.oa1_parms = [
               'wind_dir', 'avg_wind_spd', 'atm_press', 'air_temp', 'water_temp',
               'sal', 'O2_conc', 'chl', 'pCO2_water', 'pCO2_air', 'pH',
              ]
cl.oa1_startDatetime = startdate
cl.oa1_endDatetime = enddate

# Mooring 0A2
cl.oa2_base = cl.dodsBase + 'CANON/2015_OffSeason/Platforms/Moorings/OA2/'
cl.oa2_files = [
               'OA2_Canon2015_OffSeason.nc'
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
#                                   18815 and 21515
#   copied to local BOG_Data/CANON_OS2105 dir
###################################################################################################
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data/CANON_OS2015/')
cl.subsample_csv_files = [
    'STOQS_18815_CARBON_GFF.csv', 'STOQS_18815_CHLA.csv', 'STOQS_18815_CHL_1U.csv', 'STOQS_18815_CHL_5U.csv',
    'STOQS_18815_CHL_GFF.csv', 'STOQS_18815_NO2.csv', 'STOQS_18815_NO3.csv', 'STOQS_18815_PHAEO_1U.csv',
    'STOQS_18815_PHAEO_5U.csv', 'STOQS_18815_PHAEO_GFF.csv', 'STOQS_18815_PO4.csv', 'STOQS_18815_SIO4.csv',

    'STOQS_21515_CARBON_GFF.csv', 'STOQS_21515_CHLA.csv', 'STOQS_21515_CHL_1U.csv', 'STOQS_21515_CHL_5U.csv',
    'STOQS_21515_CHL_GFF.csv', 'STOQS_21515_NO2.csv', 'STOQS_21515_NO3.csv', 'STOQS_21515_PHAEO_1U.csv',
    'STOQS_21515_PHAEO_5U.csv', 'STOQS_21515_PHAEO_GFF.csv','STOQS_21515_PO4.csv', 'STOQS_21515_SIO4.csv',

                          ]

###################################################################################################################

# Execute the load 
cl.process_command_line()

if cl.args.test:
    cl.stride = 100
else:
    cl.stride = cl.args.stride

cl.loadL_662()
##cl.load_NPS29()
##cl.load_UCSC294() 
##cl.load_UCSC260()
cl.load_wg_Tiny()
cl.loadM1()
cl.load_oa1()
cl.load_oa2()
##cl.loadDorado()
cl.loadLRAUV('daphne', startdate, enddate)
cl.loadLRAUV('tethys', startdate, enddate)
cl.loadLRAUV('makai', startdate, enddate)
cl.loadRCuctd()
cl.loadRCpctd()
##cl.loadWFuctd()   
##cl.loadWFpctd()

cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

