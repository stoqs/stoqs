#!/usr/bin/env python
__author__    = 'Mike McCann,Duane Edgington,Reiko Michisaki'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'duane at mbari.org'

__doc__ = '''

Master loader for all CANON activities in September 2013

Mike McCann; Modified by Duane Edgington and Reiko Michisaki
MBARI 02 September 2013

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime  # needed for glider data
import time      # for startdate, enddate args
project_dir = os.path.dirname(__file__)

# the next line makes it possible to find CANON
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # this makes it possible to find CANON, one directory up

from CANON import CANONLoader
       
# building input data sources object
from socket import gethostname
hostname=gethostname()
print(hostname)
if hostname=='odss-test.shore.mbari.org':
    cl = CANONLoader('stoqs_september2011', 'CANON - September 2011')
else:
    cl = CANONLoader('stoqs_september2013', 'CANON - September 2013')


# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'

# Set start and end dates for mooring, twice per day.  In the morning and afternoon.
##t =time.strptime("2013-09-09 0:01", "%Y-%m-%d %H:%M")
##startdate=t[:6]
ts=time.time()-(33*60*60)
st=datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
t= time.strptime("2013-09-18 0:01", "%Y-%m-%d %H:%M") #deployed 09/18/13
#t=time.strptime(st,"%Y-%m-%d %H:%M")
startdate=t[:6]
t =time.strptime("2013-10-17 0:01", "%Y-%m-%d %H:%M")
enddate=t[:6]
print((startdate, enddate))

######################################################################
#  MOORINGS
######################################################################
# Mooring M1 Combined file produced by DPforSSDS processing - for just the duration of the campaign
#cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/201209/' # new deployment 09/18/13
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/201309/'
cl.m1_files = ['OS_M1_20130918hourly_CMSTV.nc']
cl.m1_parms = [ 'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
                     'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
                     'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR'
                   ]
cl.m1_startDatetime = datetime.datetime(*startdate[:])
cl.m1_endDatetime = datetime.datetime(*enddate[:])

cl.process_command_line()

if cl.args.test:
    cl.loadM1(stride=10)

elif cl.args.optimal_stride:
    cl.loadM1(stride=1)

else:
    cl.loadM1(stride=1)
