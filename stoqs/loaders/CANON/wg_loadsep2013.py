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
ts=time.time()-(13.2*60*60)  
st=datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
t=time.strptime(st,"%Y-%m-%d %H:%M")
#t =time.strptime("2013-09-01 0:01", "%Y-%m-%d %H:%M")
startdate=t[:6]
t =time.strptime("2013-10-31 0:01", "%Y-%m-%d %H:%M")
enddate=t[:6]


# Glider ctd
cl.glider_ctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/Slocum_Teledyne/'
cl.glider_ctd_files = [ 'nemesis_ctd.nc',
#                        'ucsc260_ctd.nc',
                        'ucsc294_ctd.nc']
cl.glider_ctd_parms = ['TEMP', 'PSAL' ]
cl.glider_ctd_startDatetime = datetime.datetime(*startdate[:])
cl.glider_ctd_endDatetime = datetime.datetime(*enddate[:])


# Glider met 
cl.glider_met_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/Slocum_Teledyne/'
cl.glider_met_files = [ 'nemesis_met.nc',
#                        'ucsc260_met.nc',
                        'ucsc294_met.nc']
cl.glider_met_parms = ['meanu','meanv' ]
cl.glider_met_startDatetime = datetime.datetime(*startdate[:])
cl.glider_met_endDatetime = datetime.datetime(*enddate[:])

# WG OA
cl.wg_oa_ctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/WG_OA/NetCDF/'
cl.wg_oa_ctd_files = [ 'WG_OA_ctd.nc']
cl.wg_oa_ctd_parms = ['TEMP', 'PSAL','DENSITY','OXYGEN' ]
cl.wg_oa_ctd_startDatetime = datetime.datetime(*startdate[:])
cl.wg_oa_ctd_endDatetime = datetime.datetime(*enddate[:])

# WG Tex
cl.wg_tex_ctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/WG_Tex/NetCDF/'
cl.wg_tex_ctd_files = [ 'WG_Tex_ctd.nc']
cl.wg_tex_ctd_parms = ['TEMP', 'PSAL','DENSITY' ]
cl.wg_tex_ctd_startDatetime = datetime.datetime(*startdate[:])
cl.wg_tex_ctd_endDatetime = datetime.datetime(*enddate[:])
 
# WG OA
cl.wg_oa_met_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/WG_OA/NetCDF/'
cl.wg_oa_met_files = [ 'WG_OA_met.nc']
cl.wg_oa_met_parms = ['WINDSPEED','WINDDIRECTION','AIRTEMPERATURE','AIRPRESSURE']
cl.wg_oa_met_startDatetime = datetime.datetime(*startdate[:])
cl.wg_oa_met_endDatetime = datetime.datetime(*enddate[:])

# WG Tex
cl.wg_tex_met_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/WG_Tex/NetCDF/'
cl.wg_tex_met_parms = ['WINDSPEED','WINDDIRECTION','AIRTEMPERATURE','AIRPRESSURE']
cl.wg_tex_met_files = [ 'WG_Tex_met.nc']
cl.wg_tex_met_startDatetime = datetime.datetime(*startdate[:])
cl.wg_tex_met_endDatetime = datetime.datetime(*enddate[:])

# WG OA
cl.wg_oa_pco2_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/WG_OA/NetCDF/'
cl.wg_oa_pco2_files = [ 'WG_OA_pco2.nc']
cl.wg_oa_pco2_parms = ['pH','eqpco2','airco2','airtemp' ]
cl.wg_oa_pco2_startDatetime = datetime.datetime(*startdate[:])
cl.wg_oa_pco2_endDatetime = datetime.datetime(*enddate[:])


###################################################################################################################
# Execute the load
cl.process_command_line()

if cl.args.test:
#    cl.load_wg_oa_pco2(stride=1) 
#    cl.load_wg_oa_ctd(stride=1) 
#    cl.load_wg_oa_met(stride=1) 
    cl.load_wg_tex_ctd(stride=1) 
    cl.load_wg_tex_met(stride=1) 
    cl.load_glider_ctd(stride=1)
    cl.load_glider_met(stride=1)

elif cl.args.optimal_stride:
#    cl.load_wg_oa_pco2(stride=2) 
#    cl.load_wg_oa_ctd(stride=2) 
#    cl.load_wg_oa_met(stride=2) 
    cl.load_wg_tex_ctd(stride=2) 
    cl.load_wg_tex_met(stride=2) 
    cl.load_glider_ctd(stride=2)
    cl.load_glider_met(stride=2)

else:
#    cl.load_wg_oa_pco2(stride=1) 
#    cl.load_wg_oa_ctd(stride=1) 
#    cl.load_wg_oa_met(stride=1) 
    cl.load_wg_tex_ctd(stride=1) 
    cl.load_wg_tex_met(stride=1) 
    cl.load_glider_ctd(stride=1)
    cl.load_glider_met(stride=1)

