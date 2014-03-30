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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # settings.py is one dir up

from BEDS import BEDSLoader

bl = BEDSLoader('stoqs_beds_canyon_events', 'BEDS - Canyon Events', 
                                x3dTerrains= { 
                                    'http://dods.mbari.org/terrain/x3d/MontereyCanyonBeds_1m+5m_1x/MontereyCanyonBeds_1m+5m_1x.x3d': {
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

# Files created by bed2netcdf.py from the BEDS SVN BEDS repository
bl.bed_base = bl.dodsBase + 'BEDS/'
bl.bed_files = [
                'bed01/BED00038.nc', 'bed01/BED00039.nc',
                'bed03/30100046_partial_decimated10.nc',
               ]

bl.bed_parms = ['XA', 'YA', 'ZA', 'XR', 'YR', 'ZR', 'ROT', 'A', 'PRESS', 'BED_DEPTH']


# Execute the load
bl.process_command_line()

if bl.args.test:
    bl.bed_files = [ 'bed01/BED00038.nc', 'bed01/BED00039.nc', ]
    ##bl.loadBEDS(pName='BED01', stride=1000)
    bl.bed_files = [ 'bed03/30100046_partial_decimated10.nc', ]
    bl.loadBEDS(pName='BED03', stride=10)

elif bl.args.optimal_stride:
    bl.loadBEDS(stride=1)

else:
    bl.stride = bl.args.stride
    bl.loadBEDS()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
bl.addTerrainResources()
##bl.addPlaybackResources()

print "All Done."

