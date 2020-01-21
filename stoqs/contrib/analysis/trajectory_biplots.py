#!/usr/bin/env python
'''
Script to query the database for measured parameters from the same instantpoint and to
make scatter plots of temporal segments of the data.  A simplified trackline of the
trajectory data and the start time of the temporal segment are added to each plot.

Make use of STOQS metadata to make it as simple as possible to use this script for
different platforms, parameters, and campaigns.

Mike McCann
MBARI Dec 6, 2013
'''

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
import django
django.setup()

import re
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from matplotlib.dates import DAILY
from matplotlib.colors import rgb2hex
from collections import defaultdict
from datetime import datetime, timedelta
from django.contrib.gis.geos import LineString
from utils.utils import round_to_n
from stoqs.models import MeasuredParameterResource, Resource
from textwrap import wrap
from mpl_toolkits.basemap import Basemap
import matplotlib.gridspec as gridspec

from contrib.analysis import BiPlot, NoPPDataException, NoTSDataException


class PlatformsBiPlot(BiPlot):
    '''
    Make customized BiPlots (Parameter Parameter plots) for platforms from STOQS.
    '''
    def ppSubPlot(self, x, y, platform, color, xParm, yParm, ax, point_color='k'):
        '''
        Given names of platform, x & y paramters add a subplot to figure fig.
        '''
        xmin, xmax, xUnits = self._getAxisInfo(platform, xParm)
        ymin, ymax, yUnits = self._getAxisInfo(platform, yParm)

        # Make the plot 
        ax.set_xlim(round_to_n(xmin, 1), round_to_n(xmax, 1))
        ax.set_ylim(round_to_n(ymin, 1), round_to_n(ymax, 1))

        if self.args.xLabel == '':
            ax.set_xticks([])
        elif self.args.xLabel:
            ax.set_xlabel(self.args.xLabel)
        else:
            ax.set_xlabel('%s (%s)' % (xParm, xUnits))

        if self.args.yLabel == '':
            ax.set_yticks([])
        elif self.args.yLabel:
            ax.set_ylabel(self.args.yLabel)
        else:
            ax.set_ylabel('%s (%s)' % (yParm, yUnits))

        ax.scatter(x, y, marker='.', s=10, c=point_color, lw = 0, clip_on=True)
        ax.text(0.0, 1.0, platform, transform=ax.transAxes, color=color, horizontalalignment='left', verticalalignment='top')

        return ax

    def ppSubPlotColor(self, x_ids, y_ids, platform, color, xParm, yParm, ax):
        '''
        Given names of platform, x & y paramter ids return a categorically colored subplot
        See: https://gist.github.com/jakevdp/8a992f606899ac24b711
        and https://stackoverflow.com/questions/28033046/matplotlib-scatter-color-by-categorical-factors?answertab=active#tab-top
        '''
        all_labels = (Resource.objects.using(self.args.database)
                        .filter(resourcetype__name__contains=self.args.groupName)
                        .order_by('value')
                        .distinct()
                        .values_list('value', flat=True))
        if not all_labels:
            raise ValueError(f'Found no resources containing --groupName {self.args.groupName}')
        total_num_colors = len(all_labels)

        colors = {}
        if total_num_colors < 11:
            ck = plt.cm.Vega10
        elif total_num_colors < 21:
            ck = plt.cm.Vega20
        else:
            cl = plt.cm.viridis

        for b, c in zip(all_labels, ck(np.arange(0, ck.N, ck.N/total_num_colors, dtype=int))):
            colors[b] = c

        mprs = MeasuredParameterResource.objects.using(self.args.database).filter(
                        resource__resourcetype__name__contains=self.args.groupName,
                        measuredparameter__id__in=(x_ids + y_ids))

        if self.args.verbose:
            print(f'{mprs.count()} mprs for {self.args.groupName}')

        for label in all_labels:
            xy_data = defaultdict(list)
            for mpr in mprs.filter(resource__value=label):
                xy_data[mpr.measuredparameter.parameter.name].append(mpr.measuredparameter.datavalue)
            if xy_data: 
                if self.args.verbose:
                    print(f'{len(xy_data[xParm])} points for {label}, color = {colors[label]}')
                ax.scatter(xy_data[xParm], xy_data[yParm], marker='.', s=15, label=label, 
                           color=colors[label], clip_on=True)

        ax.legend(loc='upper left', fontsize=7)
        ax.text(1.0, 1.0, platform, transform=ax.transAxes, color=color, horizontalalignment='right', verticalalignment='top')

        xmin, xmax, xUnits = self._getAxisInfo(platform, xParm)
        ymin, ymax, yUnits = self._getAxisInfo(platform, yParm)

        ax.set_xlim(round_to_n(xmin, 1), round_to_n(xmax, 1))
        ax.set_ylim(round_to_n(ymin, 1), round_to_n(ymax, 1))

        if self.args.xLabel == '':
            ax.set_xticks([])
        elif self.args.xLabel:
            ax.set_xlabel(self.args.xLabel)
        else:
            ax.set_xlabel('%s (%s)' % (xParm, xUnits))

        if self.args.yLabel == '':
            ax.set_yticks([])
        elif self.args.yLabel:
            ax.set_ylabel(self.args.yLabel)
        else:
            ax.set_ylabel('%s (%s)' % (yParm, yUnits))

        return ax


    def timeSubPlot(self, platformDTHash, ax1, startTime, endTime, swrTS):
        '''
        Make subplot of depth time series for all the platforms and highlight the time range
        '''
        for pl, ats in list(platformDTHash.items()):
            color = self._getColor(pl)
            for _, ts in list(ats.items()):
                datetimeList = []
                depths = []
                for ems, d in ts:
                    datetimeList.append(datetime.utcfromtimestamp(ems/1000.0))
                    depths.append(d)
           
                ax1.plot_date(matplotlib.dates.date2num(datetimeList), depths, '-', c=color, alpha=0.2)

        # Highlight the selected time extent
        ax1.axvspan(*matplotlib.dates.date2num([startTime, endTime]), facecolor='k', alpha=0.6)  

        if self.args.minDepth is not None:
            ax1.set_ylim(bottom=self.args.minDepth)
        if self.args.maxDepth:
            ax1.set_ylim(top=self.args.maxDepth)
        ax1.set_ylim(ax1.get_ylim()[::-1])

        if swrTS:
            # Plot short wave radiometer data
            if self.args.verbose: print('Plotting swrTS...')
            ax2 = ax1.twinx()
            ax2.plot_date(matplotlib.dates.date2num(swrTS[0]), swrTS[1], '-', c='black', alpha=0.5)
            ax2.set_ylabel('SWR (W/m^2)')
            plt.locator_params(axis='y', nbins=3)
        
        ax1.set_ylabel('Depth (m)')

        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%Y'))
        plt.gca().xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
        plt.gca().xaxis.set_minor_locator(mdates.DayLocator())

        return ax1

    def spatialSubPlot(self, platformLineStringHash, ax, e, resolution='l'):
        '''
        Make subplot of tracks for all the platforms within the time range. 
        '''
        m = Basemap(llcrnrlon=e[0], llcrnrlat=e[1], urcrnrlon=e[2], urcrnrlat=e[3], projection='cyl', resolution=resolution, ax=ax)
        ##m.wmsimage('http://www.gebco.net/data_and_products/gebco_web_services/web_map_service/mapserv?', layers=['GEBCO_08_Grid'])    # Works, but coarse
        m.arcgisimage(server='http://services.arcgisonline.com/ArcGIS', service='Ocean_Basemap')
 
        for pl, LS in list(platformLineStringHash.items()):
            x,y = list(zip(*LS))
            m.plot(x, y, '-', c=self._getColor(pl), linewidth=3)

        if self.args.mapLabels:
            m.drawparallels(np.linspace(e[1],e[3],num=3), labels=[True,False,False,False], linewidth=0)
            m.drawmeridians(np.linspace(e[0],e[2],num=3), labels=[False,False,False,True], linewidth=0)

        return ax

    def getFilename(self, startTime):
        '''
        Construct plot file name
        '''
        if self.args.title:
            p = re.compile('[\s()]')
            fnTempl = p.sub('_', self.args.title) + '_{time}'
        else:
            fnTempl= 'platforms_{time}' 
            
        fileName = fnTempl.format(time=startTime.strftime('%Y%m%dT%H%M'))
        wcName = fnTempl.format(time=r'*')
        wcName = os.path.join(self.args.plotDir, self.args.plotPrefix + wcName)
        if self.args.daytime:
            fileName += '_day'
            wcName += '_day'
        if self.args.nighttime:
            fileName += '_night'
            wcName += '_night'
        fileName += '.png'

        fileName = os.path.join(self.args.plotDir, self.args.plotPrefix + fileName)

        return fileName, wcName

    def makePlatformsBiPlots(self):
        '''
        Cycle through all the platforms & parameters (there will be more than one) and make the correlation plots
        for the interval as subplots on the same page.  Include a map overview and timeline such that if a movie 
        is made of the resulting images a nice story is told.  Layout of the plot page is like:

         D  +-------------------------------------------------------------------------------------------+
         e  |                                                                                           |
         p  |                                                                                           |
         t  |                                                                                           |
         h  +-------------------------------------------------------------------------------------------+
                                                        Time

            +---------------------------------------+           +-------------------+-------------------+
            |                                       |           |                   |                   |
            |                                       |         y |                   |                   |
         L  |                                       |         P |                   |                   |
         a  |                                       |         a |    Platform 0     |    Platform 1     |
         t  |                                       |         r |                   |                   |
         i  |                                       |         m |                   |                   |
         t  |                                       |           |                   |                   |
         u  |                                       |           +-------------------+-------------------+
         d  |                                       |           |                   |                   |
         e  |                                       |         y |                   |                   |
            |                                       |         P |                   |                   |
            |                                       |         a |    Platform 2     |    Platform 3     |
            |                                       |         r |                   |                   |
            |                                       |         m |                   |                   |
            |                                       |           |                   |                   |
            +---------------------------------------+           +-------------------+-------------------+
                           Longitude                                    xParm               xParm

        '''
        # Nested GridSpecs for Subplots
        outer_gs = gridspec.GridSpec(2, 1, height_ratios=[1,4])
        time_gs  = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=outer_gs[0])
        lower_gs = gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=outer_gs[1])
        map_gs   = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=lower_gs[0])
        plat1_gs = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=lower_gs[1])
        plat4_gs = gridspec.GridSpecFromSubplotSpec(2, 2, subplot_spec=lower_gs[1], wspace=0.0, hspace=0.0, width_ratios=[1,1], height_ratios=[1,1])

        # Get overall temporal and spatial extents of platforms requested
        allActivityStartTime, allActivityEndTime, allExtent  = self._getActivityExtent(self.args.platform)

        # Setup the time windowing and stepping - if none specified then use the entire extent that is in the database
        if self.args.hourStep:
            timeStep = timedelta(hours=self.args.hourStep)
            if self.args.hourWindow:
                timeWindow = timedelta(hours=self.args.hourWindow)
            else:
                if self.args.hourStep:
                    timeWindow = timedelta(hours=self.args.hourStep)
        else:
            timeWindow = allActivityEndTime - allActivityStartTime
            timeStep = timeWindow

        if self.args.start:
            startTime = datetime.strptime(self.args.start, '%Y%m%dT%H%M%S')
        else:
            startTime = allActivityStartTime

        endTime = startTime + timeWindow

        # Get overall temporal data for placement in the temporal subplot
        platformDTHash = self._getplatformDTHash()
        try:
            swrTS = self._getTimeSeriesData(allActivityStartTime, allActivityEndTime, parameterStandardName='surface_downwelling_shortwave_flux_in_air')
        except NoTSDataException as e:
            swrTS = None
            print("WARNING:", e)

        if self.args.end:
            set_end_time = datetime.strptime(self.args.end, '%Y%m%dT%H%M%S')
        else:
            set_end_time = allActivityEndTime

        # Loop through sections of the data with temporal query constraints based on the window and step command line parameters
        while endTime <= set_end_time:

            # Start a new figure - size is in inches
            fig = plt.figure(figsize=(9, 6))

            # Plot temporal overview
            ax = plt.Subplot(fig, time_gs[:])
            fig.add_subplot(ax)
            if self.args.title:
                ax.set_title(self.args.title)
            self.timeSubPlot(platformDTHash, ax, startTime, endTime, swrTS)

            # Make scatter plots of data from the platforms 
            platformLineStringHash = {}
            for i, (pl, xP, yP) in enumerate(zip(self.args.platform, self.args.xParm, self.args.yParm)):
                try: 
                    x_ids, y_ids, x, y, points = self._getPPData(startTime, endTime, pl, xP, yP, returnIDs=True)
                    platformLineStringHash[pl] = LineString(points).simplify(tolerance=.001)
                except (NoPPDataException, ValueError) as e:
                    if self.args.verbose: print(e)
                    x, y = ([], [])

                if len(self.args.platform) == 1:
                    ax = plt.Subplot(fig, plat1_gs[0])
                elif len(self.args.platform) < 5:
                    ax = plt.Subplot(fig, plat4_gs[i])
                else:
                    raise Exception('Cannot handle more than 4 platform Parameter-Parameter plots')

                fig.add_subplot(ax)
                if self.args.groupName:
                    self.ppSubPlotColor(x_ids, y_ids, pl, self._getColor(pl), xP, yP, ax)
                else:
                    self.ppSubPlot(x, y, pl, self._getColor(pl), xP, yP, ax)

            # Plot spatial
            ax = plt.Subplot(fig, map_gs[:])
            fig.add_subplot(ax, aspect='equal')
            self.spatialSubPlot(platformLineStringHash, ax, allExtent)
           
            startTime = startTime + timeStep
            endTime = startTime + timeWindow

            provStr = 'Created with STOQS command ' + '\\\n'.join(wrap(self.commandline, width=100)) + ' on ' + datetime.now().ctime() + ' GMT'
            plt.figtext(0.0, 0.0, provStr, size=7, horizontalalignment='left', verticalalignment='bottom')

            fileName, wcName = self.getFilename(startTime)
            print('Saving to file', fileName)
            fig.savefig(fileName)
            plt.clf()
            plt.close()
            ##raw_input('P')

        print('Done.')
        print('Make an animated gif with: convert -delay 10 {wcName}.png {baseName}.gif'.format(wcName=wcName, baseName='_'.join(fileName.split('_')[:-1])))
        print('Make an MPEG 4 with: ffmpeg -r 10 -i {baseName}.gif -vcodec mpeg4 -qscale 1 -y {baseName}.mp4'.format(
                baseName='_'.join(fileName.split('_')[:-1])))
        print('On a Mac open the .mp4 file in QuickTime Player and export the file for "iPad, iPhone & Apple TV" (.m4v format) for best portability.')

    def process_command_line(self):
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n\n' 
        examples += sys.argv[0] + " -d stoqs_september2013 -p tethys Slocum_294 daphne Slocum_260 -x bb650 optical_backscatter660nm bb650 optical_backscatter700nm -y chlorophyll fluorescence chlorophyll fluorescence --plotDir /tmp --plotPrefix stoqs_september2013_ --hourStep 1 --hourWindow 2 --xLabel '' --yLabel '' --title 'Fl vs. bb (red)' --minDepth 0 --maxDepth 100\n"
        examples += sys.argv[0] + ' -d stoqs_september2013_o -p dorado Slocum_294 tethys -x bbp420 optical_backscatter470nm bb470 -y fl700_uncorr fluorescence chlorophyll\n'
        examples += sys.argv[0] + ' -d stoqs_march2013_o -p daphne tethys -x bb470 bb470 -y chlorophyll chlorophyll --hourStep 6 --hourWindow 12\n'
        examples += '\n\nMultiple platform and parameter names are paired up in respective order.\n'
        examples += '\nIf running from cde-package replace ".py" with ".py.cde" in the above list.'
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Read Parameter-Parameter data from a STOQS database and make bi-plots',
                                         epilog=examples)
                                             
        parser.add_argument('-x', '--xParm', action='store', help='One or more Parameter names for the X axis', 
                nargs='*', default='bb470', required=True)
        parser.add_argument('-y', '--yParm', action='store', help='One or more Parameter names for the Y axis', 
                nargs='*', default='chlorophyll', required=True)
        parser.add_argument('-p', '--platform', action='store', help='One or more platform names separated by spaces', 
                nargs='*', default='tethys', required=True)
        parser.add_argument('-d', '--database', action='store', help='Database alias', default='stoqs_september2013_o', required=True)
        parser.add_argument('--hourWindow', action='store', help='Window in hours for interval plot. If not specified it will be the same as hourStep.', 
                type=int)
        parser.add_argument('--hourStep', action='store', help='Step though the time series and make plots at this hour interval', type=int)
        parser.add_argument('--daytime', action='store_true', help='Select only daytime hours: 10 am to 2 pm local time')
        parser.add_argument('--nighttime', action='store_true', help='Select only nighttime hours: 10 pm to 2 am local time')
        parser.add_argument('--minDepth', action='store', help='Minimum depth for data queries', default=None, type=float)
        parser.add_argument('--maxDepth', action='store', help='Maximum depth for data queries', default=None, type=float)
        parser.add_argument('--plotDir', action='store', help='Directory where to write the plot output', default='.')
        parser.add_argument('--plotPrefix', action='store', help='Prefix to use in naming plot files', default='')
        parser.add_argument('--xLabel', action='store', help='Override Parameter-Parameter X axis label - will be applied to all plots')
        parser.add_argument('--yLabel', action='store', help='Override Parameter-Parameter Y axis label - will be applied to all plots') 
        parser.add_argument('--mapLabels', action='store_true', help='Put latitude and longitude labels and tics on the map')
        parser.add_argument('--platformColors', action='store', help='Override database platform colors - put in quotes, e.g. "#ff0000"', nargs='*')
        parser.add_argument('--title', action='store', help='Title to appear on top of plot')
        parser.add_argument('--extend', action='store', help='Extend the data extent for the map boundaries by this value in degrees', type=float)
        parser.add_argument('--extent', action='store', help='Space separated specific map boundary in degrees: ll_lon ll_lat ur_lon ur_lat', 
                nargs=4, default=[])
        parser.add_argument('--start', action='store', help='Start time in YYYYMMDDTHHMMSS format, otherwise allActivityStartTime is used')
        parser.add_argument('--end', action='store', help='End time in YYYYMMDDTHHMMSS format, otherwise allActivityEndTime is used')
        parser.add_argument('--groupName', action='store', help='Color points in scatter plots according to labels or clusters in groupName')
        parser.add_argument('-v', '--verbose', nargs='?', choices=[1,2,3], type=int, help='Turn on verbose output. Higher number = more output.', const=1, default=0)
    
        self.args = parser.parse_args()
        self.commandline = ""
        for item in sys.argv:
            if item == '':
                # Preserve empty string specifications in the command line
                self.commandline += "''" + ' '
            else:
                self.commandline += item + ' '
    
    
if __name__ == '__main__':

    bp = PlatformsBiPlot()
    bp.process_command_line()
    if len(bp.args.platform) > 0:
        bp.makePlatformsBiPlots()
    else:
        bp.makePlatformsBiPlots()

