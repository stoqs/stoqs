#!/usr/bin/env python
__author__    = 'Mike McCann,Duane Edgington,Reiko Michisaki'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'duane at mbari.org'

__doc__ = '''

Master loader for all CANON activities in September 2013

Mike McCann; Modified by Duane Edgington and Reiko Michisaki
MBARI 02 September 2013

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime  # needed for glider data
import time      # for startdate, enddate args
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)

# the next line makes it possible to find CANON
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # this makes it possible to find CANON, one directory up

from CANON import CANONLoader
       
# building input data sources object
cl = CANONLoader('stoqs_september2013', 'CANON - September 2013')

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'

#####################################################################
#  DORADO 
#####################################################################
# special location for dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2013/netcdf/'
cl.dorado_files = [# 'Dorado389_2013_228_00_228_00_decim.nc',
                   # 'Dorado389_2013_228_01_228_01_decim.nc'
                   # 'Dorado389_2013_259_00_259_00_decim.nc'     #Sep 16
                   # 'Dorado389_2013_259_00_259_01_decim.nc' 
                   # 'Dorado389_2013_260_00_260_00_decim.nc'     #Sep 17 
                   # 'Dorado389_2013_260_00_260_01_decim.nc' 
                   # 'Dorado389_2013_261_00_261_00_decim.nc'     #Sep 18
                   # 'Dorado389_2013_261_00_261_01_decim.nc' 
                   # 'Dorado389_2013_262_00_262_00_decim.nc'     #Sep 19
                   # 'Dorado389_2013_262_00_262_01_decim.nc' 
                   # 'Dorado389_2013_273_00_273_00_decim.nc'     #Sep 30
                   # 'Dorado389_2013_273_00_273_01_decim.nc' 
				   ]

######################################################################
#  GLIDERS
######################################################################
# Set start and end dates for all glider loads
t =time.strptime("2013-08-29 0:01", "%Y-%m-%d %H:%M")
startdate=t[:6]
t =time.strptime("2013-09-29 0:01", "%Y-%m-%d %H:%M")
enddate=t[:6]

# SPRAY glider - for just the duration of the campaign
cl.l_662_base = 'http://www.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_files = ['OS_Glider_L_662_20130711_TS.nc']
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = datetime.datetime(*startdate[:]) 
cl.l_662_endDatetime = datetime.datetime(*enddate[:])

# NPS34
cl.nps34_base = 'http://www.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.nps34_files = [ 'OS_Glider_NPS_G34_20130829_TS.nc']
cl.nps34_parms = ['TEMP', 'PSAL']
cl.nps34_startDatetime = datetime.datetime(*startdate[:])
cl.nps34_endDatetime = datetime.datetime(*enddate[:])

# NPS29
cl.nps29_base = 'http://www.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.nps29_files = [ 'OS_Glider_NPS_G29_20130829_TS.nc']
cl.nps29_parms = ['TEMP', 'PSAL', 'OPBS']
cl.nps29_startDatetime = datetime.datetime(*startdate[:])
cl.nps29_endDatetime = datetime.datetime(*enddate[:])

# Liquid Robotics Waveglider
cl.waveglider_base = cl.dodsBase + 'CANON_september2013/waveglider/'
cl.waveglider_files = [ 'waveglider_gpctd_WG.nc' ]
cl.waveglider_parms = [ 'TEMP', 'PSAL', 'oxygen' ]
cl.waveglider_startDatetime = datetime.datetime(*startdate[:])
cl.waveglider_endDatetime = datetime.datetime(*enddate[:])

######################################################################
#  WESTERN FLYER: September 20-27
######################################################################
# UCTD
cl.wfuctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Ships/Western_Flyer/netcdf/uctd/'
cl.wfuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.wfuctd_files = [ 
'24211WF01.nc', '27211WF01.nc', '27411WF01.nc', '27511WF01.nc', '27711WF01.nc', '27811WF01.nc', '27911wf01.nc', '28011wf01.nc', '28111wf01.nc',
'28211wf01.nc'
                      ]

# PCTD
cl.pctdDir = 'CANON_september2013/Platforms/Ships/Western_Flyer/netcdf/pctd/'
cl.wfpctd_base = cl.dodsBase + cl.pctdDir
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl' , 'oxygen']
cl.wfpctd_files = [ 
#'canon13c01.nc', 'canon13c02.nc', 'canon13c03.nc', 'canon13c04.nc', 'canon13c05.nc', 'canon13c06.nc', 'canon13c07.nc',
#'canon13c08.nc', 'canon13c09.nc', 'canon13c10.nc', 'canon13c11.nc', 'canon13c12.nc', 'canon13c13_A.nc', 'canon13c13_B.nc', 'canon13c14.nc',
#'canon13c16.nc', 'canon13c17.nc', 'canon13c19_A.nc', 'canon13c20.nc', 'canon13c22.nc', 'canon13c23.nc', 'canon13c24.nc', 'canon13c25.nc',
#'canon13c26.nc', 'canon13c27.nc', 'canon13c28.nc', 'canon13c29.nc', 'canon13c30.nc', 'canon13c31.nc', 'canon13c32.nc', 'canon13c33.nc',
#'canon13c34.nc', 'canon13c35.nc', 'canon13c36.nc', 'canon13c37.nc', 'canon13c38.nc', 'canon13c39.nc', 'canon13c40.nc', 'canon13c41.nc',
#'canon13c42.nc', 'canon13c43.nc', 'canon13c44.nc', 'canon13c45.nc', 'canon13c46.nc', 'canon13c48.nc', 'canon13c49.nc', 'canon13c50.nc',
#'canon13c51.nc', 'canon13c52.nc', 'canon13c53.nc', 'canon13c54.nc', 'canon13c55.nc', 'canon13c56.nc', 'canon13c57.nc', 'canon13c58.nc',
#'canon13c59.nc', 'canon13c60.nc', 'canon13c61.nc', 'canon13c62.nc', 'canon13c63.nc', 'canon13c64.nc', 'canon13c65.nc', 'canon13c66.nc',
#'canon13c67.nc', 'canon13c68.nc', 'canon13c69.nc', 'canon13c70.nc', 'canon13c71.nc', 'canon13c72.nc', 'canon13c73.nc', 'canon13c74.nc',
#'canon13c75.nc', 'canon13c76.nc', 'canon13c77.nc', 'canon13c78.nc', 'canon13c79.nc', 'canon13c80.nc', 'canon13c81.nc', 'canon13c82.nc' 
]

# BCTD
# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/GOC12/ copied to local BOG_Data dir
cl.bctdDir = 'CANON_september2013/Platforms/Ships/Western_Flyer/netcdf/bctd/'
cl.subsample_csv_base = cl.dodsBase + cl.bctdDir
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data')
cl.subsample_csv_files = [
                            #'STOQS_canon13_CHL_1U.csv', 'STOQS_canon13_CHL_5U.csv', 'STOQS_canon13_NH4.csv', 'STOQS_canon13_NO2.csv',
                    		#'STOQS_canon13_NO3.csv','STOQS_canon13_OXY_ML.csv', 'STOQS_canon13_PHAEO_1U.csv', 'STOQS_canon13_PHAEO_5U.csv',
                            #'STOQS_canon13_PHAEO_GFF.csv', 'STOQS_canon13_PO4.csv', 'STOQS_canon13_SIO4.csv', #'STOQS_canon13_CARBON_GFF.csv
							#'STOQS_canon13_CHL_GFF.csv',
                         ]

######################################################################
#  RACHEL CARSON: September 16-20? (259-262) Sep 30 - Oct 3
######################################################################
# UCTD
cl.rcuctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Ships/Rachel_Carson/uctd/'
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.rcuctd_files = [ 
                        '07413plm01.nc', '07513plm02.nc', '07613plm03.nc', '07913plm04.nc',
                        '08013plm05.nc', '08113plm06.nc',
                      ]

# PCTD
cl.pctdDir = 'CANON_september2013/Platforms/Ships/Rachel_Carson/pctd/'
cl.rcpctd_base = cl.dodsBase + cl.pctdDir
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.rcpctd_files = [ 
                    '25913RCc01.nc', '07413c02.nc', '07413c03.nc', '07413c04.nc', '07413c05.nc', '07413c06.nc', '07413c07.nc',
                      ]
# BCTD
# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/GOC12/ copied to local BOG_Data dir
cl.bctdDir = 'CANON_september2013/Platforms/Ships/Rachel_Carson/bctd/'
cl.subsample_csv_base = cl.dodsBase + cl.bctdDir
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data')
cl.subsample_csv_files = [
#                            'STOQS_canon13_CHL_1U.csv', 'STOQS_canon13_CHL_5U.csv', 'STOQS_canon13_NH4.csv', 'STOQS_canon13_NO2.csv', 'STOQS_canon13_NO3.csv', 
			    'STOQS_canon13_OXY_ML.csv', 'STOQS_canon13_PHAEO_1U.csv', 'STOQS_canon13_PHAEO_5U.csv',
                            'STOQS_canon13_PHAEO_GFF.csv', 'STOQS_canon13_PO4.csv', 'STOQS_canon13_SIO4.csv', 'STOQS_canon13_CARBON_GFF.csv',
                            'STOQS_canon13_CHL_GFF.csv',
                         ]

#####################################################################
# JOHN MARTIN
#####################################################################
cl.martin_base = cl.dodsBase + 'CANON_september2013/Platforms/Ships/Western_Flyer/uctd/' 
cl.martin_parms = ['TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.martin_files = [ '27710c01jm.nc',   '27910c06jm.nc',   '28410c02jm.nc',   '28710c03jm.nc',   '29810c01jm.nc',
                  ]

######################################################################
#  MOORINGS
######################################################################
# Mooring M1 Combined file produced by DPforSSDS processing - for just the duration of the campaign
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/201010/'
cl.m1_files = ['OS_M1_20101027hourly_CMSTV.nc']
cl.m1_parms = [ 'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
                     'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
                     'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR'
                   ]
cl.m1_startDatetime = datetime.datetime(*startdate[:])
cl.m1_endDatetime = datetime.datetime(*enddate[:])


# Mooring OA1 CTD
cl.oaDir = 'CANON_september2013/Platforms/Moorings/OA_1/'
cl.OA1ctd_base = cl.dodsBase + cl.oaDir
cl.OA1ctd_files = ['OA1_ctd_2013.nc']
cl.OA1ctd_parms = ['TEMP', 'PSAL', 'conductivity' ]
cl.OA1ctd_startDatetime = datetime.datetime(*startdate[:])
cl.OA1ctd_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA1 MET
cl.OA1met_base = cl.dodsBase + cl.oaDir
cl.OA1met_files = ['OA1_met_2013.nc']
cl.OA1met_parms = ['Wind_direction','Wind_speed','Air_temperature','Barometric_pressure']
cl.OA1met_startDatetime = datetime.datetime(*startdate[:])
cl.OA1met_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA1 PH
cl.OA1pH_base = cl.dodsBase + cl.oaDir
cl.OA1pH_files = ['OA1_pH_2013.nc']
cl.OA1pH_parms = ['pH' ]
cl.OA1pH_startDatetime = datetime.datetime(*startdate[:])
cl.OA1pH_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA1 PCO2
cl.OA1pco2_base = cl.dodsBase + cl.oaDir
cl.OA1pco2_files = ['OA1_pco2_2013.nc']
cl.OA1pco2_parms = ['pCO2' ]
cl.OA1pco2_startDatetime = datetime.datetime(*startdate[:])
cl.OA1pco2_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA1 O2
cl.OA1o2_base = cl.dodsBase + cl.oaDir
cl.OA1o2_files = ['OA1_o2_2013.nc']
cl.OA1o2_parms = ['oxygen', 'oxygen_saturation' ]
cl.OA1o2_startDatetime = datetime.datetime(*startdate[:])
cl.OA1o2_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA1 Fluorescence
cl.OA1fl_base = cl.dodsBase + cl.oaDir
cl.OA1fl_files = ['OA1_fl_2013.nc']
cl.OA1fl_parms = [ 'fluor' ]
cl.OA1fl_startDatetime = datetime.datetime(*startdate[:])
cl.OA1fl_endDatetime = datetime.datetime(*enddate[:])
 
# Mooring OA2 CTD
cl.oaDir = 'CANON_september2013/Platforms/Moorings/OA_2/'
cl.OA2ctd_base = cl.dodsBase + cl.oaDir
cl.OA2ctd_files = ['OA2_ctd_2013.nc']
cl.OA2ctd_parms = ['TEMP', 'PSAL', 'conductivity' ]
cl.OA2ctd_startDatetime = datetime.datetime(*startdate[:])
cl.OA2ctd_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA2 MET
cl.OA2met_base = cl.dodsBase + cl.oaDir
cl.OA2met_files = ['OA2_met_2013.nc']
cl.OA2met_parms = ['Wind_direction','Wind_speed','Air_temperature','Barometric_pressure']
cl.OA2met_startDatetime = datetime.datetime(*startdate[:])
cl.OA2met_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA2 PH
cl.OA2pH_base = cl.dodsBase + cl.oaDir
cl.OA2pH_files = ['OA2_pH_2013.nc']
cl.OA2pH_parms = ['pH' ]
cl.OA2pH_startDatetime = datetime.datetime(*startdate[:])
cl.OA2pH_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA2 PCO2
cl.OA2pco2_base = cl.dodsBase + cl.oaDir
cl.OA2pco2_files = ['OA2_pco2_2013.nc']
cl.OA2pco2_parms = ['pCO2' ]
cl.OA2pco2_startDatetime = datetime.datetime(*startdate[:])
cl.OA2pco2_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA2 O2
cl.OA2o2_base = cl.dodsBase + cl.oaDir
cl.OA2o2_files = ['OA2_o2_2013.nc']
cl.OA2o2_parms = ['oxygen', 'oxygen_saturation' ]
cl.OA2o2_startDatetime = datetime.datetime(*startdate[:])
cl.OA2o2_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA2 Fluorescence
cl.OA2fl_base = cl.dodsBase + cl.oaDir
cl.OA2fl_files = ['OA2_fl_2013.nc']
cl.OA2fl_parms = [ 'fluor' ]
cl.OA2fl_startDatetime = datetime.datetime(*startdate[:])
cl.OA2fl_endDatetime = datetime.datetime(*enddate[:])
 
#######################################################################################
# DRIFTERS
#######################################################################################

# Stella 203
cl.stella203_base = cl.dodsBase + 'CANON_september2013/Platforms/Drifters/Stella_1/'
cl.stella203_parms = [ 'TEMP', 'pH' ]
cl.stella203_files = [ 
                        'stella203.nc',
                      ]

# MBARI ESPs Mack and Bruce
cl.espmack_base = cl.dodsBase + 'CANON_september2013/Platforms/Moorings/ESP_Mack/NetCDF/'
cl.espmack_parms = [ 'TEMP', 'PSAL', 'chl', 'chlini', 'no3' ]
cl.espmack_files = [ 
                        'ctd.nc',
                      ]

# add code for Bruce here. we think that all the plumbing is in place for Bruce, just need .nc file(s)

###################################################################################################################
# Execute the load
cl.process_command_line()

if cl.args.test:
    ##cl.loadDorado(stride=100)
#    cl.loadL_662(stride=100) # done
#    cl.load_NPS29(stride=100) 
#    cl.load_NPS34(stride=100) 
    ##cl.loadWFuctd(stride=100) # done
    ##cl.loadWaveglider(stride=100)
    ##cl.loadDaphne(stride=10)
    ##cl.loadTethys(stride=10)
    ##cl.loadESPdrift(stride=10)
    ##cl.loadWFpctd(stride=50)
    ##cl.loadSubSamples()
    ##cl.loadM1ts(stride=1)
    ##cl.loadM1met(stride=1)
    ##cl.loadM1met(stride=1)
    ##cl.loadRCuctd(stride=10)
    cl.loadStella203(stride=1)
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
#    cl.loadOA2fl(stride=1)
#    cl.loadOA2o2(stride=1)
    ##cl.loadRCpctd(stride=1)
    ##cl.loadESPmack()
    ##cl.loadESPbruce()
    #cl.loadMartin(stride=1)

elif cl.args.optimal_stride:
    #cl.loadDorado(stride=2)
    #cl.loadL_662(stride=1)
#    cl.load_NPS29(stride=100)
#    cl.load_NPS34(stride=100)
#    cl.loadWFuctd(stride=1)
#    cl.loadWFpctd(stride=1)
    ##cl.loadSubSamples()
##    cl.loadM1met(stride=1)
#    cl.loadOA1ctd(stride=1)
#    cl.loadOA1met(stride=1)
#    cl.loadOA1pH(stride=1)
    cl.loadOA1pco2(stride=1)
#    cl.loadOA1fl(stride=1)
#    cl.loadOA1o2(stride=1)
#    cl.loadOA2ctd(stride=1)
#    cl.loadOA2met(stride=1)
#    cl.loadOA2pH(stride=1)
    cl.loadOA2pco2(stride=1)
#    cl.loadOA2fl(stride=1)
#    cl.loadOA2o2(stride=1)
    ##cl.loadRCuctd(stride=10)
    ##cl.loadRCpctd(stride=1)
    ##cl.loadESPmack()
    ##cl.loadESPbruce()
   #cl.loadMartin(stride=1)

else:
#    cl.loadDorado(stride=cl.args.stride)
#    cl.loadL_662()
#    cl.load_NPS29(stride=100) 
#    cl.load_NPS34(stride=100)
#    cl.loadWFuctd()
#    cl.loadWFpctd()
    ##cl.loadSubSamples()
##    cl.loadM1met(stride=1)
#    cl.loadOA1ctd(stride=1)
#    cl.loadOA1met(stride=1)
#    cl.loadOA1pH(stride=1)
    cl.loadOA1pco2(stride=1)
#    cl.loadOA1fl(stride=1)
#    cl.loadOA1o2(stride=1)
#    cl.loadOA2ctd(stride=1)
#    cl.loadOA2met(stride=1)
#    cl.loadOA2pH(stride=1)
#    cl.loadOA2pco2(stride=1)
#    cl.loadOA2fl(stride=1)
#    cl.loadOA2o2(stride=1)
    ##cl.loadRCuctd()
    ##cl.loadRCpctd()
    ##cl.loadESPmack()
    ##cl.loadESPbruce()
   #cl.loadMartin()
