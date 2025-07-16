#!/usr/bin/env python

'''
Tests special case data loaders, e.g.:
- Non-GridType Trajectory data: http://dods.mbari.org/opendap/data/waveglider/deployment_data/wgTiny/20160315/SV3_20160315.nc
- EPIC data from CCE Campaign: From file stoqs/loaders/CCE/loadCCE_2015.py

Mike McCann
MBARI 24 October 2017
'''

import os
import sys
parent_dir = os.path.join(os.path.dirname(__file__), "../../loaders")
sys.path.insert(0, parent_dir)  # So that CCE & DAPloaders are found

from argparse import Namespace
from datetime import datetime
from load import Loader
from CCE.loadCCE_2015 import CCE_2015_Campaign
from DAPloaders import runGliderLoader, runLrauvLoader

class Campaigns():
    pass

# Reuse CCELoader and Loader code to create our test db and load a
# small amount of data for testing of the loading code
db_alias = 'stoqs'
campaign_name = 'Loading test database'
campaign_description = 'Test database for all kinds of data: EPIC from CCE, Glider, LRAUV, etc.'
campaign = CCE_2015_Campaign(db_alias, campaign_name)
loader = Loader()

campaigns = Campaigns()
loader.args = Namespace()
loader.args.test = False
loader.args.clobber = True
loader.args.db = db_alias
loader.args.drop_indexes = False
loader.args.noinput = False
loader.args.restore = False

campaigns.campaigns = {db_alias: 'CCE/loadCCE_2015.py'}
try:
    loader._dropdb(db_alias)
except KeyError:
    pass
loader.load(campaigns, create_only=True)

# Load only the March 2016 event lores Mooring data for ms2
campaign.hires_event_times = []
campaign.lores_event_times = [campaign.lores_event_times[1]]
campaign.cl.ccems2_start_datetime, campaign.cl.ccems2_end_datetime = campaign.lores_event_times[0]
campaign.load_ccemoorings(stride=500, start_mooring=2, end_mooring=2)
campaign.load_ccemoorings_ev(low_res_stride=500, start_mooring=2, end_mooring=2)

# Add Trajectory data for the same time period
l_662_url = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line67/OS_Glider_L_662_20151124_TS.nc'
l_662_parms = ['TEMP', 'PSAL', 'FLU2']
runGliderLoader(l_662_url, campaign_name, '', '/'.join(l_662_url.split('/')[-1:]),
                'SPRAY_L66a_Glider', '38978f', 'glider', 'Glider Mission',
                l_662_parms, db_alias, 10, campaign.lores_event_times[0][0], 
                campaign.lores_event_times[0][1])


# Add Glider Trajectory data for a time period when we have LRAUV oxygen data
l_662_url = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line67/OS_Glider_L_662_20180816_TS.nc'
l_662_parms = ['TEMP', 'PSAL', 'FLU2', 'oxygen']
oxygen_start = datetime(2018, 9, 4, 22, 22, 0)
oxygen_end = datetime(2018, 9, 5, 1, 58, 0)
runGliderLoader(l_662_url, campaign_name, '', '/'.join(l_662_url.split('/')[-1:]),
                'SPRAY_L66a_Glider', '38978f', 'glider', 'Glider Mission',
                l_662_parms, db_alias, 1, oxygen_start, oxygen_end)

# Load Daphne data to test for same Parameter name (oxygen from l_662) having different units
url = 'http://dods.mbari.org/opendap/data/lrauv/daphne/missionlogs/2018/20180904_20180911/20180904T210211/201809042102_201809050138_10S_sci.nc'
parameters = ['temperature', 'salinity', 'chlorophyll', 'nitrate', 'oxygen',
              'bbp470', 'bbp650','PAR', 'yaw', 'pitch', 'roll', ]
runLrauvLoader(url, campaign_name, campaign_description, url.rsplit('/', 1)[-1],
               'daphne', 'feb24c', 'auv', 'AUV mission',
               parameters, db_alias, stride=1, plotTimeSeriesDepth=0,
               startDatetime=oxygen_start, endDatetime=oxygen_end)

print("All Done.")

