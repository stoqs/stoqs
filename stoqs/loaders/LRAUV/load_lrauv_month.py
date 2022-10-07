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
import django
import logging

from argparse import ArgumentParser, Namespace
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from make_load_scripts import LoaderMaker
from loaders.load import Loader, DatabaseLoadError

class AutoLoad():

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    lm = LoaderMaker()

    def _YYYYMM_to_monyyyy(self, YYYYMM):
        return datetime(int(YYYYMM[:4]), int(YYYYMM[4:]), 1).strftime("%b%Y").lower()

    def _do_the_load(self, monyyyy):
        self.loader.args.db = (f"stoqs_lrauv_{monyyyy}", )
        self.logger.debug(f"--db arg set to {self.loader.args.db}")
        self.loader.checks()
        try:
            self.logger.debug(f"Executing self.loader.load()...")
            self.loader.load(cl_args=self.args)
        except DatabaseLoadError:
            self.logger.warning(f"Failed to load {self.loader.args.db}")
            return

        if not self.args.append:
            self.logger.debug(f"Executing self.loader.updateprovenance()...")
            self.loader.updateprovenance()

        self.logger.debug(f"Executing self.loader.grant_everyone_select()...")
        self.loader.grant_everyone_select()
        self.logger.debug(f"Executing self.loader.pg_dump()...")
        self.loader.pg_dump()

    def _update_campaigns(self, year):
            # Ensure that we have load script and campaign created for the year requested
            items = self.lm.create_load_scripts(year)
            num_new_campaigns = self.lm.update_lrauv_campaigns(items)
            if num_new_campaigns:
                self.logger.info(f"{num_new_campaigns} campaigns added to campaigns.py file")
                self.logger.warning(f"If you are running in a Docker container you you need to restart the stoqs service with this file before executing the loads.")

    def execute(self):
        if self.args.verbose:
            self.logger.setLevel(logging.DEBUG)
            self.lm.logger.setLevel(logging.DEBUG)

        self.loader = Loader()

        # Start with default arguments for Loader - set args to force reload databases
        self.loader.args = Namespace(background=False, campaigns='campaigns', clobber=False, db=None, 
                                drop_indexes=False, email=None, grant_everyone_select=False, 
                                list=False, noinput=False, pg_dump=False, removetest=False, 
                                slack=False, test=False, updateprovenance=False, verbose=0)
        self.loader.args.noinput = True
        self.loader.args.clobber = True
        self.loader.args.test = self.args.test
        self.loader.args.verbose = self.args.verbose
        self.loader.args.drop_if_fail = True
        self.loader.args.create_only = False
        self.loader.args.restore = ''
        if self.args.append:
            self.loader.args.append = True
            yesterday = datetime.utcnow() - timedelta(days=1)
            self.loader.args.startdate = yesterday.strftime("%Y%m%d")
            self.args.startdate = self.loader.args.startdate

        if self.args.YYYYMM:
            self._update_campaigns(int(self.args.YYYYMM[:4]))
            self._do_the_load(self._YYYYMM_to_monyyyy(self.args.YYYYMM))

        elif self.args.start_YYYYMM and self.args.end_YYYYMM:
            # First, create the campaigns.py file for the whole duration
            for year in range(int(self.args.start_YYYYMM[:4]), int(self.args.end_YYYYMM[:4]) + 1):
                self._update_campaigns(year)
            # Second, execute the loads
            start_year = int(self.args.start_YYYYMM[:4])
            end_year = int(self.args.end_YYYYMM[:4])
            for year in range(start_year, end_year + 1):
                if year == start_year and year == end_year:
                    for month in range(int(self.args.start_YYYYMM[4:]), int(self.args.end_YYYYMM[4:]) + 1):
                        self._do_the_load(self._YYYYMM_to_monyyyy(f"{year}{month:02d}"))
                elif year == start_year:
                    for month in range(int(self.args.start_YYYYMM[4:]), 13):
                        self._do_the_load(self._YYYYMM_to_monyyyy(f"{year}{month:02d}"))
                elif year != start_year and year != end_year:
                    for month in range(1, 13):
                        self._do_the_load(self._YYYYMM_to_monyyyy(f"{year}{month:02d}"))
                elif year == end_year:
                    for month in range(1, int(self.args.end_YYYYMM[4:]) + 1):
                        self._do_the_load(self._YYYYMM_to_monyyyy(f"{year}{month:02d}"))

        elif self.args.previous_month:
            prev_mon = datetime.today() - relativedelta(months=1)
            YYYYMM = prev_mon.strftime("%Y%m")
            self._update_campaigns(int(YYYYMM[:4]))
            self._do_the_load(self._YYYYMM_to_monyyyy(YYYYMM))

        elif self.args.current_month:
            curr_mon = datetime.today()
            # Ensure that we have load script and campaign created for the year requested
            YYYYMM = curr_mon.strftime("%Y%m")
            self._update_campaigns(int(YYYYMM[:4]))
            self._do_the_load(self._YYYYMM_to_monyyyy(YYYYMM))

    def process_command_line(self):
        parser = ArgumentParser()
        parser.add_argument('--YYYYMM', action='store', help='Year and month for database to recreate, e.g. 201906')
        parser.add_argument('--start_YYYYMM', action='store', help='Start year and month, e.g. 201701')
        parser.add_argument('--end_YYYYMM', action='store', help='End year and month, e.g. 201812')
        parser.add_argument('--previous_month', action='store_true', help='Recreate the database for the previous month')
        parser.add_argument('--current_month', action='store_true', help='Recreate the database for the current month')
        parser.add_argument('--test', action='store_true', help='Load test database(s)')
        parser.add_argument('--realtime', action='store_true', help='Load realtime data')
        parser.add_argument('--missionlogs', action='store_true', help='Load delayed mode (missionlogs) data')
        parser.add_argument('--append', action='store_true', help='Append data to existting database')
        parser.add_argument('--startdate', help='Startdate in YYYYMMDD format for appending data')
        parser.add_argument('--remove_appended_activities', action='store_true', help='First remove activities loaded after load_date_gmt')
        parser.add_argument('-v', '--verbose', nargs='?', choices=[1,2,3], type=int, 
                            help='Turn on verbose output. If > 2 load is verbose too.', const=1, default=0)

        self.args = parser.parse_args()
        if (self.args.YYYYMM or (self.args.start_YYYYMM and self.args.end_YYYYMM) 
            or self.args.previous_month or self.args.current_month):
            pass
        else: 
            parser.print_help(sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    autoload = AutoLoad()
    autoload.process_command_line()
    try:
        autoload.execute()
    except django.db.utils.ConnectionDoesNotExist as e:
        autoload.logger.error(str(e))
        autoload.logger.info(f"Perhaps stoqs/campaigns.py doesn't contain the db_aliases you are trying to load?")

