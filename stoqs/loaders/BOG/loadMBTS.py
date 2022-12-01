#!/usr/bin/env python
'''
MBARI Biological Oceanography Group
Master loader for Monterey Bay Time Series data

Mike McCann, Duane Edgington, Danelle Cline
MBARI 8 April 2019
'''

import os
import sys

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
from datetime import datetime
from loaders.LRAUV.make_load_scripts import lrauvs
import timing

cl = CANONLoader('stoqs_mbts', 'BOG - Monterey Bay Time Series',
                 description='MBARI Biological Oceanography Group Monterey Bay Time Series data',
                 x3dTerrains={
                   'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
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

syear = datetime(2015, 1, 1)
eyear = datetime.utcnow()

# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.stride = 1000
elif cl.args.stride:
    cl.stride = cl.args.stride

# Sipper loading tests
#-cl.daphne_base = 'http://dods.mbari.org/opendap/data/lrauv/daphne/missionlogs/2018/20180220_20180221/20180221T074336/'
#-cl.daphne_files = ['201802210743_201802211832_2S_scieng.nc']
#-cl.daphne_parms = ['temperature']
#-cl.loadLRAUV('daphne', datetime(2018, 2, 1), datetime(2018, 2, 20), build_attrs=False)

# Error on load: value too long
#-cl.tethys_base = 'http://dods.mbari.org/opendap/data/lrauv/tethys/missionlogs/2019/20190304_20190307/20190305T002713/'
#-cl.tethys_files = ['201903050027_201903050636_2S_scieng.nc']
#-cl.tethys_parms = ['temperature']
#-cl.loadLRAUV('tethys', datetime(2018, 3, 1), datetime(2018, 3, 20), build_attrs=False)

# File "/srv/stoqs/loaders/BOG/../../loaders/__init__.py", line 1582, in addAltitude
#    bdepth = line.split()[2]
# IndexError: list index out of range
#-cl.tethys_base = 'http://dods.mbari.org/opendap/data/lrauv/tethys/missionlogs/2016/20160325_20160330/20160330T211745/'
#-cl.tethys_files = ['201603302117_201604041633_2S_scieng.nc']
#-cl.tethys_parms = ['temperature']
#-cl.loadLRAUV('tethys', datetime(2016, 3, 29), datetime(2016, 4, 5), build_attrs=False)

for lrauv in lrauvs:
    cl.loadLRAUV(lrauv, syear, eyear, dlist_str='MBTS', err_on_missing_file=True)

##cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

