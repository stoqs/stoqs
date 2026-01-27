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
    cl.stride = 1


    # Initial short survey to test plankton_proxies loading
    ## startdate = datetime(2003, 12, 5)
    ## enddate = datetime(2003, 12, 7)
    ## cl.loadDorado(startdate, enddate, build_attrs=True, plankton_proxies=True)

    # One of the early (short) surveys with LOPC data
    ## startdate = datetime(2008, 10, 21, 16)
    ## enddate = datetime(2008, 10, 22, 16)
    ## cl.loadDorado(startdate, enddate, build_attrs=True, plankton_proxies=True)

    # Standard test load - for testing loading all Parameters
    ## cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
    ## cl.dorado_files = [ 'Dorado389_2010_300_00_300_00_decim.nc' ]
    ## cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
    ##                     'fl700_uncorr', 'salinity', 'biolume', 'roll', 'pitch', 'yaw',
    ##                     'sepCountList', 'mepCountList' ]
    ## cl.loadDorado(stride=100, plankton_proxies=False)

    # Survey with 0 mps_loaded
    ## cl.dorado_base = 'http://dods.mbari.org/thredds/dodsC/auv/dorado/2004/netcdf/'
    ## cl.dorado_files = ['Dorado389_2004_251_00_251_00_decim.nc']
    ## cl.dorado_parms = ['temperature']
    ## cl.loadDorado(startdate, enddate, build_attrs=False, plankton_proxies=True)

    # Most recent survey during validation tests of production load
    ## startdate = datetime(2019, 10, 3)
    ## enddate = datetime(2019, 10, 5)
    ## cl.loadDorado(startdate, enddate, build_attrs=True, plankton_proxies=True)

    # Survey that has ActivityParameters for _proxies.nc Parameters, but no other
    ## startdate = datetime(2007, 9, 11)
    ## enddate = datetime(2007, 9, 13)
    ## cl.loadDorado(startdate, enddate, build_attrs=True, plankton_proxies=True)

    # IndexError discovered on test production load 29 April 2021
    # - Should now continue on with bad coordinates warning
    ## cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2011/netcdf/'
    ## cl.dorado_files = [ 'Dorado389_2011_158_00_158_00_decim.nc' ]
    ## cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
    ##                     'fl700_uncorr', 'salinity', 'biolume', 'roll', 'pitch', 'yaw',
    ##                     'sepCountList', 'mepCountList' ]
    ## cl.loadDorado(stride=1, plankton_proxies=True)

    # Recent survey for testing pre-commit and GitHub Actions work in March 2025
    ## cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2024/netcdf/'
    ## cl.dorado_files = [ 'dorado_2024.317.01_1S.nc' ]
    ## cl.dorado_parms = [ 'lopc_countListSum',
    ##         'lopc_transCount', 'lopc_nonTransCount', 'lopc_LCcount', 'lopc_flowSpeed',
    ##         ]
    ## cl.loadDorado(stride=1)

    # Actual short survey for testing auv-python's pre-commit and GitHub Actions work in March 2025: http://stoqs.mbari.org/p/DmHOaxI
    ## cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2011/netcdf/'
    ## cl.dorado_files = [ 'dorado_2011.256.02_1S.nc' ]
    ## cl.dorado_parms = ['ctd1_temperature_onboard', 'ctd1_temperature', 'ctd1_salinity_onboard', 'ctd1_salinity', 'ctd1_flow1',
    ##         'ctd2_temperature_onboard', 'ctd2_temperature', 'ctd2_salinity_onboard', 'ctd2_salinity', 'ctd2_flow2',
    ##         'ctd1_dissolvedO2', 'ctd1_oxygen_mll', 'ctd1_oxygen_umolkg', 'hs2_bb470', 'hs2_bb676', 'hs2_fl676', 'hs2_bbp470',
    ##         'hs2_bbp676', 'hs2_bb420', 'hs2_bb700', 'hs2_fl700', 'hs2_bbp420', 'hs2_bbp700', 'navigation_roll',
    ##         'navigation_pitch', 'navigation_yaw', 'navigation_mWaterSpeed', 'tailcone_propRpm', 'lopc_countListSum',
    ##         'lopc_transCount', 'lopc_nonTransCount', 'lopc_LCcount', 'lopc_flowSpeed', 'ecopuck_bbp700', 'ecopuck_cdom',
    ##         'ecopuck_chl', 'biolume_flow', 'biolume_raw', 'biolume_avg_biolume', 'biolume_nbflash_high', 'biolume_nbflash_low',
    ##         'biolume_bg_biolume', 'biolume_proxy_adinos', 'biolume_proxy_hdinos', 'biolume_proxy_diatoms', 'biolume_intflash',
    ##         'profile_number', 'isus_nitrate', 'isus_quality']
    ## cl.loadDorado(stride=1)

    # Short survey with lopc data for testing lopc processing in March 2025: http://stoqs.mbari.org/p/SVGDeLc
    ## cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
    ## cl.dorado_files = [ 'dorado_2010.341.00_1S.nc' ]
    ## cl.dorado_parms = [ 'lopc_countListSum',
    ##         'lopc_transCount', 'lopc_nonTransCount', 'lopc_LCcount', 'lopc_flowSpeed',
    ##         ]
    ## cl.loadDorado(stride=1)

    # Multi-night MBTSLINE mission for testing auv-python's revised select_nighttime_bl_raw: http://stoqs.mbari.org/p/lblVNGs
    ## cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2020/netcdf/'
    ## cl.dorado_files = [ 'dorado_2020.337.00_1S.nc' ]
    ## cl.dorado_parms = [
    ##         'biolume_flow', 'biolume_raw', 'biolume_avg_biolume', 'biolume_nbflash_high', 'biolume_nbflash_low',
    ##         'biolume_bg_biolume', 'biolume_proxy_adinos', 'biolume_proxy_hdinos', 'biolume_proxy_diatoms', 'biolume_intflash',
    ##         'profile_number']
    ## cl.loadDorado(stride=1)

    # For testing compute_backscatter() use in additional missions beside 2022.201.00, April, October
    ## cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2017/netcdf/'
    ## cl.dorado_files = [ 'dorado_2017.275.01_1S.nc' ]
    ## cl.dorado_parms = ['ctd1_temperature_onboard', 'ctd1_temperature', 'ctd1_salinity_onboard', 'ctd1_salinity', 'ctd1_flow1',
    ##         'ctd2_temperature_onboard', 'ctd2_temperature', 'ctd2_salinity_onboard', 'ctd2_salinity', 'ctd2_flow2',
    ##         'ctd1_dissolvedO2', 'ctd1_oxygen_mll', 'ctd1_oxygen_umolkg', 'hs2_bb470', 'hs2_bb676', 'hs2_fl676', 'hs2_bbp470',
    ##         'hs2_bbp676', 'hs2_bb420', 'hs2_bb700', 'hs2_fl700', 'hs2_bbp420', 'hs2_bbp700', 'navigation_roll',
    ##         'hs2_bbp_cb420', 'hs2_bbp_cb700',
    ##         'navigation_pitch', 'navigation_yaw', 'navigation_mWaterSpeed', 'tailcone_propRpm', 'lopc_countListSum',
    ##         'lopc_transCount', 'lopc_nonTransCount', 'lopc_LCcount', 'lopc_flowSpeed', 'ecopuck_bbp700', 'ecopuck_cdom',
    ##         'ecopuck_chl', 'biolume_flow', 'biolume_raw', 'biolume_avg_biolume', 'biolume_nbflash_high', 'biolume_nbflash_low',
    ##         'biolume_bg_biolume', 'biolume_proxy_adinos', 'biolume_proxy_hdinos', 'biolume_proxy_diatoms', 'biolume_intflash',
    ##         'profile_number', 'isus_nitrate', 'isus_quality']
    ## cl.loadDorado(stride=1)
    ## cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2018/netcdf/'
    ## cl.dorado_files = [ 'dorado_2018.099.00_1S.nc' ]
    ## cl.dorado_parms = ['ctd1_temperature_onboard', 'ctd1_temperature', 'ctd1_salinity_onboard', 'ctd1_salinity', 'ctd1_flow1',
    ##         'ctd2_temperature_onboard', 'ctd2_temperature', 'ctd2_salinity_onboard', 'ctd2_salinity', 'ctd2_flow2',
    ##         'ctd1_dissolvedO2', 'ctd1_oxygen_mll', 'ctd1_oxygen_umolkg', 'hs2_bb470', 'hs2_bb676', 'hs2_fl676', 'hs2_bbp470',
    ##         'hs2_bbp676', 'hs2_bb420', 'hs2_bb700', 'hs2_fl700', 'hs2_bbp420', 'hs2_bbp700', 'navigation_roll',
    ##         'hs2_bbp_cb420', 'hs2_bbp_cb700',
    ##         'navigation_pitch', 'navigation_yaw', 'navigation_mWaterSpeed', 'tailcone_propRpm', 'lopc_countListSum',
    ##         'lopc_transCount', 'lopc_nonTransCount', 'lopc_LCcount', 'lopc_flowSpeed', 'ecopuck_bbp700', 'ecopuck_cdom',
    ##         'ecopuck_chl', 'biolume_flow', 'biolume_raw', 'biolume_avg_biolume', 'biolume_nbflash_high', 'biolume_nbflash_low',
    ##         'biolume_bg_biolume', 'biolume_proxy_adinos', 'biolume_proxy_hdinos', 'biolume_proxy_diatoms', 'biolume_intflash',
    ##         'profile_number', 'isus_nitrate', 'isus_quality']
    ##cl.loadDorado(stride=1)

    # Honor startdate and enddate command line arguments, just like execution without --test
    cl.stride = cl.args.stride
    if cl.args.startdate:
        startdate = datetime.strptime(cl.args.startdate, '%Y%m%d')
    if cl.args.enddate:
        enddate = datetime.strptime(cl.args.enddate, '%Y%m%d')
    cl.loadDorado(startdate, enddate, build_attrs=True, file_patterns=(r".*netcdf/dorado_.*1S.nc", ))

elif cl.args.stride:
    cl.stride = cl.args.stride
    if cl.args.startdate:
        startdate = datetime.strptime(cl.args.startdate, '%Y%m%d')
    if cl.args.enddate:
        enddate = datetime.strptime(cl.args.enddate, '%Y%m%d')
    cl.loadDorado(startdate, enddate, build_attrs=True, file_patterns=(r".*netcdf/dorado_.*1S.nc", ))
    #cl.loadDorado(startdate, enddate, build_attrs=True, file_patterns=(r".*_decim.nc$", ), plankton_proxies=True)

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

