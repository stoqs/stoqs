#!/usr/bin/env python
__author__    = 'Mike McCann,Duane Edgington,Reiko Michisaki'
__copyright__ = '2014'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Real-time data loader for NPS29 Glider data for Fall 2014 CANON campaign

Mike McCann
MBARI 1 October 2014

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime
import time

parentDir = os.path.join(os.path.dirname(__file__), "../../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader

cl = CANONLoader('stoqs_september2014', 'CANON-ECOHAB - September 2014',
                    description = 'Fall 2014 Dye Release Experiment in Monterey Bay',
                    x3dTerrains = {
                                    'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                                        'position': '-2822317.31255 -4438600.53640 3786150.85474',
                                        'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                                        'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                                        'VerticalExaggeration': '10',
                                        'speed': '1',
                                    }
                    },
                    grdTerrain = os.path.join(parentDir, 'Monterey25.grd')
                  )

# Set beginning start and end dates for this campaign - if this script is to be run regularly from cron to add new
# data to STOQS then use the --append option to append new data.  Do not change these values.
startdate = datetime.datetime(2014, 9, 1)
enddate  = datetime.datetime(2014, 10, 12)

# NPS_29
cl.nps29_base = 'http://www.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.nps29_files = [ 'OS_Glider_NPS_G29_20140930_TS.nc' ]
cl.nps29_parms = ['TEMP', 'PSAL', 'RHOD']
cl.nps29_startDatetime = startdate
cl.nps29_endDatetime = enddate

cl.process_command_line()

if cl.args.test:
    cl.load_NPS29(stride=10)

elif cl.args.optimal_stride:
    cl.load_NPS29(stride=2)

else:
    cl.load_NPS29()

