#!/usr/bin/env python
__author__    = 'Mike McCann,Duane Edgington,Reiko Michisaki'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'duane at mbari.org'

__doc__ = '''

Loader for OA CANON activities in September 2013

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

######################################################################
# Set start and end dates for all glider loads
#t =time.strptime("2013-09-11 0:01", "%Y-%m-%d %H:%M")
ts=time.time()-(11*60*60)
st=datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
startdate=t[:6]
t =time.strptime("2013-09-29 0:01", "%Y-%m-%d %H:%M")
enddate=t[:6]

# Mooring OA1 CTD
cl.oaDir = 'CANON_september2013/Platforms/Moorings/OA_1/'
cl.OA1ctd_base = cl.dodsBase + cl.oaDir
cl.OA1ctd_files = ['OA1_ctd_2013.nc']
cl.OA1ctd_parms = ['TEMP', 'PSAL', 'conductivity' ]
cl.OA1ctd_startDatetime = datetime.datetime(*startdate[:])
cl.OA1ctd_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA1 MET
cl.OA1met_base = cl.dodsBase + cl.oaDir
cl.OA1met_files = ['OA1_met_2013.nc']
cl.OA1met_parms = ['Wind_direction','Wind_speed','Air_temperature','Barometric_pressure']
cl.OA1met_startDatetime = datetime.datetime(*startdate[:])
cl.OA1met_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA1 PH
cl.OA1pH_base = cl.dodsBase + cl.oaDir
cl.OA1pH_files = ['OA1_pH_2013.nc']
cl.OA1pH_parms = ['pH' ]
cl.OA1pH_startDatetime = datetime.datetime(*startdate[:])
cl.OA1pH_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA1 PCO2
cl.OA1pco2_base = cl.dodsBase + cl.oaDir
cl.OA1pco2_files = ['OA1_pco2_2013.nc']
cl.OA1pco2_parms = ['pCO2' ]
cl.OA1pco2_startDatetime = datetime.datetime(*startdate[:])
cl.OA1pco2_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA1 O2
cl.OA1o2_base = cl.dodsBase + cl.oaDir
cl.OA1o2_files = ['OA1_o2_2013.nc']
cl.OA1o2_parms = ['oxygen', 'oxygen_saturation' ]
cl.OA1o2_startDatetime = datetime.datetime(*startdate[:])
cl.OA1o2_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA1 Fluorescence
cl.OA1fl_base = cl.dodsBase + cl.oaDir
cl.OA1fl_files = ['OA1_fl_2013.nc']
cl.OA1fl_parms = [ 'fluor' ]
cl.OA1fl_startDatetime = datetime.datetime(*startdate[:])
cl.OA1fl_endDatetime = datetime.datetime(*enddate[:])
 
# Mooring OA2 CTD
cl.oaDir = 'CANON_september2013/Platforms/Moorings/OA_2/'
cl.OA2ctd_base = cl.dodsBase + cl.oaDir
cl.OA2ctd_files = ['OA2_ctd_2013.nc']
cl.OA2ctd_parms = ['TEMP', 'PSAL', 'conductivity' ]
cl.OA2ctd_startDatetime = datetime.datetime(*startdate[:])
cl.OA2ctd_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA2 MET
cl.OA2met_base = cl.dodsBase + cl.oaDir
cl.OA2met_files = ['OA2_met_2013.nc']
cl.OA2met_parms = ['Wind_direction','Wind_speed','Air_temperature','Barometric_pressure']
cl.OA2met_startDatetime = datetime.datetime(*startdate[:])
cl.OA2met_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA2 PH
cl.OA2pH_base = cl.dodsBase + cl.oaDir
cl.OA2pH_files = ['OA2_pH_2013.nc']
cl.OA2pH_parms = ['pH' ]
cl.OA2pH_startDatetime = datetime.datetime(*startdate[:])
cl.OA2pH_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA2 PCO2
cl.OA2pco2_base = cl.dodsBase + cl.oaDir
cl.OA2pco2_files = ['OA2_pco2_2013.nc']
cl.OA2pco2_parms = ['pCO2' ]
cl.OA2pco2_startDatetime = datetime.datetime(*startdate[:])
cl.OA2pco2_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA2 O2
cl.OA2o2_base = cl.dodsBase + cl.oaDir
cl.OA2o2_files = ['OA2_o2_2013.nc']
cl.OA2o2_parms = ['oxygen', 'oxygen_saturation' ]
cl.OA2o2_startDatetime = datetime.datetime(*startdate[:])
cl.OA2o2_endDatetime = datetime.datetime(*enddate[:])
# Mooring OA2 Fluorescence
cl.OA2fl_base = cl.dodsBase + cl.oaDir
cl.OA2fl_files = ['OA2_fl_2013.nc']
cl.OA2fl_parms = [ 'fluor' ]
cl.OA2fl_startDatetime = datetime.datetime(*startdate[:])
cl.OA2fl_endDatetime = datetime.datetime(*enddate[:])
 
###################################################################################################################
# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadOA1ctd(stride=1)
    cl.loadOA1met(stride=1)
    cl.loadOA1pH(stride=1)
    cl.loadOA1pco2(stride=1)
    cl.loadOA1fl(stride=1)
    cl.loadOA1o2(stride=1)
    cl.loadOA2ctd(stride=1)
    cl.loadOA2met(stride=1)
    cl.loadOA2pH(stride=1)
   ##cl.loadOA2pco2(stride=1)
    cl.loadOA2fl(stride=1)
    cl.loadOA2o2(stride=1)

elif cl.args.optimal_stride:
    cl.loadOA1ctd(stride=1)
    cl.loadOA1met(stride=1)
    cl.loadOA1pH(stride=1)
    cl.loadOA1pco2(stride=1)
    cl.loadOA1fl(stride=1)
    cl.loadOA1o2(stride=1)
    cl.loadOA2ctd(stride=1)
    cl.loadOA2met(stride=1)
    cl.loadOA2pH(stride=1)
   ##cl.loadOA2pco2(stride=1)
    cl.loadOA2fl(stride=1)
    cl.loadOA2o2(stride=1)

else:
    cl.loadOA1ctd(stride=1)
    cl.loadOA1met(stride=1)
    cl.loadOA1pH(stride=1)
    cl.loadOA1pco2(stride=1)
    cl.loadOA1fl(stride=1)
    cl.loadOA1o2(stride=1)
    cl.loadOA2ctd(stride=1)
    cl.loadOA2met(stride=1)
    cl.loadOA2pH(stride=1)
   ##cl.loadOA2pco2(stride=1)
    cl.loadOA2fl(stride=1)
    cl.loadOA2o2(stride=1)


