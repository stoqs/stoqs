#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Loader for IOOS Glider DAC

Mike McCann
MBARI 14 April 2014

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))      # So that IOOS is found

from IOOS import IOOSLoader

il = IOOSLoader('stoqs_ioos_gliders', 'IOOS Gliders', 
                                x3dTerrains = {
                                    'http://dods.mbari.org/terrain/x3d/Globe_1m_bath_10x/Globe_1m_bath_10x_scene.x3d': {
                                        'position': '14051448.48336 -15407886.51486 6184041.22775',
                                        'orientation': '0.83940 0.33030 0.43164 1.44880',
                                        'centerOfRotation': '0 0 0',
                                        'VerticalExaggeration': '10',
                                    }
                                }
)

##startDatetime = datetime.datetime(2013, 2, 18)
##endDatetime = datetime.datetime(2013, 7, 18)
startDatetime = None
endDatetime = None

# TODO: Use beautiful soup to scrape the TDS html for .ncml files to load

# Spray glider - for just the duration of the campaign
# http://tds.gliders.ioos.us/thredds/dodsC/Rutgers-University_ru29-20130111T0724_Time.ncml
il.glider_ctd_base = 'http://tds.gliders.ioos.us/thredds/dodsC/'
il.glider_ctd_files = ['Rutgers-University_ru29-20130111T0724_Time.ncml']
# http://tds.gliders.ioos.us/thredds/dodsC/Rutgers-University_ru29-20130111T0724_Files/ru29-20130129T013229_rt0.nc
##il.glider_ctd_base = 'http://tds.gliders.ioos.us/thredds/dodsC/Rutgers-University_ru29-20130111T0724_Files/'
##il.glider_ctd_files = ['ru29-20130129T013229_rt0.nc']
il.glider_ctd_parms = ['temperature', 'salinity', 'density']
il.glider_ctd_startDatetime = startDatetime
il.glider_ctd_endDatetime = endDatetime


# Execute the load
il.process_command_line()

if il.args.test:
##    il.load_glider_ctd(stride=100)
    pass

elif il.args.optimal_stride:
    il.load_glider_ctd(stride=1)

else:
    il.stride = il.args.stride
    il.load_glider_ctd()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
il.addTerrainResources()

print "All Done."

