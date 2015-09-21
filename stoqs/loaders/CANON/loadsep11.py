#!/usr/bin/env python
__author__    = 'Duane Edgington'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'duane at mbari.org'

__doc__ = '''

Master loader for all CANON activities in September 2011 and beyound

Mike McCann and Duane Edgington and Reiko
MBARI 15 August 2013

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime  # needed for glider data
import time
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)

# the next line makes it possible to find CANON
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # settings.py is one dir up

from CANON import CANONLoader
       
# building input data sources object
cl = CANONLoader('stoqs_september2011', 'CANON - September 2011')

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'

#####################################################################
#  DORADO
#####################################################################
# special location for dorado data
#cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2011/netcdf/'
#cl.dorado_files = [# 'Dorado389_2011_249_00_249_00_decim.nc',
                   # 'Dorado389_2011_250_01_250_01_decim.nc'
#                     'Dorado389_2011_255_00_255_00_decim.nc' ]
# already loaded dorado file 249

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
cl.waveglider_base = cl.dodsBase + 'CANON_september2012/waveglider/'
cl.waveglider_files = [ 'waveglider_gpctd_WG.nc' ]
cl.waveglider_parms = [ 'TEMP', 'PSAL', 'oxygen' ]
cl.waveglider_startDatetime = datetime.datetime(2012, 8, 31, 18, 47, 0)
cl.waveglider_endDatetime = datetime.datetime(2012, 9, 25, 16, 0, 0)

######################################################################
#  WESTERN FLYER
######################################################################

cl.wfuctd_base = cl.dodsBase + 'CANON_september2011/wf/uctd/'
cl.wfuctd_files = [ 
'24211WF01.nc', '27211WF01.nc', '27411WF01.nc', '27511WF01.nc', '27711WF01.nc', '27811WF01.nc', '27911wf01.nc', '28011wf01.nc', '28111wf01.nc',
'28211wf01.nc'
                      ]
cl.wfuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]


# Western Flyer Profile CTD
cl.pctdDir = 'CANON_september2011/wf/pctd/'
cl.wfpctd_base = cl.dodsBase + cl.pctdDir
cl.wfpctd_files = [ 
'canon11c01.nc', 'canon11c02.nc', 'canon11c03.nc', 'canon11c04.nc', 'canon11c05.nc', 'canon11c06.nc', 'canon11c07.nc',
'canon11c08.nc', 'canon11c09.nc', 'canon11c10.nc', 'canon11c11.nc', 'canon11c12.nc', 'canon11c13_A.nc', 'canon11c13_B.nc', 'canon11c14.nc',
'canon11c16.nc', 'canon11c17.nc', 'canon11c19_A.nc', 'canon11c20.nc', 'canon11c22.nc', 'canon11c23.nc', 'canon11c24.nc', 'canon11c25.nc',
'canon11c26.nc', 'canon11c27.nc', 'canon11c28.nc', 'canon11c29.nc', 'canon11c30.nc', 'canon11c31.nc', 'canon11c32.nc', 'canon11c33.nc',
'canon11c34.nc', 'canon11c35.nc', 'canon11c36.nc', 'canon11c37.nc', 'canon11c38.nc', 'canon11c39.nc', 'canon11c40.nc', 'canon11c41.nc',
'canon11c42.nc', 'canon11c43.nc', 'canon11c44.nc', 'canon11c45.nc', 'canon11c46.nc', 'canon11c48.nc', 'canon11c49.nc', 'canon11c50.nc',
'canon11c51.nc', 'canon11c52.nc', 'canon11c53.nc', 'canon11c54.nc', 'canon11c55.nc', 'canon11c56.nc', 'canon11c57.nc', 'canon11c58.nc',
'canon11c59.nc', 'canon11c60.nc', 'canon11c61.nc', 'canon11c62.nc', 'canon11c63.nc', 'canon11c64.nc', 'canon11c65.nc', 'canon11c66.nc',
'canon11c67.nc', 'canon11c68.nc', 'canon11c69.nc', 'canon11c70.nc', 'canon11c71.nc', 'canon11c72.nc', 'canon11c73.nc', 'canon11c74.nc',
'canon11c75.nc', 'canon11c76.nc', 'canon11c77.nc', 'canon11c78.nc', 'canon11c79.nc', 'canon11c80.nc', 'canon11c81.nc', 'canon11c82.nc' ]
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl' , 'oxygen']
#cl.wfpctd_parms = [ 'oxygen' ] we were able to load oxygen for 'c0912c03.nc'

# tried to access the BOG_Data files on thredds server (beach)
# this did not work:

#cl.bctdDir = 'CANON_september2011/wf/bctd/'
#cl.subsample_csv_base = cl.dodsBase + cl.bctdDir


# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/GOC12/ copied to local BOG_Data dir
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data')
cl.subsample_csv_files = [
#                            'STOQS_Canon11_CHL_1U.csv', 'STOQS_Canon11_CHL_5U.csv', 'STOQS_Canon11_NH4.csv', 'STOQS_Canon11_NO2.csv', 'STOQS_Canon11_NO3.csv', 
			    'STOQS_Canon11_OXY_ML.csv', 'STOQS_Canon11_PHAEO_1U.csv', 'STOQS_Canon11_PHAEO_5U.csv',
                            'STOQS_Canon11_PHAEO_GFF.csv', 'STOQS_Canon11_PO4.csv', 'STOQS_Canon11_SIO4.csv', 'STOQS_Canon11_CARBON_GFF.csv',
                            'STOQS_CANON11_CHL_GFF.csv',
                         ]

######################################################################
#  WESTERN FLYER
######################################################################
# Mooring M1 Combined file produced by DPforSSDS processing - for just the duration of the campaign
#cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/201010/'
#cl.m1_files = ['OS_M1_20101027hourly_CMSTV.nc']
#cl.m1_parms = [ 'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
#                     'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
#                     'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR'
#                   ]
#cl.m1_startDatetime = datetime.datetime(2011, 9, 13)
#cl.m1_endDatetime = datetime.datetime(2011, 9, 14)


# Mooring OA1 CTD
cl.oaDir = 'CANON_september2011/wf/oa/'
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
cl.oaDir = 'CANON_september2011/wf/oa/'
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
 
# Rachel Carson Underway CTD
cl.rcuctd_base = cl.dodsBase + 'CANON_march2013/carson/uctd/'
cl.rcuctd_files = [ 
                        '07413plm01.nc', '07513plm02.nc', '07613plm03.nc', '07913plm04.nc',
                        '08013plm05.nc', '08113plm06.nc',
                      ]
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]

# Rachel Carson Profile CTD
cl.pctdDir = 'CANON_march2013/carson/pctd/'
cl.rcpctd_base = cl.dodsBase + cl.pctdDir
cl.rcpctd_files = [ 
                    '07413c01.nc', '07413c02.nc', '07413c03.nc', '07413c04.nc', '07413c05.nc', '07413c06.nc', '07413c07.nc',
                    '07413c08.nc', '07413c09.nc', '07413c10.nc', '07413c11.nc', '07513c12.nc', '07513c13.nc', '07513c14.nc',
                    '07513c15.nc', '07513c16.nc', '07513c17.nc', '07513c18.nc', '07513c19.nc', '07613c20.nc', '07613c21.nc',
                    '07613c22.nc', '07613c23.nc', '07613c24.nc', '07613c25.nc', '07613c26.nc', '07913c27.nc', '07913c28.nc',
                    '07913c29.nc', '07913c30.nc', '07913c31.nc', '08013c32.nc', '08013c33.nc', '08013c34.nc', '08013c35.nc',
                    '08013c36.nc', '08113c37.nc', '08113c38.nc', '08113c39.nc', '08113c40.nc', '08113c41.nc', '08113c42.nc',
                    '08113c43.nc',
                      ]
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]

########################################################################################################
# DRIFTERS
########################################################################################################
# STELLA
cl.stella203_base = cl.dodsBase + 'CANON_september2013/Platforms/Drifters/Stella_1/'
cl.stella203_files = [ 
                        'stella203_data.nc',
                      ]
cl.stella203_parms = [ 'TEMP', 'pH' ]

# STELLA
cl.stella204_base = cl.dodsBase + 'CANON_september2013/Platforms/Drifters/Stella_1/'
cl.stella204_files = [ 
                        'stella204_data.nc',
                      ]
cl.stella204_parms = [ 'TEMP', 'pH' ]

########################################################################################################
# ESP
########################################################################################################
# MBARI ESPs Mack and Bruce
cl.espmack_base = cl.dodsBase + 'CANON_march2013/esp/instances/Mack/data/processed/'
cl.espmack_files = [ 
                        'ctd.nc',
                      ]
# note: .nc file not in the directory 8/29/2013 => blamo!

cl.espmack_parms = [ 'TEMP', 'PSAL', 'chl', 'chlini', 'no3' ]

# add code for Bruce here. we think that all the plumbing is in place for Bruce, just need .nc file(s)

cl.martin_base = cl.dodsBase + 'CANON_september2011/wf/uctd/' # test 
#cl.martin_base = cl.dodsBase + 'CANON_september2011/wf/jm/' # used to be: 'http://odss.mbari.org/thredds/dodsC/jhm_underway'
cl.martin_files = [ '27710c01jm.nc',   '27910c06jm.nc',   '28410c02jm.nc',   '28710c03jm.nc',   '29810c01jm.nc',
                   # '27710_jhmudas_v1.nc',
                   # '27810_jhmudas_v1.nc',
                   # '27910_jhmudas_v1.nc',
                   # '28010_jhmudas_v1.nc',
                   # '28110_jhmudas_v1.nc',
                   # '28410_jhmudas_v1.nc',
                   # '28510_jhmudas_v1.nc',
                   # '28610_jhmudas_v1.nc',
                   # '28710_jhmudas_v1.nc',
                   # '29010_jhmudas_v1.nc',
                   # '29110_jhmudas_v1.nc',
                   # '29210_jhmudas_v1.nc',
                   # '29310_jhmudas_v1.nc',
                   # '29410_jhmudas_v1.nc',
                   # '29810_jhmudas_v1.nc',
                   # '29910_jhmudas_v1.nc',
                   # '30010_jhmudas_v1.nc',
                   # '30110_jhmudas_v1.nc',
                  ]
# cl.martin_parms = [ 'Conductivity', 'Temperature', 'Salinity', 'Fluorescence', 'Turbidity']

# cl.martin_parms = [ 'conductivity', 'temperature', 'salinity', 'fluorescence', 'turbidity']

cl.martin_parms = ['TEMP', 'PSAL', 'xmiss', 'wetstar' ]
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
    ##cl.loadStella203(stride=1)
    cl.loadStella204(stride=1)
    ##cl.loadOA1ctd(stride=1)
    ##cl.loadOA1met(stride=1)
    ##cl.loadOA1pH(stride=1)
    ##cl.loadOA1pco2(stride=1)
    ##cl.loadOA1fl(stride=1)
    ##cl.loadOA1o2(stride=1)
    ##cl.loadOA2ctd(stride=1)
    ##cl.loadOA2met(stride=1)
    ##cl.loadOA2pH(stride=1)
    ##cl.loadOA2pco2(stride=1)
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
    cl.loadStella204(stride=1)
#    cl.loadOA1ctd(stride=1)
#    cl.loadOA1met(stride=1)
#    cl.loadOA1pH(stride=1)
##    cl.loadOA1pco2(stride=1)
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
    cl.loadStella204(stride=1)
#    cl.loadOA1ctd(stride=1)
#    cl.loadOA1met(stride=1)
#    cl.loadOA1pH(stride=1)
##    cl.loadOA1pco2(stride=1)
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
