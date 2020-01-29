#!/usr/bin/env python
__author__    = 'Mike McCann,Duane Edgington,Reiko Michisaki'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for all Worden's CN13ID Western Flyer cruise in October 2013
CN13ID: CANON 2013 Interdisciplinary

Mike McCann
MBARI 23 October 2013

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime  # needed for glider data
import time      # for startdate, enddate args
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE']='config.settings.local'
project_dir = os.path.dirname(__file__)

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
import timing
       
# building input data sources object
cl = CANONLoader('stoqs_cn13id_oct2013', 'CN13ID - October 2013',
                        description = 'Warden cruise on Western Flyer into the California Current System off Monterey Bay',
                        x3dTerrains = {
                            'https://stoqs.mbari.org/x3d/Globe_1m_bath_10x/Globe_1m_bath_10x_scene.x3d': {
                                'position': '14051448.48336 -15407886.51486 6184041.22775',
                                'orientation': '0.83940 0.33030 0.43164 1.44880',
                                'centerOfRotation': '0 0 0',
                                'VerticalExaggeration': '10',
                            }
                        },
                        grdTerrain = os.path.join(parentDir, 'Globe_1m_bath.grd')
                )

# Set start and end dates for all loads from sources that contain data 
# beyond the temporal bounds of the campaign
startdate = datetime.datetime(2013, 10, 6)                  # Fixed start
enddate = datetime.datetime(2013, 10, 18)                   # Fixed end

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'

#####################################################################
#  DORADO 
#####################################################################
# special location for dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2013/netcdf/'
cl.dorado_files = [
                   'Dorado389_2013_280_01_280_01_decim.nc',
                   'Dorado389_2013_282_00_282_00_decim.nc',
                   'Dorado389_2013_283_00_283_00_decim.nc',
                   'Dorado389_2013_287_01_287_01_decim.nc',
				   ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700', 
                    'fl700_uncorr', 'salinity', 'biolume',
                    'sepCountList', 'mepCountList',
                    'roll', 'pitch', 'yaw',
                  ]


######################################################################
#  GLIDERS
######################################################################

# SPRAY glider - for just the duration of the campaign
cl.l_662_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_files = ['OS_Glider_L_662_20130711_TS.nc']
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = startdate
cl.l_662_endDatetime = enddate


######################################################################
#  WESTERN FLYER: October 6-17
######################################################################
# UCTD
cl.wfuctd_base = cl.dodsBase + 'CANON_october2013/Platforms/Ships/Western_Flyer/uctd/'
cl.wfuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.wfuctd_files = [ 
'CN13IDm01.nc', 'CN13IDm02.nc', 'CN13IDm03.nc', 'CN13IDm04.nc', 'CN13IDm05.nc', 'CN13IDm06.nc', 'CN13IDm07.nc', 'CN13IDm08.nc', 'CN13IDm09.nc', 'CN13IDm10.nc',
'CN13IDm11.nc', 'CN13IDm12.nc', 'CN13IDm13.nc', 'CN13IDm14.nc',
                      ]

# PCTD
cl.pctdDir = 'CANON_october2013/Platforms/Ships/Western_Flyer/pctd/'
cl.wfpctd_base = cl.dodsBase + cl.pctdDir
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl' , 'oxygen']
cl.wfpctd_files = [ 
'CN13IDc01.nc', 'CN13IDc02.nc', 'CN13IDc03.nc', 'CN13IDc04.nc', 'CN13IDc05.nc', 'CN13IDc06.nc', 'CN13IDc07.nc', 'CN13IDc08.nc', 'CN13IDc09.nc', 'CN13IDc10.nc',
'CN13IDc11.nc', 'CN13IDc12.nc', 'CN13IDc13.nc', 'CN13IDc14.nc', 'CN13IDc15.nc', 'CN13IDc16.nc', 'CN13IDc17.nc', 'CN13IDc18.nc', 'CN13IDc19.nc', 'CN13IDc20.nc',
'CN13IDc21.nc', 'CN13IDc22.nc', 'CN13IDc23.nc', 'CN13IDc24.nc', 'CN13IDc25.nc', 'CN13IDc26.nc', 'CN13IDc27.nc', 'CN13IDc28.nc', 'CN13IDc29.nc', 'CN13IDc30.nc',
'CN13IDc31.nc', 'CN13IDc32.nc', 'CN13IDc33.nc', 'CN13IDc34.nc', 'CN13IDc35.nc', 'CN13IDc36.nc', 'CN13IDc37.nc', 'CN13IDc38.nc', 'CN13IDc39.nc', 'CN13IDc40.nc',
'CN13IDc41.nc', 'CN13IDc42.nc', 'CN13IDc43.nc', 'CN13IDc44.nc', 'CN13IDc45.nc', 'CN13IDc46.nc', 'CN13IDc47.nc', 'CN13IDc48.nc', 'CN13IDc49.nc', 'CN13IDc50.nc',
##'CN13IDc51.nc', 'CN13IDc52.nc', 'CN13IDc53.nc', 'CN13IDc54.nc', 
]

# BCTD
# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/GOC12/ copied to local BOG_Data dir
cl.bctdDir = 'CANON_october2013/Platforms/Ships/Western_Flyer/bctd/'
cl.subsample_csv_base = cl.dodsBase + cl.bctdDir
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data')
cl.subsample_csv_files = [
                            #'STOQS_canon13_CHL_1U.csv', 'STOQS_canon13_CHL_5U.csv', 'STOQS_canon13_NH4.csv', 'STOQS_canon13_NO2.csv',
                    		#'STOQS_canon13_NO3.csv','STOQS_canon13_OXY_ML.csv', 'STOQS_canon13_PHAEO_1U.csv', 'STOQS_canon13_PHAEO_5U.csv',
                            #'STOQS_canon13_PHAEO_GFF.csv', 'STOQS_canon13_PO4.csv', 'STOQS_canon13_SIO4.csv', #'STOQS_canon13_CARBON_GFF.csv
							#'STOQS_canon13_CHL_GFF.csv',
                         ]

######################################################################
#  MOORINGS
######################################################################
# Mooring M1 Combined file produced by DPforSSDS processing - for just the duration of the campaign
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/'
cl.m1_files = [
                '201309/OS_M1_20130918hourly_CMSTV.nc'
              ]
cl.m1_parms = [ 'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
                'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
                'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR'
              ]
cl.m1_startDatetime = startdate
cl.m1_endDatetime = enddate


# Mooring OA1 CTD
cl.oaDir = 'CANON_september2013/Platforms/Moorings/OA_1/'
cl.OA1ctd_base = cl.dodsBase + cl.oaDir
cl.OA1ctd_files = ['OA1_ctd_2013.nc']
cl.OA1ctd_parms = ['TEMP', 'PSAL', 'conductivity' ]
cl.OA1ctd_startDatetime = startdate
cl.OA1ctd_endDatetime = enddate
# Mooring OA1 MET
cl.OA1met_base = cl.dodsBase + cl.oaDir
cl.OA1met_files = ['OA1_met_2013.nc']
cl.OA1met_parms = ['Wind_direction','Wind_speed','Air_temperature','Barometric_pressure']
cl.OA1met_startDatetime = startdate
cl.OA1met_endDatetime = enddate
# Mooring OA1 PH
cl.OA1pH_base = cl.dodsBase + cl.oaDir
cl.OA1pH_files = ['OA1_pH_2013.nc']
cl.OA1pH_parms = ['pH' ]
cl.OA1pH_startDatetime = startdate
cl.OA1pH_endDatetime = enddate
# Mooring OA1 PCO2
cl.OA1pco2_base = cl.dodsBase + cl.oaDir
cl.OA1pco2_files = ['OA1_pco2_2013.nc']
cl.OA1pco2_parms = ['pCO2' ]
cl.OA1pco2_startDatetime = startdate
cl.OA1pco2_endDatetime = enddate
# Mooring OA1 O2
cl.OA1o2_base = cl.dodsBase + cl.oaDir
cl.OA1o2_files = ['OA1_o2_2013.nc']
cl.OA1o2_parms = ['oxygen', 'oxygen_saturation' ]
cl.OA1o2_startDatetime = startdate
cl.OA1o2_endDatetime = enddate
# Mooring OA1 Fluorescence
cl.OA1fl_base = cl.dodsBase + cl.oaDir
cl.OA1fl_files = ['OA1_fl_2013.nc']
cl.OA1fl_parms = [ 'fluor' ]
cl.OA1fl_startDatetime = startdate
cl.OA1fl_endDatetime = enddate
 
# Mooring OA2 CTD
cl.oaDir = 'CANON_september2013/Platforms/Moorings/OA_2/'
cl.OA2ctd_base = cl.dodsBase + cl.oaDir
cl.OA2ctd_files = ['OA2_ctd_2013.nc']
cl.OA2ctd_parms = ['TEMP', 'PSAL', 'conductivity' ]
cl.OA2ctd_startDatetime = startdate
cl.OA2ctd_endDatetime = enddate
# Mooring OA2 MET
cl.OA2met_base = cl.dodsBase + cl.oaDir
cl.OA2met_files = ['OA2_met_2013.nc']
cl.OA2met_parms = ['Wind_direction','Wind_speed','Air_temperature','Barometric_pressure']
cl.OA2met_startDatetime = startdate
cl.OA2met_endDatetime = enddate
# Mooring OA2 PH
cl.OA2pH_base = cl.dodsBase + cl.oaDir
cl.OA2pH_files = ['OA2_pH_2013.nc']
cl.OA2pH_parms = ['pH' ]
cl.OA2pH_startDatetime = startdate
cl.OA2pH_endDatetime = enddate
# Mooring OA2 PCO2
cl.OA2pco2_base = cl.dodsBase + cl.oaDir
cl.OA2pco2_files = ['OA2_pco2_2013.nc']
cl.OA2pco2_parms = ['pCO2' ]
cl.OA2pco2_startDatetime = startdate
cl.OA2pco2_endDatetime = enddate
# Mooring OA2 O2
cl.OA2o2_base = cl.dodsBase + cl.oaDir
cl.OA2o2_files = ['OA2_o2_2013.nc']
cl.OA2o2_parms = ['oxygen', 'oxygen_saturation' ]
cl.OA2o2_startDatetime = startdate
cl.OA2o2_endDatetime = enddate
# Mooring OA2 Fluorescence
cl.OA2fl_base = cl.dodsBase + cl.oaDir
cl.OA2fl_files = ['OA2_fl_2013.nc']
cl.OA2fl_parms = [ 'fluor' ]
cl.OA2fl_startDatetime = startdate
cl.OA2fl_endDatetime = enddate

######################################################################################################
# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/CN13ID copied to local BOG_Data/CN13ID
######################################################################################################
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data/CN13ID')
cl.subsample_csv_files = [
'STOQS_CN13ID_CARBON_GFF.csv', 'STOQS_CN13ID_CHL_1U.csv', 'STOQS_CN13ID_CHL_5U.csv', 'STOQS_CN13ID_CHLA.csv',
'STOQS_CN13ID_CHL_GFF.csv', 'STOQS_CN13ID_PHAEO_1U.csv', 'STOQS_CN13ID_PHAEO_5U.csv', 'STOQS_CN13ID_PHAEO_GFF.csv',
                         ]
 

###################################################################################################################
# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadWFuctd(stride=100)     
    cl.loadWFpctd(stride=50)
    cl.loadL_662(stride=10) 
    cl.loadDorado(stride=1000)
    cl.loadM1(stride=10)
    cl.loadOA1ctd(stride=10)
    cl.loadOA1met(stride=10)

    cl.loadOA1pH(stride=10)
    cl.loadOA1pco2(stride=10)
    cl.loadOA1fl(stride=10)
    cl.loadOA1o2(stride=10)
    cl.loadOA2ctd(stride=10)
    cl.loadOA2met(stride=10)
    cl.loadOA2pH(stride=10)
    cl.loadOA2pco2(stride=10)
    cl.loadOA2fl(stride=10)
    cl.loadOA2o2(stride=10)

    cl.loadSubSamples()

elif cl.args.optimal_stride:
    cl.loadWFuctd(stride=1)     
    cl.loadWFpctd(stride=1)
    cl.loadL_662(stride=1) 
    cl.loadDorado(stride=1)
    cl.loadM1(stride=1)
    cl.loadOA1ctd(stride=1)
    cl.loadOA1met(stride=1)

    cl.loadOA1pH(stride=1)
    cl.loadOA1pco2(stride=1)
    cl.loadOA1fl(stride=1)
    cl.loadOA1o2(stride=1)
    cl.loadOA2ctd(stride=1)
    cl.loadOA2met(stride=1)
    cl.loadOA2pH(stride=1)
    cl.loadOA2pco2(stride=1)
    cl.loadOA2fl(stride=1)
    cl.loadOA2o2(stride=1)

    cl.loadSubSamples()

else:
    cl.stride = cl.args.stride

    cl.loadWFuctd()     
    cl.loadWFpctd()
    cl.loadL_662() 
    cl.loadDorado()
    cl.loadM1()
    cl.loadOA1ctd()
    cl.loadOA1met()

    cl.loadOA1pH()
    cl.loadOA1pco2()
    cl.loadOA1fl()
    cl.loadOA1o2()
    cl.loadOA2ctd()
    cl.loadOA2met()
    cl.loadOA2pH()
    cl.loadOA2pco2()
    cl.loadOA2fl()
    cl.loadOA2o2()

    cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

