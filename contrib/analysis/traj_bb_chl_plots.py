#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2013, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

Script to query the database for measured parameters from the same instantpoint and to
make scatter plots of temporal segments of the data.  A simplified trackline of the
trajectory data and the start time of the temporal segment are added to each plot.

Make use of STOQS metadata to make it as simple as possible to use this script for
different platforms, parameters, and campaigns.

Mike McCann
MBARI Dec 6, 2013

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

import matplotlib.pyplot as plt
from django.db import connections
from datetime import datetime, timedelta
from stoqs.models import Activity, ActivityParameter, ParameterResource, Platform
from django.contrib.gis.geos import LineString, Point
from django.db.models import Max, Min
from utils.utils import round_to_n


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

    def makeIntervalPlots(self):
        '''
        Make a plot each timeInterval starting at startTime
        '''

        self._getActivityInfo()
        xmin, xmax, xUnits = self._getAxisInfo(self.args.xParm)
        ymin, ymax, yUnits = self._getAxisInfo(self.args.yParm)

        if self.args.hourInterval:
            timeInterval = timedelta(hours=self.args.hourInterval)
        else:
            timeInterval = self.activityEndTime - self.activityStartTime
 
        if self.args.verbose:
            print "Making time interval plots for platform", self.args.platform
            print "Activity start:", self.activityStartTime
            print "Activity end:  ", self.activityEndTime
            print "Time Interval =", timeInterval

        # Pull out data and plot at timeInterval intervals
        startTime = self.activityStartTime
        endTime = startTime + timeInterval
        while endTime <= self.activityEndTime:
            x, y, points = self._getData(startTime, endTime)
        
            if len(points) < 2:
                startTime = endTime
                endTime = startTime + timeInterval
                continue

            path = LineString(points).simplify(tolerance=.001)
        
            fig = plt.figure()
            plt.grid(True)
            ax = fig.add_subplot(111)
    
            # Scale path points to appear in upper right of the plot as a crude indication of the track
            xp = []
            yp = []
            for p in path:
                xp.append(0.30 * (p[0] - self.extent[0]) * (xmax - xmin) / (self.extent[2] - self.extent[0]) + 0.70 * (xmax - xmin))
                yp.append(0.18 * (p[1] - self.extent[1]) * (ymax - ymin) / (self.extent[3] - self.extent[1]) + 0.75 * (ymax - ymin))
       
            # Make the plot 
            ax.set_xlim(round_to_n(xmin, 1), round_to_n(xmax, 1))
            ax.set_ylim(round_to_n(ymin, 1), round_to_n(ymax, 1))
            ax.set_xlabel('%s (%s)' % (self.args.xParm, xUnits))
            ax.set_ylabel('%s (%s)' % (self.args.yParm, yUnits))
            ax.set_title('%s from %s' % (self.args.platform, self.args.database)) 
            ax.scatter(x, y, marker='.', s=10, c='k', lw = 0, clip_on=False)
            ax.plot(xp, yp, c=self.color)
            ax.text(0.1, 0.8, startTime.strftime('%Y-%m-%d %H:%M'), transform=ax.transAxes)
            fileName = 'chl_bb_' + startTime.strftime('%Y%m%dT%H%M')
            if self.args.daytime:
                fileName += '_day'
            if self.args.nighttime:
                fileName += '_night'
            fileName += '.png'

            fig.savefig(fileName)
            print 'Saved file', fileName
            plt.close()
    
            startTime = endTime
            endTime = startTime + timeInterval

        print 'Done. Make an animated gif with: convert -delay 100 chl_bb_*.png chl_bb_%s.gif' % self.args.platform

    def process_command_line(self):
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n\n' 
        examples += sys.argv[0] + ' -d stoqs_september2013_o -p dorado -x bbp420 -y fl700_uncorr\n'
        examples += sys.argv[0] + ' -d stoqs_march2013_o -p dorado -x bbp420 -y fl700_uncorr\n'
        examples += sys.argv[0] + ' -d stoqs_march2013_o -p daphne -x bb470 -y chlorophyll\n'
        examples += sys.argv[0] + ' -d stoqs_march2013_o -p tethys -x bb470 -y chlorophyll\n'
        examples += sys.argv[0] + ' -d stoqs_march2013_o -p tethys -x bb470 -y chlorophyll --daytime\n'
        examples += sys.argv[0] + ' -d stoqs_march2013_o -p tethys -x bb470 -y chlorophyll --nighttime\n'
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Read Parameter-Parameter data from a STOQS database and make bi-plots',
                                         epilog=examples)
                                             
        parser.add_argument('-x', '--xParm', action='store', help='Parameter name for the X axis', default='bb470')
        parser.add_argument('-y', '--yParm', action='store', help='Parameter name for the Y axis', default='chlorophyll')
        parser.add_argument('-p', '--platform', action='store', help='Platform name', default='tethys')
        parser.add_argument('-d', '--database', action='store', help='Database alias', default='stoqs_september2013_o')
        parser.add_argument('--hourInterval', action='store', help='Step though the time series and make plots at this hour interval', type=int)
        parser.add_argument('--daytime', action='store_true', help='Select only daytime hours: 10 am to 2 pm local time')
        parser.add_argument('--nighttime', action='store_true', help='Select only nighttime hours: 10 pm to 2 am local time')
        parser.add_argument('-v', '--verbose', action='store_true', help='Turn on verbose output')
    
        self.args = parser.parse_args()
    
    
if __name__ == '__main__':

    bp = BiPlot()
    bp.process_command_line()
    bp.makeIntervalPlots()

