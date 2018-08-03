#!/usr/bin/env python
__author__    = 'Duane Edgington'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'duane at mbari.org'

__doc__ = '''

Master loader for all CANON activities in September 2011 and beyound

Mike McCann and Duane Edgington and Reiko
MBARI 15 August 2013

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime  # needed for glider data
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)

# the next line makes it possible to find CANON
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # settings.py is one dir up

from CANON import CANONLoader
import timing

# building input data sources object
cl = CANONLoader('stoqs_september2011', 'CANON - September 2011')

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'


# special location for dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2011/netcdf/'
cl.dorado_files = [  'Dorado389_2011_249_00_249_00_decim.nc',
                     'Dorado389_2011_250_01_250_01_decim.nc',
                     'Dorado389_2011_255_00_255_00_decim.nc',
                     'Dorado389_2011_257_00_257_00_decim.nc',
                     'Dorado389_2011_262_00_262_00_decim.nc',
                     'Dorado389_2011_263_00_263_00_decim.nc',
                     'Dorado389_2011_264_00_264_00_decim.nc',
                     'Dorado389_2011_285_01_285_01_decim.nc',
                     'Dorado389_2011_286_00_286_00_decim.nc',
                                                             ]



# special location for spray glider data
# Spray glider - for just the duration of the campaign
cl.l_662_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_files = ['OS_Glider_L_662_20110915_TS.nc',
                                                    ]

cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = datetime.datetime(2011, 9, 15)
cl.l_662_endDatetime = datetime.datetime(2011, 9, 30)



######################################################################
#  WESTERN FLYER
######################################################################

cl.wfuctd_base = cl.dodsBase + 'CANON_september2011/wf/uctd/'
cl.wfuctd_files = [
                    '24211WF01.nc', '27211WF01.nc', '27411WF01.nc', '27511WF01.nc', '27711WF01.nc', 
                    '27811WF01.nc', '27911wf01.nc', '28011wf01.nc', '28111wf01.nc', '28211wf01.nc',
                  ]
cl.wfuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]

cl.pctdDir = 'CANON_september2011/wf/pctd/'
cl.wfpctd_base = cl.dodsBase + cl.pctdDir
cl.wfpctd_files = [
    'canon11c01.nc', 'canon11c02.nc', 'canon11c03.nc', 'canon11c04.nc', 'canon11c05.nc', 'canon11c06.nc', 'canon11c07.nc',
    'canon11c08.nc', 'canon11c09.nc', 'canon11c10.nc', 'canon11c11.nc', 'canon11c12.nc', 'canon11c13_A.nc', 'canon11c13_B.nc', 'canon11c14.nc',
    'canon11c16.nc', 'canon11c17.nc', 'canon11c19_A.nc', 'canon11c20.nc', 'canon11c22.nc', 'canon11c23.nc', 'canon11c24.nc', 'canon11c25.nc',
    'canon11c26.nc', 'canon11c27.nc', 'canon11c28.nc', 'canon11c29.nc', 'canon11c30.nc', 'canon11c31.nc', 'canon11c32.nc', 'canon11c33.nc',
    'canon11c34.nc', 'canon11c35.nc', 'canon11c36.nc', 'canon11c37.nc', 'canon11c38.nc', 'canon11c39.nc', 'canon11c40.nc', 'canon11c41.nc',
    'canon11c42.nc', 'canon11c43.nc', 'canon11c44.nc', 'canon11c45.nc', 'canon11c46.nc', 'canon11c48.nc', 'canon11c49.nc', 'canon11c50.nc',
    'canon11c51.nc', 'canon11c52.nc', 'canon11c53.nc', 'canon11c54.nc', 'canon11c55.nc', 'canon11c56.nc', 'canon11c57.nc', 'canon11c58.nc',
    'canon11c59.nc', 'canon11c60.nc', 'canon11c61.nc', 'canon11c62.nc', 'canon11c63.nc', 'canon11c64.nc', 'canon11c65.nc', 'canon11c66.nc',
    'canon11c67.nc', 'canon11c68.nc', 'canon11c69.nc', 'canon11c70.nc', 'canon11c71.nc', 'canon11c72.nc', 'canon11c73.nc', 'canon11c74.nc',
    'canon11c75.nc', 'canon11c76.nc', 'canon11c77.nc', 'canon11c78.nc', 'canon11c79.nc', 'canon11c80.nc', 'canon11c81.nc', 'canon11c82.nc' ]
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl' , 'oxygen']



# Liquid Robotics Waveglider
# added to test functionality
cl.waveglider_base = cl.dodsBase + 'CANON_september2012/waveglider/'
cl.waveglider_files = [ 'waveglider_gpctd_WG.nc' ]
cl.waveglider_parms = [ 'TEMP', 'PSAL', 'oxygen' ]
cl.waveglider_startDatetime = datetime.datetime(2012, 8, 31, 18, 47, 0)
cl.waveglider_endDatetime = datetime.datetime(2012, 9, 25, 16, 0, 0)

# Western Flyer Profile CTD
# added to test functionality
cl.pctdDir = 'CANON_september2012/wf/pctd/'
cl.wfpctd_base = cl.dodsBase + cl.pctdDir
cl.wfpctd_files = [
'c0912c01up.nc',
'c0912c01.nc',
'c0912c02.nc',
'c0912c03.nc', 'c0912c04.nc', 'c0912c05.nc', 'c0912c06.nc',
'c0912c07.nc', 'c0912c08.nc', 'c0912c09.nc', 'c0912c10.nc', 'c0912c11.nc', 'c0912c12.nc',
'c0912c13.nc', 'c0912c14.nc', 'c0912c15.nc', 'c0912c16.nc', 'c0912c17.nc', 'c0912c18.nc',
'c0912c19.nc', 'c0912c20.nc', 'c0912c21.nc', 'c0912c22.nc', 'c0912c23.nc', 'c0912c24.nc',
'c0912c25.nc', 'c0912c26.nc', 'c0912c27.nc', 'c0912c28.nc', 'c0912c29.nc', 'c0912c30.nc',
'c0912c31.nc', 'c0912c32.nc', 'c0912c33.nc', 'c0912c34.nc', 'c0912c35.nc', 'c0912c36.nc',
'c0912c37.nc', 'c0912c38.nc', 'c0912c39.nc', 'c0912c40.nc', 'c0912c41.nc', 'c0912c42.nc',
'c0912c43.nc', 'c0912c44.nc', 'c0912c45.nc', 'c0912c46.nc', 'c0912c47.nc', 'c0912c48.nc',
'c0912c49.nc', 'c0912c50.nc', 'c0912c51.nc', 'c0912c52.nc', 'c0912c53.nc', 'c0912c54.nc',
                      ]
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl' ]
#cl.wfpctd_parms = [ 'oxygen' ] we were able to load oxygen for 'c0912c03.nc'


# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadDorado(stride=100)
    cl.loadL_662(stride=100) # done
#    cl.loadWFuctd(stride=10) # done
#    cl.loadWaveglider(stride=100)
    ##cl.loadDaphne(stride=10)
    ##cl.loadTethys(stride=10)
    ##cl.loadESPdrift(stride=10)
#    cl.loadWFpctd(stride=1)
    ##cl.loadM1ts(stride=1)
    ##cl.loadM1met(stride=1)

elif cl.args.optimal_stride:
    cl.loadDorado(stride=2)
    cl.loadL_662(stride=1)
#    cl.loadWFuctd(stride=1)

else:
    cl.loadDorado(stride=cl.args.stride)
    cl.loadL_662()
#    cl.loadWFuctd()
