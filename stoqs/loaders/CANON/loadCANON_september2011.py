#!/usr/bin/env python
__author__    = 'Duane Edgington'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'duane at mbari.org'

__doc__ = '''

Master loader for all CANON activities in September 2011

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

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
import timing

cl = CANONLoader('stoqs_september2011', 'CANON - September 2011',
                    description = 'CANON observing campaign in Monterey Bay',
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

startdate = datetime.datetime(2011, 9, 6)
enddate = datetime.datetime(2011, 10, 14)

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'


# special location for dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2011/netcdf/'
cl.dorado_files = [  'Dorado389_2011_249_00_249_00_decim.nc',
                     'Dorado389_2011_250_01_250_01_decim.nc',
                     'Dorado389_2011_255_00_255_00_decim.nc',
                     'Dorado389_2011_257_00_257_00_decim.nc',
                     'Dorado389_2011_262_00_262_00_decim.nc',
                     'Dorado389_2011_263_00_263_00_decim.nc',
                     'Dorado389_2011_264_00_264_00_decim.nc',
                     'Dorado389_2011_285_01_285_01_decim.nc',
                     'Dorado389_2011_286_00_286_00_decim.nc',
                  ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                    'fl700_uncorr', 'salinity', 'biolume',
                    'sepCountList', 'mepCountList',
                    'roll', 'pitch', 'yaw',
                  ]


# special location for spray glider data
# Spray glider - for just the duration of the campaign
cl.l_662_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_files = ['OS_Glider_L_662_20110915_TS.nc',
                 ]

cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = startdate
cl.l_662_endDatetime = enddate


######################################################################
#  WESTERN FLYER
######################################################################

cl.wfuctd_base = cl.dodsBase + 'CANON_september2011/wf/uctd/'
cl.wfuctd_files = [
                    '27211WF01.nc', '27411WF01.nc', '27511WF01.nc', '27711WF01.nc', 
                    '27811WF01.nc', '27911wf01.nc', '28011wf01.nc', '28111wf01.nc', '28211wf01.nc',
                  ]
cl.wfuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]

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

cl.m2_parms = [
                'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
                'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR',
                'bb470', 'bb676', 'fl676'
              ]

# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.stride = 100
elif cl.args.stride:
    cl.stride = cl.args.stride

cl.loadDorado()
cl.loadL_662()
cl.loadWFuctd()
cl.loadWFpctd()
cl.loadM1()
cl.loadM2()


# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print( "All Done.")
