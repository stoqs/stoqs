#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2012'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for all September 2012 CANON activities.  

The default is to load data with a stride of 100 into a database named stoqs_september2012_s100.

Execute with "./loadCANON_september2012 1 stoqs_september2012" to load full resolution data.

Mike McCann
MBARI 6 September AUgust 2012

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
    dbAlias = 'stoqs_september2012_s100'


# ------------------------------------------------------------------------------------
# Data loads for all the activities, LRAUV have real-time files before full-resolution
# ------------------------------------------------------------------------------------
cl = CANONLoader(dbAlias, 'CANON - September 2012')

# 2-second decimated dorado data
# Aboard the Flyer use malibu's VSAT IP address:
# http://192.168.111.177:8080/thredds/dodsC/CANON_september2012/dorado/Dorado389_2012_258_00_258_00_decim.nc
cl.dorado_base = 'http://192.168.111.177:8080/thredds/dodsC/CANON_september2012/dorado/'
cl.dorado_files = [ 
                    'Dorado389_2012_256_00_256_00_decim.nc',
                    'Dorado389_2012_257_01_257_01_decim.nc',
                    'Dorado389_2012_258_00_258_00_decim.nc',
                  ]

# Realtime telemetered (_r_) daphne data - insert '_r_' to not load the files
##cl.daphne_base = 'http://aosn.mbari.org/lrauvtds/dodsC/lrauv/daphne/2012/'
cl.daphne_base = 'http://192.168.111.177:8080/thredds/dodsC/CANON_september2012/lrauv/daphne/realtime/sbdlogs/2012/201209/'
cl.daphne_files = [ 
# NoValidData                    '20120910T142840/shore.nc',
# NoValidData                    '20120910T143107/shore.nc',
                    '20120910T221418/shore.nc',
# NoValidData                    '20120911T005835/shore.nc',
                    '20120911T031754/shore.nc',
# NoValidData                    '20120911T105509/shore.nc',
                    '20120911T215648/shore.nc',
                  ]
cl.daphne_parms = [ 'platform_battery_charge', 'sea_water_temperature', 'downwelling_photosynthetic_photon_flux_in_sea_water',
                    'mass_concentration_of_oxygen_in_sea_water', 'mass_concentration_of_chlorophyll_in_sea_water']

# Postrecovery full-resolution (_d_) daphne data - insert '_d_' for delayed-mode to not load the data
cl.daphne_d_base = 'http://elvis.shore.mbari.org:8080/thredds/dodsC/lrauv/daphne/2012/'
cl.daphne_d_files = [ 
                  ]
cl.daphne_d_parms = [ 'sea_water_temperature', 'sea_water_salinity', 'sea_water_density', 'volume_scattering_470_nm', 'volume_scattering_650_nm',
                    'volume_scattering_650_nm', 'mass_concentration_of_oxygen_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water',
                    'mass_concentration_of_chlorophyll_in_sea_water']

# Realtime telemetered (_r_) tethys data - insert '_r_' to not load the files
##cl.tethys_base = 'http://aosn.mbari.org/lrauvtds/dodsC/lrauv/tethys/2012/'                    # Tethys realtime
cl.tethys_base = 'http://192.168.111.177:8080/thredds/dodsC/CANON_september2012/lrauv/tethys/realtime/sbdlogs/2012/201209/'
cl.tethys_files = [ 
                    '20120909T152301/shore.nc',
                    '20120910T190223/shore.nc',
                    '20120911T125230/shore.nc',
                    '20120912T003318/shore.nc',
                    '20120912T015450/shore.nc',
                    '20120912T142126/shore.nc',
                  ]
cl.tethys_parms = [ 'platform_battery_charge', 'sea_water_temperature', 'downwelling_photosynthetic_photon_flux_in_sea_water',
                    'mass_concentration_of_oxygen_in_sea_water', 'mass_concentration_of_chlorophyll_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water']

# Postrecovery full-resolution tethys data - insert '_d_' for delayed-mode to not load the data
cl.tethys_d_base = 'http://elvis.shore.mbari.org:8080/thredds/dodsC/lrauv/tethys/2012/'
cl.tethys_d_files = [ 
                  ]

cl.tethys_d_parms = [ 'sea_water_temperature', 'sea_water_salinity', 'sea_water_density', 'volume_scattering_470_nm', 'volume_scattering_650_nm',
                    'volume_scattering_650_nm', 'mass_concentration_of_oxygen_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water',
                    'mass_concentration_of_chlorophyll_in_sea_water']

cl.fulmar_base = []
cl.fulmar_files = []
cl.fulmar_parms = []

# Spray glider - for just the duration of the campaign
cl.l_662_base = 'http://www.cencoos.org/thredds/dodsC/glider/'
cl.l_662_files = ['OS_Glider_L_662_20120816_TS.nc']
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = datetime.datetime(2012, 9, 1)
cl.l_662_endDatetime = datetime.datetime(2012, 9, 30)

# Liquid Robotics Waveglider
##cl.waveglider_base = 'http://odss.mbari.org/thredds/dodsC/CANON_september2012/waveglider/'
cl.waveglider_base = 'http://192.168.111.177:8080/thredds/dodsC/CANON_september2012/waveglider/'
cl.waveglider_files = [ 
                        'waveglider_gpctd_WG.nc',
##                        'waveglider_pco2_WG.nc',
                      ]
cl.waveglider_parms = [ 
                        'TEMP', 'PSAL', 'oxygen', 
##                        'ZeroPumpOn_pco2', 'ZeroPumpOn_Temp', 'ZeroPumpOn_Pressure', 'ZeroPumpOff_pco2', 'ZeroPumpOff_Temp',
##                        'ZeroPumpOff_Pressure', 'StandardFlowOn_Pressure', 'StandardFlowOff_pco2_Humidity', 'StandardFlowOff_pco2',
##                        'StandardFlowOff_Temp', 'StandardFlowOff_Pressure', 'Longitude', 'Latitude', 'EquilPumpOn_pco2', 'EquilPumpOn_Temp',
##                        'EquilPumpOn_Pressure', 'EquilPumpOff_pco2', 'EquilPumpOff_Temp', 'EquilPumpOff_Pressure', 'EquilPumpOff_Humidity',
##                        'Durafet_pH_6', 'Durafet_pH_5', 'Durafet_pH_4', 'Durafet_pH_3', 'Durafet_pH_2', 'Durafet_pH_1', 'Can_Humidity',
##                        'AirPumpOn_pco2', 'AirPumpOn_Temp', 'AirPumpOn_Pressure', 'AirPumpOff_pco2', 'AirPumpOff_Temp', 'AirPumpOff_Pressure',
##                        'AirPumpOff_Humidity',
                      ]


cl.stride = stride
##cl.loadAll()

# For testing.  Comment out the loadAll() call, and uncomment one of these as needed
##cl.loadDorado()
##cl.loadNps_g29()
##cl.loadL_662()
##cl.loadWaveglider()
cl.loadDaphne()
##cl.loadTethys()

