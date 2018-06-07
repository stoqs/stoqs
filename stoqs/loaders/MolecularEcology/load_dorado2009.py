#!/usr/bin/env python
'''
Loader for all 2009 Dorado missions written for Monique's notice of bad
depths in Dorado389_2009_084_02_084_02_decim.nc.

Mike McCann
MBARI 15 January 2013

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

cl = CANONLoader('stoqs_dorado2009', 'Dorado - All 2009 missions',
                    description = 'In Monterey Bay and Santa Monica Basin - includes processed Gulper Samples',
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

# Dorado surveys in 2009
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2009/netcdf/'
cl.dorado_files = [ 
                    'Dorado389_2009_055_05_055_05_decim.nc',
                    'Dorado389_2009_084_00_084_00_decim.nc',
                    'Dorado389_2009_084_02_084_02_decim.nc',
                    'Dorado389_2009_085_02_085_02_decim.nc',
                    'Dorado389_2009_111_00_111_00_decim.nc',
                    'Dorado389_2009_111_01_111_01_decim.nc',
                    'Dorado389_2009_112_07_112_07_decim.nc',
                    'Dorado389_2009_113_00_113_00_decim.nc',
                    'Dorado389_2009_124_03_124_03_decim.nc',
                    'Dorado389_2009_125_00_125_00_decim.nc',
                    'Dorado389_2009_126_00_126_00_decim.nc',
                    'Dorado389_2009_152_00_152_00_decim.nc',
                    'Dorado389_2009_153_01_153_01_decim.nc',
                    'Dorado389_2009_154_00_154_00_decim.nc',
                    'Dorado389_2009_155_03_155_03_decim.nc',
                    'Dorado389_2009_182_01_182_01_decim.nc',
                    'Dorado389_2009_272_00_272_00_decim.nc',
                    'Dorado389_2009_274_03_274_03_decim.nc',
                    'Dorado389_2009_278_01_278_01_decim.nc',
                    'Dorado389_2009_278_01_278_02_decim.nc',
                    'Dorado389_2009_279_00_279_00_decim.nc',
                    'Dorado389_2009_280_00_280_00_decim.nc',
                    'Dorado389_2009_281_01_281_01_decim.nc',
                    'Dorado389_2009_308_04_308_04_decim.nc',
                    'Dorado389_2009_309_00_309_03_decim.nc',
                    'Dorado389_2009_313_02_313_02_decim.nc',
                    'Dorado389_2009_342_04_342_04_decim.nc',
                    'Dorado389_2009_348_05_348_05_decim.nc',
                  ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700', 
                    'fl700_uncorr', 'salinity', 'biolume',
                    'sepCountList', 'mepCountList',
                    'roll', 'pitch', 'yaw']

# Mooring M1ts
cl.m1ts_base = 'http://elvis.shore.mbari.org/thredds/dodsC/agg/'
cl.m1ts_files = ['OS_MBARI-M1_R_TS']
cl.m1ts_parms = [ 'PSAL', 'TEMP' ]
cl.m1ts_startDatetime = datetime.datetime(2009, 1, 1)
cl.m1ts_endDatetime = datetime.datetime(2009, 12, 31)

# Mooring M1met
cl.m1met_base = 'http://elvis.shore.mbari.org/thredds/dodsC/agg/'
cl.m1met_files = ['OS_MBARI-M1_R_M']
cl.m1met_parms = [ 'WSPD', 'WDIR', 'ATMP', 'SW', 'RELH' ]
cl.m1met_startDatetime = datetime.datetime(2009, 1, 1)
cl.m1met_endDatetime = datetime.datetime(2009, 12, 31)


# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadDorado(stride=20)
    ##cl.loadM1ts(stride=10)
    ##cl.loadM1met(stride=10)

elif cl.args.optimal_stride:
    cl.loadDorado(stride=2)
    cl.loadM1ts(stride=1)
    cl.loadM1met(stride=1)

else:
    cl.loadDorado(stride=cl.args.stride)
    ##cl.loadM1ts(stride=cl.args.stride)
    ##cl.loadM1met(stride=cl.args.stride)

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

