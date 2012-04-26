#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for all CANON activities

Mike McCann
MBARI 22 April 2012

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

try:
    stride = int(sys.argv[1])
except IndexError:
    stride = 100

# ----------------------------------------------------------------------------------
cl = CANONLoader('stoqs_september2010', 'ESP Drifter Tracking - September 2010')
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
cl.dorado_files = [ 'Dorado389_2010_257_01_258_04_decim.nc',
                    'Dorado389_2010_258_05_258_08_decim.nc',
                    'Dorado389_2010_259_00_259_03_decim.nc',
                    'Dorado389_2010_260_00_260_00_decim.nc',
                    'Dorado389_2010_261_00_261_00_decim.nc'
                  ]
cl.stride = stride
cl.loadAll()

