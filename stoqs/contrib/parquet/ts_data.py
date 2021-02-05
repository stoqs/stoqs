#!/usr/bin/env python

"""
Pull all the temperature and salinity data out of a STOQS database no
matter what platform and write it out in Parquet file format.

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
import pandas as pd
from django.db import connections
from stoqs.models import ActivityParameter

class Columnar():

    def write_parquet(self):

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

        platforms = (ActivityParameter.objects.using(self.args.db)
                                      .filter(parameter__standard_name='sea_water_salinity')
                                      .values_list('activity__platform__name', flat=True)
                                      .distinct())
        plats = ''
        if self.args.platforms:
            platforms = self.args.platforms
        for platform in platforms:
            if platform == 'makai' or platform == 'pontus':
                continue
            plats += f"'{platform}',"
        plats = plats[:-2] + "'"
        sql = sql_multp.format(plats)
        print(sql)

        print('Reading data into DataFrame...')
        # More than 10 GB of RAM is needed in Docker Desktop for reading data from stoqs_canon_october2020
        df = pd.read_sql_query(sql, connections[self.args.db])
        print(df.head())
        print(f'Writing data to file {self.args.output}...')
        df.to_parquet(self.args.output)
        print('Done')

    def process_command_line(self):
        parser = argparse.ArgumentParser(description='Transform STOQS data into columnar Parquet file format')

        parser.add_argument('--platforms', action='store', nargs='*', help='Restrict to just these platforms')
        parser.add_argument('--db', action='store', help='Database alias, e.g. stoqs_canon_october2020', required=True)
        parser.add_argument('-o', '--output', action='store', help='Output file name', required=True)
        parser.add_argument('--start', action='store', help='Start time in YYYYMMDDTHHMMSS format',
                            default='19000101T000000')
        parser.add_argument('--end', action='store', help='End time in YYYYMMDDTHHMMSS format',
                            default='22000101T000000')
        parser.add_argument('-v', '--verbose', nargs='?', choices=[1, 2, 3], type=int,
                            help='Turn on verbose output. Higher number = more output.', const=1, default=0)

        self.args = parser.parse_args()
        self.commandline = ' '.join(sys.argv)


if __name__ == '__main__':

    c = Columnar()
    c.process_command_line()
    c.write_parquet()

