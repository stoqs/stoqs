#!/usr/bin/env python
__author__    = 'Mike McCann,Duane Edgington,Reiko Michisaki'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'duane at mbari.org'

__doc__ = '''

Master loader for all CANON activities in September 2013

Mike McCann; Modified from  Duane Edgington and Reiko Michisaki's work
MBARI 18 September 2013

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
       
cl = CANONLoader('stoqs_september2013', 'CANON-ECOHAB - September 2013', 
                    description = 'Intensive 27 platform observing campaign in Monterey Bay',
                    x3dTerrains = {
                        'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                            'position': '-2822317.31255 -4438600.53640 3786150.85474',
                            'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                            'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                            'VerticalExaggeration': '10',
                            'speed': '.1',
                        }
                    },
                    grdTerrain = os.path.join(parentDir, 'Monterey25.grd')
                  )

# Set start and end dates for all loads from sources that contain data 
# beyond the temporal bounds of the campaign
startdate = datetime.datetime(2013, 9, 9)                  # Fixed start
enddate = datetime.datetime(2013, 10, 17)                  # Fixed end

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'

#####################################################################
#  DORADO 
#####################################################################
# special location for dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2013/netcdf/'
cl.dorado_files = [
                   'Dorado389_2013_259_00_259_00_decim.nc',
                   'Dorado389_2013_260_00_260_00_decim.nc',
                   'Dorado389_2013_261_01_261_01_decim.nc',
                   'Dorado389_2013_262_00_262_00_decim.nc',
                   'Dorado389_2013_262_01_262_01_decim.nc',
                   'Dorado389_2013_268_00_268_00_decim.nc',
                   'Dorado389_2013_273_00_273_00_decim.nc',
                   'Dorado389_2013_274_00_274_00_decim.nc',
                   'Dorado389_2013_275_00_275_00_decim.nc',
                   'Dorado389_2013_276_00_276_00_decim.nc',
				   ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                    'fl700_uncorr', 'salinity', 'biolume', 'rhodamine',
                    'sepCountList', 'mepCountList',
                    'roll', 'pitch', 'yaw',
                  ]

#####################################################################
#  LRAUV 
#####################################################################
# NetCDF files produced (binned, etc.) by John Ryan
cl.tethys_base = cl.dodsBase + 'CANON_september2013/Platforms/AUVs/Tethys/NetCDF/'
cl.tethys_files = ['Tethys_CANON_Fall2013.nc']
cl.tethys_parms = ['temperature', 'salinity', 'chlorophyll', 'bb470', 'bb650']

cl.daphne_base = cl.dodsBase + 'CANON_september2013/Platforms/AUVs/Daphne/NetCDF/'
cl.daphne_files = ['Daphne_CANON_Fall2013.nc']
cl.daphne_parms = ['temperature', 'chlorophyll', 'bb470', 'bb650']


######################################################################
#  GLIDERS
######################################################################
# Glider data files from CeNCOOS thredds server
# L_662
cl.l_662_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_files = ['OS_Glider_L_662_20130711_TS.nc']
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = startdate
cl.l_662_endDatetime = enddate

# NPS_34
cl.nps34_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.nps34_files = [ 'OS_Glider_NPS_G34_20130829_TS.nc']
cl.nps34_parms = ['TEMP', 'PSAL']
cl.nps34_startDatetime = startdate
cl.nps34_endDatetime = enddate

# NPS_29
cl.nps29_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.nps29_files = [ 'OS_Glider_NPS_G29_20130829_TS.nc']
cl.nps29_parms = ['TEMP', 'PSAL', 'OPBS']
cl.nps29_startDatetime = startdate
cl.nps29_endDatetime = enddate


# Other gliders - served from campaign's TDS catalog
# Slocum_260
cl.slocum_260_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/Slocum_260/final/'
cl.slocum_260_files = [ 'glider-260_20130908T204654_rt0.nc' ]
cl.slocum_260_parms = [ 'temperature', 'salinity', 'density', 'fluorescence', 'oxygen', 'optical_backscatter700nm', 
                        ##'u', 'v'      # NetCDF file needs a depth in the coordinates attributes
                      ]
cl.slocum_260_startDatetime = startdate
cl.slocum_260_endDatetime = enddate

# Slocum_294
cl.slocum_294_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/Slocum_294/final/'
cl.slocum_294_files = [ 'glider-294_20130903T013548_rt0.nc' ]
cl.slocum_294_parms = [ 'temperature', 'salinity', 'density', 'fluorescence', 'oxygen', 'phycoerythrin', 'cdom', 
                        'optical_backscatter470nm', 'optical_backscatter532nm', 'optical_backscatter660nm', 'optical_backscatter700nm', 
                        ##'u', 'v'      # NetCDF file needs a depth in the coordinates attributes
                      ]
cl.slocum_294_startDatetime = startdate
cl.slocum_294_endDatetime = enddate

# Slocum Teledyne nemesis Glider
cl.slocum_nemesis_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/Slocum_Teledyne/final/'
cl.slocum_nemesis_files = [ 'glider-nemesis_20130716T221027_rt0.nc' ]
cl.slocum_nemesis_parms = [ 'temperature', 'salinity', 'u', 'v']
cl.slocum_nemesis_startDatetime = startdate
cl.slocum_nemesis_endDatetime = enddate

######################################################################
# Wavegliders
######################################################################
# WG Tex - All instruments combined into one file - one time coordinate
cl.wg_tex_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/WG_Tex/final/'
cl.wg_tex_files = [ 'WG_Tex_all_final.nc' ]
cl.wg_tex_parms = [ 'wind_dir', 'wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal', 'density', 'bb_470', 'bb_650', 'chl' ]
cl.wg_tex_startDatetime = startdate
cl.wg_tex_endDatetime = enddate

# WG OA - All instruments combined into one file - one time coordinate
cl.wg_oa_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/WG_OA/final/'
cl.wg_oa_files = [ 'Sept_2013_OAWaveglider_final.nc' ]
cl.wg_oa_parms = [ 'distance', 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal', 'O2_conc',
                   'O2_sat', 'beta_470', 'bb_470', 'beta_700', 'bb_700', 'chl', 'pCO2_water', 'pCO2_air', 'pH' ]
cl.wg_oa_startDatetime = startdate
cl.wg_oa_endDatetime = enddate

######################################################################
#  WESTERN FLYER: September 20-27
######################################################################
# UCTD
cl.wfuctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Ships/Western_Flyer/uctd/'
cl.wfuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.wfuctd_files = [ 
'canon13m01.nc', 'canon13m02.nc', 'canon13m03.nc', 'canon13m04.nc', 'canon13m05.nc', 'canon13m06.nc', 'canon13m07.nc', 'canon13m08.nc',
'canon13m09.nc', 'canon13m10.nc', 'canon13m11.nc', 
                  ]

# PCTD
cl.wfpctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Ships/Western_Flyer/pctd/'
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl' , 'oxygen']
cl.wfpctd_files = [ 
'canon13c01.nc', 'canon13c02.nc', 'canon13c03.nc', 'canon13c04.nc', 'canon13c05.nc', 'canon13c06.nc', 'canon13c07.nc',
'canon13c08.nc', 'canon13c09.nc', 'canon13c10.nc', 'canon13c11.nc', 'canon13c12.nc', 'canon13c13.nc', 'canon13c14.nc',
'canon13c15.nc', 'canon13c16.nc', 'canon13c17.nc', 'canon13c18.nc', 'canon13c19.nc', 
                  ]

######################################################################
#  RACHEL CARSON: September 16-20? (259-262) Sep 30 - Oct 3
######################################################################
# UCTD
cl.rcuctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Ships/Rachel_Carson/uctd/'
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.rcuctd_files = [ 
                    '25913RCm01.nc', '26013RCm01.nc', '26113RCm01.nc', '27313RCm01.nc', '27413RCm01.nc', '27513RCm01.nc',
                  ]

# PCTD
cl.rcpctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Ships/Rachel_Carson/pctd/'
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.rcpctd_files = [ 
                    '25913RCc01.nc', '25913RCc02.nc', '25913RCc03.nc', '26013RCc01.nc',
                    '26113RCc01.nc',
                    '27313RCc01.nc', '27313RCc02.nc', '27313RCc03.nc',
                    '27413RCc01.nc', '27413RCc02.nc', '27413RCc03.nc',
                    '27513RCc01.nc', '27513RCc02.nc',
                    '27613RCc01.nc', '27613RCc02.nc', '27613RCc03.nc', '27613RCc04.nc', '27613RCc05.nc',
                      ]

#####################################################################
# JOHN MARTIN
#####################################################################
cl.JMuctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Ships/Martin/uctd/' 
cl.JMuctd_parms = ['TEMP', 'PSAL', 'turb_scufa', 'fl_scufa' ]
cl.JMuctd_files = [ 'jhmudas_2013101.nc', 'jhmudas_2013102.nc', 'jhmudas_2013103.nc', 'jhmudas_2013911.nc', 'jhmudas_2013913.nc', 
                    'jhmudas_2013916.nc', 'jhmudas_2013917.nc', 'jhmudas_2013919.nc', 'jhmudas_2013923.nc', 'jhmudas_2013930.nc', ]

cl.JMpctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Ships/Martin/pctd/' 
cl.JMpctd_parms = ['TEMP', 'PSAL', 'xmiss', 'wetstar', 'oxygen' ]
cl.JMpctd_files = [ 
                    '25613JMC01.nc', '25613JMC02.nc', '25613JMC03.nc', '25613JMC04.nc', '25613JMC05.nc', 
                    '26013JMC01.nc', '26013JMC02.nc', '26013JMC03.nc', '26013JMC04.nc', 
                    '26213JMC01.nc', '26213JMC02.nc', '26213JMC03.nc', '26213JMC04.nc', '26213JMC05.nc', '26613JMC01.nc',
                    '26613JMC02i1.nc', '26613JMC02.nc', '26613JMC03.nc', '27513JMC01.nc', '27513JMC02.nc', '27513JMC03.nc', 
                    '27513JMC04.nc', '27513JMC05.nc', '27613JMC01.nc', '27613JMC02.nc', '27613JMC03.nc', '27613JMC04.nc',
                  ]

######################################################################
#  MOORINGS
######################################################################
# Mooring M1 Combined file produced by DPforSSDS processing - for just the duration of the campaign
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/'
cl.m1_files = [
                '201202/OS_M1_20120222hourly_CMSTV.nc', 
                '201309/OS_M1_20130918hourly_CMSTV.nc',
                '201202/m1_hs2_20120222.nc',
                '201309/m1_hs2_20130919.nc',
              ]
cl.m1_parms = [ 'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
                'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
                'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR', 'bb470', 'bb676', 'fl676'
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
 
#######################################################################################
# DRIFTERS
#######################################################################################
# Stella drifters, requires input file stella_load.csv with the names of the 

cl.stella_base = cl.dodsBase + 'CANON_september2013/Platforms/Drifters/Stella_1/'
cl.stella_parms = [ 'TEMP', 'pH' ]
cl.stella_files = [ 
                    'stella202_data.nc',
                    'stella203_data.nc', 'stella204_data.nc', 'stella205_data.nc'
                  ]

#######################################################################################
# ESP MOORINGS
#######################################################################################
cl.bruce_moor_base = cl.dodsBase + 'CANON_september2013/Platforms/Moorings/ESP_Bruce/NetCDF/'
cl.bruce_moor_files = ['Bruce_ctd.nc']
cl.bruce_moor_parms = [ 'TEMP','PSAL','chl','xmiss','oxygen','beamc',
                   ]
cl.bruce_moor_startDatetime = startdate
cl.bruce_moor_endDatetime = enddate

cl.mack_moor_base = cl.dodsBase + 'CANON_september2013/Platforms/Moorings/ESP_Mack/NetCDF/'
cl.mack_moor_files = ['Mack_ctd.nc']
cl.mack_moor_parms = [ 'TEMP','PSAL','chl','xmiss','oxygen','beamc',
                   ]
cl.mack_moor_startDatetime = startdate
cl.mack_moor_endDatetime = enddate

###################################################################################################
# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/ 
#                                   CANON13 25913RC 25913RC 26113RC 27313RC 27413RC 27513RC 27613RC
#   copied to local CANON2013 dir
###################################################################################################
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data/CANON2013')
cl.subsample_csv_files = [
'STOQS_CANON13_CARBON_GFF.csv', 'STOQS_CANON13_CHL_1U.csv', 'STOQS_CANON13_CHL_5U.csv', 'STOQS_CANON13_CHLA.csv',
'STOQS_CANON13_CHL_GFF.csv', 'STOQS_CANON13_NO2.csv', 'STOQS_CANON13_NO3.csv', 'STOQS_CANON13_PHAEO_1U.csv',
'STOQS_CANON13_PHAEO_5U.csv', 'STOQS_CANON13_PHAEO_GFF.csv', 'STOQS_CANON13_PO4.csv', 'STOQS_CANON13_SIO4.csv',

'STOQS_25913RC_CHL_1U.csv', 'STOQS_25913RC_CHL_5U.csv', 'STOQS_25913RC_CHLA.csv', 'STOQS_25913RC_CHL_GFF.csv',
'STOQS_25913RC_NO2.csv', 'STOQS_25913RC_NO3.csv', 'STOQS_25913RC_PHAEO_1U.csv', 'STOQS_25913RC_PHAEO_5U.csv',
'STOQS_25913RC_PHAEO_GFF.csv', 'STOQS_25913RC_PO4.csv', 'STOQS_25913RC_SIO4.csv',

'STOQS_26013RC_CHL_1U.csv', 'STOQS_26013RC_CHL_5U.csv', 'STOQS_26013RC_CHLA.csv', 'STOQS_26013RC_CHL_GFF.csv',
'STOQS_26013RC_NO2.csv', 'STOQS_26013RC_NO3.csv', 'STOQS_26013RC_PHAEO_1U.csv', 'STOQS_26013RC_PHAEO_5U.csv',
'STOQS_26013RC_PHAEO_GFF.csv', 'STOQS_26013RC_PO4.csv', 'STOQS_26013RC_SIO4.csv',

'STOQS_26113RC_CHL_1U.csv', 'STOQS_26113RC_CHL_5U.csv', 'STOQS_26113RC_CHLA.csv', 'STOQS_26113RC_CHL_GFF.csv',
'STOQS_26113RC_NO2.csv', 'STOQS_26113RC_NO3.csv', 'STOQS_26113RC_PHAEO_1U.csv', 'STOQS_26113RC_PHAEO_5U.csv',
'STOQS_26113RC_PHAEO_GFF.csv', 'STOQS_26113RC_PO4.csv', 'STOQS_26113RC_SIO4.csv',

'STOQS_27313RC_CHLA.csv',

'STOQS_27413RC_CHLA.csv',

'STOQS_27513RC_CHLA.csv', 'STOQS_27513RC_CHL_GFF.csv', 'STOQS_27513RC_NO2.csv', 'STOQS_27513RC_NO3.csv',
'STOQS_27513RC_PHAEO_GFF.csv', 'STOQS_27513RC_PO4.csv', 'STOQS_27513RC_SIO4.csv',

'STOQS_27613RC_CHLA.csv',
                         ]


###################################################################################################################

# Execute the load
cl.process_command_line()


if cl.args.optimal_stride:
    cl.loadL_662(stride=1) 
    cl.load_NPS29(stride=1) 
    cl.load_NPS34(stride=1) 

    cl.load_slocum_260(stride=10)
    cl.load_slocum_294(stride=10)
    cl.load_slocum_nemesis(stride=10)

    cl.load_wg_tex(stride=1)
    cl.load_wg_oa(stride=1) 

    cl.loadDorado(stride=2)
    cl.loadLRAUV('daphne', stride=2, build_attrs=False)
    cl.loadLRAUV('tethys', stride=2, build_attrs=False)

    cl.loadRCuctd(stride=1)
    cl.loadRCpctd(stride=1)
    cl.loadJMuctd(stride=2)
    cl.loadJMpctd(stride=1)
    cl.loadWFuctd(stride=1)   
    cl.loadWFpctd(stride=1)

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
    ##cl.loadOA2pco2(stride=1)              # No data from http://odss.mbari.org/thredds/dodsC/CANON_september2013/Platforms/Moorings/OA_2/OA2_pco2_2013.nc  between 1378684800.0 and 1380499200.0.
    cl.loadOA2fl(stride=1)
    cl.loadOA2o2(stride=1)

    cl.loadBruceMoor(stride=1)
    cl.loadMackMoor(stride=1)

    cl.loadStella(stride=1)

    cl.loadSubSamples()

else:
    cl.stride = cl.args.stride

    if cl.args.test:
        # List too long for separate test section. Use full resolution with a stride override
        cl.stride = 100

    cl.loadL_662()
    cl.load_NPS29()
    cl.load_NPS34()
    cl.load_slocum_260()

    if cl.args.test:
        cl.load_slocum_294(stride=200)
    else:
        # stride=a causes 'django.db.utils.InternalError: invalid memory alloc request size 1073741824' with bulk_create() on new kraken
        cl.load_slocum_294(stride=2)

    cl.load_slocum_nemesis()

    cl.load_wg_tex()
    cl.load_wg_oa()

    cl.loadDorado()
    cl.loadLRAUV('daphne', build_attrs=False)
    cl.loadLRAUV('tethys', build_attrs=False)

    cl.loadRCuctd()
    cl.loadRCpctd()
    cl.loadJMuctd()
    cl.loadJMpctd()
    cl.loadWFuctd()   
    cl.loadWFpctd()

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
    ##cl.loadOA2pco2()              # No data from http://odss.mbari.org/thredds/dodsC/CANON_september2013/Platforms/Moorings/OA_2/OA2_pco2_2013.nc  between 1378684800.0 and 1380499200.0.
    cl.loadOA2fl()
    cl.loadOA2o2()

    cl.loadBruceMoor()
    cl.loadMackMoor()

    cl.loadStella()

    cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

