#!/usr/bin/env python

'''
Script to append a small amount of mooring data to an activity already
in the default database.  This is meant for testing the --append option
for our load scripts.

Mike McCann
MBARI 6 September 2018
'''

import datetime
from CANON import CANONLoader
import timing

# Assign input data sources - use locally served x3d terrain data
cl = CANONLoader('default', 'Initial Test Database')

# Assign input data sets from OPeNDAP URLs pointing to Discrete Sampling Geometry CF-NetCDF sources
# - TimeSeries and TimeSeriesProfile
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/'
cl.m1_files = [ '201010/OS_M1_20101027hourly_CMSTV.nc',
                '201010/m1_hs2_20101027.nc',
              ]
cl.m1_parms = [ 'northward_sea_water_velocity_HR', 'SEA_WATER_SALINITY_HR', 
                'SEA_WATER_TEMPERATURE_HR', 'AIR_TEMPERATURE_HR', 'bb470', 'fl676'
              ]

# Use the same startDatetime as in loadTestData.py so that the Activity is named the same
# Load 1 more hour of data beyond the endDatetime in loadTestData.py
cl.m1_startDatetime = datetime.datetime(2010, 10, 27)
cl.m1_endDatetime = datetime.datetime(2010, 10, 29, 1)


# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadM1(stride=10)

elif cl.args.optimal_stride:
    cl.loadM1(stride=1)

else:
    cl.loadM1(stride=2)

print("All Done.")

