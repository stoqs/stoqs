#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for all May 2012 CANON activities

Mike McCann
MBARI 22 May 2012

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
try:
    dbAlias = sys.argv[2]
except IndexError:
    dbAlias = 'stoqs_may2012'


# ----------------------------------------------------------------------------------
cl = CANONLoader(dbAlias, 'CANON - May 2011')
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2012/netcdf/'
cl.dorado_files = [ 
                    'Dorado389_2012_142_01_142_01_decim.nc',
                    'Dorado389_2012_142_02_142_02_decim.nc',
                    'Dorado389_2012_143_07_143_07_decim.nc',
                    'Dorado389_2012_143_08_143_08_decim.nc',
                  ]

cl.tethys_base = 'http://elvis.shore.mbari.org:8080/thredds/dodsC/lrauv/tethys/2012/'
cl.tethys_files = [ 
                  ]
cl.tethys_parms = [ 'sea_water_temperature', 'sea_water_salinity', 'sea_water_density', 'volume_scattering_470_nm', 'volume_scattering_650_nm',
                    'volume_scattering_650_nm', 'mass_concentration_of_oxygen_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water',
                    'mass_concentration_of_chlorophyll_in_sea_water']

cl.martin_parms = []

cl.stride = stride
cl.loadAll()


