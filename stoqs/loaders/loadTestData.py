#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2011, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

Load small sample of data from OPeNDAP and other data sources at MBARI
for testing purposes.  The collection should be sufficient to
provide decent test coverage for the STOQS application.

Mike McCann
MBARI Dec 28, 2011

@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

import os
from CANON import CANONLoader

# Assign input data sources
cl = CANONLoader('default', 'Initial Test Database',
                    description = 'Post-setup load of a single AUV mission',
                    x3dTerrains = {
                                    '/stoqsfiles/static/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                                        'position': '-2822317.31255 -4438600.53640 3786150.85474',
                                        'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                                        'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                                        'VerticalExaggeration': '10',
                                        'speed': '1',
                                    }
                    },
                    grdTerrain = os.path.join(os.path.dirname(__file__), 'Monterey25.grd')  # File expected in loaders directory
                )

# Assign input data sets from OPeNDAP URLs pointing to Discrete Sampling Geometry CF-NetCDF sources
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
cl.dorado_files = [ 'Dorado389_2010_300_00_300_00_decim.nc' ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700', 'fl700_uncorr', 'salinity', 'biolume' ]

# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadDorado(stride=100)

elif cl.args.optimal_stride:
    cl.loadDorado(stride=2)

else:
    if cl.args.stride:
        cl.logger.warn("Overriding stride parameter with a value of 1000 for this test load script")
    cl.args.stride = 1000
    cl.loadDorado(stride=cl.args.stride)

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print "All Done."

