#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2012'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''
Master loader for all May 2012 CANON activities.  

Mike McCann
MBARI 21 AUgust 2012

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

cl = CANONLoader('stoqs_may2012', 'CANON - May 2012',
                    description = 'Front detection AUV and Glider surveys in Monterey Bay',
                    x3dTerrains = {
                            'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                                'position': '-2822317.31255 -4438600.53640 3786150.85474',
                                'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                                'centerOfRotation': '-2711557.94 -4331414.32 3801353.46',
                                'VerticalExaggeration': '10',
                                'speed': '.1',
                            }
                    },
                    grdTerrain = os.path.join(parentDir, 'Monterey25.grd')
                  )

startdate = datetime.datetime(2012, 5, 15)
enddate = datetime.datetime(2012, 6, 30)

# 2-second decimated dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2012/netcdf/'
cl.dorado_files = [ 
                    'Dorado389_2012_142_01_142_01_decim.nc',
                    'Dorado389_2012_142_02_142_02_decim.nc',
                    'Dorado389_2012_143_07_143_07_decim.nc',
                    'Dorado389_2012_143_08_143_08_decim.nc',
                    'Dorado389_2012_150_00_150_00_decim.nc',
                    'Dorado389_2012_151_00_151_00_decim.nc',
                    'Dorado389_2012_152_00_152_00_decim.nc',
                    'Dorado389_2012_157_07_157_07_decim.nc',
                    'Dorado389_2012_158_00_158_00_decim.nc',
                  ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700', 
                    'fl700_uncorr', 'salinity', 'biolume',
                    'sepCountList', 'mepCountList',
                    'roll', 'pitch', 'yaw',
                  ]

# Realtime telemetered (_r_) daphne data - insert '_r_' to not load the files
cl.daphne_base = 'http://elvis.shore.mbari.org/thredds/dodsC/LRAUV/daphne/realtime/sbdlogs/2012/'
cl.daphne_files = [ 
                    '201205/20120530T160348/shore.nc',
                    '201205/20120530T215940/shore.nc',
                    '201205/20120531T010135/shore.nc',
                    '201205/20120531T011043/shore.nc',
                    '201205/20120531T050931/shore.nc',
                    '201205/20120531T062937/shore.nc',
                    '201205/20120531T174058/shore.nc',
                    '201206/20120601T235829/shore.nc',
                    '201206/20120603T002455/shore.nc',
                    '201206/20120603T200613/shore.nc',
                    '201206/20120603T213551/shore.nc',
                    '201206/20120604T211315/shore.nc',
                    '201206/20120606T050637/shore.nc',
                    '201206/20120606T094236/shore.nc',
                    '201206/20120607T001433/shore.nc',
                    '201206/20120607T151546/shore.nc',
                    '201206/20120607T162945/shore.nc',
                  ]
cl.daphne_parms = [ 'platform_battery_charge', 'sea_water_temperature', 
                    'mass_concentration_of_oxygen_in_sea_water', 'mass_concentration_of_chlorophyll_in_sea_water']

# Postrecovery full-resolution (_d_) daphne data - insert '_d_' for delayed-mode to not load the data
cl.daphne_d_base = 'http://elvis.shore.mbari.org:8080/thredds/dodsC/lrauv/daphne/'
cl.daphne_d_files = [ 
                    '2012/20120531_20120607/20120531T062937/slate.nc',
                    '2012/20120531_20120607/20120603T002455/slate.nc',
                    '2012/20120531_20120607/20120603T213551/slate.nc',
                    '2012/20120531_20120607/20120604T211315/slate.nc',
                    '2012/20120531_20120607/20120606T050637/slate.nc',
                    '2012/20120531_20120607/20120606T094236/slate.nc',
                  ]
cl.daphne_d_parms = [ 'sea_water_temperature', 'sea_water_salinity', 'sea_water_density', 'volume_scattering_470_nm', 'volume_scattering_650_nm',
                    'volume_scattering_650_nm', 'mass_concentration_of_oxygen_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water',
                    'mass_concentration_of_chlorophyll_in_sea_water']
cl.daphne_startDatetime = startdate
cl.daphne_endDatetime = enddate

# Realtime telemetered (_r_) tethys data - insert '_r_' to not load the files
cl.tethys_base = 'http://elvis.shore.mbari.org/thredds/dodsC/LRAUV/tethys/realtime/sbdlogs/2012/'
cl.tethys_files = [ 
                    '201206/20120604T192851/shore.nc',
                    '201206/20120605T193027/shore.nc',
                    '201206/20120605T193653/shore.nc',
                    '201206/20120606T163010/shore.nc',
                    '201206/20120606T171537/shore.nc',
                    '201206/20120607T194649/shore.nc',
                    '201206/20120608T162946/shore.nc',
##                    '201206/20120608T193449/shore.nc',        # degenerate netCDF
                    '201206/20120608T194202/shore.nc',
                    '201206/20120608T205115/shore.nc',
                    '201206/20120610T190213/shore.nc',
                    '201206/20120613T050147/shore.nc',
                    '201206/20120613T085821/shore.nc',
                    '201206/20120613T162943/shore.nc',
                  ]
cl.tethys_parms = [ 'platform_battery_charge', 'sea_water_temperature', 
                    'mass_concentration_of_oxygen_in_sea_water', 'mass_concentration_of_chlorophyll_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water']

# Postrecovery full-resolution tethys data - insert '_d_' for delayed-mode to not load the data
cl.tethys_d_base = 'http://elvis.shore.mbari.org:8080/thredds/dodsC/lrauv/tethys/'
cl.tethys_d_files = [ 
                    '2012/20120606_20120613/20120606T171537/slate.nc',
                    '2012/20120606_20120613/20120607T194649/slate.nc',
                    '2012/20120606_20120613/20120608T205115/slate.nc',
                    '2012/20120606_20120613/20120610T190213/slate.nc',
                  ]

cl.tethys_d_parms = [ 'sea_water_temperature', 'sea_water_salinity', 'sea_water_density', 'volume_scattering_470_nm', 'volume_scattering_650_nm',
                    'volume_scattering_650_nm', 'mass_concentration_of_oxygen_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water',
                    'mass_concentration_of_chlorophyll_in_sea_water']
cl.tethys_startDatetime = startdate
cl.tethys_endDatetime = enddate

cl.fulmar_base = []
cl.fulmar_files = []
cl.fulmar_parms = []

# NPS glider 
cl.nps_g29_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.nps_g29_files = ['OS_Glider_NPS_G29_20120524_TS.nc']
cl.nps_g29_parms = ['TEMP', 'PSAL', 'OPBS']

# Spray glider - for just the duration of the campaign
cl.l_662_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_files = ['OS_Glider_L_662_20120424_TS.nc']
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = startdate
cl.l_662_endDatetime = enddate

# Liquid Robotics Waveglider
cl.waveglider_base = 'http://odss.mbari.org/thredds/dodsC/CANON/2012_May/waveglider/netcdf/'
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
cl.waveglider_startDatetime = startdate
cl.waveglider_endDatetime = enddate


# Mooring M1 Combined file produced by DPforSSDS processing - for just the duration of the campaign
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/201202/'
cl.m1_files = ['OS_M1_20120222hourly_CMSTV.nc']
cl.m1_parms = [ 'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
                'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
                'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR'
              ]
cl.m1_startDatetime = startdate
cl.m1_endDatetime = enddate


# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadDorado(stride=100)
    cl.loadLRAUV('tethys', startdate, enddate, stride=100, build_attrs=False)
    cl.loadLRAUV('daphne', startdate, enddate, stride=100, build_attrs=False)
    cl.loadNps_g29(stride=100)
    cl.loadL_662(stride=100)
    cl.loadWaveglider(stride=100)
    cl.loadM1(stride=10)

elif cl.args.optimal_stride:
    cl.loadDorado(stride=2)
    cl.loadLRAUV('tethys', startdate, enddate, stride=1, build_attrs=False)
    cl.loadLRAUV('daphne', startdate, enddate, stride=1, build_attrs=False)
    cl.loadNps_g29(stride=1)
    cl.loadL_662(stride=1)
    cl.loadWaveglider(stride=1)
    cl.loadM1(stride=1)

else:
    cl.stride = cl.args.stride
    cl.loadDorado()
    cl.loadLRAUV('tethys', startdate, enddate, build_attrs=False)
    cl.loadLRAUV('daphne', startdate, enddate, build_attrs=False)
    cl.loadNps_g29()
    cl.loadL_662()
    cl.loadWaveglider()
    cl.loadM1()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")


