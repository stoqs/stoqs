#!/usr/bin/env python

"""
Pull all the temperature and salinity data out of a STOQS database no
matter what platform and write it out in Parquet file format.

This is a companion to select_data_in_columns_for_data_science.ipynb
where we operationalize the explorations demonstrated in this Notebook.

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
from stoqs.models import ActivityParameter, Platform
from time import time

class Columnar():

    logger = logging.getLogger(__name__)
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(levelname)s %(asctime)s %(filename)s '
                                   '%(funcName)s():%(lineno)d %(message)s')
    _handler.setFormatter(_formatter)
    _log_levels = (logging.WARN, logging.INFO, logging.DEBUG)

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

    def _sql_to_df(self, sql):
        self.logger.info('Reading from SQL query into DataFrame...')
        self.logger.debug(f'sql = {sql}')

        # More than 10 GB of RAM is needed in Docker Desktop for reading data 
        # from stoqs_canon_october2020. The chunksize option in read_sql_query()
        # does not help reduce the server side memory usage.
        # See: https://stackoverflow.com/a/31843091/1281657
        #      https://github.com/pandas-dev/pandas/issues/12265#issuecomment-181809005
        #      https://github.com/pandas-dev/pandas/issues/35689
        stime = time()
        df = pd.read_sql_query(sql, connections[self.args.db])
        etime = time() - stime
        self.logger.info(f"df.shape: {df.shape} - read_sql_query() in {etime:.1f} sec")
        self.logger.debug(df.head())

        return df

    def self_join_to_parquet(self):
        '''Approach 1. Use the same kind of self-join query used for selecting 
        data for Parameter-Parameter plots.
        '''

        self._set_platforms()

        sql_multp = '''SELECT DISTINCT stoqs_measuredparameter.id,
                        stoqs_platform.name,
                        stoqs_measurement.depth,
                        mp_salt.datavalue AS salt,
                        mp_temp.datavalue AS temp
        FROM stoqs_measuredparameter
        INNER JOIN stoqs_measurement ON (stoqs_measuredparameter.measurement_id = stoqs_measurement.id)
        INNER JOIN stoqs_instantpoint ON (stoqs_measurement.instantpoint_id = stoqs_instantpoint.id)
        INNER JOIN stoqs_activity ON (stoqs_instantpoint.activity_id = stoqs_activity.id)
        INNER JOIN stoqs_platform ON (stoqs_activity.platform_id = stoqs_platform.id)
        INNER JOIN stoqs_measurement m_salt ON m_salt.instantpoint_id = stoqs_instantpoint.id
        INNER JOIN stoqs_measuredparameter mp_salt ON mp_salt.measurement_id = m_salt.id
        INNER JOIN stoqs_parameter p_salt ON mp_salt.parameter_id = p_salt.id
        INNER JOIN stoqs_measurement m_temp ON m_temp.instantpoint_id = stoqs_instantpoint.id
        INNER JOIN stoqs_measuredparameter mp_temp ON mp_temp.measurement_id = m_temp.id
        INNER JOIN stoqs_parameter p_temp ON mp_temp.parameter_id = p_temp.id
        WHERE (p_salt.standard_name = 'sea_water_temperature')
          AND (p_temp.standard_name = 'sea_water_salinity')
          AND stoqs_platform.name IN ({})'''

        sql = sql_multp.format(self.plats)
        df = self._sql_to_df(sql)

    def pivot_table_to_parquet(self):
        '''Approach 4. Use Pandas do a pivot on data read into a DataFrame
        '''
        self._set_platforms()
        
        # Base query that's similar to the one behind the api/measuredparameter.csv request
        sql_base = '''SELECT stoqs_platform.name as platform, stoqs_instantpoint.timevalue, stoqs_measurement.depth, 
            ST_X(stoqs_measurement.geom) as longitude, ST_Y(stoqs_measurement.geom) as latitude,
            stoqs_parameter.name, standard_name, datavalue 
        FROM public.stoqs_measuredparameter
        INNER JOIN stoqs_measurement ON (stoqs_measuredparameter.measurement_id = stoqs_measurement.id)
        INNER JOIN stoqs_instantpoint ON (stoqs_measurement.instantpoint_id = stoqs_instantpoint.id)
        INNER JOIN stoqs_activity ON (stoqs_instantpoint.activity_id = stoqs_activity.id)
        INNER JOIN stoqs_platform ON (stoqs_activity.platform_id = stoqs_platform.id)
        INNER JOIN stoqs_parameter ON (stoqs_measuredparameter.parameter_id = stoqs_parameter.id)
        WHERE stoqs_platform.name IN ({})
        ORDER BY stoqs_instantpoint.timevalue, stoqs_parameter.name'''
        sql = sql_base.format(self.plats)
        df = self._sql_to_df(sql)
        context = ['platform', 'timevalue', 'depth', 'latitude', 'longitude']
        dfp = df.pivot_table(index=context, columns=self.args.collect, values='datavalue')
        self.logger.debug(dfp.shape)

        self.logger.info(f'Writing data to file {self.args.output}...')
        stime = time()
        dfp.to_parquet(self.args.output)
        etime = time() - stime
        self.logger.info(f"dfp.shape: {dfp.shape} - to_parquet() in {etime:.1f} sec")
        self.logger.info('Done')

    def process_command_line(self):
        parser = argparse.ArgumentParser(description='Transform STOQS data into columnar Parquet file format')

        parser.add_argument('--platforms', action='store', nargs='*', 
                            help='Restrict to just these platforms')
        parser.add_argument('--platforms_omit', action='store', nargs='*', default=[],
                            help='Restrict to all but these platforms')
        parser.add_argument('--collect', action='store', default='name',
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


if __name__ == '__main__':

    c = Columnar()
    c.process_command_line()
    ##c.self_join_to_parquet()
    c.pivot_table_to_parquet()

