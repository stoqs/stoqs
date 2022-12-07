#!/usr/bin/env python
'''
MBARI ESP Team
Loader for Lake Erie Brizo and Makai 2021 deployments

Brizo Lake Erie: 20210805_20210816.dlist
Makai Lake Erie: 20210804_20210808.dlist

Mike McCann, Duane Edgington, Danelle Cline
MBARI 1 September 2021
'''

import os
import sys

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
from datetime import datetime
import timing

cl = CANONLoader('stoqs_greatlakes2022', 'Great Lakes LRAUV ESP - August 2022',
                    description='Lake Michigan and Superior Triton and Brizo ESP Deployments in 2022',
                    x3dTerrains = {
                                    'https://stoqs.mbari.org/x3d/Globe_1m_bath_10x/Globe_1m_bath_10x_scene.x3d': {
                                      'position': '14051448.48336 -15407886.51486 6184041.22775',
                                      'orientation': '0.83940 0.33030 0.43164 1.44880',
                                      'centerOfRotation': '0 0 0',
                                      'VerticalExaggeration': '10',
                                    },
                                    'https://stoqs.mbari.org/x3d/michigan_lld_10x/michigan_lld_10x_src_scene.x3d': {
                                      'position': '260508.70011 -4920934.73726 4257472.30926',
                                      'orientation': '1.00000 0.00113 -0.00025 1.66609',
                                      'centerOfRotation': '239815.39152 -4691345.97184 4297950.38875',
                                      'VerticalExaggeration': '10',
                                      'speed': '0.1',
                                    },
                                    # TODO: Add glb model for Lake Superior
                    },
                    grdTerrain = os.path.join(parentDir, 'michigan_lld.grd')
                 )

brizo_sdate = datetime(2022, 8, 4)
brizo_edate = datetime(2022, 8, 30)
triton_sdate = datetime(2022, 8, 4)
triton_edate = datetime(2022, 8, 30)

cl.process_command_line()

if cl.args.test:
    cl.stride = 100
    cl.loadLRAUV('brizo', brizo_sdate, brizo_edate, critSimpleDepthTime=0.1, build_attrs=True)
    cl.loadLRAUV('triton', triton_sdate, triton_edate, critSimpleDepthTime=0.1, build_attrs=True)
elif cl.args.stride:
    cl.stride = cl.args.stride
    # Post recovery missionlogs load
    cl.loadLRAUV('brizo', brizo_sdate, brizo_edate, critSimpleDepthTime=0.1)
    cl.loadLRAUV('triton', triton_sdate, triton_edate, critSimpleDepthTime=0.1)

##cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

