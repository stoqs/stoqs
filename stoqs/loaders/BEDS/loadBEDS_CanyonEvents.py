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
                                    'http://stoqs.mbari.org/terrain/MontereyCanyonBeds_1m+5m_1x_src/MontereyCanyonBeds_1m+5m_1x_src_scene.x3d': {
                                        'position': '2232.80938 10346.25515 3543.76722',
                                        'orientation': '-0.98394 0.16804 -0.06017 1.25033',
                                        'centerOfRotation': '0 0 0',
                                        'VerticalExaggeration': '1',
                                        'geoOrigin': '36.80, -121.87, -400',
                                        'speed': '1.0',
                                        'zNear': '100.0',
                                        'zFar': '30000.0',
                                    },
                                 },
                                 # Do not check in .grd files to the repository, keep them in the loaders directory
                                 grdTerrain=os.path.join(parentDir, 'MontereyCanyonBeds_1m+5m.grd'),
               )

# Base OPeNDAP server
bl.bed_base = 'http://elvis64.shore.mbari.org/opendap/data/beds/CanyonEvents/20130601/BED1/netcdf/'
# Copied from ProjectLibrary to Hyrax server on elvis with:
#   rsync -r /mbari/ProjectLibrary/901006.BEDS/BEDS.Data/CanyonEvents /var/www/dods_html/data/beds

##bl.bed_parms = ['XA', 'YA', 'ZA', 'A', 'XR', 'YR', 'ZR', 'MX', 'MY', 'MZ', 'ROT', 'PRESS', 'BED_DEPTH']   # For timeSeries
##bl.bed_parms = ['XA', 'YA', 'ZA', 'A', 'XR', 'YR', 'ZR', 'MX', 'MY', 'MZ', 'ROT']
##bl.bed_parms = ['XA', 'YA', 'ZA', 'A', 'XR', 'YR', 'ZR', 'ROT', 'ROTRATE']
bl.bed_parms = ['XA', 'YA', 'ZA', 'A', 'XR', 'YR', 'ZR', 'ROTRATE', 'ROTCOUNT', 'P']

bl.bed_files = ['BED01_1_June_2013.nc',
##                'bed03/30100046_partial_decimated10.nc',
               ]
bl.bed_platforms = [ 'BED01',
##                     'BED03',
                   ]

bl.bed_depths = [ 303,
##
                ]
bl.bed_framegrabs = [ 'http://search.mbari.org/ARCHIVE/frameGrabs/Ventana/stills/2013/vnta3702/01_27_35_21.html' ]

# Execute the load
bl.process_command_line()

if bl.args.test:
    bl.loadBEDS(stride=10, featureType='trajectory')

elif bl.args.optimal_stride:
    bl.loadBEDS(stride=1, featureType='trajectory')

else:
    bl.stride = bl.args.stride
    bl.loadBEDS(featureType='trajectory')

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
bl.addTerrainResources()

print "All Done."

