#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for all April 2014 CANON-ECOHAB activities.  

Mike McCann MBARI 13 March 2013
edited by John Ryan, April 2014

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))      # So that CANON is found

from CANON import CANONLoader

cl = CANONLoader('stoqs_canon_apr2014', 'CANON-ECOHAB - April 2014',
                    x3dTerrains= { '/stoqs/static/x3d/SanPedroBasin50/SanPedroBasin50_10x-pop.x3d': {
                                        'position': '-2523652.5 -4726093.2 3499413.2',
                                        'orientation': '0.96902 -0.20915 -0.13134 1.74597',
                                        'centerOfRotation': '-2505293.6 -4686937.5 3513055.2',
                                        'VerticalExaggeration': '10',
                                        }
                                 } )

# Aboard the Carson use zuma
cl.tdsBase = 'http://zuma.rc.mbari.org/thredds/'       
##cl.tdsBase = 'http://odss.mbari.org/thredds/'       # Use this on shore
cl.dodsBase = cl.tdsBase + 'dodsC/'       

# 2-second decimated dorado data
cl.dorado_base = cl.dodsBase + 'CANON/2014_Apr/Platforms/AUVs/Dorado/' 
cl.dorado_files = [ 
                    #'Dorado389_2014_102_00_102_00_decim.nc',
                    #'Dorado389_2014_103_00_103_00_decim.nc',
                  ]

# Realtime telemetered (_r_) daphne data - insert '_r_' to not load the files
##cl.daphne_base = 'http://aosn.mbari.org/lrauvtds/dodsC/lrauv/daphne/2012/'
daphne_r_base = cl.dodsBase + 'CANON_march2013/lrauv/daphne/realtime/sbdlogs/2013/201303/'
daphne_r_files = [ 
                    'shore_201303132226_201303140449.nc',
                    'shore_201303140708_201303140729.nc',
                  ]
cl.daphne_r_parms = [ 'sea_water_temperature', 'mass_concentration_of_chlorophyll_in_sea_water']

# Postrecovery full-resolution (_d_) daphne data - insert '_d_' for delayed-mode to not load the data
daphne_d_base = 'http://dods.mbari.org/opendap/hyrax/data/lrauv/daphne/missionlogs/2013/'
daphne_d_files = [ 
                    '20130313_20130318/20130313T195025/201303131950_201303132226.nc',
                    '20130313_20130318/20130313T222616/201303132226_201303140321.nc',
                  ]
daphne_d_parms = [ 'sea_water_temperature', 'sea_water_salinity', 'sea_water_density', 'volume_scattering_470_nm', 
                    'volume_scattering_650_nm', 'mass_concentration_of_oxygen_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water',
                    'mass_concentration_of_chlorophyll_in_sea_water']

# Binned Daphne data
daphne_b_base = 'http://odss.mbari.org/thredds/dodsC/CANON_march2013/lrauv/daphne/'
daphne_b_files = ['Daphne_ECOHAB_March2013.nc']
daphne_b_parms = ['temperature', 'salinity', 'chlorophyll', 'bb470', 'bb650']

cl.daphne_base = daphne_b_base
cl.daphne_files = daphne_b_files
cl.daphne_parms = daphne_b_parms


# Realtime telemetered (_r_) tethys data - insert '_r_' to not load the files
tethys_r_base = cl.dodsBase + 'CANON_march2013/lrauv/tethys/realtime/sbdlogs/2013/201303/'
tethys_r_files = [ 
                    'shore_201303140812_201303141247.nc',
                    'shore_201303141252_201303141329.nc',
                    'shore_201303180743_201303181632.nc',       # Incomplete list of shore files
                  ]
tethys_r_parms = [ 'sea_water_temperature', 'mass_concentration_of_chlorophyll_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water',
                    'platform_x_velocity_current', 'platform_y_velocity_current', 'platform_z_velocity_current']

# Postrecovery full-resolution tethys data - insert '_d_' for delayed-mode to not load the data
tethys_d_base = 'http://dods.mbari.org/opendap/hyrax/data/lrauv/tethys/missionlogs/2013/'
tethys_d_files = [ 
                    '20130313_20130320/20130313T203723/201303132037_201303132240.nc',
                    '20130313_20130320/20130313T224020/201303132240_201303140239.nc',
                  ]

tethys_d_parms = [ 'sea_water_temperature', 'sea_water_salinity', 'sea_water_density', 'volume_scattering_470_nm', 
                    'volume_scattering_650_nm', 'mass_concentration_of_oxygen_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water',
                    'mass_concentration_of_chlorophyll_in_sea_water']

# Binned Tethys data
tethys_b_base = 'http://odss.mbari.org/thredds/dodsC/CANON_march2013/lrauv/tethys/'
tethys_b_files = ['Tethys_ECOHAB_March2013.nc']
tethys_b_parms = ['temperature', 'salinity', 'chlorophyll', 'bb470', 'bb650']

cl.tethys_base = tethys_b_base
cl.tethys_files = tethys_b_files
cl.tethys_parms = tethys_b_parms

# Webb gliders
cl.hehape_base = cl.dodsBase + 'CANON_march2013/usc_glider/HeHaPe/processed/'
cl.hehape_files = [
                        'OS_Glider_HeHaPe_20130305_TS.nc',
                        'OS_Glider_HeHaPe_20130310_TS.nc',
                   ]
cl.hehape_parms = [ 'TEMP', 'PSAL', 'BB532', 'CDOM', 'CHLA', 'DENS' ]

cl.rusalka_base = cl.dodsBase + 'CANON/2014_Apr/Platforms/Gliders/USC/'
cl.rusalka_files = [
                        'GliderRusalka.nc',
                   ]
cl.rusalka_parms = ['temperature', 'chlorophyll', 'bb532']

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
cl.rcuctd_base = cl.dodsBase + 'CANON/2014_Apr/Platforms/Ships/Rachel_Carson/uctd/'
cl.rcuctd_files = [ 
                        '07413plm01.nc', '07513plm02.nc', '07613plm03.nc', '07913plm04.nc',
                        '08013plm05.nc', '08113plm06.nc',
                      ]
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]

# Rachel Carson Profile CTD
cl.pctdDir = 'CANON/2014_Apr/Platforms/Ships/Rachel_Carson/pctd/'
cl.rcpctd_base = cl.dodsBase + cl.pctdDir
cl.rcpctd_files = [ 
                    '10214c01.nc', '10214c02.nc', '10214c03.nc', '10214c04.nc', '10214c05.nc', '10214c06.nc', '10314c07.nc', 
                    '10314c08.nc', '10314c09.nc', '10314c10.nc', '10314c11.nc',
                      ]
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]

# Spray glider - for just the duration of the campaign
##cl.l_662_base = 'http://www.cencoos.org/thredds/dodsC/glider/'
##cl.l_662_files = ['OS_Glider_L_662_20120816_TS.nc']
##cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
##cl.l_662_startDatetime = datetime.datetime(2012, 9, 1)
##cl.l_662_endDatetime = datetime.datetime(2012, 9, 21)


# Execute the load
cl.process_command_line()

if cl.args.test:
    ## cl.loadDorado(stride=10)
    ##cl.loadDaphne(stride=10)
    ##cl.loadTethys(stride=10)
    ##cl.loadESPmack()
    ##cl.loadESPbruce()
    ## cl.loadRCuctd(stride=2)
    cl.loadRCpctd(stride=1)
    ##cl.loadHeHaPe()
    ##cl.loadRusalka(stride=10)
    ##cl.loadYellowfin()

elif cl.args.optimal_stride:
    cl.loadDorado(stride=2)
    ##cl.loadDaphne(stride=2)
    ##cl.loadTethys(stride=2)
    ##cl.loadESPmack()
    ##cl.loadESPbruce()
    cl.loadRCuctd(stride=1)
    cl.loadRCpctd(stride=1)
    ##cl.loadHeHaPe(stride=10)      
    cl.loadRusalka()    
    ##cl.loadYellowfin()

else:
    cl.stride = cl.args.stride
    cl.loadDorado()
    ##cl.loadDaphne()
    ##cl.loadTethys()
    ##cl.loadESPmack()
    ##cl.loadESPbruce()
    cl.loadRCuctd()
    cl.loadRCpctd()
    ##cl.loadHeHaPe()
    cl.loadRusalka()
    ##cl.loadYellowfin()

# Add any X3D Terrain information specified in the constructor to the database
cl.addTerrainResources()
print "All done."
