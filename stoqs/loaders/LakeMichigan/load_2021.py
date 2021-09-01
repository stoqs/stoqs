#!/usr/bin/env python
'''
MBARI ESP Team
Loader for Lake Michigan Makai 2021 deployments

Makai Lake Michigan: 20210809_20210819.dlist

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

cl = CANONLoader('stoqs_michigan2021', 'Lake Michigan ESP 2021',
                    description='Lake Michigan Makai ESP Deployments in 2021',
                    x3dTerrains = {
                                    'https://stoqs.mbari.org/x3d/michigan_lld_10x/michigan_lld_10x_src_scene.x3d': {
                                        'position': '277414.36721 -5207201.16684 4373105.96194',
                                        'orientation': '0.99821 -0.05662 0.01901 1.48579',
                                        'centerOfRotation': '281401.0288298179 -4639090.577582279 4354217.4974804',
                                        'VerticalExaggeration': '10',
                                        'speed': '0.1',
                                    }
                    },
                    grdTerrain = os.path.join(parentDir, 'michigan_lld.grd')
                 )

sdate = datetime(2021, 8, 9)
edate = datetime(2021, 8, 21)

cl.process_command_line()

if cl.args.test:
    cl.stride = 10
    cl.loadLRAUV('makai', sdate, edate, critSimpleDepthTime=0.1)
elif cl.args.stride:
    cl.stride = cl.args.stride
    for lrauv in ('makai', ):
        cl.loadLRAUV(lrauv, sdate, edate, critSimpleDepthTime=0.1)

##cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

