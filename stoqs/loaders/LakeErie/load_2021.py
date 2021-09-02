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

cl = CANONLoader('stoqs_erie2021', 'Lake Erie ESP 2021',
                    description='Lake Erie Brizo and Makai ESP Deployments in 2021',
                    x3dTerrains = {
                                    'https://stoqs.mbari.org/x3d/erie_lld_10x/erie_lld_10x_scene.x3d': {
                                        'position': '557315.50014 -4777725.37774 4229154.62985',
                                        'orientation': '0.99936 -0.02525 -0.02534 1.59395',
                                        'centerOfRotation': '555524.3673806359 -4734293.352168839 4223218.342988144',
                                        'VerticalExaggeration': '10',
                                        'speed': '0.1',
                                    }
                    },
                    grdTerrain = os.path.join(parentDir, 'erie_lld.grd')
                 )

brizo_sdate = datetime(2021, 8, 4)
brizo_edate = datetime(2021, 8, 17)
makai_sdate = datetime(2021, 8, 3)
makai_edate = datetime(2021, 8, 8)

cl.process_command_line()

if cl.args.test:
    cl.stride = 100
    cl.loadLRAUV('brizo', brizo_sdate, brizo_edate, critSimpleDepthTime=0.1, build_attrs=True)
    cl.loadLRAUV('makai', makai_sdate, makai_edate, critSimpleDepthTime=0.1, build_attrs=True)
elif cl.args.stride:
    cl.stride = cl.args.stride
    # Post recovery missionlogs load
    cl.loadLRAUV('brizo', brizo_sdate, brizo_edate, critSimpleDepthTime=0.1)
    cl.loadLRAUV('makai', makai_sdate, makai_edate, critSimpleDepthTime=0.1)

##cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

