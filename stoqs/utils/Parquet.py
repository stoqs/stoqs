#!/usr/bin/env python

"""
Methods copied from stoqs/contrib/parquet/extract_columns.py for use in 
core web app.

Mike McCann
MBARI 26 February 2021
"""

import os
import sys
import logging
import pandas as pd
import psutil
import tempfile
import warnings
from django.db import connections
from stoqs.models import Platform
from time import time

logger = logging.getLogger(__name__)

# To debug this on a docker production development system run:
#   docker-compose exec stoqs /bin/bash
#   stoqs/manage.py runserver_plus 0.0.0.0:8001 --settings=config.settings.local
# Place breakpoint()s in this code and hit http://localhost:8001 from your host

class Columnar():

    # Set to GB of RAM that have been resourced to the Docker engine
    MAX_CONTAINER_MEMORY = psutil.virtual_memory().total / 1024 / 1024 / 1024
    DF_TO_RAM_FACTOR = 12.3

    context = ['platform', 'timevalue', 'depth', 'latitude', 'longitude']

    def _sql_to_df(self, sql, extract=False, request=None, set_index=False):
        if extract:
            where_clause = self.request_to_sql_where(request) 
            total_recs = self._sql_to_df(self._build_sql(count=True,
                                         where_clause=where_clause))[0]['count'][0]
            logger.info(f'Extracting {total_recs} records from SQL query into DataFrame...')

        # More than 10 GB of RAM is needed in Docker Desktop for reading data 
        # from stoqs_canon_october2020. The chunksize option in read_sql_query()
        # does not help reduce the server side memory usage.
        # See: https://stackoverflow.com/a/31843091/1281657
        #      https://github.com/pandas-dev/pandas/issues/12265#issuecomment-181809005
        #      https://github.com/pandas-dev/pandas/issues/35689
        stime = time()
        # See https://github.com/pandas-dev/pandas/issues/45660#issuecomment-1077355514
        with warnings.catch_warnings():
            # Ignore warning for non-SQLAlchemy Connecton
            warnings.simplefilter('ignore', UserWarning)
            if set_index or extract:
                df = pd.read_sql_query(sql, connections[self.db], index_col=self.context)
            else:
                df = pd.read_sql_query(sql, connections[self.db])
        etime = time() - stime
        if extract:
            logger.info(f"sql = {sql}")
            logger.info(f"df.shape: {df.shape} <- read_sql_query() in {etime:.1f} sec")
            logger.info(f"Actual df.memory_usage().sum():"
                             f" {(df.memory_usage().sum()/1.e9):.3f} GB")
            logger.debug(f"Head of original df:\n{df.head()}")

        return df, etime

    def _build_sql(self, limit=None, order=True, count=False, where_clause=None):
        
        # Base query that's similar to the one behind the api/measuredparameter.csv request
        joins = f'''\nFROM public.stoqs_measuredparameter
        INNER JOIN stoqs_measurement ON (stoqs_measuredparameter.measurement_id = stoqs_measurement.id)
        INNER JOIN stoqs_instantpoint ON (stoqs_measurement.instantpoint_id = stoqs_instantpoint.id)
        INNER JOIN stoqs_activity ON (stoqs_instantpoint.activity_id = stoqs_activity.id)
        INNER JOIN stoqs_platform ON (stoqs_activity.platform_id = stoqs_platform.id)
        INNER JOIN stoqs_parameter ON (stoqs_measuredparameter.parameter_id = stoqs_parameter.id)
        '''

        if count:
            selects = 'SELECT count(*) '
        else:
            selects = f'''SELECT stoqs_platform.name as platform,
                stoqs_instantpoint.timevalue, stoqs_measurement.depth,
                ST_X(stoqs_measurement.geom) as longitude,
                ST_Y(stoqs_measurement.geom) as latitude,'''
            if self.collect:
                if 'standard_name' in self.collect:
                    selects += f'\nstoqs_parameter.standard_name,'
                elif 'name' in self.collect:
                    selects += f'\nstoqs_parameter.name,'
                if 'activity__name' in self.include:
                    selects += '\nstoqs_activity.name as activity__name,'
                    self.context = ['platform', 'activity__name', 'timevalue', 
                                    'depth', 'latitude', 'longitude']
                selects += '\nstoqs_measuredparameter.datavalue'
            else:
                selects += '\nstoqs_measuredparameter.datavalue'

        sql = selects + joins

        if where_clause:
            sql += where_clause

        if order and not count:
            sql += ('\nORDER BY stoqs_platform.name, stoqs_instantpoint.timevalue,'
                        ' stoqs_measurement.depth, stoqs_parameter.name')

        if limit:
            sql += f"\nLIMIT {limit}"
        logger.debug(f'sql = {sql}')

        return sql

    def _estimate_memory(self, where_clause=None):
        '''Perform a small query on the selection and extrapolate
        to estimate the server-side memory required for the full extraction.
        '''
        SAMPLE_SIZE = 100
        sql = self._build_sql(limit=SAMPLE_SIZE, order=False, where_clause=where_clause)
        df, sample_time = self._sql_to_df(sql, set_index=True)

        sample_memory = df.memory_usage().sum()
        logger.debug(f"{sample_memory} Bytes for {SAMPLE_SIZE} records")

        total_recs = self._sql_to_df(self._build_sql(count=True,
                                     where_clause=where_clause))[0]['count'][0]
        logger.debug(f"total_recs = {total_recs}")

        required_memory = total_recs * sample_memory / SAMPLE_SIZE / 1.e9
        container_memory = self.DF_TO_RAM_FACTOR * required_memory 
        logger.info(f"Estimated required_memory:"
                         f" {required_memory:.3f} GB for DataFrame,"
                         f" {container_memory:.3f} GB for container RAM,")

        sample_time = sample_time / 60
        required_time = total_recs * sample_time / SAMPLE_SIZE /60
        logger.info(f"sample_time = {sample_time} min,"
                    f" required_time = {required_time} min")

        logger.debug(f"pivot_table(index={self.context}, columns={self.collect}, values='datavalue')")
        dfp = df.pivot_table(index=self.context, columns=self.collect, values='datavalue')
        logger.debug(f"dfp.head() = {dfp.head()}")
        sample_est_records = dfp.shape[0]
        est_records = int(total_recs * sample_est_records / SAMPLE_SIZE)
        logger.info(f"sample_est_records = {sample_est_records},"
                    f" est_records = {est_records}")

        if container_memory > self.MAX_CONTAINER_MEMORY:
            logger.exception(f"Request of {container_memory:.3f} GB would"
                                  f" exceed {self.MAX_CONTAINER_MEMORY} GB"
                                  f" of RAM available")

        try:
            time_available = float(os.environ['UWSGI_READ_TIMEOUT'])
        except KeyError:
            logger.info("UWSGI_READ_TIMEOUT environment variable not set."
                        " Setting time_available to 60 seconds.")
            time_available = 60

        return {'RAM_GB': container_memory, 
                'avl_RAM_GB': self.MAX_CONTAINER_MEMORY,
                'size_MB': required_memory * 1.e3,
                'est_records': est_records, 
                'time_min': required_time, 
                'time_avl': time_available / 60,    # minutes
                'preview': dfp.head(2).to_html()}

    def request_to_sql_where(self, request):
        '''Convert query sring parameters to SQL WHERE statements
        '''
        logger.debug(f"request = {request}") 
        self.db = request.META['dbAlias']
        logger.debug(f"db = {self.db}") 

        self.platforms = request.GET.getlist("measurement__instantpoint__activity__platform__name")
        logger.debug(f"platforms = {self.platforms}")

        self.collect = request.GET.getlist("collect", 'standard_name')
        logger.debug(f"collect = {self.collect}")
        self.include = request.GET.getlist("include")
        logger.debug(f"include = {self.include}")

        self.parameters = request.GET.getlist("parameter__name")
        logger.debug(f"parameters = {self.parameters}")

        self.stime = request.GET.get('measurement__instantpoint__timevalue__gt')
        logger.debug(f"stime = {self.stime}")
        self.etime = request.GET.get('measurement__instantpoint__timevalue__lt')
        logger.debug(f"etime = {self.etime}")

        self.min_depth = request.GET.get('measurement__depth__gte')
        logger.debug(f"stime = {self.min_depth}")
        self.max_depth = request.GET.get('measurement__depth__lte')
        logger.debug(f"etime = {self.max_depth}")

        self.activitynames = request.GET.getlist("activitynames")
        logger.debug(f"activitynames = {self.activitynames}")
        self.activity__name__contains = []
        for name in request.GET.getlist("activity__name__contains"):
            self.activity__name__contains.append(name)
        self.activity__name = []
        for name in request.GET.getlist("activity__name"):
            self.activity__name.append(name)
        for name in request.GET.getlist("measurement__instantpoint__activity__name__contains"):
            # To match similar .html request
            self.activity__name__contains.append(name)
        logger.debug(f"activity__name__contains = {self.activity__name__contains}")

        where_list = []
        if self.platforms:
            where_list.append(f"stoqs_platform.name IN ({repr(self.platforms)[1:-1]})")
        if 'standard_name' in self.collect:
            where_list.append(f"stoqs_parameter.standard_name is not null")
        if 'name' in self.collect:
            where_list.append(f"stoqs_parameter.name is not null")
        if self.parameters:
            where_list.append(f"stoqs_parameter.name IN ({repr(self.parameters)[1:-1]})")
        if self.stime:
            where_list.append(f"stoqs_instantpoint.timevalue >= '{self.stime}'")
        if self.etime:
            where_list.append(f"stoqs_instantpoint.timevalue <= '{self.etime}'")
        if self.min_depth:
            where_list.append(f"stoqs_measurement.depth >= '{self.min_depth}'")
        if self.max_depth:
            where_list.append(f"stoqs_measurement.depth <= '{self.max_depth}'")
        if self.activitynames:
            where_list.append(f"stoqs_activity.name IN ({repr(self.activitynames)[1:-1]})")
        if self.activity__name__contains:
            anc_list = []
            for name in self.activity__name__contains:
                anc_list.append(f"stoqs_activity.name LIKE '%{name}%'")
            logger.debug('(' + ' OR '.join(anc_list) + ')')
            where_list.append('(' + ' OR '.join(anc_list) + ')')
        if self.activity__name:
            an_list = []
            for name in self.activity__name:
                an_list.append(f"stoqs_activity.name = '{name}'")
            logger.debug('(' + ' OR '.join(an_list) + ')')
            where_list.append('(' + ' OR '.join(an_list) + ')')

        where_clause = ''
        if where_list:
            where_clause = 'WHERE ' + '\n  AND '.join(where_list)
            logger.debug(f"where_clause = {where_clause}")

        return where_clause

    def request_estimate(self, request):
        return self._estimate_memory(self.request_to_sql_where(request))

    def request_to_parquet(self, request):
        sql = self._build_sql(where_clause=self.request_to_sql_where(request))
        df, _ = self._sql_to_df(sql, extract=True, request=request)
        dfp = df.pivot_table(index=self.context, columns=self.collect, values='datavalue')
        logger.debug(dfp.shape)

        stime = time()
        fn = tempfile.NamedTemporaryFile(dir='/tmp', suffix='.parquet').name
        dfp.to_parquet(fn)
        etime = time() - stime
        logger.info(f"dfp.shape: {dfp.shape} -> to_parquet() in {etime:.1f} sec")
        logger.debug(f"Head of pivoted df {fn}:\n{dfp.head()}")
        logger.info(f'Done creating {fn}')

        # TODO: return actuals & fn in dictionary
        return fn
