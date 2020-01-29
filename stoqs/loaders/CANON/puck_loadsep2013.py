#!/usr/bin/env python
__author__    = 'Mike McCann,Duane Edgington,Reiko Michisaki'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'duane at mbari.org'

__doc__ = '''

cron loader for  CANON  wave gliders slocum, OA and TEX in September 2013

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
#  GLIDERS
######################################################################
# Set start and end dates for all glider loads
# startdate is 24hours from now
ts=time.time()-(12.2*60*60)  
st=datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
t=time.strptime(st,"%Y-%m-%d %H:%M")
t =time.strptime("2013-09-03 0:01", "%Y-%m-%d %H:%M")
startdate=t[:6]
t =time.strptime("2013-10-15 0:01", "%Y-%m-%d %H:%M")
enddate=t[:6]


# WG Tex Eco Puck
cl.wg_tex_ctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/WG_Tex/NetCDF/'
cl.wg_tex_ctd_files = [ 'WG_Tex_eco.nc']
cl.wg_tex_ctd_parms = ['chlorophyll','backscatter650','backscatter470']
cl.wg_tex_ctd_startDatetime = datetime.datetime(*startdate[:])
cl.wg_tex_ctd_endDatetime = datetime.datetime(*enddate[:])
 


###################################################################################################################
# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.load_wg_tex_ctd(stride=1) 

elif cl.args.optimal_stride:
    cl.load_wg_tex_ctd(stride=1) 
#    cl.loadStella204(stride=1)

else:

    cl.load_wg_tex_ctd(stride=1) 
