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
import datetime
from CANON import CANONLoader
import timing

# Assign input data sources - use locally served x3d terrain data
cl = CANONLoader('default', 'Initial Test Database',
                    description = 'Post-setup load of a variety of data to use for testing',
                    x3dTerrains = {
                            '/static/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                                'position': '-2822317.31255 -4438600.53640 3786150.85474',
                                'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                                'centerOfRotation': '-2711557.94 -4331414.32 3801353.46',
                                'VerticalExaggeration': '10',
                                'speed': '.1',
                            }
                    },
                    # Terrain data file is expected to be in loaders directory
                    grdTerrain = os.path.join(os.path.dirname(__file__), 'Monterey25.grd')
                )

# Assign input data sets from OPeNDAP URLs pointing to Discrete Sampling Geometry CF-NetCDF sources

# - Trajectory
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
cl.dorado_files = [ 'Dorado389_2010_300_00_300_00_decim.nc' ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700', 
                    'fl700_uncorr', 'salinity', 'biolume', 'roll', 'pitch', 'yaw',
                    'sepCountList', 'mepCountList']

# - TimeSeries and TimeSeriesProfile
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/'
cl.m1_files = [ '201010/OS_M1_20101027hourly_CMSTV.nc',
                '201010/m1_hs2_20101027.nc',
              ]
cl.m1_parms = [ 'northward_sea_water_velocity_HR', 'SEA_WATER_SALINITY_HR', 
                'SEA_WATER_TEMPERATURE_HR', 'AIR_TEMPERATURE_HR', 'bb470', 'fl676'
              ]
cl.m1_startDatetime = datetime.datetime(2010, 10, 27)
cl.m1_endDatetime = datetime.datetime(2010, 10, 29)

# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/GOC12/ copied to local GOC12 dir
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../stoqs/tests')
cl.subsample_csv_files = ['Dorado_2010_300_Bogus_Samples.csv']


# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadDorado(stride=100, plankton_proxies=False)
    cl.loadM1(stride=10)
    cl.loadSubSamples()

elif cl.args.optimal_stride:
    cl.loadDorado(stride=2, plankton_proxies=False)
    cl.loadM1(stride=1)
    cl.loadSubSamples()

else:
    if cl.args.stride:
        cl.logger.warning("Overriding Dorado load stride parameter with a value of 1000 for this test load script")
    cl.loadDorado(stride=1000, plankton_proxies=False)
    cl.loadM1(stride=2)
    cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

