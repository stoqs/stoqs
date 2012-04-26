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

# ----------------------------------------------------------------------------------
cl = CANONLoader('stoqs_october2010', 'CANON/Biospace/Latmix - October 2010')
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
cl.dorado_files = [ 'Dorado389_2010_277_01_277_01_decim.nc',
                    'Dorado389_2010_278_01_278_01_decim.nc',
                    'Dorado389_2010_279_02_279_02_decim.nc',
                    'Dorado389_2010_280_01_280_01_decim.nc',
                    'Dorado389_2010_284_00_284_00_decim.nc',
                    'Dorado389_2010_285_00_285_00_decim.nc',
                    'Dorado389_2010_286_01_286_02_decim.nc',
                    'Dorado389_2010_287_00_287_00_decim.nc',
                    'Dorado389_2010_291_00_291_00_decim.nc',
                    'Dorado389_2010_292_01_292_01_decim.nc',
                    'Dorado389_2010_293_00_293_00_decim.nc',
                    'Dorado389_2010_294_01_294_01_decim.nc',
                    'Dorado389_2010_298_01_298_01_decim.nc',
                    'Dorado389_2010_299_00_299_00_decim.nc',
                    'Dorado389_2010_300_00_300_00_decim.nc',
                    'Dorado389_2010_301_00_301_00_decim.nc',
                  ]
cl.tethys_base = 'http://dods.mbari.org/opendap/data/auvctd/tethys/2010/netcdf/'
cl.tethys_files = [ '20101018T143308_Chl_.nc',
                    '20101019T001815_Chl_.nc',
                    '20101019T155117_Chl_.nc',
                    '20101020T113957_Chl_.nc',
                  ]
cl.martin_base = 'http://odss.mbari.org/thredds/dodsC/jhm_underway'
cl.martin_files = [ '27710_jhmudas_v1.nc',
                    '27810_jhmudas_v1.nc',
                    '27910_jhmudas_v1.nc',
                    '28010_jhmudas_v1.nc',
                    '28110_jhmudas_v1.nc',
                    '28410_jhmudas_v1.nc',
                    '28510_jhmudas_v1.nc',
                    '28610_jhmudas_v1.nc',
                    '28710_jhmudas_v1.nc',
                    '29010_jhmudas_v1.nc',
                    '29110_jhmudas_v1.nc',
                    '29210_jhmudas_v1.nc',
                    '29310_jhmudas_v1.nc',
                    '29410_jhmudas_v1.nc',
                    '29810_jhmudas_v1.nc',
                    '29910_jhmudas_v1.nc',
                    '30010_jhmudas_v1.nc',
                    '30110_jhmudas_v1.nc',
                  ]
cl.martin_parms = [ 'conductivity', 'temperature', 'salinity', 'fluorescence', 'turbidity']
cl.stride = stride
cl.loadAll()

# ----------------------------------------------------------------------------------
cl = CANONLoader('stoqs_april2011', 'CANON - April 2011')
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


