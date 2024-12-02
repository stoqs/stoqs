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

cl = CANONLoader('stoqs_denmark2024', 'Denmark LRAUV Deployments - June 2024',
                    description='LRAUV Deployments Deployments near Denmark in 2024',
                    x3dTerrains = {
                                    'https://stoqs.mbari.org/x3d/Globe_1m_bath_10x/Globe_1m_bath_10x_scene.x3d': {
                                      'position': '14051448.48336 -15407886.51486 6184041.22775',
                                      'orientation': '0.83940 0.33030 0.43164 1.44880',
                                      'centerOfRotation': '0 0 0',
                                      'VerticalExaggeration': '10',
                                    },
                    #                'https://stoqs.mbari.org/x3d/michigan_lld_10x/michigan_lld_10x_src_scene.x3d': {
                    #                  'position': '260508.70011 -4920934.73726 4257472.30926',
                    #                  'orientation': '1.00000 0.00113 -0.00025 1.66609',
                    #                  'centerOfRotation': '239815.39152 -4691345.97184 4297950.38875',
                    #                  'VerticalExaggeration': '10',
                    #                  'speed': '0.1',
                    #                },
                                    # Need to convert .grd to legacy format for mbgrd2gtlf:
                                    # gmt grdconvert michigan_lld.grd -Gmichigan_lld_new.grd=cd
                                    # mbgrd2gltf michigan_lld_new.grd -e 100 -b
                                    # mv michigan_lld_new.glb michigan_lld_100x.glb # Then copy to stoqs.mbari.org
                    #                'https://stoqs.mbari.org/x3d/michigan_lld_100x/michigan_lld_100x.glb': {
                    #                  'position': '260508.70011 -4920934.73726 4257472.30926',
                    #                  'orientation': '1.00000 0.00113 -0.00025 1.66609',
                    #                  'centerOfRotation': '239815.39152 -4691345.97184 4297950.38875',
                    #                  'VerticalExaggeration': '100',
                    #                  'speed': '0.1',
                    #                },
                                    # TODO: Add glb model for Lake Superior
                    },
                    grdTerrain = os.path.join(parentDir, 'michigan_lld.grd')
                 )

makai_sdate = datetime(2024, 6, 5)
makai_edate = datetime(2024, 6, 19)
brizo_sdate = datetime(2024, 6, 5)
brizo_edate = datetime(2024, 6, 19)

cl.process_command_line()

if cl.args.test:
    cl.stride = 1
    # Uncomment the test to use...

    # Test loading brizo's ESP Cartridges 29 to 23
    # cl.brizo_base = 'http://dods.mbari.org/opendap/data/lrauv/brizo/missionlogs/2024/20240607_20240615/20240612T184249/'
    # cl.brizo_files = ['202406121843_202406130908_2S_scieng.nc']
    # cl.brizo_parms =['temperature', 'current_direction_navigation_frame', 'current_speed_navigation_frame']
    # cl.loadLRAUV('brizo', brizo_sdate, brizo_edate, critSimpleDepthTime=0.1, build_attrs=False)

    # Test loading makai's ESP Cartridges 59/58
    # https://dods.mbari.org/opendap/data/lrauv/makai/missionlogs/2024/20240607_20240615/20240607T125711/202406071257_202406080957_2S_scieng.nc.html
    # cl.makai_base = 'http://dods.mbari.org/opendap/data/lrauv/makai/missionlogs/2024/20240607_20240615/20240607T125711/'
    # cl.makai_files = ['202406071257_202406080957_2S_scieng.nc']
    # cl.makai_parms =['temperature', 'current_direction_navigation_frame', 'current_speed_navigation_frame']
    # cl.loadLRAUV('makai', makai_sdate, makai_edate, critSimpleDepthTime=0.1, build_attrs=False)

    # Test loading makai's ESP Cartridges 56/55
    cl.makai_base = 'http://dods.mbari.org/opendap/data/lrauv/makai/missionlogs/2024/20240607_20240615/20240608T095744/'
    cl.makai_files = ['202406080957_202406082214_2S_scieng.nc ']
    cl.makai_parms =['temperature', 'current_direction_navigation_frame', 'current_speed_navigation_frame']
    cl.loadLRAUV('makai', makai_sdate, makai_edate, critSimpleDepthTime=0.1, build_attrs=False)

    # Test Duplicate data and missing/overlapping Cartridges for makai
    # makai_sdate = datetime(2024, 6, 7)
    # makai_edate = datetime(2024, 6, 16)
    # cl.loadLRAUV('makai', makai_sdate, makai_edate, critSimpleDepthTime=0.1, build_attrs=True)

    # cl.loadLRAUV('makai', makai_sdate, makai_edate, critSimpleDepthTime=0.1)
    # cl.loadLRAUV('brizo', brizo_sdate, brizo_edate, critSimpleDepthTime=0.1)
elif cl.args.stride:
    cl.stride = cl.args.stride
    # Realtime sbd logs load
    # cl.loadLRAUV('makai', makai_sdate, makai_edate, critSimpleDepthTime=0.1, sbd_logs=True)
    # cl.loadLRAUV('brizo', brizo_sdate, brizo_edate, critSimpleDepthTime=0.1, sbd_logs=True)
    # Post recovery missionlogs load
    cl.loadLRAUV('makai', makai_sdate, makai_edate, critSimpleDepthTime=0.1)
    cl.loadLRAUV('brizo', brizo_sdate, brizo_edate, critSimpleDepthTime=0.1)

# Add any X3D simulation anbd Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

