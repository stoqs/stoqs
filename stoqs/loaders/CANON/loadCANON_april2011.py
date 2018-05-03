#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''
Master loader for all CANON activities in April 2011

Mike McCann
MBARI 22 April 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader

# Assign input data sources
cl = CANONLoader('stoqs_april2011', 'CANON - April 2011',
                    description = 'Dorado and Tethys surveys in Monterey Bay',
                    x3dTerrains = {
                        'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                            'position': '-2822317.31255 -4438600.53640 3786150.85474',
                            'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                            'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                            'VerticalExaggeration': '10',
                            'speed': '.1',
                        }
                    },
                    grdTerrain = os.path.join(parentDir, 'Monterey25.grd')
                  )

cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2011/netcdf/'
cl.dorado_files = [ 'Dorado389_2011_110_12_110_12_decim.nc',
                    'Dorado389_2011_111_00_111_00_decim.nc',
                    'Dorado389_2011_115_10_115_10_decim.nc',
                    'Dorado389_2011_116_00_116_00_decim.nc',
                    'Dorado389_2011_117_01_117_01_decim.nc',
                    'Dorado389_2011_118_00_118_00_decim.nc'
                  ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700', 
                    'fl700_uncorr', 'salinity', 'biolume', 
                    'sepCountList', 'mepCountList']

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

# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadDorado(stride=100)
    cl.loadTethys(stride=1000)

elif cl.args.optimal_stride:
    cl.loadDorado(stride=2)
    cl.loadTethys(stride=20)

else:
    cl.loadDorado(stride=cl.args.stride)
    cl.loadTethys(stride=cl.args.stride)
   
# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")
 

