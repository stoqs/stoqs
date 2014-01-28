#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2013, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

Base class for querying the database for measured parameters from the same instantpoint and to
make scatter plots of temporal segments of the data from platforms.

Make use of STOQS metadata to make it as simple as possible to use this script for
different platforms, parameters, and campaigns.

Mike McCann
MBARI January 28, 2014

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE']='settings'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))  # settings.py is one dir up

from django.db import connections
from datetime import datetime, timedelta
from stoqs.models import Activity, ActivityParameter, ParameterResource, Platform
from django.contrib.gis.geos import LineString, Point
from django.db.models import Max, Min


class BiPlot():
    '''
    Make customized BiPlots (Parameter Parameter plots) from STOQS.
    '''

    def _getData(self, startDatetime, endDatetime):
        '''
        Use the command line arguments and the SQL template to retrieve the X and Y
        values and other ancillary information from the database
        '''
        # SQL template copied from STOQS UI Parameter-Parameter -> sql tab
        sql_template = '''SELECT DISTINCT stoqs_measurement.depth,
                mp_x.datavalue AS x, mp_y.datavalue AS y,
                ST_X(stoqs_measurement.geom) AS lon, ST_Y(stoqs_measurement.geom) AS lat,
                stoqs_instantpoint.timevalue 
            FROM stoqs_activity
            INNER JOIN stoqs_platform ON stoqs_platform.id = stoqs_activity.platform_id
            INNER JOIN stoqs_instantpoint ON stoqs_instantpoint.activity_id = stoqs_activity.id
            INNER JOIN stoqs_measurement ON stoqs_measurement.instantpoint_id = stoqs_instantpoint.id
            INNER JOIN stoqs_measurement m_y ON m_y.instantpoint_id = stoqs_instantpoint.id
            INNER JOIN stoqs_measuredparameter mp_y ON mp_y.measurement_id = m_y.id
            INNER JOIN stoqs_parameter p_y ON mp_y.parameter_id = p_y.id
            INNER JOIN stoqs_measurement m_x ON m_x.instantpoint_id = stoqs_instantpoint.id
            INNER JOIN stoqs_measuredparameter mp_x ON mp_x.measurement_id = m_x.id
            INNER JOIN stoqs_parameter p_x ON mp_x.parameter_id = p_x.id
            WHERE (p_x.name = '{pxname}')
                AND (p_y.name = '{pyname}')
                AND (stoqs_instantpoint.timevalue >= '{start}'
                AND stoqs_instantpoint.timevalue <= '{end}')
                AND stoqs_platform.name IN ('{platform}')
                {day_night_clause}
            ORDER BY stoqs_instantpoint.timevalue '''

        # Get connection to database; self.args.database must be defined in privateSettings
        cursor = connections[self.args.database].cursor()

        # Apply SQL where clause to restrict to just do or night measurements
        daytimeHours = (17, 22)
        nighttimeHours = (5, 10)
        dnSQL = ''
        if self.args.daytime:
            dnSQL = "AND date_part('hour', stoqs_instantpoint.timevalue) > %d AND date_part('hour', stoqs_instantpoint.timevalue) < %d" % daytimeHours
        if self.args.nighttime:
            dnSQL = "AND date_part('hour', stoqs_instantpoint.timevalue) > %d AND date_part('hour', stoqs_instantpoint.timevalue) < %d" % nighttimeHours

        sql = sql_template.format(start=startDatetime, end=endDatetime, pxname=self.args.xParm, pyname=self.args.yParm, 
                                    platform=self.args.platform, day_night_clause=dnSQL)
        if self.args.verbose:
            print "sql =", sql

        x = [] 
        y = []
        points = []
        cursor.execute(sql)
        for row in cursor:
            x.append(float(row[1]))
            y.append(float(row[2]))
            points.append(Point(float(row[3]), float(row[4])))

        return x, y, points

    def _getActivityInfo(self):
        '''
        Get details of the Activities that the platform has. 
        '''
        # Get start and end datetimes, color and geographic extent of the activity
        aQS = Activity.objects.using(self.args.database).filter(platform__name=self.args.platform)
        seaQS = aQS.aggregate(Min('startdate'), Max('enddate'))
        self.activityStartTime = seaQS['startdate__min'] 
        self.activityEndTime = seaQS['enddate__max']
        try:
            self.color = '#' + Platform.objects.using(self.args.database).filter(name=self.args.platform).values_list('color')[0][0]
        except IndexError, e:
            print "Error: Unable to get color of platform name", self.args.platform
            sys.exit(-1)

        self.extent = aQS.extent(field_name='maptrack')

    def _getAxisInfo(self, parm):
        '''
        Return appropriate min and max values and units for a parameter name
        '''
        # Get the 1 & 99 percentiles of the data for setting limits on the scatter plot
        apQS = ActivityParameter.objects.using(self.args.database).filter(activity__platform__name=self.args.platform)
        pQS = apQS.filter(parameter__name=parm).aggregate(Min('p010'), Max('p990'))
        min, max = (pQS['p010__min'], pQS['p990__max'])

        # Get units for each parameter
        prQS = ParameterResource.objects.using(self.args.database).filter(resource__name='units').values_list('resource__value')
        try:
            units = prQS.filter(parameter__name=parm)[0][0]
        except IndexError, e:
            print "Error: Unable to get units for parameter name", parm
            sys.exit(-1)

        return min, max, units

