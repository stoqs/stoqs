#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for all CANON activities in September 2010

Mike McCann
MBARI 22 April 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))      # So that CANON is found

from CANON import CANONLoader

# Assign input data sources
cl = CANONLoader('stoqs_september2010', 'CANON - September 2010')
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
cl.dorado_files = [ 'Dorado389_2010_257_01_258_04_decim.nc',
                    'Dorado389_2010_258_05_258_08_decim.nc',
                    'Dorado389_2010_259_00_259_03_decim.nc',
                    'Dorado389_2010_260_00_260_00_decim.nc',
                    'Dorado389_2010_261_00_261_00_decim.nc'
                  ]

# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadDorado(stride=100)

elif cl.args.optimal_stride:
    cl.loadDorado(stride=2)

else:
    cl.loadDorado(stride=cl.args.stride)

