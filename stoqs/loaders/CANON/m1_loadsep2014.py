#!/usr/bin/env python
__author__    = 'Mike McCann,Duane Edgington,Reiko Michisaki'
__copyright__ = '2014'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Real-time data loader for M1 Mooring data for Fall 2014 CANON campaign

Mike McCann; Modified by Duane Edgington and Reiko Michisaki
MBARI 02 September 2014

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime
import time

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader

cl = CANONLoader('stoqs_september2014', 'CANON-ECOHAB - September 2014',
                    description = 'Fall 2014 Dye Release Experiment in Monterey Bay',
                    x3dTerrains = {
                                    'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                                        'position': '-2822317.31255 -4438600.53640 3786150.85474',
                                        'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                                        'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                                        'VerticalExaggeration': '10',
                                        'speed': '1',
                                    }
                    },
                    grdTerrain = os.path.join(parentDir, 'Monterey25.grd')
                  )

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'

######################################################################
#  MOORINGS
######################################################################
# Set beginning start and end dates for this campaign - if this script is to be run regularly from cron to add new
# data to STOQS then use the --append option to append new data.  Do not change these values.
cl.m1_startDatetime = datetime.datetime(2014, 9, 1)
cl.m1_endDatetime  = datetime.datetime(2014, 10, 12)

# Mooring M1 Combined file produced by DPforSSDS processing - for just the duration of the campaign
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/201407/'
cl.m1_files = ['OS_M1_20140716hourly_CMSTV.nc']
cl.m1_parms = [ 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR', 'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR',
                'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR',
                'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR' ]

cl.process_command_line()

if cl.args.test:
    cl.loadM1(stride=10)

elif cl.args.optimal_stride:
    cl.loadM1(stride=1)

else:
    cl.loadM1(stride=1)

