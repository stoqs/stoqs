#!/usr/bin/env python
'''
Loader for Midwater i2MAP missions
'''

import os
import sys
from datetime import datetime

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)

from CANON import CANONLoader
import timing

# Captured from https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_e10.html
# INFO: 
# <Viewpoint position="-2709340.15630 3838759.47032 -4315928.63232" orientation="-0.92531 0.16085 0.34340 1.48161" 
#  zNear="11.03910" zFar="110390.98923" centerOfRotation="-2698376.20956 3816324.15548 -4328209.99402" fieldOfView="0.78540" description=""></Viewpoint>

cl = CANONLoader('stoqs_all_i2map', 'Midwater All i2MAP Missions',
                 description='All i2MAP Missions done at Midwater Site',
                 x3dTerrains={
                   'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                     'name': 'Monterey25_10x',
                     'position': '-2822317.31255 -4438600.53640 3786150.85474',
                     'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                     'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                     'zNear': '10000.0',
                     'zFar': '30000000.0',
                     'VerticalExaggeration': '10',
                   },
                   'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_e10.glb': {
                     'name': 'Monterey25_e10',
                     'position': '-2709340.15630 3838759.47032 -4315928.63232',
                     'orientation': '-0.92531 0.16085 0.34340 1.48161',
                     'centerOfRotation': '-2698376.20956 3816324.15548 -4328209.99402',
                     'zNear': '10000.0',
                     'zFar': '30000000.0',
                     'VerticalExaggeration': '10',
                   },
                   'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_e10_lat_rev.glb': {
                     'name': 'Monterey25_e10_lat_rev',
                     'position': '-2709340.15630 3838759.47032 -4315928.63232',
                     'orientation': '-0.92531 0.16085 0.34340 1.48161',
                     'centerOfRotation': '-2698376.20956 3816324.15548 -4328209.99402',
                     'zNear': '10000.0',
                     'zFar': '30000000.0',
                     'VerticalExaggeration': '10',
                   },
                   'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_e10_sphere.glb': {
                     'name': 'Monterey25_e10_sphere',
                     'position': '-2709340.15630 3838759.47032 -4315928.63232',
                     'orientation': '-0.92531 0.16085 0.34340 1.48161',
                     'centerOfRotation': '-2698376.20956 3816324.15548 -4328209.99402',
                     'zNear': '10000.0',
                     'zFar': '30000000.0',
                     'VerticalExaggeration': '10',
                   },
                   'https://stoqs.mbari.org/x3d/Globe_1m_bath_10x/Globe_1m_bath_10x_scene.x3d': {
                     'position': '14051448.48336 -15407886.51486 6184041.22775',
                     'orientation': '0.83940 0.33030 0.43164 1.44880',
                     'centerOfRotation': '0 0 0',
                     'zNear': '10000.0',
                     'zFar': '30000000.0',
                     'VerticalExaggeration': '10',
                   },
                 },
                 grdTerrain=os.path.join(parentDir, 'Monterey25.grd')
                 )

# Default is entrire i2map time range
startdate = datetime(2017, 1, 1)
enddate = datetime.utcnow()

# Execute the load
cl.process_command_line()
cl.stride = 10

if cl.args.test:
    cl.stride = 10
elif cl.args.stride:
    cl.stride = cl.args.stride

# Override default time range with command line settings
# (The --previous_month or --current_month argument will set startdate & startdate)
if cl.args.startdate:
    startdate = datetime.strptime(cl.args.startdate, '%Y%m%d')
if cl.args.enddate:
    enddate = datetime.strptime(cl.args.enddate, '%Y%m%d')

#cl.load_i2MAP(datetime(2022, 3, 1), datetime(2022, 4, 1), build_attrs=True)
cl.load_i2MAP(startdate, enddate, build_attrs=True)

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")
