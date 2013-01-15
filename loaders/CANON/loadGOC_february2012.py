#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2012'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for all February 2012 WF GOC activities.  

The default is to load data with a stride of 100 into a database named stoqs_february2012_s100.

Execute with "./loadGOC_february2012.py 1 stoqs_february2012" to load full resolution data.

Mike McCann
MBARI 14 January 2012

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

try:
    stride = int(sys.argv[1])
except IndexError:
    stride = 100
try:
    dbAlias = sys.argv[2]
except IndexError:
    dbAlias = 'stoqs_february2012_s100'


# ------------------------------------------------------------------------------------
# Data loads for all the activities, LRAUV have real-time files before full-resolution
# ------------------------------------------------------------------------------------
cl = CANONLoader(dbAlias, 'GOC - February 2012')

cl.dodsBase = 'http://odss.mbari.org:8080/thredds/dodsC/' 
cl.tdsBase = 'http://odss.mbari.org:8080/thredds/'      

# Western Flyer Underway CTD
cl.wfuctd_base = cl.dodsBase + 'GOC_february2012/wf/uctd/'
cl.wfuctd_files = [ 
                        'wf_uctd.nc',
                      ]
cl.wfuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]

# Western Flyer Profile CTD
cl.pctdDir = 'GOC_february2012/wf/pctd/'
cl.wfpctd_base = cl.dodsBase + cl.pctdDir
cl.wfpctd_files = [ 
'GOC12c01.nc', 'GOC12c02.nc', 'GOC12c03.nc', 'GOC12c04.nc', 'GOC12c05.nc', 'GOC12c06.nc', 
'GOC12c07.nc', 'GOC12c08.nc', 'GOC12c09.nc', 'GOC12c10.nc', 'GOC12c11.nc', 'GOC12c12.nc', 
'GOC12c13.nc', 'GOC12c14.nc', 'GOC12c15.nc', 'GOC12c16.nc', 'GOC12c17.nc', 'GOC12c18.nc', 
'GOC12c19.nc', 'GOC12c20.nc', 'GOC12c21.nc', 'GOC12c22.nc', 'GOC12c23.nc', 'GOC12c24.nc', 
'GOC12c25.nc', 'GOC12c26.nc', 'GOC12c27.nc', 'GOC12c28.nc', 'GOC12c29.nc', 'GOC12c30.nc', 
'GOC12c31.nc', 'GOC12c32.nc', 'GOC12c33.nc', 'GOC12c34.nc', 'GOC12c35.nc', 'GOC12c36.nc', 
'GOC12c37.nc', 'GOC12c38.nc', 'GOC12c39.nc', 'GOC12c40.nc', 'GOC12c41.nc'
                      ]
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl' ]


cl.stride = stride
##cl.loadAll()

# For testing.  Comment out the loadAll() call, and uncomment one of these as needed
cl.loadWFuctd()
##cl.loadWFpctd()

