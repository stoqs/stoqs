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
                 description='Lake Erie Makai ESP Deployments in 2019',
                 )

sdate = datetime(2019, 8, 13)
edate = datetime(2019, 8, 30)

cl.process_command_line()

if cl.args.test:
    cl.stride = 1000
elif cl.args.stride:
    cl.stride = cl.args.stride

# Realtime data load - Loads files produced by stoqs/loaders/CANON/realtime/monitorLrauv_erie2019.sh
# Need small critSimpleDepthTime for the 1-2 m shallow yo-yos done
for lrauv in ('makai', 'tethys'):
    cl.loadLRAUV(lrauv, sdate, edate, critSimpleDepthTime=0.1, sbd_logs=True,
                 parameters=['chlorophyll', 'temperature', 'salinity', 
                             'mass_concentration_of_oxygen_in_sea_water'])

# Post recovery missionlogs load
for lrauv in ('makai', 'tethys'):
    cl.loadLRAUV(lrauv, sdate, edate, critSimpleDepthTime=0.1)

##cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

