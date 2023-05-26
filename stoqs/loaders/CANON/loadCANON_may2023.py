#!/usr/bin/env python
__author__ = 'Mike McCann'
__copyright__ = '2023'
__license__ = 'GPL v3'

import os
import sys
import datetime

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
import timing

cl = CANONLoader('stoqs_canon_may2023', 'CANON - May 2023',
                 description='May 2023 LRAUV coordinated campaign observations centered on DEIMOS in Monterey Bay',
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

startdate = datetime.datetime(2023, 5, 18)
enddate = datetime.datetime(2023, 5, 30)

cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'


######################################################################
#  MOORINGS
######################################################################
# M1
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/'
cl.m1_files = [ 
    '202207/OS_M1_19700101hourly_CMSTV.nc',
    '202207/m1_hs2_1m_20220718.nc',
              ]
cl.m1_parms = [
  'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
  'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
  'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR',
  'bb470', 'bb676', 'fl676',
]

cl.m1_startDatetime = startdate
cl.m1_endDatetime = enddate

# DEIMOS
# TODO: Get data (csv file) for deimos-2023-CANON-Spring
cl.deimos_base = cl.dodsBase + 'Other/routine/Platforms/DEIMOS/netcdf/'
cl.deimos_parms = [ 'Sv_mean' ]
cl.deimos_files = [ 'deimos-2023-CANON-Spring.nc' ]


# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.stride = 100
elif cl.args.stride:
    cl.stride = cl.args.stride

cl.loadM1()  
cl.loadDEIMOS()
cl.load_i2MAP(startdate, enddate, build_attrs=True)
for lrauv in ('brizo', 'galene', 'makai',):
    cl.loadLRAUV(lrauv, startdate, enddate, critSimpleDepthTime=0.1)

#cl.loadSubSamples() ##when subsamples ready to load...

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

