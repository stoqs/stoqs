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
from datetime import datetime, timedelta
from django.contrib.gis.geos import LineString, Point
from utils.utils import round_to_n

from contrib.analysis import BiPlot

class PlatformsBiPlot(BiPlot):
    '''
    Make customized BiPlots (Parameter Parameter plots) for platforms from STOQS.
    '''

    def xySubPlot(self, x, y, platform, color, xParm, yParm, fig, subplot, startTime):
        '''
        Given names of platform, x & y paramters add a subplot to figure fig.
        '''

        xmin, xmax, xUnits = self._getAxisInfo(platform, xParm)
        ymin, ymax, yUnits = self._getAxisInfo(platform, yParm)

        # Make the plot 
        ax = fig.add_subplot(int(subplot))
        ax.set_xlim(round_to_n(xmin, 1), round_to_n(xmax, 1))
        ax.set_ylim(round_to_n(ymin, 1), round_to_n(ymax, 1))
        ax.set_xlabel('%s (%s)' % (xParm, xUnits))
        ax.set_ylabel('%s (%s)' % (yParm, yUnits))
        ax.set_title('%s' % (platform,)) 
        ##ax.set_title('%s from %s' % (platform, self.args.database)) 
        ax.scatter(x, y, marker='.', s=10, c='k', lw = 0, clip_on=False)
        ##ax.plot(xp, yp, c=color)
        ##ax.text(0.1, 0.8, startTime.strftime('%Y-%m-%d %H:%M'), transform=ax.transAxes)

    def makeIntervalPlots(self):
        '''
        Make a plot each timeInterval starting at startTime
        '''

        self._getActivityInfo(self.args.platform)
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
            x, y, points = self._getData(startTime, endTime, self.args.platform, self.args.xParm, self.args.yParm)
        
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
            fnTempl= '{platform}_{xParm}_{yParm}_{time}' 
            fileName = fnTempl.format(platform=self.args.platform, xParm=self.args.xParm, yParm=self.args.yParm, time=startTime.strftime('%Y%m%dT%H%M'))
            wcName = fnTempl.format(platform=self.args.platform, xParm=self.args.xParm, yParm=self.args.yParm, time=r'*')
            if self.args.daytime:
                fileName += '_day'
                wcName += '_day'
            if self.args.nighttime:
                fileName += '_night'
                wcName += '_night'
            fileName += '.png'

            fig.savefig(fileName)
            print 'Saved file', fileName
            plt.close()
    
            startTime = endTime
            endTime = startTime + timeInterval

        print 'Done. Make an animated gif with: convert -delay 100 {wcName}.png {gifName}.gif'.format(wcName=wcName, gifName='_'.join(fileName.split('_')[:3]))

    def makePlatformsPlots(self):
        '''
        Cycle through all the platforms & parameters (there will be more than one) and make the correlation plots
        for the interval as subplots on the same page.  Include a map overview and timeline such that if a movie 
        is made of the resulting images a nice story is told.
        '''
        allActivityStartTime, allActivityEndTime, color, extent  = self._getActivityInfo(self.args.platform)
        if self.args.hourInterval:
            timeInterval = timedelta(hours=self.args.hourInterval)
        else:
            timeInterval = allActivityEndTime - allActivityStartTime
        startTime = allActivityStartTime
        endTime = startTime + timeInterval

        # Default subplot is 2 rows, 2 columns.  If len(self.args.platform) > 4 then must change this.
        subplot_base = '22'
        while endTime <= allActivityEndTime:
 
            i = 0
            fig = plt.figure()
            for pl, xP, yP in zip(self.args.platform, self.args.xParm, self.args.yParm):
                i = i + 1
                activityStartTime, activityEndTime, color, extent  = self._getActivityInfo(pl)

                if self.args.verbose:
                    print "Making time interval plots for platform", pl
                    print "Activity start:", activityStartTime
                    print "Activity end:  ", activityEndTime
                    print "Time Interval =", timeInterval
    
                # Pull out data and plot at timeInterval intervals
                x, y, points = self._getData(startTime, endTime, pl, xP, yP)
            
                if len(points) < 2:
                    startTime = endTime
                    endTime = startTime + timeInterval
                    continue
                path = LineString(points).simplify(tolerance=.001)

                subplot = subplot_base + str(i)
                self.xySubPlot(x, y, pl, color, xP, yP, fig, subplot, startTime)

            startTime = endTime
            endTime = startTime + timeInterval

            fnTempl= 'platforms_{time}' 
            fileName = fnTempl.format(time=startTime.strftime('%Y%m%dT%H%M'))
            wcName = fnTempl.format(time=r'*')
            if self.args.daytime:
                fileName += '_day'
                wcName += '_day'
            if self.args.nighttime:
                fileName += '_night'
                wcName += '_night'
            fileName += '.png'

            fig.savefig(fileName)
            print 'Saved file', fileName

            plt.close()

        print 'Done. Make an animated gif with: convert -delay 100 {wcName}.png {gifName}.gif'.format(wcName=wcName, gifName='_'.join(fileName.split('_')[:3]))

    def process_command_line(self):
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n\n' 
        examples += sys.argv[0] + ' -d stoqs_september2013_o -p dorado Slocum_294 tethys -x bbp420 optical_backscatter470nm bb470 -y fl700_uncorr fluorescence chlorophyll\n'
        examples += sys.argv[0] + ' -d stoqs_september2013_o -p dorado -x bbp420 -y fl700_uncorr\n'
        examples += sys.argv[0] + ' -d stoqs_september2013_o -p tethys -x bb470 -y chlorophyll --hourInterval 24\n'
        examples += sys.argv[0] + ' -d stoqs_september2013_o -p Slocum_294 -x optical_backscatter470nm -y fluorescence --hourInterval 24\n'
        examples += sys.argv[0] + ' -d stoqs_september2013_o -p dorado -x bbp420 -y fl700_uncorr\n'
        examples += sys.argv[0] + ' -d stoqs_march2013_o -p dorado -x bbp420 -y fl700_uncorr\n'
        examples += sys.argv[0] + ' -d stoqs_march2013_o -p daphne -x bb470 -y chlorophyll\n'
        examples += sys.argv[0] + ' -d stoqs_march2013_o -p tethys -x bb470 -y chlorophyll\n'
        examples += sys.argv[0] + ' -d stoqs_march2013_o -p tethys -x bb470 -y chlorophyll --daytime\n'
        examples += sys.argv[0] + ' -d stoqs_march2013_o -p tethys -x bb470 -y chlorophyll --nighttime\n'
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Read Parameter-Parameter data from a STOQS database and make bi-plots',
                                         epilog=examples + '\n\nMultiple platform and parameter names are paired up in order.\n(Image files will be written to the current working directory)')
                                             
        parser.add_argument('-x', '--xParm', action='store', help='One or more Parameter names for the X axis', nargs='*', default='bb470')
        parser.add_argument('-y', '--yParm', action='store', help='One or more Parameter names for the Y axis', nargs='*', default='chlorophyll')
        parser.add_argument('-p', '--platform', action='store', help='One or more platform names separated by spaces', nargs='*', default='tethys')
        parser.add_argument('-d', '--database', action='store', help='Database alias', default='stoqs_september2013_o')
        parser.add_argument('--hourInterval', action='store', help='Step though the time series and make plots at this hour interval', type=int)
        parser.add_argument('--daytime', action='store_true', help='Select only daytime hours: 10 am to 2 pm local time')
        parser.add_argument('--nighttime', action='store_true', help='Select only nighttime hours: 10 pm to 2 am local time')
        parser.add_argument('-v', '--verbose', action='store_true', help='Turn on verbose output')
    
        self.args = parser.parse_args()
    
    
if __name__ == '__main__':

    bp = PlatformsBiPlot()
    bp.process_command_line()
    if len(bp.args.platform) > 1:
        bp.makePlatformsPlots()
    else:
        bp.makeIntervalPlots()

