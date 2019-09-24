#!/usr/bin/env python
'''
Master load script intended to be called from cron for
routine loading of all LRUAV data available on a DAP server.

Given a year and month argument in the form YYYYMM this script will:

1. Generated a load script for the stoqs_lrauv_monYYYY campaign
2. Enter a line for it in the lruav_campaigns.py file
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

from make_load_scripts import create_load_scripts, update_lrauv_campaigns

items = create_load_scripts(2017)
update_lrauv_campaigns(items)

#items = create_load_scripts(2018)
#update_lrauv_campaigns(items)

#items = create_load_scripts()
#update_lrauv_campaigns(items)
