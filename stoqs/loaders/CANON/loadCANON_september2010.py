#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''
Master loader for all CANON activities in September 2010

Mike McCann
MBARI 22 April 2012
'''

import os
import sys
parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found
from CANON import CANONLoader

# Assign input data sources
cl = CANONLoader('stoqs_september2010', 'CANON - September 2010',
                    description = 'ESP Drift with Dorado circling outside Monterey Bay',
                    x3dTerrains = {
                        'http://dods.mbari.org/terrain/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                            'position': '-2822317.31255 -4438600.53640 3786150.85474',
                            'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                            'centerOfRotation': '-2711557.94 -4331414.32 3801353.46',
                            'VerticalExaggeration': '10',
                            'speed': '.1',
                        }
                    },
                    grdTerrain = os.path.join(parentDir, 'Monterey25.grd')
                )

cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
cl.dorado_files = [ 'Dorado389_2010_257_01_258_04_decim.nc',
                    'Dorado389_2010_258_05_258_08_decim.nc',
                    'Dorado389_2010_259_00_259_03_decim.nc',
                    'Dorado389_2010_260_00_260_00_decim.nc',
                    'Dorado389_2010_261_00_261_00_decim.nc',
                  ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                    'fl700_uncorr', 'salinity', 'biolume',
                    'sepCountList', 'mepCountList',
                  ]

# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadDorado(stride=100)

elif cl.args.optimal_stride:
    cl.loadDorado(stride=2)

else:
    cl.loadDorado(stride=cl.args.stride)

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print "All Done."

