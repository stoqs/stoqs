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
from django.db import connections
from stoqs.models import Platform
from time import time

logger = logging.getLogger(__name__)

class Columnar():

    logger = logging.getLogger(__name__)
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(levelname)s %(asctime)s %(filename)s '
                                   '%(funcName)s():%(lineno)d %(message)s')
    _handler.setFormatter(_formatter)
    _log_levels = (logging.WARN, logging.INFO, logging.DEBUG)

    # Set to GB of RAM that have been resourced to the Docker engine
    MAX_CONTAINER_MEMORY = psutil.virtual_memory().total / 1024 / 1024 / 1024
    DF_TO_RAM_FACTOR = 12.3


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
        df = pd.read_sql_query(sql, connections[self.db])
        etime = time() - stime
        if extract:
            self.logger.info(f"df.shape: {df.shape} <- read_sql_query() in {etime:.1f} sec")
            self.logger.info(f"Actual df.memory_usage().sum():"
                             f" {(df.memory_usage().sum()/1.e9):.3f} GB")
            self.logger.debug(f"Head of original df:\n{df.head()}")

        return df

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
                selects += f'''
                stoqs_parameter.{self.collect},
                stoqs_measuredparameter.datavalue'''
            else:
                selects += '''stoqs_measuredparameter.datavalue'''

        sql = selects + joins

        if where_clause:
            sql += where_clause

        if order and not count:
            sql += ('\nORDER BY stoqs_platform.name, stoqs_instantpoint.timevalue,'
                        ' stoqs_measurement.depth, stoqs_parameter.name')

        if limit:
            sql += f"\nLIMIT {limit}"
        self.logger.debug(f'sql = {sql}')

        return sql

    def _estimate_memory(self, where_clause=None):
        '''Perform a small query on the selection and extrapolate
        to estimate the server-side memory required for the full extraction.
        '''
        SAMPLE_SIZE = 100
        sql = self._build_sql(limit=SAMPLE_SIZE, order=False, where_clause=where_clause)
        df = self._sql_to_df(sql)

        sample_memory = df.memory_usage().sum()
        self.logger.debug(f"{sample_memory} Bytes for {SAMPLE_SIZE} records")

        total_recs = self._sql_to_df(self._build_sql(count=True,
                                     where_clause=where_clause))['count'][0]
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

        return {'RAM_GB': container_memory, 'size_MB': required_memory * 1.e3,
                'records': total_recs, 'time_min': 'TDB'}

    def request_to_sql_where(self, request):
        '''Convert query sring parameters to SQL WHERE statements
        '''
        logger.debug(f"request = {request}") 
        self.db = request.META['dbAlias']
        logger.debug(f"db = {self.db}") 
        self.platforms = request.GET.getlist("measurement__instantpoint__activity__platform__name")
        logger.debug(f"platforms = {self.platforms}")
        self.collect = request.GET.get("collect", 'standard_name')
        logger.debug(f"collect = {self.collect}")

        where_list = []
        if self.platforms:
            where_list.append(f"stoqs_platform.name IN ({repr(self.platforms)[1:-1]})")
        if self.collect:
            where_list.append(f"stoqs_parameter.{self.collect} is not null")

        if where_list:
            where_clause = 'WHERE\n' + ' AND '.join(where_list)

        logger.debug(f"where_clause = {where_clause}")

        return where_clause

    def request_estimate(self, request):
        return self._estimate_memory(self.request_to_sql_where(request))

    def request_to_parquet(self, request):
        sql = self._build_sql(where_clause=self.request_to_sql_where(request))
        df = self._sql_to_df(sql, extract=True)
        context = ['platform', 'timevalue', 'depth', 'latitude', 'longitude']
        dfp = df.pivot_table(index=context, columns=self.collect, values='datavalue')
        logger.debug(dfp.shape)

        stime = time()
        fn = tempfile.NamedTemporaryFile(dir='/tmp', suffix='.parquet').name
        dfp.to_parquet(fn)
        etime = time() - stime
        logger.info(f"dfp.shape: {dfp.shape} -> to_parquet() in {etime:.1f} sec")
        logger.debug(f"Head of pivoted df {fn}:\n{dfp.head()}")
        logger.info(f'Done creating {fn}')

        return fn
