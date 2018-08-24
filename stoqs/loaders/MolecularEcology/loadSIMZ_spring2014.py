#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for all October 2014 SIMZ activities.  

John Ryan
MBARI 12 March 2014

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime
parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)      # So that CANON is found

from CANON import CANONLoader
import timing

cl = CANONLoader('stoqs_simz_spring2014', 'Sampling and Identification of Marine Zooplankton - Spring 2014',
                                description = 'Month-long investigation of water in northern Monterey Bay',
                                x3dTerrains = {
                                    'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                                        'position': '-2822317.31255 -4438600.53640 3786150.85474',
                                        'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                                        'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                                        'VerticalExaggeration': '10',
                                        'speed': '.1',
                                    }
                                },
                                # Do not check in .grd files to the repository, keep them in the loaders directory
                                grdTerrain=os.path.join(parentDir, 'Monterey25.grd'),
                )

startDatetime = datetime.datetime(2014, 2, 18)
endDatetime = datetime.datetime(2014, 3, 18)

# Aboard the Carson use zuma:
##cl.tdsBase = 'http://zuma.rc.mbari.org/thredds/'
# On shore, use the odss server:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'       

# 2-second decimated dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2014/netcdf/'   # Dorado archive
cl.dorado_files = [ 
                    'Dorado389_2014_050_00_050_00_decim.nc', 
                    'Dorado389_2014_050_01_050_01_decim.nc', 
                    'Dorado389_2014_071_01_071_01_decim.nc', 
                    'Dorado389_2014_071_02_071_02_decim.nc', 
                    'Dorado389_2014_072_00_072_00_decim.nc', 
                    'Dorado389_2014_072_01_072_01_decim.nc', 
                  ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                    'fl700_uncorr', 'salinity', 'biolume',
                    'roll', 'pitch', 'yaw',
                    'sepCountList', 'mepCountList' ]

# Spray glider - for just the duration of the campaign
cl.l_662_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_files = ['OS_Glider_L_662_20131125_TS.nc','OS_Glider_L_662_20140311_TS.nc']
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = startDatetime
cl.l_662_endDatetime = endDatetime

# Rachel Carson Underway CTD
cl.rcuctd_base = cl.dodsBase + 'SIMZ/2014_spring/Platforms/Ships/Rachel_Carson/uctd/'
cl.rcuctd_files = [ 
                    '2014simzplm01.nc', '2014simzplm02.nc', 
                  ]
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]

# Rachel Carson Profile CTD
cl.pctdDir = 'SIMZ/2014_spring/Platforms/Ships/Rachel_Carson/pctd/'
cl.rcpctd_base = cl.dodsBase + cl.pctdDir
cl.rcpctd_files = [ 
'simz2014c03.nc', 'simz2014c06.nc', 'simz2014c09.nc',  'simz2014c12.nc',  'simz2014c15.nc',  'simz2014c18.nc',  'simz2014c21.nc',	'simz2014c24.nc',
'simz2014c01.nc',  'simz2014c04.nc',  'simz2014c07.nc',  'simz2014c10.nc',  'simz2014c13.nc',  'simz2014c16.nc',  'simz2014c19.nc',  'simz2014c22.nc',
'simz2014c02.nc',  'simz2014c05.nc',  'simz2014c08.nc',  'simz2014c11.nc',  'simz2014c14.nc',  'simz2014c17.nc',  'simz2014c20.nc',  'simz2014c23.nc',
                      ]
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]

# Mooring M1 Combined file produced by DPforSSDS processing - for just the duration of the campaign
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/201309/'
cl.m1_files = ['OS_M1_20130918hourly_CMSTV.nc']
cl.m1_parms = [ 'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR', 
                     'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR', 
                     'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR'
                   ]
cl.m1_startDatetime = startDatetime
cl.m1_endDatetime = endDatetime

# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/GOC12/ copied to local GOC12 dir
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'SIMZAug2013')
cl.subsample_csv_files = [
                            '2013_Aug_SIMZ_Niskin_microscopy_STOQS.csv',
                         ]


# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadL_662(stride=10)
    cl.loadDorado(stride=100)
    cl.loadRCuctd(stride=10)
    cl.loadRCpctd(stride=1)
    cl.loadM1(stride=10)
    ##cl.loadSubSamples()

elif cl.args.optimal_stride:
    cl.loadL_662(stride=1)
    cl.loadDorado(stride=1)
    cl.loadRCuctd(stride=1)
    cl.loadRCpctd(stride=1)
    cl.loadM1(stride=1)
    ##cl.loadSubSamples()

else:
    cl.stride = cl.args.stride
    cl.loadL_662()
    cl.loadDorado()
    cl.loadRCuctd()
    cl.loadRCpctd()
    cl.loadM1()
    ##cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

