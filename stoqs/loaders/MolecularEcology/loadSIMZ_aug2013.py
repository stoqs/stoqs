#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for all August 2013 SIMZ activities.  

Mike McCann
MBARI 13 August

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

cl = CANONLoader('stoqs_simz_aug2013', 'Sampling and Identification of Marine Zooplankton - August 2013',
                    description = 'Rachel Carson and Dorado surveys in Northern Monterey Bay',
                    x3dTerrains = {
                            'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                                'position': '-2822317.31255 -4438600.53640 3786150.85474',
                                'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                                'centerOfRotation': '-2711557.94 -4331414.32 3801353.46',
                                'VerticalExaggeration': '10',
                                'speed': '.1',
                            }
                    },
                    grdTerrain = os.path.join(parentDir, 'Monterey25.grd')
                )

# Aboard the Carson use zuma
##cl.tdsBase = 'http://zuma.rc.mbari.org/thredds/'       
cl.tdsBase = 'http://odss.mbari.org/thredds/'       # Use this on shore
cl.dodsBase = cl.tdsBase + 'dodsC/'       

# 2-second decimated dorado data
##cl.dorado_base = cl.dodsBase + 'SIMZ/2013_Aug/dorado/'
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2013/netcdf/'
cl.dorado_files = [ 
                    'Dorado389_2013_224_02_224_02_decim.nc', 'Dorado389_2013_225_00_225_00_decim.nc',
                    'Dorado389_2013_225_01_225_01_decim.nc', 'Dorado389_2013_226_01_226_01_decim.nc',
                    'Dorado389_2013_226_03_226_03_decim.nc', 'Dorado389_2013_227_00_227_00_decim.nc',
                    'Dorado389_2013_227_01_227_01_decim.nc', 'Dorado389_2013_228_00_228_00_decim.nc',
                    'Dorado389_2013_228_01_228_01_decim.nc',
                  ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700', 
                    'fl700_uncorr', 'salinity', 'biolume',
                    'roll', 'pitch', 'yaw',
                    'sepCountList', 'mepCountList' ]

# Spray glider - for just the duration of the campaign
cl.l_662_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_files = ['OS_Glider_L_662_20130711_TS.nc']
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = datetime.datetime(2013, 8, 10)
cl.l_662_endDatetime = datetime.datetime(2013, 8, 17)


# Rachel Carson Underway CTD
cl.rcuctd_base = cl.dodsBase + 'SIMZ/2013_Aug/carson/uctd/'
cl.rcuctd_files = [ 
                    'simz2013plm01.nc', 'simz2013plm02.nc', 'simz2013plm03.nc', 'simz2013plm04.nc',
                    'simz2013plm05.nc',
                  ]
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]

# Rachel Carson Profile CTD
cl.pctdDir = 'SIMZ/2013_Aug/carson/pctd/'
cl.rcpctd_base = cl.dodsBase + cl.pctdDir
cl.rcpctd_files = [ 
                    'simz2013c01.nc', 'simz2013c02.nc', 'simz2013c03.nc', 'simz2013c04.nc',
                    'simz2013c05.nc', 'simz2013c06.nc', 'simz2013c07.nc', 'simz2013c08.nc',
                    'simz2013c09.nc', 'simz2013c10.nc', 'simz2013c11.nc', 'simz2013c12.nc',
                    'simz2013c13.nc', 'simz2013c14.nc', 'simz2013c15.nc', 'simz2013c16.nc',
                    'simz2013c17.nc', 'simz2013c18.nc',
                      ]
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar', 'oxygen' ]

# Mooring M1 Combined file produced by DPforSSDS processing - for just the duration of the campaign
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/201202/'
cl.m1_files = ['OS_M1_20120222hourly_CMSTV.nc']
cl.m1_parms = [ 'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR', 
                     'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR', 
                     'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR'
                   ]
cl.m1_startDatetime = datetime.datetime(2013, 8, 12)
cl.m1_endDatetime = datetime.datetime(2013, 8, 19)
cl.m1_nominaldepth = 0.0

# SubSample data files received from Julio in email and copied to local directory
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'SIMZAug2013')
cl.subsample_csv_files = [
                            '2013_Aug_SIMZ_Niskin_microscopy_STOQS.csv',
                            '2013_SIMZ_AUV_STOQS.csv',
                            '2013_SIMZ_Niskins_STOQS.csv',
                            '2013_SIMZ_TowNets_STOQS.csv',
                            'SIMZ_2013_PPump_STOQS_tidy_v2.csv',
                         ]

# Produce parent samples file with (will need to 'mkdir stoqs/loaders/MolecularEcology/SIMZAug2013' on a fresh system):
# cd stoqs/loaders/MolecularEcology/SIMZAug2013
# gunzip 2013_SIMZ_TowNets_STOQS.csv.gz
# ../../nettow.py --database stoqs_simz_aug2013 --subsampleFile 2013_SIMZ_TowNets_STOQS.csv --csvFile 2013_SIMZ_TowNet_ParentSamples.csv -v
cl.parent_nettow_file = '2013_SIMZ_TowNet_ParentSamples.csv'
# gunzip SIMZ_2013_PPump_STOQS_tidy_v2.csv.gz
# ../../planktonpump.py --database stoqs_simz_aug2013 --subsampleFile SIMZ_2013_PPump_STOQS_tidy_v2.csv --csv_file 2013_SIMZ_PlanktonPump_ParentSamples.csv -v
cl.parent_planktonpump_file = '2013_SIMZ_PlanktonPump_ParentSamples.csv'


# Execute the load
cl.process_command_line()

if cl.args.test:
    ##cl.loadL_662(stride=100)
    cl.loadDorado(stride=100)
    cl.loadRCuctd(stride=10)
    cl.loadRCpctd(stride=10)
    cl.loadM1(stride=1)
    cl.loadParentNetTowSamples()
    cl.loadParentPlanktonPumpSamples(duration=10)
    cl.loadSubSamples()

elif cl.args.optimal_stride:
    ##cl.loadL_662(stride=1)
    cl.loadDorado(stride=1)
    cl.loadRCuctd(stride=1)
    cl.loadRCpctd(stride=1)
    cl.loadM1(stride=1)
    cl.loadParentNetTowSamples()
    cl.loadParentPlanktonPumpSamples(duration=10)
    cl.loadSubSamples()

else:
    cl.stride = cl.args.stride
    ##cl.loadL_662()
    cl.loadDorado()
    cl.loadRCuctd()
    cl.loadRCpctd()
    cl.loadM1()
    cl.loadParentNetTowSamples()
    cl.loadParentPlanktonPumpSamples(duration=10)
    cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

