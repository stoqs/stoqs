#!/usr/bin/env python
'''
MBARI ESP Team
Loader for Lake Erie Makai 2018 deployments

Mike McCann, Duane Edgington, Danelle Cline
MBARI 25 April 2019
'''

import os
import sys

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
from datetime import datetime
import timing

cl = CANONLoader('stoqs_erie2018', 'Lake Erie ESP 2018',
                    description='Lake Erie Makai ESP DEployments in 2018',
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

# From: John Ryan <ryjo@mbari.org>
# Subject: Lake Erie 2018
# Date: April 25, 2019 at 11:07:53 AM PDT
# To: Mike McCann <mccann@mbari.org>
# Reply-To: John Ryan <ryjo@mbari.org>
# 
# Hi Mike,
# 
# The 'Lake Erie 2018' STOQS database will include Makai data from these directories:
# /Volumes/LRAUV/Makai/missionlogs/2018/20180823_20180827/
# /Volumes/LRAUV/Makai/missionlogs/2018/20180828_20180903/
# 
# Thanks!
# 
# John

# Extend syear and eyear one day beyond limits of .dlist files in above email
syear = datetime(2018, 8, 22)
eyear = datetime(2018, 9, 4)

# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.stride = 10000
elif cl.args.stride:
    cl.stride = cl.args.stride

for lrauv in ('makai', ):
    cl.loadLRAUV(lrauv, syear, eyear, dlist_str='Lake Erie', err_on_missing_file=True,
                 critSimpleDepthTime=1)

##cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

