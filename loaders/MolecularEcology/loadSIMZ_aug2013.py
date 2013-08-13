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
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # settings.py is one dir up

from CANON import CANONLoader

cl = CANONLoader('stoqs_simz_aug2013', 'Sampling and Identification of Marine Zooplankton - August 2013')

# Aboard the Carson use zuma
cl.tdsBase = 'http://zuma.rc.mbari.org/thredds/'       
##cl.tdsBase = 'http://odss.mbari.org/thredds/'       # Use this on shore
cl.dodsBase = cl.tdsBase + 'dodsC/'       

# 2-second decimated dorado data
cl.dorado_base = cl.dodsBase + 'SIMZ_august2013/dorado/'
cl.dorado_files = [ 
                    'Dorado389_2013_224_02_224_02_decim.nc',
                  ]

# Spray glider - for just the duration of the campaign
cl.l_662_base = 'http://www.cencoos.org/thredds/dodsC/glider/'
cl.l_662_files = ['OS_Glider_L_662_20120816_TS.nc']
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = datetime.datetime(2013, 8, 3)
cl.l_662_endDatetime = datetime.datetime(2013, 8, 17)


# Rachel Carson Underway CTD
cl.rcuctd_base = cl.dodsBase + 'SIMZ_august2013/carson/uctd/'
cl.rcuctd_files = [ 
##                        '07413plm01.nc', 
                      ]
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]

# Rachel Carson Profile CTD
cl.pctdDir = 'SIMZ_august2013/carson/pctd/'
cl.rcpctd_base = cl.dodsBase + cl.pctdDir
cl.rcpctd_files = [ 
##                    '07413c01.nc', 
                      ]
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]


# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.stride = stride
    cl.loadDorado(stride=10)
    cl.loadRCuctd(stride=10)
    cl.loadRCpctd(stride=10)

elif cl.args.optimal_stride:
    cl.loadDorado(stride=1)
    cl.loadRCuctd(stride=1)
    cl.loadRCpctd(stride=1)

else:
    cl.stride = cl.args.stride
    cl.loadDorado()
    cl.loadRCuctd()
    cl.loadRCpctd()

