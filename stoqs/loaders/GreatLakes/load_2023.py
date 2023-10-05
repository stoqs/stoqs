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

cl = CANONLoader('stoqs_greatlakes2023', 'Great Lakes LRAUV Deployments - June-October 2023',
                    description='Great Lakes LRAUV Deployments Deployments in 2023',
                    x3dTerrains = {
                    #                'https://stoqs.mbari.org/x3d/Globe_1m_bath_10x/Globe_1m_bath_10x_scene.x3d': {
                    #                  'position': '14051448.48336 -15407886.51486 6184041.22775',
                    #                  'orientation': '0.83940 0.33030 0.43164 1.44880',
                    #                  'centerOfRotation': '0 0 0',
                    #                  'VerticalExaggeration': '10',
                    #                },
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
                                    'https://stoqs.mbari.org/x3d/michigan_lld_100x/michigan_lld_100x.glb': {
                                      'position': '260508.70011 -4920934.73726 4257472.30926',
                                      'orientation': '1.00000 0.00113 -0.00025 1.66609',
                                      'centerOfRotation': '239815.39152 -4691345.97184 4297950.38875',
                                      'VerticalExaggeration': '100',
                                      'speed': '0.1',
                                    },
                                    # TODO: Add glb model for Lake Superior
                    },
                    simulations = {
                                    # It's 50x faster to use a local file rather than an opendap url, the code will wget it and open locally
                                    # Staring 2009-01-02T04:00:00 and lasting 4.8 days
                                    # dimensions: depth = 27 ; time = 465 ; x = 160 ; y = 33 ;
                                    "http://stoqs.mbari.org/simulation/LakeMichigan/BurgerOilfieldSpillCoarse.nc3": {
                                        "variable": "oil_concentration",
                                        "data_range": "0 43",       # Must encompass actual range of data
                                        "scaled_range": "0 255",    # Can reverse to make high data values black
                                        "geocoords": "43.1 -86.1 -13.05",           # Latitude (center) Longitude (center) Altitude (midpoint) GeoLocation
                                        "dimensions": "143100 26.1 28800",          # X (easting) Y (depth) Z (northing) ranges
                                        "tile_dims": "3x11",                        # For montage's --tile and ImageTextureAtlas's X and Y [must = ds.dims('y')]
                                        # To start at datetime(2023, 6, 25, 2, 30)
                                        "time_adjustment": "456816600",             # Seconds to add for matching time of data in STOQS
                                        "directory": "BurgerOilfieldSpillCoarse",   # dir in media/simulation holding ImageAtlas files for ea time step
                                        "half_time_step_secs": "450",               # Needed to restrict animation to just one ImageTextureAtlas at a time
                                    },
                                    # Staring 2009-01-02T03:15:00 and lasting 4.9 days
                                    # dimensions: depth = 27 ; time = 468 ; x = 116 ; y = 80 ;
                                    "http://stoqs.mbari.org/simulation/LakeMichigan/BurgerOilfieldSpillMed.nc3": {
                                        "variable": "oil_concentration",
                                        "data_range": "0 19",       # Must encompass actual range of data
                                        "scaled_range": "0 255",    # Can reverse to make high data values black
                                        "geocoords": "43.1 -86.5 -13.05",           # Latitude (center) Longitude (center) Altitude (midpoint) GeoLocation
                                        "dimensions": "34500 26.1 23700",           # X (easting) Y (depth) Z (northing) ranges
                                        "tile_dims": "4x20",                        # For montage's --tile and ImageTextureAtlas's X and Y [must = ds.dims('y')]
                                        # To start at datetime(2023, 6, 25, 2, 30)
                                        "time_adjustment": "456816600",             # Seconds to add for matching time of data in STOQS
                                        "directory": "BurgerOilfieldSpillMed",      # dir in media/simulation holding ImageAtlas files for ea time step
                                        "half_time_step_secs": "450",               # Needed to restrict animation to just one ImageTextureAtlas at a time
                                    },
                                  },
                    grdTerrain = os.path.join(parentDir, 'michigan_lld.grd')
                 )

makai_sdate = datetime(2023, 6, 23)
makai_edate = datetime(2023, 10, 18)
triton_sdate = datetime(2023, 6, 23)
triton_edate = datetime(2023, 10, 18)

cl.process_command_line()

# Uncomment for testing of simulation load
#cl.addSimulationResources(build_image_atlases=True)
#cl.stride = 10
#cl.loadLRAUV('makai', datetime(2023, 6, 25), datetime(2023, 6, 30), critSimpleDepthTime=0.1, build_attrs=True)
#cl.addSimulationResources()
#cl.addTerrainResources()
#breakpoint()

if cl.args.test:
    cl.stride = 100
    cl.loadLRAUV('makai', makai_sdate, makai_edate, critSimpleDepthTime=0.1, build_attrs=True)
    cl.loadLRAUV('triton', triton_sdate, triton_edate, critSimpleDepthTime=0.1, build_attrs=True)
elif cl.args.stride:
    cl.stride = cl.args.stride
    # Realtime sbd logs load
    cl.loadLRAUV('makai', makai_sdate, makai_edate, critSimpleDepthTime=0.1, sbd_logs=True)
    cl.loadLRAUV('triton', triton_sdate, triton_edate, critSimpleDepthTime=0.1, sbd_logs=True)
    # Post recovery missionlogs load
    cl.loadLRAUV('makai', makai_sdate, makai_edate, critSimpleDepthTime=0.1)
    cl.loadLRAUV('triton', triton_sdate, triton_edate, critSimpleDepthTime=0.1)

# Add any X3D simulation anbd Terrain information specified in the constructor to the database - must be done after a load is executed
# cl.addSimulationResources(build_image_atlases=True)   # Use build_image_atlases=True the first time thie loader is run on a server
cl.addSimulationResources()                             # Update metadata only
cl.addTerrainResources()

print("All Done.")

