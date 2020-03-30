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

sdate = datetime(2019, 8, 13)
edate = datetime(2019, 8, 30)

cl.process_command_line()

if cl.args.test:
    cl.stride = 1
    # Cartridge 14 simpledepthtime only 2 points, need smaller sample_simplify_crit
    #-cl.makai_base = 'http://dods.mbari.org/opendap/data/lrauv/makai/missionlogs/2019/20190822_20190827/20190823T235351/'
    #-cl.makai_files = ['201908232353_201908261943_2S_scieng.nc']
    #-cl.makai_parms = ['temperature']
    # Shorter log for testing setting sample_simplify_crit
    ##cl.makai_base = 'http://dods.mbari.org/opendap/data/lrauv/makai/missionlogs/2019/20190819_20190821/20190819T210619/'
    ##cl.makai_files = ['201908192106_201908200410_2S_scieng.nc']
    # Test for missing Cartridge 45
    cl.makai_base = 'http://dods.mbari.org/opendap/data/lrauv/makai/missionlogs/2019/20190819_20190821/20190820T055043/'
    cl.makai_files = ['201908200550_201908201158_2S_scieng.nc']
    cl.makai_parms = ['temperature']
    cl.loadLRAUV('makai', sdate, edate, critSimpleDepthTime=0.1, build_attrs=False)
elif cl.args.stride:
    cl.stride = cl.args.stride

    # Realtime data load - Loads files produced by stoqs/loaders/CANON/realtime/monitorLrauv_erie2019.sh
    # Need small critSimpleDepthTime for the 1-2 m shallow yo-yos done
    ##for lrauv in ('makai', 'tethys'):
    ##    cl.loadLRAUV(lrauv, sdate, edate, critSimpleDepthTime=0.1, sbd_logs=True,
    ##                 parameters=['chlorophyll', 'temperature', 'salinity', 
    ##                             'mass_concentration_of_oxygen_in_sea_water'])

    # Post recovery missionlogs load
    for lrauv in ('makai', 'tethys'):
        cl.loadLRAUV(lrauv, sdate, edate, critSimpleDepthTime=0.1)

##cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

