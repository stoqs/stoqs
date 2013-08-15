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
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # settings.py is one dir up

from CANON import CANONLoader

# Assign input data sources
cl = CANONLoader('stoqs_september2011', 'CANON - September 2011')
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2011/netcdf/'
cl.dorado_files = [ 'Dorado389_2011_249_00_249_00_decim.nc',
                    
                  ]

# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadDorado(stride=100)

elif cl.args.optimal_stride:
    cl.loadDorado(stride=2)

else:
    cl.loadDorado(stride=cl.args.stride)

