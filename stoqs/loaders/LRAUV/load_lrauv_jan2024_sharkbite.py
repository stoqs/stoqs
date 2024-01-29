#!/usr/bin/env python

import os
import sys

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from argparse import ArgumentParser
from CANON import CANONLoader
from datetime import datetime
from stoqs.models import Activity
import timing
import traceback

cl = CANONLoader('stoqs_lrauv_jan2024_sharkbite', 'LRAUV - 10 Hz shark bite data - January 2024',
                 description='MBARI Long Range Autonomous Vehicle i10 Hz shark bite data during January 2024',
                 x3dTerrains={
                   'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                     'position': '-2822317.31255 -4438600.53640 3786150.85474',
                     'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                     'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                     'VerticalExaggeration': '10',
                   },
                   'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_e10_lat_rev.glb': {
                     'name': 'Monterey25_e10',
                     'position': '-2709340.15630 3838759.47032 -4315928.63232',
                     'orientation': '-0.92531 0.16085 0.34340 1.48161',
                     'centerOfRotation': '-2698376.20956 3816324.15548 -4328209.99402',
                     'zNear': '10000.0',
                     'zFar': '30000000.0',
                     'VerticalExaggeration': '10',
                   },
                 },
                 grdTerrain=os.path.join(parentDir, 'Monterey25.grd')
                 )

cl.process_command_line()

sdate = datetime(2024, 1, 20)
edate = datetime(2024, 1, 31)

# Add to stoqs/mbari_lrauv_campaigns.py:
#   ('stoqs_lrauv_jan2024_sharkbite', 'LRAUV/load_lrauv_jan2024_sharkbite.py'),

# Load 10 Hz orientation data from the shark bite at 2041 21 Jan 2024, see:
# Slack thread: https://mbari.slack.com/archives/C4VJ11Q83/p1706201788496489
cl.pontus_base = 'http://dods.mbari.org/opendap/data/lrauv/pontus/missionlogs/2024/20240117_20240122/20240121T161500/'
cl.pontus_files = ['202401211615_202401212128_100ms_scieng.nc']
cl.pontus_parms = [ 'yaw', 'pitch', 'roll',
                    'volumescatcoeff117deg470nm', 'volumescatcoeff117deg650nm',
                    'control_inputs_mass_position', 'control_inputs_buoyancy_position', 'control_inputs_propeller_rotation_rate',
                  ]
cl.loadLRAUV('pontus', sdate, edate, build_attrs=False)
cl.addTerrainResources()

print("All Done loading stoqs_lrauv_jan2024_sharkbite.")

