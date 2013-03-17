#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for all March 2013 CANON-ECOHAB activities.  

The default is to load data with a stride of 100 into a database named stoqs_march2013_s100.

Execute with "./loadCANON_march2013 1 stoqs_march2013" to load full resolution data.

Mike McCann
MBARI 13 March 2013

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
    dbAlias = 'stoqs_march2013_s100'


# ------------------------------------------------------------------------------------
# Data loads for all the activities, LRAUV have real-time files before full-resolution
# ------------------------------------------------------------------------------------
campaignName = 'CANON-ECOHAB - March 2013'
if stride != 1:
    campaignName = campaignName + ' with stride=%d' % stride
cl = CANONLoader(dbAlias, campaignName)

# Aboard the Carson use zuma
cl.tdsBase = 'http://zuma.rc.mbari.org/thredds/'       
##cl.tdsBase = 'http://odss.mbari.org/thredds/'       # Use this on shore
cl.dodsBase = cl.tdsBase + 'dodsC/'       

# 2-second decimated dorado data
cl.dorado_base = cl.dodsBase + 'CANON_march2013/dorado/'
cl.dorado_files = [ 
                    'Dorado389_2013_074_02_074_02_decim.nc',
                  ]

# Realtime telemetered (_r_) daphne data - insert '_r_' to not load the files
##cl.daphne_base = 'http://aosn.mbari.org/lrauvtds/dodsC/lrauv/daphne/2012/'
cl.daphne_base = cl.dodsBase + 'CANON_march2013/lrauv/daphne/realtime/sbdlogs/2013/201303/'
cl.daphne_files = [ 
                    'shore_201303132226_201303140449.nc',
                    'shore_201303140708_201303140729.nc',
                    'shore_201303140729_201303141609.nc',
                    'shore_201303141631_201303151448.nc',
                    'shore_201303141631_201303161621.nc',
                  ]
cl.daphne_parms = [ 'sea_water_temperature', 'mass_concentration_of_chlorophyll_in_sea_water']

# Postrecovery full-resolution (_d_) daphne data - insert '_d_' for delayed-mode to not load the data
cl.daphne_d_base = 'http://elvis.shore.mbari.org:8080/thredds/dodsC/lrauv/daphne/2013/'
cl.daphne_d_files = [ 
                  ]
cl.daphne_d_parms = [ 'sea_water_temperature', 'sea_water_salinity', 'sea_water_density', 'volume_scattering_470_nm', 'volume_scattering_650_nm',
                    'volume_scattering_650_nm', 'mass_concentration_of_oxygen_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water',
                    'mass_concentration_of_chlorophyll_in_sea_water']

# Realtime telemetered (_r_) tethys data - insert '_r_' to not load the files
##cl.tethys_base = 'http://aosn.mbari.org/lrauvtds/dodsC/lrauv/tethys/2012/'                    # Tethys realtime
cl.tethys_base = cl.dodsBase + 'CANON_march2013/lrauv/tethys/realtime/sbdlogs/2013/201303/'
cl.tethys_files = [ 
                    'shore_201303140812_201303141247.nc',
                    'shore_201303141252_201303141329.nc',
                    'shore_201303141331_201303150644.nc',
                    'shore_201303150645_201303151308.nc',
                    'shore_201303151312_201303151339.nc',
                    'shore_201303151333_201303151334.nc',
                    'shore_201303151337_201303151503.nc',
                    'shore_201303151504_201303151706.nc',
                    'shore_201303151714_201303151730.nc',
                    'shore_201303151728_201303151747.nc',
                    'shore_201303151748_201303151947.nc',
                    'shore_201303151950_201303152001.nc',
                    'shore_201303152003_201303152011.nc',
                    'shore_201303152013_201303152026.nc',
                    'shore_201303152027_201303160953.nc',
                  ]
cl.tethys_parms = [ 'sea_water_temperature', 'mass_concentration_of_chlorophyll_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water',
                    'platform_x_velocity_current', 'platform_y_velocity_current', 'platform_z_velocity_current']

# Postrecovery full-resolution tethys data - insert '_d_' for delayed-mode to not load the data
cl.tethys_d_base = 'http://elvis.shore.mbari.org:8080/thredds/dodsC/lrauv/tethys/2012/'
cl.tethys_d_files = [ 
                  ]

cl.tethys_d_parms = [ 'sea_water_temperature', 'sea_water_salinity', 'sea_water_density', 'volume_scattering_470_nm', 'volume_scattering_650_nm',
                    'volume_scattering_650_nm', 'mass_concentration_of_oxygen_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water',
                    'mass_concentration_of_chlorophyll_in_sea_water']

# Webb gliders
cl.hehape_base = cl.dodsBase + 'CANON_march2013/usc_glider/HeHaPe/processed/'
cl.hehape_files = [
                        'OS_Glider_HeHaPe_20130305_TS.nc',
                        'OS_Glider_HeHaPe_20130310_TS.nc',
                   ]
cl.hehape_parms = [ 'TEMP', 'PSAL', 'BB532', 'CDOM', 'CHLA', 'DENS' ]

cl.rusalka_base = cl.dodsBase + 'CANON_march2013/usc_glider/Rusalka/processed/'
cl.rusalka_files = [
                        'OS_Glider_Rusalka_20130301_TS.nc',
                   ]
cl.rusalka_parms = [ 'TEMP', 'PSAL', 'BB532', 'CDOM', 'CHLA', 'DENS' ]

# Spray glider - for just the duration of the campaign
cl.l_662_base = 'http://www.cencoos.org/thredds/dodsC/glider/'
cl.l_662_files = ['OS_Glider_L_662_20120816_TS.nc']
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = datetime.datetime(2012, 9, 10)
cl.l_662_endDatetime = datetime.datetime(2012, 9, 20)


# MBARI ESPs Mack and Bruce
cl.espmack_base = cl.dodsBase + 'CANON_march2013/esp/instances/Mack/data/processed/'
cl.espmack_files = [ 
                        'ctd.nc',
                      ]
cl.espmack_parms = [ 'TEMP', 'PSAL', 'chl', 'chlini', 'no3' ]

# Rachel Carson Underway CTD
cl.rcuctd_base = cl.dodsBase + 'CANON_march2013/carson/data/'
cl.rcuctd_files = [ 
                        'rc_uctd.nc',
                      ]
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]

# Rachel Carson Profile CTD
cl.pctdDir = 'CANON_march2013/carson/pctd/'
cl.rcpctd_base = cl.dodsBase + cl.pctdDir
cl.rcpctd_files = [ 
                    '07413c01.nc',
                    '07413c02.nc',
                    '07413c03.nc',
                    '07413c04.nc',
                    '07413c05.nc',
                    '07413c06.nc',
                    '07413c07.nc',
                    '07413c08.nc',
                    '07413c09.nc',
                    '07413c10.nc',
                    '07413c11.nc',
                      ]
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl' ]

# Spray glider - for just the duration of the campaign
##cl.l_662_base = 'http://www.cencoos.org/thredds/dodsC/glider/'
##cl.l_662_files = ['OS_Glider_L_662_20120816_TS.nc']
##cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
##cl.l_662_startDatetime = datetime.datetime(2012, 9, 1)
##cl.l_662_endDatetime = datetime.datetime(2012, 9, 21)


cl.stride = stride
##cl.loadAll()

# For testing.  Comment out the loadAll() call, and uncomment one of these as needed
##cl.loadDorado()
##cl.loadDaphne()
##cl.loadTethys()
##cl.loadESPmack()
##cl.loadESPbruce()
##cl.loadRCuctd()
cl.loadRCpctd()
##cl.loadHeHaPe()
##cl.loadRusalka()
##cl.loadL_662()

