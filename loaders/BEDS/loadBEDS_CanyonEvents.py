#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for all BEDS Canyon Event data.

Mike McCann
MBARI 29 March 2014

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
parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # settings.py is one dir up

from BEDS import BEDSLoader

bl = BEDSLoader('stoqs_beds_canyon_events', 'BEDS - Canyon Events',
                                description = 'Benthic Event Detector data for significant events in Monterey Canyon',
                                x3dTerrains = { 
                                    'http://dods.mbari.org/terrain/x3d/MontereyCanyonBeds_1m+5m_1x_GeoOrigin_-121_36_0/MontereyCanyonBeds_1m+5m_1x_GeoOrigin_-121_36_0_scene.x3d': {
                                        'position': '-44571.54862 77379.85721 71401.38520',
                                        'orientation': '0.92328 -0.26229 -0.28063 1.50408',
                                        'centerOfRotation': '-39420.23433350699 85753.45910644953 70752.14499748436',
                                        'geoOrigin': '-121 36 0',
                                        'VerticalExaggeration': '1',
                                        'speed': '0.1',
                                        'zNear': '1.0',
                                    },
                                    'http://dods.mbari.org/terrain/x3d/MontereyCanyonBeds_1m+5m_1x/MontereyCanyonBeds_1m+5m_1x_scene.x3d': {
                                        'position': '-44571.54862 77379.85721 71401.38520',
                                        'orientation': '0.92328 -0.26229 -0.28063 1.50408',
                                        'centerOfRotation': '-39420.23433350699 85753.45910644953 70752.14499748436',
                                        'VerticalExaggeration': '1',
                                        'speed': '0.1',
                                    },
                                    ##'/stoqs/static/x3d/Monterey25/Monterey25_10x-pop.x3d': {
                                    ##    'position': '-2822317.31255 -4438600.53640 3786150.85474',
                                    ##    'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                                    ##    'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                                    ##    'VerticalExaggeration': '10',
                                    ##}
                                 },
                                 # Do not check in .grd files to the repository, keep them in the loaders directory
                                 grdTerrain=os.path.join(parentDir, 'MontereyCanyonBeds_1m+5m.grd'),

               )

# Base OPeNDAP server
bl.tdsBase = 'http://odss-test.shore.mbari.org/thredds/'
bl.dodsBase = bl.tdsBase + 'dodsC/'       

# Files created by bed2netcdf.py from the BEDS SVN BEDS repository
bl.bed_base = bl.dodsBase + 'BEDS/'
# Copied from ProjectLibrary to Hyrax server on elvis with:
#   rsync -r /mbari/ProjectLibrary/901006.BEDS/BEDS.Data/CanyonEvents /var/www/dods_html/data/beds
bl.bed_base = 'http://elvis.shore.mbari.org/opendap/hyrax/data/beds/CanyonEvents/20130601/BED1/netcdf/'
##bl.bed_parms = ['XA', 'YA', 'ZA', 'A', 'XR', 'YR', 'ZR', 'MX', 'MY', 'MZ', 'ROT', 'PRESS', 'BED_DEPTH']   # For timeSeries
##bl.bed_parms = ['XA', 'YA', 'ZA', 'A', 'XR', 'YR', 'ZR', 'MX', 'MY', 'MZ', 'ROT']
bl.bed_parms = ['XA', 'YA', 'ZA', 'A', 'XR', 'YR', 'ZR', 'ROT', 'ROTRATE']

bl.bed_files = ['BED01_1_June_2013.nc',
##                'bed03/30100046_partial_decimated10.nc',
               ]
bl.bed_platforms = [ 'BED01',
##                     'BED03',
                   ]

bl.bed_depths = [ 303,
##
                ]

# Execute the load
bl.process_command_line()

if bl.args.test:
    bl.loadBEDS(stride=100, featureType='trajectory')

elif bl.args.optimal_stride:
    bl.loadBEDS(stride=1, featureType='trajectory')

else:
    bl.stride = bl.args.stride
    bl.loadBEDS(featureType='trajectory')

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
bl.addTerrainResources()

print "All Done."

