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

try:
    dbAlias = sys.argv[2]
except IndexError:
    dbAlias = 'stoqs_april2011'

# ----------------------------------------------------------------------------------
campaignName = 'CANON - April 2011'
if stride != 1:
    campaignName = campaignName + ' with stride=%d' % stride

cl = CANONLoader(dbAlias, campaignName)
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2011/netcdf/'
cl.dorado_files = [ 'Dorado389_2011_110_12_110_12_decim.nc',
                    'Dorado389_2011_111_00_111_00_decim.nc',
                    'Dorado389_2011_115_10_115_10_decim.nc',
                    'Dorado389_2011_116_00_116_00_decim.nc',
                    'Dorado389_2011_117_01_117_01_decim.nc',
                    'Dorado389_2011_118_00_118_00_decim.nc'
                  ]
cl.tethys_base = 'http://elvis.shore.mbari.org:8080/thredds/dodsC/lrauv/tethys/2011/'
cl.tethys_files = [ '20110415_20110418/20110415T163108/slate.nc',
                    '20110415_20110418/20110416T074851/slate.nc',
                    '20110415_20110418/20110417T064753/slate.nc',
                    '20110415_20110418/20110418T060227/slate.nc',
                    '20110415_20110418/20110418T192351/slate.nc',
                    '20110421_20110424/20110421T170430/slate.nc',
                    '20110421_20110424/20110422T001932/slate.nc',
                    '20110421_20110424/20110423T223119/slate.nc',
                    '20110421_20110424/20110424T214938/slate.nc',
                    '20110426_20110502/20110426T171129/slate.nc',
                    '20110426_20110502/20110427T191236/slate.nc',
                    '20110426_20110502/20110429T222225/slate.nc',
                    '20110426_20110502/20110430T132028/slate.nc',
                    '20110426_20110502/20110502T040031/slate.nc'
                  ]
cl.tethys_parms = [ 'sea_water_temperature', 'sea_water_salinity', 'sea_water_density', 'volume_scattering_470_nm', 'volume_scattering_650_nm',
                    'volume_scattering_650_nm', 'mass_concentration_of_oxygen_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water',
                    'mass_concentration_of_chlorophyll_in_sea_water']
cl.stride = stride
cl.loadAll()

