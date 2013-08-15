#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for all CANON activities in September 2011

Mike McCann and Duane Edgington
MBARI 15 August 2013

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime  # needed for glider data
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)

# the next line makes it possible to find CANON
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # settings.py is one dir up

from CANON import CANONLoader

# Assign input data sources
cl = CANONLoader('stoqs_september2011', 'CANON - September 2011')
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2011/netcdf/'
cl.dorado_files = [ 'Dorado389_2011_249_00_249_00_decim.nc',
                    
                  ]

# Spray glider - for just the duration of the campaign
cl.l_662_base = 'http://www.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_files = ['OS_Glider_L_662_20110915_TS.nc']
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = datetime.datetime(2011, 9, 15)
cl.l_662_endDatetime = datetime.datetime(2012, 1, 04)



# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadDorado(stride=100)

elif cl.args.optimal_stride:
    cl.loadDorado(stride=2)

else:
    cl.loadDorado(stride=cl.args.stride)

