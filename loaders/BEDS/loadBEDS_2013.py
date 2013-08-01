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
##cl.bed_files = ['BED%05d.nc' % i for i in range(1,234)]
cl.bed_files = ['BED00001.nc', 'BED00002.nc', 'BED00003.nc', 'BED00005.nc',
                'BED00006.nc', 'BED00008.nc', 'BED00014.nc', 'BED00015.nc',
                'BED00017.nc', 'BED00018.nc', 'BED00020.nc', 'BED00026.nc',
                'BED00038.nc', 'BED00039.nc', 'BED00040.nc', 'BED00041.nc',
                'BED00042.nc', 'BED00043.nc', 'BED00044.nc', 'BED00046.nc',
                'BED00047.nc', 'BED00048.nc', 'BED00049.nc', 'BED00062.nc',
                'BED00082.nc', 'BED00083.nc', 'BED00084.nc', 'BED00085.nc',
                'BED00086.nc', 'BED00087.nc', 'BED00088.nc', 'BED00089.nc',
                'BED00090.nc', 'BED00092.nc', 'BED00093.nc', 'BED00094.nc',
                'BED00095.nc', 'BED00096.nc', 'BED00097.nc', 'BED00098.nc',
                'BED00100.nc', 'BED00101.nc', 'BED00102.nc', 'BED00103.nc',
                'BED00104.nc', 'BED00106.nc', 'BED00107.nc', 'BED00108.nc',
                'BED00109.nc', 'BED00110.nc', 'BED00111.nc', 'BED00112.nc',
                'BED00113.nc', 'BED00114.nc', 'BED00115.nc', 'BED00116.nc',
                'BED00117.nc', 'BED00118.nc', 'BED00123.nc', 'BED00124.nc',
                'BED00125.nc', 'BED00126.nc', 'BED00127.nc', 'BED00129.nc',
                'BED00130.nc', 'BED00131.nc', 'BED00132.nc', 'BED00133.nc',
                'BED00136.nc', 'BED00137.nc', 'BED00138.nc', 'BED00139.nc',
                'BED00142.nc', 'BED00143.nc', 'BED00144.nc', 'BED00146.nc',
                'BED00148.nc', 'BED00149.nc', 'BED00151.nc', 'BED00152.nc',
                'BED00154.nc', 'BED00155.nc', 'BED00156.nc', 'BED00157.nc',
                'BED00158.nc', 'BED00159.nc', 'BED00160.nc', 'BED00161.nc',
                'BED00162.nc', 'BED00163.nc', 'BED00164.nc', 'BED00166.nc',
                'BED00167.nc', 'BED00169.nc', 'BED00170.nc', 'BED00172.nc',
                'BED00173.nc', 'BED00174.nc', 'BED00175.nc', 'BED00176.nc',
                'BED00177.nc', 'BED00178.nc', 'BED00179.nc', 'BED00180.nc',
                'BED00181.nc', 'BED00182.nc', 'BED00183.nc', 'BED00185.nc',
                'BED00186.nc', 'BED00197.nc', 'BED00198.nc', 'BED00200.nc',
                'BED00203.nc', 'BED00204.nc', 'BED00205.nc', 'BED00206.nc',
                'BED00207.nc', 'BED00211.nc', 'BED00212.nc', 'BED00213.nc',
                'BED00214.nc', 'BED00215.nc', 'BED00216.nc', 'BED00217.nc',
                'BED00218.nc', 'BED00219.nc', 'BED00220.nc', 'BED00221.nc',
                'BED00222.nc', 'BED00223.nc', 'BED00224.nc', 'BED00227.nc',
                'BED00229.nc', 'BED00230.nc', 'BED00231.nc']

##cl.bed_parms = ['XA', 'XR', 'PRESS', 'BED_DEPTH']
cl.bed_parms = ['XA', 'YA', 'ZA', 'XR', 'YR', 'ZR', 'PRESS', 'BED_DEPTH']

cl.stride = stride

cl.loadBEDS()

