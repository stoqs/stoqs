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
sys.path.insert(0, parent_dir)  # So that CCE & DAPLoaders are found

from argparse import Namespace
from CCE.loadCCE_2015 import CCE_2015_Campaign
from load import Loader

class Campaigns():
    pass

# Reuse CCELoader and Loader code to create our test db and load a
# small amount of data for testing of the loading code
db_alias = 'stoqs_load_test'
campaign_name = 'Loading test database'
campaign = CCE_2015_Campaign(db_alias, campaign_name)
loader = Loader()

campaigns = Campaigns()
loader.args = Namespace()
loader.args.test = False
loader.args.clobber = True
loader.args.db = db_alias
loader.args.drop_indexes = False

campaigns.campaigns = {db_alias: 'CCE/loadCCE_2015.py'}
loader.load(campaigns, create_only=True)

# Load only the March 2016 event lores Mooring data
campaign.lores_event_times = [campaign.lores_event_times[1]]
campaign.hires_event_times = []
campaign.load_cce_moorings(start_mooring=2, end_mooring=3)

# Load WaveGlider Trajectory data for the same event time period


print("All Done.")

