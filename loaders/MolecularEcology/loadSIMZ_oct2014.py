#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for all October 2013 SIMZ activities.  

Mike McCann
MBARI 24 October 2013

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader

cl = CANONLoader('stoqs_simz_oct2014', 'Sampling and Identification of Marine Zooplankton - October 2014',
                        description = 'Rachel Carson and Dorado surveys in Northern Monterey Bay',
                        x3dTerrains = {
                            'http://dods.mbari.org/terrain/x3d/Monterey25_10x_GeoOrigin_-122_3675_0/Monterey25_10x_GeoOrigin_-122_3675_0_scene.x3d': {
                                'position': '-28552.237 -47480.893 -11887.605',
                                'orientation': '0.94840 -0.25575 -0.18743 1.73273',
                                'centerOfRotation': '9698.914 6008.664 13476.855',
                                'VerticalExaggeration': '10',
                                'geoOrigin': '-122 36.75 0',
                                'speed': '0.1',
                            }
                        },
                        grdTerrain = os.path.join(parentDir, 'Monterey25.grd')
                )

startDatetime = datetime.datetime(2014, 10, 15)
endDatetime = datetime.datetime(2014, 10, 23)

# Aboard the Carson use zuma:
##cl.tdsBase = 'http://zuma.rc.mbari.org/thredds/'       
# On shore, use the odss server:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'       

# 2-second decimated dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2014/netcdf/'   # Dorado archive
cl.dorado_files = [ 
                    'Dorado389_2014_289_04_289_04_decim.nc',
                    'Dorado389_2014_290_00_290_00_decim.nc',
                    'Dorado389_2014_293_00_293_00_decim.nc',
                    'Dorado389_2014_294_00_294_00_decim.nc',
                    'Dorado389_2014_295_00_295_00_decim.nc',
                  ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                    'fl700_uncorr', 'salinity', 'biolume' ]

# Rachel Carson Underway CTD
cl.rcuctd_base = cl.dodsBase + 'SIMZ/2014_Oct/carson/uctd/'
cl.rcuctd_files = [ 
                    '28914plm01.nc', '29014plm01.nc', '29314plm01.nc', '29414plm01.nc', '29514plm01.nc',
                  ]
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]

# Rachel Carson Profile CTD
cl.pctdDir = 'SIMZ/2014_Oct/carson/pctd/'
cl.rcpctd_base = cl.dodsBase + cl.pctdDir
cl.rcpctd_files = [ 
            'SIMZ2014C40.nc', 'SIMZ2014C41.nc', 'SIMZ2014C42.nc', 'SIMZ2014C43.nc', 'SIMZ2014C44.nc',
            'SIMZ2014C45.nc', 'SIMZ2014C46.nc', 'SIMZ2014C47.nc', 'SIMZ2014C48.nc', 'SIMZ2014C49.nc',
            'SIMZ2014C50.nc', 'SIMZ2014C51.nc', 'SIMZ2014C52.nc', 'SIMZ2014C53.nc', 'SIMZ2014C54.nc',
            'SIMZ2014C55.nc', 'SIMZ2014C56.nc', 'SIMZ2014C57.nc', 'SIMZ2014C58.nc', 'SIMZ2014C59.nc',
            'SIMZ2014C60.nc', 'SIMZ2014C61.nc', 'SIMZ2014C62.nc', 'SIMZ2014C63.nc', 'SIMZ2014C64.nc',
            'SIMZ2014C65.nc', 'SIMZ2014C66.nc', 'SIMZ2014C67.nc', 'SIMZ2014C68.nc', 'SIMZ2014C69.nc',
                      ]
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]

# Mooring M1 Combined file produced by DPforSSDS processing - for just the duration of the campaign
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/201407/'
cl.m1_files = ['OS_M1_20140716hourly_CMSTV.nc']
cl.m1_parms = [ 'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR', 
                     'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR', 
                     'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR'
                   ]
cl.m1_startDatetime = startDatetime
cl.m1_endDatetime = endDatetime

# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/GOC12/ copied to local GOC12 dir
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'SIMZOct2013')
cl.subsample_csv_files = [
                            #'2013_SIMZ_AUV_STOQS.csv',
                            #'2013_SIMZ_Niskins_STOQS.csv',
                            ##'2013_SIMZ_TowNets_STOQS.csv',
                         ]


# Execute the load
cl.process_command_line()

if cl.args.test:
    ##cl.loadL_662(stride=1)
    cl.loadDorado(stride=100)
    cl.loadRCuctd(stride=100)
    cl.loadRCpctd(stride=1)
    cl.loadM1(stride=10)
    #cl.loadSubSamples()

elif cl.args.optimal_stride:
    ##cl.loadL_662(stride=1)
    cl.loadDorado(stride=1)
    cl.loadRCuctd(stride=1)
    cl.loadRCpctd(stride=1)
    cl.loadM1(stride=1)
    #cl.loadSubSamples()

else:
    cl.stride = cl.args.stride
    ##cl.loadL_662()
    cl.loadDorado()
    cl.loadRCuctd()
    cl.loadRCpctd()
    cl.loadM1()
    #cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print "All Done."

