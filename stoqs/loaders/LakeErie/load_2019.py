#!/usr/bin/env python
'''
MBARI ESP Team
Loader for Lake Erie Makai 2019 deployments

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

cl = CANONLoader('stoqs_erie2019', 'Lake Erie ESP 2019',
                 description='Lake Erie Makai ESP DEployments in 2019',
                 )

syear = datetime(2019, 8, 13)
eyear = datetime(2019, 9, 30)

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

