#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for all May 2012 CANON activities

Mike McCann
MBARI 22 May 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # settings.py is one dir up

from CANON import CANONLoader

try:
    stride = int(sys.argv[1])
except IndexError:
    stride = 100
try:
    dbAlias = sys.argv[2]
except IndexError:
    dbAlias = 'stoqs_may2012'


# ------------------------------------------------------------------------------------
# Data loads for all the activities, LRAUV have real-time files before full-resolution
# ------------------------------------------------------------------------------------
cl = CANONLoader(dbAlias, 'CANON - May 2011')

cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2012/netcdf/'
cl.dorado_files = [ 
##                    'Dorado389_2012_142_01_142_01_decim.nc',
##                    'Dorado389_2012_142_02_142_02_decim.nc',
##                    'Dorado389_2012_143_07_143_07_decim.nc',
##                    'Dorado389_2012_143_08_143_08_decim.nc',
##                    'Dorado389_2012_150_00_150_00_decim.nc',
##                    'Dorado389_2012_151_00_151_00_decim.nc',
##                    'Dorado389_2012_152_00_152_00_decim.nc',
                    'Dorado389_2012_157_07_157_07_decim.nc',
                  ]

cl.daphne_base = 'http://aosn.mbari.org/lrauvtds/dodsC/lrauv/daphne/2012/'
cl.daphne_files = [ 
##                    '201205/20120530T160348/shore.nc',
##                    '201205/20120530T215940/shore.nc',
##                    '201205/20120531T010135/shore.nc',
##                    '201205/20120531T011043/shore.nc',
##                    '201205/20120531T050931/shore.nc',
##                    '201205/20120531T062937/shore.nc',
##                    '201205/20120531T174058/shore.nc'
##                    '201206/20120601T235829/shore.nc',
##                    '201206/20120603T002455/shore.nc',
##                    '201206/20120603T200613/shore.nc',
##                    '201206/20120603T213551/shore.nc',
##                    '201206/20120604T211315/shore.nc',
                    '201206/20120606T050637/shore.nc',
                    '201206/20120606T094236/shore.nc',
                  ]
cl.daphne_parms = [ 'platform_battery_charge', 'sea_water_temperature', 
                    'mass_concentration_of_oxygen_in_sea_water', 'mass_concentration_of_chlorophyll_in_sea_water']

##cl.tethys_base = 'http://elvis.shore.mbari.org:8080/thredds/dodsC/lrauv/tethys/2012/'         # Tethys full resolution
##cl.tethys_parms = [ 'sea_water_temperature', 'sea_water_salinity', 'sea_water_density', 'volume_scattering_470_nm', 'volume_scattering_650_nm',
##                    'volume_scattering_650_nm', 'mass_concentration_of_oxygen_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water',
##                    'mass_concentration_of_chlorophyll_in_sea_water']

cl.tethys_base = 'http://aosn.mbari.org/lrauvtds/dodsC/lrauv/tethys/2012/'                    # Tethys realtime
cl.tethys_files = [ 
                    '201206/20120606T171537/shore.nc',
                  ]
cl.tethys_parms = [ 'platform_battery_charge', 'sea_water_temperature', 
                    'mass_concentration_of_oxygen_in_sea_water', 'mass_concentration_of_chlorophyll_in_sea_water']

cl.fulmar_base = []
cl.fulmar_files = []
cl.fulmar_parms = []

# Garbled TDS response: 1 June 2012
cl.nps_g29_base = 'http://www.cencoos.org/thredds/dodsC/glider/'
cl.nps_g29_files = ['OS_Glider_NPS_G29_20120524_TS.nc']
cl.nps_g29_parms = ['TEMP', 'PSAL', 'OPBS']

# Zeros at end of time axis: 1 June 2012
cl.l_662_base = 'http://www.cencoos.org/thredds/dodsC/glider/'
cl.l_662_files = ['OS_Glider_L_662_20120424_TS.nc']
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_dataStartDatetime = datetime.datetime(2012,5, 15)

cl.waveglider_base = 'http://odss.mbari.org/thredds/dodsC/CANON_may2012/waveglider/'
cl.waveglider_files = [ 
                        'waveglider_gpctd_WG.nc',
                        'waveglider_pco2_WG.nc',
                      ]
cl.waveglider_parms = [ 
                        'temp', 'salinity', 'oxygen', 
                        'ZeroPumpOn_pco2', 'ZeroPumpOn_Temp', 'ZeroPumpOn_Pressure', 'ZeroPumpOff_pco2', 'ZeroPumpOff_Temp',
                        'ZeroPumpOff_Pressure', 'StandardFlowOn_Pressure', 'StandardFlowOff_pco2_Humidity', 'StandardFlowOff_pco2',
                        'StandardFlowOff_Temp', 'StandardFlowOff_Pressure', 'Longitude', 'Latitude', 'EquilPumpOn_pco2', 'EquilPumpOn_Temp',
                        'EquilPumpOn_Pressure', 'EquilPumpOff_pco2', 'EquilPumpOff_Temp', 'EquilPumpOff_Pressure', 'EquilPumpOff_Humidity',
                        'Durafet_pH_6', 'Durafet_pH_5', 'Durafet_pH_4', 'Durafet_pH_3', 'Durafet_pH_2', 'Durafet_pH_1', 'Can_Humidity',
                        'AirPumpOn_pco2', 'AirPumpOn_Temp', 'AirPumpOn_Pressure', 'AirPumpOff_pco2', 'AirPumpOff_Temp', 'AirPumpOff_Pressure',
                        'AirPumpOff_Humidity',
                      ]


cl.stride = stride
##cl.loadAll()

##cl.loadNps_g29()
##cl.loadL_662()
##cl.loadWaveglider()

cl.loadDorado()
##cl.loadTethys()
##cl.loadDaphne()


