#!/usr/bin/env python
'''
Master load script intended to be called from cron for
routine loading of all LRUAV data available on a DAP server.

Given a year and month argument in the form YYYYMM this script will:

1. Generated a load script for the stoqs_lrauv_monYYYY campaign
2. Enter a line for it in the mbari_lrauv_campaigns.py file
3. Execute the load
4. Execute the --updateprovenance option
5. Create a pg_dump of the database

This script writes load scripts for month's worth of LRAUV data.
It also enters lines into the lruav_campaigns.py file.

Executing the load is accomplished with another step, e.g.:

   stoqs/loaders/load.py --db stoqs_lrauv_may2019

Mike McCann
MBARI 24 September 2019
'''
import os
import sys
stoqs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.insert(0, stoqs_dir)

from argparse import Namespace
from make_load_scripts import create_load_scripts, update_lrauv_campaigns
from loaders.load import Loader

# 1. Create load scripts and 2. update mbari_lrauv_campaigns.py file
items = create_load_scripts(2018)
update_lrauv_campaigns(items)

# 3. Execute the load for specified month

loader = Loader()
monyyyy = 'sep2018'

loader.args = Namespace(background=False, campaigns='campaigns', clobber=False, db=None, drop_indexes=False, email=None, grant_everyone_select=False, list=False, noinput=False, pg_dump=False, removetest=False, slack=False, test=False, updateprovenance=False, verbose=0)

loader.args.db = (f"stoqs_lrauv_{monyyyy}", )
loader.args.clobber = True
loader.args.verbose = 2

loader.checks()
loader.load()

