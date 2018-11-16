#!/usr/bin/env python
__author__    = 'Danelle Cline'
__copyright__ = '2016'
__license__   = 'GPL v3'
__contact__   = 'dcline at mbari.org'

__doc__ = '''

Master loader for LRAUV Lake Michigan 2016 experiment

Danelle Cline
MBARI 21 July 2016

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime  # needed for glider data
import time      # for startdate, enddate args
import csv
import urllib.request, urllib.error, urllib.parse
import urllib.parse
import requests

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
import timing

cl = CANONLoader('stoqs_michigan2016', 'Lake Michigan LRAUV Experiment 2016',
                    description = 'LRAUV 2016 Experiment in Lake Michigan',
                    x3dTerrains = {
                                    'https://stoqs.mbari.org/x3d/michigan_lld_10x/michigan_lld_10x_src_scene.x3d': {
                                        'position': '277414.36721 -5207201.16684 4373105.96194',
                                        'orientation': '0.99821 -0.05662 0.01901 1.48579',
                                        'centerOfRotation': '281401.0288298179 -4639090.577582279 4354217.4974804',
                                        'VerticalExaggeration': '10',
                                        'speed': '0.1',
                                    }
                    },
                    grdTerrain = os.path.join(parentDir, 'michigan_lld.grd')
                  )

# Set start and end dates for all loads from sources that contain data
# beyond the temporal bounds of the campaign
#
startdate = datetime.datetime(2016, 7, 24)      # Fixed start
enddate = datetime.datetime(2016, 8, 24)        # Fixed end


#####################################################################
#  LRAUV
#####################################################################

# Load netCDF files produced (binned, etc.) by Danelle Cline
# These binned files are created with the makeLRAUVNetCDFs.sh script in the
# toNetCDF directory. You must first edit and run that script once to produce
# the binned files before this will work

# Use defaults in loadLRAUV() calls below


# Execute the load
cl.process_command_line()

if cl.args.test:

    cl.loadLRAUV('tethys', startdate, enddate, stride=100)

else:
    cl.loadLRAUV('tethys', startdate, enddate)

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")


