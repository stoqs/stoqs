#!/usr/bin/env python
'''
Load all Dorado data for the PlanktonProxies Project

Mike McCann
MBARI 9 August 2018
'''

import os
import sys
import datetime

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
import timing

cl = CANONLoader('stoqs_all_dorado', 'Plankton Proxies - All Dorado Data',
                 description='All Dorado survey data from 2003 through 2019 and beyond',
                 x3dTerrains={
                   'https://dods.mbari.org/terrain/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
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

startdate = datetime.datetime(2003, 1, 1)
enddate = datetime.datetime(2019, 12, 31)

# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.stride = 1
    startdate = datetime.datetime(2003, 12, 5)
    enddate = datetime.datetime(2003, 12, 7)
    cl.loadDorado(startdate, enddate, build_attrs=True, plankton_proxies=True)
elif cl.args.stride:
    cl.stride = cl.args.stride
    cl.loadDorado(startdate, enddate, build_attrs=True)

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

