#!/usr/bin/env python
'''
MBARI Biological Oceanography Group
Master loader for Monterey Bay Time Series data

Mike McCann, Duane Edgington, Danelle Cline
MBARI 8 April 2019
'''

import os
import sys

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
from datetime import datetime
import timing

cl = CANONLoader('stoqs_mbts', 'BOG - Monterey Bay Time Series',
                 description='MBARI Biological Oceanography Group Monterey Bay Time Series data',
                 x3dTerrains={
                   'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                     'position': '-2822317.31255 -4438600.53640 3786150.85474',
                     'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                     'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                     'VerticalExaggeration': '10',
                   },
                   'https://stoqs.mbari.org/x3d/Monterey25_1x/Monterey25_1x_src_scene.x3d': {
                     'name': 'Monterey25_1x',
                     'position': '-2822317.31255 -4438600.53640 3786150.85474',
                     'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                     'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                     'VerticalExaggeration': '1',
                   },
                 },
                 grdTerrain=os.path.join(parentDir, 'Monterey25.grd')
                 )

# Will likely need to adjust eyear as time goes on
syear = datetime(2015, 1, 1)
eyear = datetime(2019, 12, 31)

# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.stride = 10000
elif cl.args.stride:
    cl.stride = cl.args.stride

for lrauv in ('tethys', 'daphne'):
    cl.loadLRAUV(lrauv, syear, eyear, dlist_str='MBTS', err_on_missing_file=True)

cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

