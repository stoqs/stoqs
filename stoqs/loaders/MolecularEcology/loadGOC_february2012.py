#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2012'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''
Master loader for all February 2012 WF GOC activities.  

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

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found


from CANON import CANONLoader
from SampleLoaders import SubSamplesLoader
import timing

cl = CANONLoader('stoqs_february2012', 'GOC - February 2012',
                        description = 'Western Flyer profile and underway CTD data from Monterey to Gulf of California with Sample data from BOG',
                        x3dTerrains = {
                            'https://stoqs.mbari.org/x3d/Globe_1m_bath_10x/Globe_1m_bath_10x_scene.x3d': {
                                'position': '14051448.48336 -15407886.51486 6184041.22775',
                                'orientation': '0.83940 0.33030 0.43164 1.44880',
                                'centerOfRotation': '0 0 0',
                                'VerticalExaggeration': '10',
                            }
                        },
                        grdTerrain = os.path.join(parentDir, 'Globe_1m_bath.grd')
                )


# Base OPenDAP server - if aboard a ship change to the local odss server
cl.tdsBase = 'http://odss.mbari.org/thredds/'      
cl.dodsBase = cl.tdsBase + 'dodsC/' 

# Western Flyer Underway CTD
cl.wfuctd_base = cl.dodsBase + 'GOC_february2012/wf/uctd/'
cl.wfuctd_files = [ 
			        'goc12m01.nc',
			        'goc12m02.nc',
			        'goc12m03.nc',
			        'goc12m04.nc',
			        'goc12m05.nc',
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

# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/GOC12/ copied to local GOC12 dir
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data')
cl.subsample_csv_files = [
                            'STOQS_GOC12_CHL_1U.csv',
                            'STOQS_GOC12_CHL_5U.csv',
                            'STOQS_GOC12_NH4.csv',
                            'STOQS_GOC12_NO2.csv',
                            'STOQS_GOC12_NO3.csv',
                            'STOQS_GOC12_O2.csv',
                            'STOQS_GOC12_PHAEO_1U.csv',
                            'STOQS_GOC12_PHAEO_5U.csv',
                            'STOQS_GOC12_PHAEO_GFF.csv',
                            'STOQS_GOC12_PO4.csv',
                            'STOQS_GOC12_SIO4.csv',
                         ]


# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadWFuctd(stride=10)
    cl.loadWFpctd(stride=1)
    cl.loadSubSamples()

elif cl.args.optimal_stride:
    # Override default platformNames with same name if underway and profile are wished to be visualized together in stoqs ui
    ##cl.loadWFuctd(platformName='wf_ctd', activitytypeName='Western Flyer CTD Data', stride=1)
    ##cl.loadWFpctd(platformName='wf_ctd', activitytypeName='Western Flyer CTD Data', stride=1)
    cl.loadWFuctd(stride=10)
    cl.loadWFpctd(stride=1)
    cl.loadSubSamples()

else:
    cl.stride = cl.args.stride
    # Override default platformNames with same name if underway and profile are wished to be visualized together in stoqs ui
    ##cl.loadWFuctd(platformName='wf_ctd', activitytypeName='Western Flyer CTD Data')
    ##cl.loadWFpctd(platformName='wf_ctd', activitytypeName='Western Flyer CTD Data')
    cl.loadWFuctd()
    cl.loadWFpctd()
    cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

