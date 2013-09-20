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
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)

# the next line makes it possible to find CANON
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # this makes it possible to find CANON, one directory up

from CANON import CANONLoader
       
# building input data sources object
#cl = CANONLoader('stoqs_september2011', 'CANON - September 2011')
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
#t =time.strptime("2013-09-03 20:01", "%Y-%m-%d %H:%M")
startdate=t[:6]
t =time.strptime("2013-10-31 10:37", "%Y-%m-%d %H:%M")
enddate=t[:6]
print startdate, enddate
# SPRAY glider - for just the duration of the campaign
cl.l_662_base = 'http://www.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_files = ['OS_Glider_L_662_20130711_TS.nc']
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = datetime.datetime(*startdate[:]) 
cl.l_662_endDatetime = datetime.datetime(*enddate[:])

# NPS34
cl.nps34_base = 'http://www.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.nps34_files = [ 'OS_Glider_NPS_G34_20130829_TS.nc']
cl.nps34_parms = ['TEMP', 'PSAL']
cl.nps34_startDatetime = datetime.datetime(*startdate[:])
cl.nps34_endDatetime = datetime.datetime(*enddate[:])

# NPS29
cl.nps29_base = 'http://www.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.nps29_files = [ 'OS_Glider_NPS_G29_20130829_TS.nc']
cl.nps29_parms = ['TEMP', 'PSAL', 'FLU2']
cl.nps29_startDatetime = datetime.datetime(*startdate[:])
cl.nps29_endDatetime = datetime.datetime(*enddate[:])

# nemesis ctd
cl.nemesis_ctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/Slocum_Teledyne/'
cl.nemesis_ctd_files = [ 'nemesis_ctd.nc']
cl.nemesis_ctd_parms = ['TEMP', 'PSAL' ]
cl.nemesis_ctd_startDatetime = datetime.datetime(*startdate[:])
cl.nemesis_ctd_endDatetime = datetime.datetime(*enddate[:])

# nemesis met 
cl.nemesis_met_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/Slocum_Teledyne/'
cl.nemesis_met_files = [ 'nemesis_met.nc']
cl.nemesis_met_parms = ['TEMP', 'PSAL' ]
cl.nemesis_met_startDatetime = datetime.datetime(*startdate[:])
cl.nemesis_met_endDatetime = datetime.datetime(*enddate[:])

# ucsc294 met 
cl.ucsc294_met_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/Slocum_UCSC_2/'
cl.ucsc294_met_files = [ 'ucsc294_met.nc']
cl.ucsc294_met_parms = ['TEMP', 'PSAL' ]
cl.ucsc294_met_startDatetime = datetime.datetime(*startdate[:])
cl.ucsc294_met_endDatetime = datetime.datetime(*enddate[:])

# ucsc294 ctd 
cl.ucsc294_ctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/Slocum_UCSC_2/'
cl.ucsc294_ctd_files = [ 'ucsc294_ctd.nc']
cl.ucsc294_ctd_parms = ['TEMP', 'PSAL' ,'oxygen','chla','backscatter']
cl.ucsc294_ctd_startDatetime = datetime.datetime(*startdate[:])
cl.ucsc294_ctd_endDatetime = datetime.datetime(*enddate[:])

# Liquid Robotics Waveglider
cl.waveglider_base = cl.dodsBase + 'CANON_september2013/waveglider/'
cl.waveglider_files = [ 'waveglider_gpctd_WG.nc' ]
cl.waveglider_parms = [ 'TEMP', 'PSAL', 'oxygen' ]
cl.waveglider_startDatetime = datetime.datetime(*startdate[:])
cl.waveglider_endDatetime = datetime.datetime(*enddate[:])

 
#######################################################################################
# DRIFTERS
#######################################################################################

# Stella 203
cl.stella203_base = cl.dodsBase + 'CANON_september2013/Platforms/Drifters/Stella_1/'
cl.stella203_parms = [ 'TEMP', 'pH' ]
cl.stella203_files = [ 
                        'stella203_data.nc',
                      ]

# Stella 204
cl.stella204_base = cl.dodsBase + 'CANON_september2013/Platforms/Drifters/Stella_1/'
cl.stella204_parms = [ 'TEMP', 'pH' ]
cl.stella204_files = [ 
                        'stella204_data.nc',
                      ]


###################################################################################################################
# Execute the load
cl.process_command_line()

if cl.args.test:
#    cl.loadStella203(stride=1)
#    cl.loadStella204(stride=1)
#    cl.load_ucsc294_ctd(stride=1) 
    cl.load_NPS29(stride=1) 
    cl.load_NPS34(stride=1) 
#    cl.load_nemesis_met(stride=1) 
#    cl.load_ucsc294_met(stride=1) 
#    cl.load_nemesis_ctd(stride=1) 
    cl.loadL_662(stride=1) # done

elif cl.args.optimal_stride:
    cl.loadL_662(stride=1) # done
    cl.load_NPS29(stride=1) 
    cl.load_NPS34(stride=1) 
#    cl.load_nemesis_ctd(stride=1) 
#    cl.load_ucsc294_ctd(stride=1) 
#    cl.load_nemesis_met(stride=1) 
#    cl.load_ucsc294_met(stride=1) 
#    cl.loadStella203(stride=1)
#    cl.loadStella204(stride=1)

else:
    cl.loadL_662(stride=1) # done
    cl.load_NPS29(stride=1) 
    cl.load_NPS34(stride=1) 
#    cl.load_nemesis_ctd(stride=1) 
#    cl.load_ucsc294_ctd(stride=1) 
#    cl.load_nemesis_met(stride=1) 
#    cl.load_ucsc294_met(stride=1) 
#    cl.loadStella203(stride=1)
#    cl.loadStella204(stride=1)

