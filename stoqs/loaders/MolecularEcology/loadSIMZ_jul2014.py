#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for July 2014 SIMZ, Bodega CA

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
import timing

cl = CANONLoader('stoqs_simz_jul2014', 'Sampling and Identification of Marine Zooplankton - July 2014',
                        description = 'Rachel Carson and Dorado surveys, Bodega Bay region',
                        x3dTerrains = {
                            'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                                'position': '-2822317.31255 -4438600.53640 3786150.85474',
                                'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                                'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                                'VerticalExaggeration': '10',
                                'speed': '0.1',
                            }
                        },
                        grdTerrain = os.path.join(parentDir, 'Monterey25.grd')
                )

startDatetime = datetime.datetime(2014, 7, 28)
endDatetime = datetime.datetime(2014, 7, 31)

# Aboard the Carson use zuma:
##cl.tdsBase = 'http://zuma.rc.mbari.org/thredds/'       
# On shore, use the odss server:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'       

# 2-second decimated dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2014/netcdf/'   # shore 
##cl.dorado_base = cl.dodsBase + 'SIMZ/2014_Jul/Platforms/AUVs/Dorado/' # copied to zuma
cl.dorado_files = [ 
                    'Dorado389_2014_210_01_210_01_decim.nc', 
                    'Dorado389_2014_210_02_210_02_decim.nc', 
                    'Dorado389_2014_211_02_211_02_decim.nc', 
                    'Dorado389_2014_211_03_211_03_decim.nc', 
                    'Dorado389_2014_212_00_212_00_decim.nc', 
                  ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                    'fl700_uncorr', 'salinity', 'biolume', 'rhodamine',
                    'roll', 'pitch', 'yaw',
                    'sepCountList', 'mepCountList' ]

# Rachel Carson Underway CTD
cl.rcuctd_base = cl.dodsBase + 'SIMZ/2014_Jul/Platforms/Ships/Rachel_Carson/uctd/'
cl.rcuctd_files = [ 
                    '2014simzplm05.nc', 
                    '2014simzplm06.nc', 
                    '2014simzplm07.nc', 
                  ]
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]

# Rachel Carson Profile CTD
cl.pctdDir = 'SIMZ/2014_Jul/Platforms/Ships/Rachel_Carson/pctd/'
cl.rcpctd_base = cl.dodsBase + cl.pctdDir
cl.rcpctd_files = [ 
                     'simz2014c25.nc', 'simz2014c26.nc', 'simz2014c27.nc', 'simz2014c28.nc', 'simz2014c29.nc', 'simz2014c30.nc',
                     'simz2014c31.nc', 'simz2014c32.nc', 'simz2014c33.nc',
                     'simz2014c34.nc', 'simz2014c35.nc', 'simz2014c36.nc',
                     'simz2014c37.nc', 'simz2014c38.nc', 'simz2014c39.nc',
                      ]
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]

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
    ##cl.loadM1(stride=10)
    ##cl.loadSubSamples()

elif cl.args.optimal_stride:
    ##cl.loadL_662(stride=1)
    cl.loadDorado(stride=1)
    cl.loadRCuctd(stride=1)
    cl.loadRCpctd(stride=1)
    ##cl.loadM1(stride=1)
    ##cl.loadSubSamples()

else:
    cl.stride = cl.args.stride
    ##cl.loadL_662()
    cl.loadDorado()
    cl.loadRCuctd()
    cl.loadRCpctd()
    ##cl.loadM1()
    ##cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

