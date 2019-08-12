#!/usr/bin/env python
'''
Routine loading of all LRUAV data available on a DAP server
This script writes load scripts for month's worth of LRAUV data.
It also enters lines into the lruav_campaigns.py file.

Executing the load is accomplished with another step, e.g.:

   stoqs/loaders/load.py --db stoqs_lrauv_may2019

Mike McCann
MBARI 3 June 2019
'''
import os
import sys
this_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
stoqs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

import calendar
from datetime import datetime
from string import Template

campaign_template = 'mbari_lrauv_campaigns.template'
campaign_file_name = 'mbari_lrauv_campaigns.py'
campaign_items = ''
script_template = 'load_lrauv.template'

# Construct list of lrauvs with: ls -d /mbari/LRAUV/*/missionlogs | cut -d/ -f4
lrauvs = ('ahi', 'aku', 'brezo', 'daphne', 'galene', 'makai', 'opah', 'pontus', 
          'sim', 'tethys', 'triton', 'whoidhs', )

title_base = 'LRAUV - Routine Operational data'
description_base='MBARI Long Range Autonomous Vehicle data'

for year in range(2019, 2020):
    for month in range(1, 13):
        month_name = datetime(year, month, 1).strftime("%B")
        month_name_short = datetime(year, month, 1).strftime("%b")

        db_alias = f"stoqs_lrauv_{month_name_short.lower()}{year}"
        title = f"{title_base} - {month_name} {year}"
        description = f"{description_base} during {month_name} {year}"
    
        s_year = str(year)
        e_year = str(year)
        s_month = str(month)
        e_month = str(month)
        s_day = str(1)
        e_day = str(calendar.monthrange(year, month)[1])

        with open(os.path.join(this_dir, script_template)) as s_t:
            source = Template(s_t.read())

        script = source.substitute({'db_alias': db_alias, 'title': title, 'description': description,
                                    's_year': s_year, 's_month': s_month, 's_day': s_day,
                                    'e_year': e_year, 'e_month': e_month, 'e_day': e_day,
                                    'lrauvs': repr(lrauvs)})

        load_file_name = f"load_lrauv_{month_name_short.lower()}{year}.py"
        with open(os.path.join(this_dir, load_file_name), 'w') as lf:
            lf.write(script)

        os.chmod(os.path.join(this_dir, load_file_name), 0o755)
        print(f"Done making: {os.path.join(this_dir, load_file_name)}")

        campaign_items += f"    ('{db_alias}', '{os.path.join(os.path.basename(this_dir), load_file_name)}'),\n"

# Write out campaign file
with open(os.path.join(stoqs_dir, campaign_template)) as c_t:
    source = Template(c_t.read())
script = source.substitute({'campaign_tuples': campaign_items})
with open(os.path.join(stoqs_dir, campaign_file_name), 'w') as cf:
    cf.write(script)

print(f"Done writing {os.path.join(stoqs_dir, campaign_file_name)}")
