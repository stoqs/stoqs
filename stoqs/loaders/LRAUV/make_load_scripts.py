#!/usr/bin/env python
'''
Routine loading of all LRUAV data available on a DAP server.
This module writes load scripts for month's worth of LRAUV data.
It is imported by stoqs/loaders/LRAUV/load_lrauv_month.py for
creating multiple year scripts.  Running this script will create
load scripts for the current year only.

It also enters lines into the lruav_campaigns.py file.

Executing the load is then accomplished with another step, e.g.:

   stoqs/loaders/load.py --db stoqs_lrauv_may2019

Mike McCann
MBARI 3 June 2019
'''
import os
import sys
this_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
stoqs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

import calendar
import logging
import re
from datetime import datetime
from string import Template

campaign_template = 'mbari_lrauv_campaigns.template'
campaign_file_name = 'mbari_lrauv_campaigns.py'
script_template = 'load_lrauv.template'

# Construct list of lrauvs with: ls -d /mbari/LRAUV/*/missionlogs | cut -d/ -f4
lrauvs = ('ahi', 'aku', 'brezo', 'brizo', 'daphne', 'galene', 'makai', 'opah', 'pontus', 
          'tethys', 'triton', 'whoidhs', 'polaris', )

title_base = 'LRAUV - Routine Operational data'
description_base='MBARI Long Range Autonomous Vehicle data'

class LoaderMaker():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    def create_load_scripts(self, start_year=None, end_year=None):
        # If called with no arguments process the current year
        if not start_year:
            start_year = datetime.today().year
        if not end_year:
            end_year = start_year + 1
        else:
            end_year += 1

        monyyyys = []
        for year in range(start_year, end_year):
            for month in range(1, 13):
                month_name = datetime(year, month, 1).strftime("%B")
                month_name_short = datetime(year, month, 1).strftime("%b")

                monyyyy = f"{month_name_short.lower()}{year}"
                monyyyys.append(monyyyy)
                db_alias = f"stoqs_lrauv_{monyyyy}"
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

                load_file_name = f"load_lrauv_{monyyyy}.py"
                with open(os.path.join(this_dir, load_file_name), 'w') as lf:
                    lf.write(script)

                os.chmod(os.path.join(this_dir, load_file_name), 0o755)
                print(f"Done making: {os.path.join(this_dir, load_file_name)}")
                self.logger.info(f"Done making: {os.path.join(this_dir, load_file_name)}")

        return monyyyys

    def update_lrauv_campaigns(self, monyyyys):
        '''Respect existing items in existing mbari_lrauv_campaigns.py file
        and only update with any new campaign_items.
        '''

        # Read items (if any) from any existing mbari_lrauv_campaigns.py file
        #     ('stoqs_lrauv_jan2018', 'LRAUV/load_lrauv_jan2018.py'),\n
        CAMPAIGN_ITEM = re.compile(r".*\('stoqs_lrauv_(.*)', 'LRAUV\/load_lrauv_(.*).py'\),")
        monyyyy_in_file = []
        try:
            with open(os.path.join(stoqs_dir, campaign_file_name)) as cf:
                for line in cf:
                    c_match = re.match(CAMPAIGN_ITEM, line)
                    if c_match:
                        monyyyy_in_file.append(c_match.group(1))
        except FileNotFoundError as e:
            self.logger.debug(str(e))

        # Rewrite the file with existing and new campaigns
        campaign_items_str = ''
        for monyyyy in monyyyy_in_file:
            load_file_name = f"load_lrauv_{monyyyy}.py"
            campaign_items_str += f"    ('stoqs_lrauv_{monyyyy}', '{os.path.join(os.path.basename(this_dir), load_file_name)}'),\n"

        num_new_campaigns = 0
        for monyyyy in monyyyys:
            if monyyyy not in monyyyy_in_file:
                num_new_campaigns += 1
                load_file_name = f"load_lrauv_{monyyyy}.py"
                campaign_items_str += f"    ('stoqs_lrauv_{monyyyy}', '{os.path.join(os.path.basename(this_dir), load_file_name)}'),\n"

        # Write out campaign file
        with open(os.path.join(stoqs_dir, campaign_template)) as c_t:
            source = Template(c_t.read())
        script = source.substitute({'campaign_tuples': campaign_items_str})
        with open(os.path.join(stoqs_dir, campaign_file_name), 'w') as cf:
            cf.write(script)

        print(f"Done writing {os.path.join(stoqs_dir, campaign_file_name)} with {num_new_campaigns} new campaign entries")
        self.logger.info(f"Done writing {os.path.join(stoqs_dir, campaign_file_name)} with {num_new_campaigns} new campaign entries")
        return num_new_campaigns


if __name__ == '__main__':
    lm = LoaderMaker()
    lm.logger.setLevel(logging.DEBUG)

    this_year = datetime.today().year
    items = lm.create_load_scripts(this_year, this_year)
    lm.update_lrauv_campaigns(items)

