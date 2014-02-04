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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))      # So that CANON is found

from CANON import CANONLoader

cl = CANONLoader('stoqs_simz_aug2013', 'Sampling and Identification of Marine Zooplankton - August 2013')

# Aboard the Carson use zuma
cl.tdsBase = 'http://zuma.rc.mbari.org/thredds/'       
##cl.tdsBase = 'http://odss.mbari.org/thredds/'       # Use this on shore
cl.dodsBase = cl.tdsBase + 'dodsC/'       

# 2-second decimated dorado data
cl.dorado_base = cl.dodsBase + 'SIMZ_august2013/dorado/'
cl.dorado_files = [ 
                    'Dorado389_2013_224_02_224_02_decim.nc', 'Dorado389_2013_225_00_225_00_decim.nc',
                    'Dorado389_2013_225_01_225_01_decim.nc', 'Dorado389_2013_226_01_226_01_decim.nc',
                    'Dorado389_2013_226_03_226_03_decim.nc', 'Dorado389_2013_227_00_227_00_decim.nc',
                    'Dorado389_2013_227_01_227_01_decim.nc', 'Dorado389_2013_228_00_228_00_decim.nc',
                    'Dorado389_2013_228_01_228_01_decim.nc',
                  ]

# Spray glider - for just the duration of the campaign
cl.l_662_base = 'http://www.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_files = ['OS_Glider_L_662_20130711_TS.nc']
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = datetime.datetime(2013, 8, 10)
cl.l_662_endDatetime = datetime.datetime(2013, 8, 17)


# Rachel Carson Underway CTD
cl.rcuctd_base = cl.dodsBase + 'SIMZ_august2013/carson/uctd/'
cl.rcuctd_files = [ 
                    'simz2013plm01.nc', 'simz2013plm02.nc', 'simz2013plm03.nc', 'simz2013plm04.nc',
                    'simz2013plm05.nc',
                  ]
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]

# Rachel Carson Profile CTD
cl.pctdDir = 'SIMZ_august2013/carson/pctd/'
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

# SubSample data files received from Julio in email and copied to local directory
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'SIMZAug2013')
cl.subsample_csv_files = [
                            '2013_Aug_SIMZ_Niskin_microscopy_STOQS.csv',
                            '2013_SIMZ_AUV_STOQS.csv',
                            '2013_SIMZ_Niskins_STOQS.csv',
                         ]


# Execute the load
cl.process_command_line()

if cl.args.test:
    ##cl.loadL_662(stride=100)
    cl.loadDorado(stride=100)
    cl.loadRCuctd(stride=10)
    cl.loadRCpctd(stride=10)
    cl.loadM1(stride=1)
    cl.loadSubSamples()

elif cl.args.optimal_stride:
    ##cl.loadL_662(stride=1)
    cl.loadDorado(stride=1)
    cl.loadRCuctd(stride=1)
    cl.loadRCpctd(stride=1)
    cl.loadM1(stride=1)
    cl.loadSubSamples()

else:
    cl.stride = cl.args.stride
    ##cl.loadL_662()
    cl.loadDorado()
    cl.loadRCuctd()
    cl.loadRCpctd()
    cl.loadM1()
    cl.loadSubSamples()

