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
#  Western Flyer: September 20-27? (259-262) Sep 30 - Oct 3
######################################################################
# UCTD
cl.wfuctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Ships/Western_Flyer/uctd/'
cl.wfuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.wfuctd_files = [ 
                    #    'canon13m01.nc', 'canon13m02.nc', 
                    #    'canon13m03.nc', 'canon13m04.nc',
                    #    'canon13m05.nc', 'canon13m06.nc',
                    #    'canon13m07.nc', 
                    #    'canon13m08.nc', 'canon13m09.nc',
                    #    'canon13m10.nc', 'canon13m11.nc',     # loaded 10/1/13
                      ]

# PCTD
cl.pctdDir = 'CANON_september2013/Platforms/Ships/Western_Flyer/pctd/'
cl.wfpctd_base = cl.dodsBase + cl.pctdDir
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.wfpctd_files = [ 
                   'canon13c01.nc', 'canon13c02.nc', 'canon13c03.nc', 'canon13c04.nc', 
                   'canon13c05.nc', 'canon13c06.nc', 'canon13c07.nc', 'canon13c08.nc', 
                   'canon13c09.nc', 'canon13c10.nc', 'canon13c11.nc', 'canon13c12.nc',
                   'canon13c13.nc', 'canon13c14.nc', 'canon13c15.nc', 
                   'canon13c16.nc', 'canon13c17.nc',                                      #added Sept 25
                   'canon13c18.nc',                                                     #this file had a bad date in it (12-31-12)
                   'canon13c19.nc',                                                       #added Sept 26 2013 
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
   cl.loadWFuctd(stride=1)
   cl.loadWFpctd(stride=1)

elif cl.args.optimal_stride:
   # cl.loadWFpctd(stride=1)
   cl.loadWFuctd(stride=1)
   #cl.loadMartin(stride=1)
#    cl.loadRCuctd(stride=1)
#    cl.loadRCpctd(stride=1)

else:
   cl.loadWFpctd(stride=1)
   #  cl.loadWFuctd(stride=1)
#    cl.loadRCuctd(stride=1)
#    cl.loadRCpctd(stride=1)
