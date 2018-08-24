#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''
Master loader for all CANON activities in April 2011

Mike McCann
MBARI 22 April 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
import datetime
import timing

startdate = datetime.datetime(2011, 4, 15)
enddate = datetime.datetime(2011, 5, 3)

# Assign input data sources
cl = CANONLoader('stoqs_april2011', 'CANON - April 2011',
                    description = 'Dorado and Tethys surveys in Monterey Bay',
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

cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2011/netcdf/'
cl.dorado_files = [ 'Dorado389_2011_110_12_110_12_decim.nc',
                    'Dorado389_2011_111_00_111_00_decim.nc',
                    'Dorado389_2011_115_10_115_10_decim.nc',
                    'Dorado389_2011_116_00_116_00_decim.nc',
                    'Dorado389_2011_117_01_117_01_decim.nc',
                    'Dorado389_2011_118_00_118_00_decim.nc'
                  ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700', 
                    'fl700_uncorr', 'salinity', 'biolume', 
                    'sepCountList', 'mepCountList',
                    'roll', 'pitch', 'yaw',
                  ]

cl.tethys_base = 'http://dods.mbari.org/thredds/dodsC/LRAUV/tethys/missionlogs/2011/'
cl.tethys_files = [ '20110415_20110418/20110415T163108/slate.nc',
                    '20110415_20110418/20110416T074851/slate.nc',
                    '20110415_20110418/20110417T064753/slate.nc',
                    '20110415_20110418/20110418T060227/slate.nc',
                    '20110415_20110418/20110418T192351/slate.nc',
                    '20110421_20110424/20110421T170430/slate.nc',
                    '20110421_20110424/20110422T001932/slate.nc',
                    '20110421_20110424/20110423T223119/slate.nc',
                    '20110421_20110424/20110424T214938/slate.nc',
                    '20110426_20110502/20110426T171129/slate.nc',
                    '20110426_20110502/20110427T191236/slate.nc',
                    '20110426_20110502/20110429T222225/slate.nc',
                    '20110426_20110502/20110430T132028/slate.nc',
                    '20110426_20110502/20110502T040031/slate.nc'
                  ]
cl.tethys_parms = [ 'sea_water_temperature', 'sea_water_salinity', 'sea_water_density', 'volume_scattering_470_nm', 'volume_scattering_650_nm',
                    'volume_scattering_650_nm', 'mass_concentration_of_oxygen_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water',
                    'mass_concentration_of_chlorophyll_in_sea_water']

# Moorings
cl.m1_startDatetime = startdate
cl.m1_endDatetime = enddate
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/'
cl.m1_files = [
                '201010/OS_M1_20101027hourly_CMSTV.nc',
                '201010/m1_hs2_20101027.nc'
                ]
cl.m1_parms = [
                'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
                'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
                'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR',
                'bb470', 'bb676', 'fl676'
              ]

cl.m2_startDatetime = startdate
cl.m2_endDatetime = enddate
cl.m2_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m2/201004/'
cl.m2_files = [
                'OS_M2_20100402hourly_CMSTV.nc',
                'm2_hs2_20100402.nc',
                ]

cl.m2_parms = [ # No ADCP data from M2 in September 2010
                'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
                'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR',
                'bb470', 'bb676', 'fl676'
              ]


# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadDorado(stride=100)
    cl.loadLRAUV('tethys', startdate, enddate, stride=100, build_attrs=False)
    cl.loadM1(stride=100)
    cl.loadM2(stride=100)

elif cl.args.optimal_stride:
    cl.loadDorado(stride=2)
    cl.loadLRAUV('tethys', startdate, enddate, stride=20, build_attrs=False)
    cl.loadM1(stride=1)
    cl.loadM2(stride=1)

else:
    cl.stride = cl.args.stride

    cl.loadDorado()
    cl.loadLRAUV('tethys', startdate, enddate, build_attrs=False)
    cl.loadM1()
    cl.loadM2()
   
# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")
 

