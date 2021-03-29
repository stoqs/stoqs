#!/usr/bin/env python
'''
Load all Dorado data for the PlanktonProxies Project

Mike McCann
MBARI 9 August 2018
'''

import os
import sys
from datetime import datetime

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
import timing

cl = CANONLoader('stoqs_all_dorado', 'Plankton Proxies - All Dorado Data',
                 description='All Dorado survey data from 2003 through 2019 and beyond',
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

startdate = datetime(2003, 1, 1)
enddate = datetime(2029, 12, 31)

# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.stride = 10

    # Initial short survey to test plankton_proxies loading
    startdate = datetime(2003, 12, 5)
    enddate = datetime(2003, 12, 7)
    cl.loadDorado(startdate, enddate, build_attrs=True, plankton_proxies=True)

    # One of the early (short) surveys with LOPC data
    startdate = datetime(2008, 10, 21, 16)
    enddate = datetime(2008, 10, 22, 16)
    cl.loadDorado(startdate, enddate, build_attrs=True, plankton_proxies=True)

    # Standard test load - for testing loading all Parameters
    cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
    cl.dorado_files = [ 'Dorado389_2010_300_00_300_00_decim.nc' ]
    cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                        'fl700_uncorr', 'salinity', 'biolume', 'roll', 'pitch', 'yaw',
                        'sepCountList', 'mepCountList' ]
    cl.loadDorado(stride=100, plankton_proxies=False)

    # Survey with 0 mps_loaded
    cl.dorado_base = 'http://dods.mbari.org/thredds/dodsC/auv/dorado/2004/netcdf/'
    cl.dorado_files = ['Dorado389_2004_251_00_251_00_decim.nc']
    cl.dorado_parms = ['temperature']
    cl.loadDorado(startdate, enddate, build_attrs=False, plankton_proxies=True)

    # Most recent survey during validation tests of production load
    startdate = datetime(2019, 10, 3)
    enddate = datetime(2019, 10, 5)
    cl.loadDorado(startdate, enddate, build_attrs=True, plankton_proxies=True)

    # Survey that has ActivityParameters for _proxies.nc Parameters, but no other
    startdate = datetime(2007, 9, 11)
    enddate = datetime(2007, 9, 13)
    cl.loadDorado(startdate, enddate, build_attrs=True, plankton_proxies=True)

    # IndexError discovered on test production load 29 April 2021
    # - Should now continue on with bad coordinates warning
    cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2011/netcdf/'
    cl.dorado_files = [ 'Dorado389_2011_158_00_158_00_decim.nc' ]
    cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                        'fl700_uncorr', 'salinity', 'biolume', 'roll', 'pitch', 'yaw',
                        'sepCountList', 'mepCountList' ]
    cl.loadDorado(stride=1, plankton_proxies=True)

elif cl.args.stride:
    cl.stride = cl.args.stride
    if cl.args.startdate:
        startdate = datetime.strptime(cl.args.startdate, '%Y%m%d')
    if cl.args.enddate:
        enddate = datetime.strptime(cl.args.enddate, '%Y%m%d')
    cl.loadDorado(startdate, enddate, build_attrs=True, plankton_proxies=True)

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

