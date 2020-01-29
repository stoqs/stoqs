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
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE']='config.settings.local'
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

#25613JMC01.nc                                                                              100% 3172     3.1KB/s   00:00
#25613JMC02.nc                                                                              100% 6268     6.1KB/s   00:00
#25613JMC03.nc                                                                              100% 5692     5.6KB/s   00:00
#25613JMC04.nc                                                                              100% 6340     6.2KB/s   00:00
#25613JMC05.nc                                                                              100% 4468     4.4KB/s   00:00
#26013JMC01.nc                                                                              100% 6484     6.3KB/s   00:00
#26013JMC02.nc                                                                              100% 3460     3.4KB/s   00:00
#26013JMC03.nc                                                                              100% 6484     6.3KB/s   00:00
#26013JMC04.nc                                                                              100% 5692     5.6KB/s   00:00
#uctd/25413JMm01.txt
#uctd/25613JMm01.txt

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'


######################################################################
#  John Martin: September 16-20? (259-262) Sep 30 - Oct 3
######################################################################
# UCTD
cl.JMuctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Ships/Martin/uctd/'
cl.JMuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.JMuctd_files = [ 
                        '25913RCm01.nc', '26013RCm01.nc', 
                      ]

# PCTD
cl.pctdDir = 'CANON_september2013/Platforms/Ships/Martin/pctd/'
cl.JMpctd_base = cl.dodsBase + cl.pctdDir
cl.JMpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.JMpctd_files = [ 
                    '25613JMC01.nc', '25613JMC02.nc', '25613JMC03.nc', '25613JMC04.nc', '25613JMC05.nc',
                    '26013JMC01.nc', '26013JMC02.nc', '26013JMC03.nc','26013JMC04.nc', 
                      ]
# BCTD
# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/GOC12/ copied to local BOG_Data dir
#cl.bctdDir = 'CANON_september2013/Platforms/Ships/Rachel_Carson/bctd/'
#cl.subsample_csv_base = cl.dodsBase + cl.bctdDir
#cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data')
#cl.subsample_csv_files = [
#                            'STOQS_canon13_CHL_1U.csv', 'STOQS_canon13_CHL_5U.csv', 'STOQS_canon13_NH4.csv', 'STOQS_canon13_NO2.csv', 'STOQS_canon13_NO3.csv', 
#			    'STOQS_canon13_OXY_ML.csv', 'STOQS_canon13_PHAEO_1U.csv', 'STOQS_canon13_PHAEO_5U.csv',
#                            'STOQS_canon13_PHAEO_GFF.csv', 'STOQS_canon13_PO4.csv', 'STOQS_canon13_SIO4.csv', 'STOQS_canon13_CARBON_GFF.csv',
#                            'STOQS_canon13_CHL_GFF.csv',
#                         ]


###################################################################################################################
# Execute the load
cl.process_command_line()

if cl.args.test:
#    cl.loadJMuctd(stride=1)
    cl.loadJMpctd(stride=1)

elif cl.args.optimal_stride:
   #cl.loadMartin(stride=1)
#    cl.loadJMuctd(stride=1)
    cl.loadJMpctd(stride=1)

else:
#    cl.loadDorado(stride=cl.args.stride)
#    cl.loadJMuctd(stride=1)
    cl.loadJMpctd(stride=1)
