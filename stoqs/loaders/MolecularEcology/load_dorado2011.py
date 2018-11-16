#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''
Loader for all 2011 Dorado missions written for loading Vrijenhoek Lab SubSamples from Julio

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

cl = CANONLoader('stoqs_dorado2011', 'Dorado - All 2011 missions',
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

# Dorado surveys in 2011
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2011/netcdf/'
cl.dorado_files = [ 
                    'Dorado389_2011_060_01_060_01_decim.nc',
                    'Dorado389_2011_061_00_061_00_decim.nc',
                    'Dorado389_2011_062_05_062_05_decim.nc',
                    'Dorado389_2011_074_02_074_02_decim.nc',
                    'Dorado389_2011_110_12_110_12_decim.nc',
                    'Dorado389_2011_111_00_111_00_decim.nc',
                    'Dorado389_2011_115_10_115_10_decim.nc',
                    'Dorado389_2011_116_00_116_00_decim.nc',
                    'Dorado389_2011_117_01_117_01_decim.nc',
                    'Dorado389_2011_118_00_118_00_decim.nc',
                    'Dorado389_2011_155_04_155_04_decim.nc',
                    'Dorado389_2011_157_01_157_01_decim.nc',
                    'Dorado389_2011_158_00_158_00_decim.nc',
                    'Dorado389_2011_164_05_164_05_decim.nc',
                    'Dorado389_2011_165_00_165_00_decim.nc',
                    'Dorado389_2011_166_00_166_00_decim.nc',
                    'Dorado389_2011_171_01_171_01_decim.nc',
                    'Dorado389_2011_172_00_172_00_decim.nc',
                    'Dorado389_2011_249_00_249_00_decim.nc',
                    'Dorado389_2011_250_01_250_01_decim.nc',
                    'Dorado389_2011_255_00_255_00_decim.nc',
                    'Dorado389_2011_256_02_256_03_decim.nc',
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
                    'roll', 'pitch', 'yaw']

# Mooring M1ts
cl.m1ts_base = 'http://elvis.shore.mbari.org/thredds/dodsC/agg/'
cl.m1ts_files = ['OS_MBARI-M1_R_TS']
cl.m1ts_parms = [ 'PSAL', 'TEMP' ]
cl.m1ts_startDatetime = datetime.datetime(2011, 1, 1)
cl.m1ts_endDatetime = datetime.datetime(2011, 12, 31)

# Mooring M1met
cl.m1met_base = 'http://elvis.shore.mbari.org/thredds/dodsC/agg/'
cl.m1met_files = ['OS_MBARI-M1_R_M']
cl.m1met_parms = [ 'WSPD', 'WDIR', 'ATMP', 'SW', 'RELH' ]
cl.m1met_startDatetime = datetime.datetime(2011, 1, 1)
cl.m1met_endDatetime = datetime.datetime(2011, 12, 31)

# SubSample data files received from Julio in email and copied to local directory
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Dorado2011')
cl.subsample_csv_files = [
                            '2011_AUVdorado_Samples_Database.csv'
                         ]


# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadDorado(stride=100)
    cl.loadM1ts(stride=10)
    cl.loadM1met(stride=10)
    cl.loadSubSamples()

elif cl.args.optimal_stride:
    cl.loadDorado(stride=2)
    cl.loadM1ts(stride=1)
    cl.loadM1met(stride=1)
    cl.loadSubSamples()

else:
    cl.loadDorado(stride=cl.args.stride)
    cl.loadM1ts(stride=cl.args.stride)
    cl.loadM1met(stride=cl.args.stride)
    cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

