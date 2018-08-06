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

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found


from CANON import CANONLoader
import timing

cl = CANONLoader('stoqs_canon_april2014', 'CANON-ECOHAB - April 2014',
                    description = 'Spring 2014 ECOHAB in San Pedro Bay',
                    x3dTerrains= { 'https://stoqs.mbari.org/x3d/SanPedroBasin50/SanPedroBasin50_10x-pop.x3d': {
                                        'position': '-2523652.5 -4726093.2 3499413.2',
                                        'orientation': '0.96902 -0.20915 -0.13134 1.74597',
                                        'centerOfRotation': '-2505293.6 -4686937.5 3513055.2',
                                        'VerticalExaggeration': '10',
                                        }
                                 },
                    grdTerrain = os.path.join(parentDir, 'SanPedroBasin50.grd')
                 )

# Aboard the Carson use zuma
##cl.tdsBase = 'http://zuma.rc.mbari.org/thredds/'       
cl.tdsBase = 'http://odss.mbari.org/thredds/'       # Use this on shore
cl.dodsBase = cl.tdsBase + 'dodsC/'       

# Decimated dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2014/netcdf/'
cl.dorado_files = [ 
                    'Dorado389_2014_102_00_102_00_decim.nc', 'Dorado389_2014_103_00_103_00_decim.nc',
                    'Dorado389_2014_103_01_103_01_decim.nc', 'Dorado389_2014_104_01_104_01_decim.nc',
                    'Dorado389_2014_107_00_107_00_decim.nc', 'Dorado389_2014_108_01_108_01_decim.nc',
                    'Dorado389_2014_108_02_108_02_decim.nc', 'Dorado389_2014_109_00_109_00_decim.nc', 
                    'Dorado389_2014_109_01_109_01_decim.nc',
                  ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                    'fl700_uncorr', 'salinity', 'biolume',
                    'sepCountList', 'mepCountList',
                    'roll', 'pitch', 'yaw',
                  ]

# Rachel Carson Underway CTD
cl.rcuctd_base = cl.dodsBase + 'CANON/2014_Apr/Platforms/Ships/Rachel_Carson/uctd/'
cl.rcuctd_files = [ 
                    '10214plm01.nc', '10314plm01.nc', '10414plm01.nc', '10714plm01.nc', '10814plm01.nc', '10914plm01.nc'
                      ]
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]

# Rachel Carson Profile CTD
cl.pctdDir = 'CANON/2014_Apr/Platforms/Ships/Rachel_Carson/pctd/'
cl.rcpctd_base = cl.dodsBase + cl.pctdDir
cl.rcpctd_files = [ 
                    '10214c01.nc', '10214c02.nc', '10214c03.nc', '10214c04.nc', '10214c05.nc', '10214c06.nc', '10314c07.nc', 
                    '10314c08.nc', '10314c09.nc', '10314c10.nc', '10314c11.nc', '10414c12.nc', '10414c13.nc', '10414c14.nc',
                    '10414c15.nc', '10414c16.nc', '10714c17.nc', '10714c18.nc', '10714c19.nc', '10714c20.nc', '10714c21.nc',
                    '10814c22.nc', '10814c23.nc', '10814c24.nc', '10814c25.nc', '10914c26.nc', '10914c27.nc', '10914c28.nc',
                      ]
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]


# Realtime telemetered (_r_) daphne data - insert '_r_' to not load the files
##cl.daphne_base = 'http://aosn.mbari.org/lrauvtds/dodsC/lrauv/daphne/2012/'
daphne_r_base = cl.dodsBase + 'CANON_march2013/lrauv/daphne/realtime/sbdlogs/2013/201303/'
daphne_r_files = [ 
                    'shore_201303132226_201303140449.nc',
                    'shore_201303140708_201303140729.nc',
                  ]
cl.daphne_r_parms = [ 'sea_water_temperature', 'mass_concentration_of_chlorophyll_in_sea_water']

# Postrecovery full-resolution (_d_) daphne data - insert '_d_' for delayed-mode to not load the data
daphne_d_base = 'http://dods.mbari.org/opendap/data/lrauv/daphne/missionlogs/2013/'
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
tethys_d_base = 'http://dods.mbari.org/opendap/data/lrauv/tethys/missionlogs/2013/'
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
cl.l_662_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
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

# Spray glider - for just the duration of the campaign
##cl.l_662_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
##cl.l_662_files = ['OS_Glider_L_662_20120816_TS.nc']
##cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
##cl.l_662_startDatetime = datetime.datetime(2012, 9, 1)
##cl.l_662_endDatetime = datetime.datetime(2012, 9, 21)


# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadDorado(stride=100)
    cl.loadRCuctd(stride=100)
    cl.loadRCpctd()

elif cl.args.optimal_stride:
    cl.loadDorado(stride=2)
    cl.loadRCuctd(stride=1)
    cl.loadRCpctd(stride=1)
    cl.loadRusalka()    

else:
    cl.stride = cl.args.stride
    cl.loadDorado()
    cl.loadRCuctd()
    cl.loadRCpctd()
    cl.loadRusalka()

# Add any X3D Terrain information specified in the constructor to the database
cl.addTerrainResources()
print("All done.")
