#!/usr/bin/env python
'''
Master loader for EcoHAB May 2022 Campaign in Santa Barbara Channel
'''

import os
import sys
from datetime import datetime

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)

from CANON import CANONLoader
import timing

cl = CANONLoader('stoqs_ecohab_may2022', 'ECOHAB - May 2022',
                 description='May-June 2022 EcoHAB LRAUV-ESP Campaign in Santa Barbara Channel',
                 x3dTerrains={
                     'https://stoqs.mbari.org/x3d/Globe_1m_bath_10x/Globe_1m_bath_10x_scene.x3d': {
                     'position': '14051448.48336 -15407886.51486 6184041.22775',
                     'orientation': '0.83940 0.33030 0.43164 1.44880',
                     'centerOfRotation': '0 0 0',
                     'VerticalExaggeration': '10',
                   },
                 },
                 grdTerrain=os.path.join(parentDir, 'Monterey25.grd')
                 )


# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.stride = 10
elif cl.args.stride:
    cl.stride = cl.args.stride

lrauv_start = datetime(2022, 5, 16)
lrauv_end = datetime(2022, 6, 15)
cl.loadLRAUV('brizo', lrauv_start, lrauv_end)
cl.loadLRAUV('makai', lrauv_start, lrauv_end)

##cl.loadSubSamples() 

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")
