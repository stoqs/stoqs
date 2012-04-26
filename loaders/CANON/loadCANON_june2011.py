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
cl = CANONLoader('stoqs_june2011', 'CANON - June 2011')
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2011/netcdf/'
cl.dorado_files = [ 'Dorado389_2011_164_05_164_05_decim.nc',
                    'Dorado389_2011_165_00_165_00_decim.nc',
                    'Dorado389_2011_166_00_166_00_decim.nc',
                    'Dorado389_2011_171_01_171_01_decim.nc',
                  ]
cl.tethys_base = 'http://elvis.shore.mbari.org:8080/thredds/dodsC/lrauv/tethys/2011/'
cl.tethys_files = [ '20110610_20110616/20110610T212639/slate.nc',
                    '20110610_20110616/20110611T232740/slate.nc',
                    '20110610_20110616/20110612T191007/slate.nc',
                    '20110610_20110616/20110613T001706/slate.nc',
                    '20110610_20110616/20110613T053217/slate.nc',
                    '20110610_20110616/20110614T093150/slate.nc',
                    '20110610_20110616/20110614T201835/slate.nc',
                    '20110610_20110616/20110615T030544/slate.nc',
                    '20110610_20110616/20110616T000907/slate.nc',
                    '20110618_20110623/20110618T211745/slate.nc',
                    '20110618_20110623/20110619T231706/slate.nc',
                    '20110618_20110623/20110620T143623/slate.nc',
                    '20110618_20110623/20110620T190006/slate.nc',
                    '20110618_20110623/20110621T185433/slate.nc'
                  ]
cl.tethys_parms = [ 'sea_water_temperature', 'sea_water_salinity', 'sea_water_density', 'volume_scattering_470_nm', 'volume_scattering_650_nm',
                    'volume_scattering_650_nm', 'mass_concentration_of_oxygen_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water',
                    'mass_concentration_of_chlorophyll_in_sea_water']
cl.stride = stride
cl.loadAll()


