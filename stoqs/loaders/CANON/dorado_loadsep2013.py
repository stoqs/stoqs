#!/usr/bin/env python
__author__    = 'Mike McCann,Duane Edgington,Reiko Michisaki'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'duane at mbari.org'

__doc__ = '''

Dorado loader for all CANON activities in September 2013

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


# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'

#####################################################################
#  DORADO 
#####################################################################
# special location for dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2013/netcdf/'
cl.dorado_files = [# 'Dorado389_2013_259_00_259_00_decim.nc',     #Sep 16 Loaded
                   # 'Dorado389_2013_261_01_261_01_decim.nc',
                   # 'Dorado389_2013_262_00_262_00_decim.nc',     #Sep 19 Dorado389_2013_262_00_262_00 
                   # 'Dorado389_2013_262_01_262_01_decim.nc', 
                   # 'Dorado389_2013_268_00_268_00_decim.nc',
                   # 'Dorado389_2013_273_00_273_00_decim.nc',     #Sep 30
                   # 'Dorado389_2013_274_00_274_00_decim.nc',
                   # 'Dorado389_2013_274_01_274_01_decim.nc',
                   # 'Dorado389_2013_275_00_275_00_decim.nc',
                   # 'Dorado389_2013_275_01_275_01_decim.nc',
                   'Dorado389_2013_276_00_276_00_decim.nc',
                    ]



###################################################################################################################
# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadDorado(stride=1)

elif cl.args.optimal_stride:
    cl.loadDorado(stride=2)

else:
    cl.loadDorado(stride=cl.args.stride)
