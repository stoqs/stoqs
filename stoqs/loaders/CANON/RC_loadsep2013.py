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


######################################################################
#  RACHEL CARSON: September 16-20? (259-262) Sep 30 - Oct 3
######################################################################
# UCTD
cl.rcuctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Ships/Rachel_Carson/uctd/'
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.rcuctd_files = [ 
                      #  '25913RCm01.nc', '26013RCm01.nc',
                      #  '26113RCm01.nc',
                      #  '27313RCm01.nc', 
                      # '27413RCm01.nc',
                      # '27513RCm01.nc',
                       ]

# PCTD
cl.pctdDir = 'CANON_september2013/Platforms/Ships/Rachel_Carson/pctd/'
cl.rcpctd_base = cl.dodsBase + cl.pctdDir
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.rcpctd_files = [ 
                    '25913RCc01.nc', '25913RCc02.nc', '25913RCc03.nc', '26013RCc01.nc',
                    '26113RCc01.nc',
                    '27313RCc01.nc', '27313RCc02.nc', '27313RCc03.nc',
                    '27413RCc01.nc', '27413RCc02.nc', '27413RCc03.nc',
                    '27513RCc01.nc', '27513RCc02.nc',  
                    '27613RCc01.nc', '27613RCc02.nc', '27613RCc03.nc', '27613RCc04.nc', '27613RCc05.nc',
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
   # cl.loadRCuctd(stride=1)
    cl.loadRCpctd(stride=1)

elif cl.args.optimal_stride:
    cl.loadRCuctd(stride=1)
    cl.loadRCpctd(stride=1)

else:
    cl.loadRCuctd(stride=1)
    cl.loadRCpctd(stride=1)
