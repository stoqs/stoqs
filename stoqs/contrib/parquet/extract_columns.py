#!/usr/bin/env python

"""
Pull all the temperature and salinity data out of a STOQS database no
matter what platform and write it out in Parquet file format.

This is a companion to select_data_in_columns_for_data_science.ipynb
where we operationalize the explorations demonstrated in this Notebook:

https://nbviewer.jupyter.org/github/stoqs/stoqs/blob/master/stoqs/contrib/notebooks/select_data_in_columns_for_data_science.ipynb

Sample command line executions:

(base) ➜  docker git:(master) ✗ docker-compose exec stoqs stoqs/contrib/parquet/extract_columns.py --db stoqs_canon_october2020 --platforms dorado -o dorado.parquet -v
INFO 2021-02-24 21:35:53,588 extract_columns.py _estimate_memory():161 Estimated required_memory = 146584085.76
INFO 2021-02-24 21:35:53,588 extract_columns.py _sql_to_df():65 Reading from SQL query into DataFrame...
INFO 2021-02-24 21:36:11,430 extract_columns.py _sql_to_df():77 df.shape: (2245467, 8) - read_sql_query() in 17.8 sec
INFO 2021-02-24 21:36:11,433 extract_columns.py _sql_to_df():78 df.memory_usage().sum(): 143710016
INFO 2021-02-24 21:36:13,876 extract_columns.py pivot_table_to_parquet():172 Writing data to file dorado.parquet...
INFO 2021-02-24 21:36:14,378 extract_columns.py pivot_table_to_parquet():176 dfp.shape: (169159, 16) - to_parquet() in 0.5 sec
INFO 2021-02-24 21:36:14,378 extract_columns.py pivot_table_to_parquet():177 Done
stoqs container peak memory usage: 2.1 GB

(base) ➜  docker git:(master) ✗ docker-compose exec stoqs stoqs/contrib/parquet/extract_columns.py --db stoqs_canon_october2020 --platforms pontus makai -o lrauv.parquet -v
INFO 2021-02-24 21:38:42,623 extract_columns.py _estimate_memory():161 Estimated required_memory = 645795521.28
INFO 2021-02-24 21:38:42,624 extract_columns.py _sql_to_df():65 Reading from SQL query into DataFrame...
INFO 2021-02-24 21:40:13,936 extract_columns.py _sql_to_df():77 df.shape: (9892701, 8) - read_sql_query() in 91.3 sec
INFO 2021-02-24 21:40:13,938 extract_columns.py _sql_to_df():78 df.memory_usage().sum(): 633132992
INFO 2021-02-24 21:40:30,517 extract_columns.py pivot_table_to_parquet():172 Writing data to file lrauv.parquet...
INFO 2021-02-24 21:40:31,798 extract_columns.py pivot_table_to_parquet():176 dfp.shape: (744662, 25) - to_parquet() in 1.3 sec
INFO 2021-02-24 21:40:31,798 extract_columns.py pivot_table_to_parquet():177 Done
stoqs container peak memory usage: 7.9 GB

(base) ➜  docker git:(master) ✗ docker-compose exec stoqs stoqs/contrib/parquet/extract_columns.py --db stoqs_canon_october2020 -o all_plats.parquet -v
INFO 2021-02-24 21:41:53,151 extract_columns.py _estimate_memory():161 Estimated required_memory = 896823624.96
INFO 2021-02-24 21:41:53,153 extract_columns.py _sql_to_df():65 Reading from SQL query into DataFrame...
INFO 2021-02-24 21:43:56,723 extract_columns.py _sql_to_df():77 df.shape: (13738107, 8) - read_sql_query() in 123.6 sec
INFO 2021-02-24 21:43:56,725 extract_columns.py _sql_to_df():78 df.memory_usage().sum(): 879238976
INFO 2021-02-24 21:44:20,578 extract_columns.py pivot_table_to_parquet():172 Writing data to file all_plats.parquet...
INFO 2021-02-24 21:44:23,349 extract_columns.py pivot_table_to_parquet():176 dfp.shape: (1123909, 61) - to_parquet() in 2.8 sec
INFO 2021-02-24 21:44:23,349 extract_columns.py pivot_table_to_parquet():177 Done
stoqs container peak memory usage: 11 GB

A regression of estimated df size to container memory usage gives a factor of 12.3

Mike McCann
MBARI 29 January 2021
"""

import os
import sys

# Insert Django App directory (parent of config) into python path
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../../")))
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
# django >=1.7
try:
    import django

    django.setup()
except AttributeError:
    pass

import argparse
import logging
import pandas as pd
from django.db import connections
from stoqs.models import Platform
from time import time

class Columnar():

    logger = logging.getLogger(__name__)
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(levelname)s %(asctime)s %(filename)s '
                                   '%(funcName)s():%(lineno)d %(message)s')
    _handler.setFormatter(_formatter)
    _log_levels = (logging.WARN, logging.INFO, logging.DEBUG)
    logger.addHandler(_handler)

    # Set to GB of RAM that have been resourced to the Docker engine
    MAX_CONTAINER_MEMORY = 16
    DF_TO_RAM_FACTOR = 12.3

    def _set_platforms(self):
        '''Set plats and plat_list member variables
        '''
        platforms = (self.args.platforms or 
                     Platform.objects.using(self.args.db).all()
                     .values_list('name', flat=True).order_by('name'))
        self.logger.debug(platforms)
        self.plats = ''
        self.plat_list = []
        for platform in platforms:
            if platform in self.args.platforms_omit:
                # Omit some platforms for shorter execution times
                continue
            self.plats += f"'{platform}',"
            self.plat_list.append(platform)
        self.plats = self.plats[:-2] + "'"

    def _sql_to_df(self, sql, extract=False):
        if extract:
            self.logger.info('Reading from SQL query into DataFrame...')

        # More than 10 GB of RAM is needed in Docker Desktop for reading data 
        # from stoqs_canon_october2020. The chunksize option in read_sql_query()
        # does not help reduce the server side memory usage.
        # See: https://stackoverflow.com/a/31843091/1281657
        #      https://github.com/pandas-dev/pandas/issues/12265#issuecomment-181809005
        #      https://github.com/pandas-dev/pandas/issues/35689
        stime = time()
        df = pd.read_sql_query(sql, connections[self.args.db])
        etime = time() - stime
        if extract:
            self.logger.info(f"df.shape: {df.shape} <- read_sql_query() in {etime:.1f} sec")
            self.logger.info(f"Actual df.memory_usage().sum():"
                             f" {(df.memory_usage().sum()/1.e9):.3f} GB")
            self.logger.debug(f"Head of original df:\n{df.head()}")

        return df

    def _build_sql(self, limit=None, order=True, count=False):
        self._set_platforms()
        
        # Base query that's similar to the one behind the api/measuredparameter.csv request
        sql = f'''\nFROM public.stoqs_measuredparameter
        INNER JOIN stoqs_measurement ON (stoqs_measuredparameter.measurement_id = stoqs_measurement.id)
        INNER JOIN stoqs_instantpoint ON (stoqs_measurement.instantpoint_id = stoqs_instantpoint.id)
        INNER JOIN stoqs_activity ON (stoqs_instantpoint.activity_id = stoqs_activity.id)
        INNER JOIN stoqs_platform ON (stoqs_activity.platform_id = stoqs_platform.id)
        INNER JOIN stoqs_parameter ON (stoqs_measuredparameter.parameter_id = stoqs_parameter.id)
        WHERE stoqs_platform.name IN ({self.plats}) 
          AND stoqs_parameter.{self.args.collect} is not null'''

        if count:
            sql = 'SELECT count(*) ' + sql
        else:
            sql = f'''SELECT stoqs_platform.name as platform,
                stoqs_instantpoint.timevalue, stoqs_measurement.depth,
                ST_X(stoqs_measurement.geom) as longitude,
                ST_Y(stoqs_measurement.geom) as latitude,
                stoqs_parameter.{self.args.collect},
                stoqs_measuredparameter.datavalue {sql}'''
            if order:
                sql += ('\nORDER BY stoqs_platform.name, stoqs_instantpoint.timevalue,'
                            ' stoqs_measurement.depth, stoqs_parameter.name')

        if limit:
            sql += f"\nLIMIT {limit}"
        self.logger.debug(f'sql = {sql}')

        return sql

    def _estimate_memory(self):
        '''Perform a small query on the selection and extrapolate
        to estimate the server-side memory required for the full extraction.
        '''
        SAMPLE_SIZE = 100
        sql = self._build_sql(limit=SAMPLE_SIZE, order=False)
        df = self._sql_to_df(sql)

        sample_memory = df.memory_usage().sum()
        self.logger.debug(f"{sample_memory} B for {SAMPLE_SIZE} records")

        total_recs = self._sql_to_df(self._build_sql(count=True))['count'][0]
        self.logger.debug(f"total_recs = {total_recs}")

        required_memory = total_recs * sample_memory / SAMPLE_SIZE / 1.e9
        container_memory = self.DF_TO_RAM_FACTOR * required_memory 
        self.logger.info(f"Estimated required_memory:"
                         f" {required_memory:.3f} GB for DataFrame,"
                         f" {container_memory:.3f} GB for container RAM,")

        if container_memory > self.MAX_CONTAINER_MEMORY:
            self.logger.exception(f"Request of {container_memory:.3f} GB would"
                                  f" exceed {self.MAX_CONTAINER_MEMORY} GB"
                                  f" of RAM available")
            sys.exit(-1)

    def pivot_table_to_parquet(self):
        '''Approach 4. Use Pandas do a pivot on data read into a DataFrame
        '''
        self._estimate_memory()
        sql = self._build_sql()
        df = self._sql_to_df(sql, extract=True)
        context = ['platform', 'timevalue', 'depth', 'latitude', 'longitude']
        dfp = df.pivot_table(index=context, columns=self.args.collect, values='datavalue')
        self.logger.debug(dfp.shape)

        self.logger.info(f'Writing data to file {self.args.output}...')
        stime = time()
        dfp.to_parquet(self.args.output)
        etime = time() - stime
        self.logger.info(f"dfp.shape: {dfp.shape} -> to_parquet() in {etime:.1f} sec")
        self.logger.debug(f"Head of pivoted df:\n{dfp.head()}")
        self.logger.info('Done')

    def process_command_line(self):
        parser = argparse.ArgumentParser(description='Transform STOQS data into columnar Parquet file format')

        parser.add_argument('--platforms', action='store', nargs='*', 
                            help='Restrict to just these platforms')
        parser.add_argument('--platforms_omit', action='store', nargs='*', default=[],
                            help='Restrict to all but these platforms')
        parser.add_argument('--collect', action='store', default='name',
                            choices=['name', 'standard_name'],
                            help='The column to collect: name or standard_name')
        parser.add_argument('--db', action='store', required=True,
                            help='Database alias, e.g. stoqs_canon_october2020')
        parser.add_argument('-o', '--output', action='store', required=True,
                            help='Output file name')
        parser.add_argument('--start', action='store', help='Start time in YYYYMMDDTHHMMSS format',
                            default='19000101T000000')
        parser.add_argument('--end', action='store', help='End time in YYYYMMDDTHHMMSS format',
                            default='22000101T000000')
        parser.add_argument('-v', '--verbose', type=int, choices=range(3),
                            action='store', default=0, const=1, nargs='?',
                            help="verbosity level: " + ', '.join(
                                [f"{i}: {v}" for i, v, in enumerate(('WARN', 'INFO', 'DEBUG'))]))

        self.args = parser.parse_args()
        self.commandline = ' '.join(sys.argv)
        self.logger.setLevel(self._log_levels[self.args.verbose])
        self.logger.debug(f"Using databases at DATABASE_URL ="
                          f" {os.environ['DATABASE_URL']}")


if __name__ == '__main__':

    c = Columnar()
    c.process_command_line()
    c.pivot_table_to_parquet()

