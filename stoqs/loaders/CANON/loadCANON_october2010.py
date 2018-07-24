#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for all CANON activities in October 2010

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
import timing

cl = CANONLoader('stoqs_october2010', 'CANON - October 2010',
                    description = 'Bloomex observing campaign in Monterey Bay',
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

# Dorado data - 2 second gridded 
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
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                    'fl700_uncorr', 'salinity', 'biolume',
                    'sepCountList', 'mepCountList',
                    'roll', 'pitch', 'yaw',
                  ]
# These are full resolution (_d_) data files with Chl only from the first Tethys data used for CANON
# Offical long-term archive location is: http://dods.mbari.org/opendap/data/lrauv/tethys/missionlogs/2010/
cl.tethys_base = 'http://dods.mbari.org/opendap/data/auvctd/tethys/2010/netcdf/'
cl.tethys_files = [ '20101018T143308_Chl_.nc',
                    '20101019T001815_Chl_.nc',
                    '20101019T155117_Chl_.nc',
                    '20101020T113957_Chl_.nc',
                  ]
cl.tethys_parms = ['mass_concentration_of_chlorophyll_in_sea_water']

# Realtime shore.nc files - not a DODS server...
cl.tethys_r_base = 'http://aosn.mbari.org/sbdlogs/tethys/2010/201010/'
cl.tethys_r_files = [ '20101018T143308/shore.nc',
                    '20101019T001815/shore.nc',
                    '20101019T155117/shore.nv',
                    '20101020T113957/shore.nc',
                  ]
cl.tethys_r_parms = ['mass_concentration_of_chlorophyll_in_sea_water']
cl.tethys_aux_coords = {}
for v in cl.tethys_r_parms:
    cl.tethys_aux_coords[v] = {'time': 'Time', 'latitude': 'latitude', 'longitude': 'longitude', 'depth': 'depth'}

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


# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadDorado(stride=50)
    cl.loadTethys(stride=1000)
    cl.loadMartin(stride=1000)

elif cl.args.optimal_stride:
    cl.loadDorado(stride=2)
    cl.loadTethys(stride=2)
    cl.loadMartin(stride=1)

else:
    cl.stride = cl.args.stride
    cl.loadDorado()
    cl.loadTethys()
    cl.loadMartin()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

