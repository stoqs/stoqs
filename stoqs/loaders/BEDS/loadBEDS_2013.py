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
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # settings.py is one dir up

from BEDS import BEDSLoader
import timing

bl = BEDSLoader('stoqs_beds2013', 'BEDS - 2013', 
                                x3dTerrains= { 
                                    'https://stoqs.mbari.org/x3d/MontereyCanyonBeds_1m+5m_1x/MontereyCanyonBeds_1m+5m_1x.x3d': {
                                        'position': '-2706054.97556 -4352297.32558 3798919.71875',
                                        'orientation': '0.92863 -0.26237 -0.26231 1.59089',
                                        'centerOfRotation': '-2700040.0076912297 -4342439.858864189 3798898.2847731174',
                                        'VerticalExaggeration': '1',
                                    },
                                    ##'/stoqs/static/x3d/Monterey25/Monterey25_10x-pop.x3d': {
                                    ##    'position': '-2822317.31255 -4438600.53640 3786150.85474',
                                    ##    'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                                    ##    'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                                    ##    'VerticalExaggeration': '10',
                                    ##}
                                 }

)

# Base OPeNDAP server
bl.tdsBase = 'http://odss-test.shore.mbari.org/thredds/'
bl.dodsBase = bl.tdsBase + 'dodsC/'       

# Files created by bed2nc.py from the BEDS SVN BEDS repository
bl.bed_base = bl.dodsBase + 'BEDS_2013/beds01/'
##bl.bed_files = ['BED%05d.nc' % i for i in range(1,234)]
bl.bed_files = ['BED00001.nc', 'BED00002.nc', 'BED00003.nc', 'BED00005.nc',
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

##bl.bed_parms = ['XA', 'XR', 'PRESS', 'BED_DEPTH']
bl.bed_parms = ['XA', 'YA', 'ZA', 'XR', 'YR', 'ZR', 'PRESS', 'BED_DEPTH']


# Execute the load
bl.process_command_line()

if bl.args.test:
    bl.loadBEDS(stride=10)

elif bl.args.optimal_stride:
    bl.loadBEDS(stride=1)

else:
    bl.stride = bl.args.stride
    bl.loadBEDS()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
bl.addTerrainResources()

print("All Done.")

