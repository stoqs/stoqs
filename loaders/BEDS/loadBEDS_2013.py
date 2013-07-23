#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for all BEDS deployments.

The default is to load data with a stride of 1 into a database named stoqs_beds2013.

Execute with "./loadBEDS_2013.py 10 stoqs_beds2013" to load with a stride of 10.

Mike McCann
MBARI 13 May 2013

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

from BEDS import BEDSLoader

try:
    stride = int(sys.argv[1])
except IndexError:
    stride = 1
try:
    dbAlias = sys.argv[2]
except IndexError:
    dbAlias = 'stoqs_beds2013'


# ------------------------------------------------------------------------------------
# Data loads for all the activities, LRAUV have real-time files before full-resolution
# ------------------------------------------------------------------------------------
campaignName = 'BEDS - 2013'
if stride != 1:
    campaignName = campaignName + ' with stride=%d' % stride
cl = BEDSLoader(dbAlias, campaignName)

cl.tdsBase = 'http://odss-test.shore.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'       

# Files created by bed2nc.py from the BEDS SVN BEDS repository
cl.bed_base = cl.dodsBase + 'BEDS_2013/beds01/'
cl.bed_files = [ 
                    'BED00039.nc',
                  ]
##cl.bed_parms = ['XA', 'XR', 'PRESS', 'BED_DEPTH']
cl.bed_parms = ['XA', 'YA', 'ZA', 'XR', 'YR', 'ZR', 'PRESS', 'BED_DEPTH']

cl.stride = stride

cl.loadBEDS()

