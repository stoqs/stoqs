#!/usr/bin/env python
__author__    = 'D.Cline'
__version__ = '$Revision: $'.split()[1]
__date__ = '$Date: $'.split()[1]
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'dcline at mbari.org'

__doc__ = '''

Creates still and animated contour and dot plots plots from MBARI LRAUV data

D Cline
MBARI 25 September 2015

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE']='settings'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))  # settings.py is one dir up
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from django.contrib.gis.geos import LineString, MultiLineString, Point
import numpy as np
import re
import time
import pytz
import logging
import signal
import datetime
import ephem
import bisect
import tempfile
import shutil

from django.contrib.gis.geos import fromstr, MultiPoint
from django.db.models import Max, Min
from collections import OrderedDict
from collections import defaultdict
from django.db import connections
from datetime import datetime, timedelta, tzinfo
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
#from matplotlib.mlab import griddata
from numpy import arange
from scipy.interpolate import griddata
from scipy.spatial import ckdtree
from scipy.interpolate import Rbf
from mpl_toolkits.basemap import Basemap
from stoqs.models import Activity, ActivityParameter, ParameterResource, Platform, SimpleDepthTime, MeasuredParameter, Measurement, Parameter
from utils.utils import percentile
from matplotlib.transforms import Bbox, TransformedBbox,  blended_transform_factory
from matplotlib import dates
from mpl_toolkits.axes_grid1.inset_locator import BboxPatch, BboxConnector, BboxConnectorPatch

# Set up global variables for logging output to STDOUT
logger = logging.getLogger('monitorTethysHotSpotLogger')
fh = logging.StreamHandler()
f = logging.Formatter("%(levelname)s %(asctime)sZ %(filename)s %(funcName)s():%(lineno)d %(message)s")
fh.setFormatter(f)
logger.addHandler(fh)
logger.setLevel(logging.DEBUG)

class NoPPDataException(Exception):
    pass

class Contour(object):

    '''
    Create plots for visualizing data from LRAUV vehicles
    '''
    def __init__(self, startDatetime, endDatetime, database, platformName, plotGroup, title, outFilename, autoscale, plotDotParmName, booleanPlotGroup, animate=False, zoom=6, overlap=3):
        self.startDatetime = startDatetime
        self.endDatetime = endDatetime
        self.platformName = platformName
        self.plotGroup = plotGroup
        self.plotGroupValid = []
        self.title = title
        self.animate = animate
        self.outFilename = outFilename
        self.database = database
        self.autoscale = autoscale
        self.plotDotParmName = plotDotParmName
        self.booleanPlotGroup = booleanPlotGroup
        self.zoom = zoom
        self.overlap = overlap
        self.dirpath = []

    def getActivityExtent(self,startDatetime, endDatetime):
        '''
        Get spatial temporal extent for a platform.
        '''
        qs = Activity.objects.using(self.database).filter(platform__name__in=self.platformName)
        qs = qs.filter(startdate__gte=startDatetime)
        qs = qs.filter(enddate__lte=endDatetime)
        seaQS = qs.aggregate(Min('startdate'), Max('enddate'))
        self.activityStartTime = seaQS['startdate__min']
        self.activityEndTime = seaQS['enddate__max']
        dataExtent = qs.extent(field_name='maptrack')
        return dataExtent

    def getAxisInfo(self, parm):
        '''
        Return appropriate min and max values and units for a parameter name
        '''
        # Get the 1 & 99 percentiles of the data for setting limits on the scatter plot
        apQS = ActivityParameter.objects.using(self.database).filter(activity__platform__name=self.platformName)
        pQS = apQS.filter(parameter__name=parm).aggregate(Min('p010'), Max('p990'))
        min, max = (pQS['p010__min'], pQS['p990__max'])

        # Get units for each parameter
        prQS = ParameterResource.objects.using(self.database).filter(resource__name='units').values_list('resource__value')
        try:
            units = prQS.filter(parameter__name=parm)[0][0]
        except IndexError as e:
            raise Exception("Unable to get units for parameter name %s from platform %s" % (parm, self.platformName))
            sys.exit(-1)

        return min, max, units

    def getTimeSeriesData(self, startDatetime, endDatetime):
        '''
        Return time series of a list of Parameters from a Platform
        '''
        data_dict = defaultdict(lambda: {'datetime': [], 'lon': [], 'lat': [], 'depth': [], 'datavalue':[], 'units':'', 'p010':'', 'p990':''})

        start_dt= []
        end_dt = []

        if not self.plotGroup :
            raise Exception('Must specify list plotGroup')

        for pln in self.platformName:
            for g in self.plotGroup:
                parameters = [x.strip() for x in g.split(',')]
                parameters_valid = []
                try:
                    for pname in parameters:

                        apQS = ActivityParameter.objects.using(self.database)
                        apQS = apQS.filter(activity__platform__name=pln)
                        apQS = apQS.filter(parameter__name=pname)
                        pQS = apQS.aggregate(Min('p010'), Max('p990'))
                        min, max = (pQS['p010__min'], pQS['p990__max'])
                        data_dict[pln+pname]['p010'] = pQS['p010__min']
                        data_dict[pln+pname]['p990'] = pQS['p990__max']
                        units=apQS.values('parameter__units')
                        data_dict[pln+pname]['units'] = units[0]['parameter__units']

                        qs = MeasuredParameter.objects.using(self.database)
                        qs = qs.filter(measurement__instantpoint__timevalue__gte=startDatetime)
                        qs = qs.filter(measurement__instantpoint__timevalue__lte=endDatetime)
                        qs = qs.filter(parameter__name=pname)
                        qs = qs.filter(measurement__instantpoint__activity__platform__name=pln)
                        sdt_count = qs.values_list('measurement__instantpoint__simpledepthtime__depth').count()
                        qs = qs.values('measurement__instantpoint__timevalue', 'measurement__depth', 'measurement__geom', 'datavalue').order_by('measurement__instantpoint__timevalue')
                        data_dict[pln+pname]['sdt_count'] = sdt_count

                        # only plot data with more than one point
                        if len(qs) > 0:
                            for rs in qs:
                                geom = rs['measurement__geom']
                                lat = geom.y
                                lon = geom.x
                                data_dict[pln+pname]['lat'].insert(0, lat)
                                data_dict[pln+pname]['lon'].insert(0, lon)
                                data_dict[pln+pname]['datetime'].insert(0, rs['measurement__instantpoint__timevalue'])
                                data_dict[pln+pname]['depth'].insert(0, rs['measurement__depth'])
                                data_dict[pln+pname]['datavalue'].insert(0, rs['datavalue'])

                            # for salinity, throw out anything less than 30 and do the percentiles manually
                            if pname.find('salinity') != -1 :
                                numpvar = np.array(data_dict[pln+pname]['datavalue'])
                                numpvar_filtered = numpvar[numpvar>30.0]
                                numpvar_filtered.sort()
                                listvar = list(numpvar_filtered)
                                p010 = percentile(listvar, 0.010)
                                p990 = percentile(listvar, 0.990)
                                data_dict[pln+pname]['p010'] = p010
                                data_dict[pln+pname]['p990'] = p990

                            # dates are in reverse order - newest first
                            start_dt.append(data_dict[pln+pname]['datetime'][-1])
                            end_dt.append(data_dict[pln+pname]['datetime'][0])
                            logger.debug('Loaded data for parameter %s' % pname)
                            parameters_valid.append(pname)

                except Exception, e:
                    logger.error('%s not available in database for the dates %s %s' %(pname, startDatetime, endDatetime))
                    continue

                except Exception, e:
                    logger.error('%s not available in database for the dates %s %s' %(pname, startDatetime, endDatetime))
                    continue

                if len(parameters_valid) > 0:
                    self.plotGroupValid.append(','.join(parameters_valid))

        # get the ranges of the data
        if start_dt and end_dt:
            data_start_dt = sorted(start_dt)[0]
            data_end_dt = sorted(end_dt)[-1]
        else:
            #otherwise default to requested dates
            data_start_dt = startDatetime
            data_end_dt = endDatetime

        return data_dict, data_start_dt, data_end_dt

    def getMeasuredPPData(self, startDatetime, endDatetime, platform, parm):
        points = []
        data = []
        activity_names = []
        maptracks = []

        try:
            qs = MeasuredParameter.objects.using(self.database)
            qs = qs.filter(measurement__instantpoint__timevalue__gte=startDatetime)
            qs = qs.filter(measurement__instantpoint__timevalue__lte=endDatetime)
            qs = qs.filter(parameter__name=parm)
            qs = qs.filter(measurement__instantpoint__activity__platform__name=platform)
            qs = qs.values('measurement__instantpoint__timevalue', 'measurement__geom', 'parameter', 'datavalue', 'measurement__instantpoint__activity__maptrack',  'measurement__instantpoint__activity__name').order_by('measurement__instantpoint__timevalue')

            for rs in qs:
                geom = rs['measurement__geom']
                lon = geom.x
                lat = geom.y
                pt = Point(float(lon),float(lat))
                points.append(pt)
                value = rs['datavalue']
                data.append(float(value))
                geom = rs['measurement__instantpoint__activity__maptrack']
                activity_name = rs['measurement__instantpoint__activity__name']
                # only keep  maptracks from new activities
                if not any(activity_name in s for s in activity_names):
                    activity_names.append(activity_name)
                    maptracks.append(geom)

        except Exception, e:
            logger.error('%s not available in database for the dates %s %s' %(parm, startDatetime, endDatetime))

        return data, points, maptracks

    def loadData(self, startDatetime, endDatetime):
        try:
            self.data, dataStart, dataEnd = self.getTimeSeriesData(startDatetime, endDatetime)
            return dataStart, dataEnd

        except Exception, e:
            logger.warn(e)
            raise e

        return startDatetime, endDatetime

    class DateFormatter(mpl.ticker.Formatter):
        def __init__(self, scale_factor=1):
            self.scale_factor = scale_factor

        def __call__(self, x, pos=None):
            d = time.gmtime(x*self.scale_factor)
            utc = datetime(*d[:6])
            local_tz = pytz.timezone('America/Los_Angeles')
            utc_tz = pytz.timezone('UTC')
            utc = utc.replace(tzinfo=utc_tz)
            pst = utc.astimezone(local_tz)
            return pst.strftime('%Y-%m-%d %H:%M')

    def readCLT(self, fileName):
        '''
        Read the color lookup table from disk and return a python list of rgb tuples.
        '''
        cltList = []
        for rgb in open(fileName, 'r'):
            (r, g, b) = rgb.split('  ')[1:]
            cltList.append([float(r), float(g), float(b)])

        return cltList

    def shadeNight(self,ax,xdates,miny,maxy):
        '''
        Shades plots during local nighttime hours
        '''
        utc_zone = pytz.utc

        if len(xdates) < 50:
            logger.debug("skipping day/night shading - too few points")
            return

        datetimes = []
        for xdt in xdates:
            dt = datetime.fromtimestamp(xdt)
            datetimes.append(dt.replace(tzinfo=utc_zone))

        loc = ephem.Observer()
        loc.lat = '36.7087' # Monterey Bay region
        loc.lon = '-121.0000'
        loc.elev = 0
        sun = ephem.Sun(loc)
        mint=min(datetimes)
        maxt=max(datetimes)
        numdays = (maxt - mint).days
        d = [mint + timedelta(days=dt) for dt in xrange(numdays+1)]
        d.sort()
        sunrise = map(lambda x:dates.date2num(loc.next_rising(sun,start=x).datetime()),d)
        sunset = map(lambda x:dates.date2num(loc.next_setting(sun,start=x).datetime()),d)

        result = []
        for st in datetimes:
              result.append(bisect.bisect(sunrise, dates.date2num(st)) != bisect.bisect(sunset, dates.date2num(st)))

        if self.scale_factor:
            scale_xdates = [x/self.scale_factor for x in xdates]
        else:
            scale_xdates = xdates

        ax.fill_between(scale_xdates, miny, maxy, where=result, facecolor='#C8C8C8', edgecolor='none', alpha=0.3)

    def createPlot(self, startDatetime, endDatetime):

        if len(self.data) == 0:
            logger.debug('no data found to plot')
            raise Exception('no data found to plot')

        # GridSpecs for plots
        outer_gs = gridspec.GridSpec(nrows=2, ncols=1, height_ratios=[1,3])
        # tighten up space between plots
        outer_gs.update(left=0.10, right=0.90, hspace=0.05)
        map_gs = gridspec.GridSpecFromSubplotSpec(nrows=1, ncols=1, subplot_spec=outer_gs[0])
        lower_gs = gridspec.GridSpecFromSubplotSpec(nrows=len(self.plotGroupValid), ncols=1, subplot_spec=outer_gs[1])

        STATIC_ROOT = '/var/www/html/stoqs/static'      # Warning: Hard-coded
        clt = self.readCLT(os.path.join(STATIC_ROOT, 'colormaps', 'jetplus.txt'))
        self.cm_jetplus = mpl.colors.ListedColormap(np.array(clt))

        # start a new figure - size is in inches
        fig = plt.figure(figsize=(8, 10))
        fig.suptitle(self.title+'\n'+self.subtitle1+'\n'+self.subtitle2, fontsize=8)

        pn = self.platformName[0]

        # bound the depth to cover max of all parameter group depths
        # and flag removal of scatter plot if have more than 2000 points in any parameter
        maxy = 0
        for group in self.plotGroupValid:
            parm = [x.strip() for x in group.split(',')]
            for name in parm:
                y = max(self.data[pn+name]['depth'])
                sz = len(self.data[pn+name]['datavalue'])
                if y > maxy:
                    maxy = y

        # pad the depth by 20 meters to make room for parameter name to be displayed at bottom
        rangey = [0.0, int(maxy) + 20]

        i = 0
        # add contour plots for each parameter group
        for group in self.plotGroupValid:
            parm = [x.strip() for x in group.split(',')]
            plot_step =  sum([self.data[pn+p]['units'].count('bool') for p in parm]) # counter the number of boolean plots in the groups
            plot_scatter = len(parm) - plot_step # otherwise all other plots are scatter plots
            #plot_dense = sum([val for val  in len(self.data[pn+name]['datavalue']) > 2000]) #  if more than 2000 points, skip the scatter plot

            # choose the right type of gridspec to display the data
            if plot_scatter:
                # one row for scatter and one for contour
                plot_gs = gridspec.GridSpecFromSubplotSpec(nrows=len(parm)*2, ncols=2, subplot_spec=lower_gs[i], width_ratios=[30,1], wspace=0.05)
            else:
                # one row for step plots/or contour plots
                plot_gs = gridspec.GridSpecFromSubplotSpec(nrows=len(parm), ncols=2, subplot_spec=lower_gs[i], width_ratios=[30,1], wspace=0.05)
            j = 0
            i += 1
            for name in parm:
                title = name
                x = [time.mktime(xe.timetuple()) for xe in self.data[pn+name]['datetime']]
                y = self.data[pn+name]['depth']
                z = self.data[pn+name]['datavalue']
                sdt_count = self.data[pn+name]['sdt_count']

                units = '(' + self.data[pn+p]['units'] + ')'

                if len(z):
                    if self.autoscale:
                        rangez = [self.data[pn+p]['p010'],self.data[pn+p]['p990']]
                    else:
                        rangez = [min(z), max(z)]
                else:
                    rangez = [0, 0]

                if name.find('chlorophyll') != -1 :
                    if not self.autoscale:
                        rangez = [0.0, 10.0]
                if name.find('salinity') != -1 :
                    if not self.autoscale:
                        rangez = [33.3, 34.9]
                    units = ''
                if name.find('temperature') != -1 :
                    if not self.autoscale:
                        rangez = [10.0, 14.0]
                    units = ' ($^\circ$C)'

                logger.debug('getting subplot ax0')
                gs = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=plot_gs[j])
                ax0_plot = plt.Subplot(fig, gs[:])
                fig.add_subplot(ax0_plot)

                gs = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=plot_gs[j+1])
                ax0_colorbar = plt.Subplot(fig, gs[:])
                fig.add_subplot(ax0_colorbar)

                if plot_scatter:
                    logger.debug('getting subplot ax1')
                    gs = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=plot_gs[j + 2])
                    ax1_plot = plt.Subplot(fig, gs[:])
                    fig.add_subplot(ax1_plot)

                    gs = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=plot_gs[j + 3])
                    ax1_colorbar = plt.Subplot(fig, gs[:])
                    fig.add_subplot(ax1_colorbar)

                # if no data found add in some fake data and plot a placeholder time/depth plot
                if not x:
                    tmin = time.mktime(startDatetime.timetuple())
                    tmax = time.mktime(endDatetime.timetuple())
                    x.append(tmin)
                    x.append(tmax)
                    y.append(np.NaN)
                    y.append(np.NaN)
                    z.append(np.NaN)
                    z.append(np.NaN)

                if plot_scatter:
                    cs0, zi = self.createContourPlot(title + pn,ax0_plot,x,y,z,rangey,rangez,startDatetime,endDatetime,sdt_count)
                    cs1 = self.createScatterPlot(title + pn,ax1_plot,x,y,z,rangey,rangez,startDatetime,endDatetime)
                else:
                    if plot_step:
                        cs0 = self.createStepPlot(title + pn,title,ax0_plot,x,z,rangez,startDatetime,endDatetime)
                    else:
                        cs0, zi = self.createContourPlot(title + pn,ax0_plot,x,y,z,rangey,rangez,startDatetime,endDatetime,sdt_count)

                if plot_scatter:
                    ax1_plot.text(0.95,0.02, name, verticalalignment='bottom',
                                horizontalalignment='right',transform=ax1_plot.transAxes,color='black',fontsize=8)
                else:
                    ax0_plot.text(0.95,0.02, name, verticalalignment='bottom',
                        horizontalalignment='right',transform=ax0_plot.transAxes,color='black',fontsize=8)

                self.shadeNight(ax0_plot,sorted(x),rangey[0], rangey[1])
                if plot_scatter:
                    self.shadeNight(ax1_plot,sorted(x),rangey[0], rangey[1])

                logger.debug('plotting colorbars')
                if plot_scatter:
                    cbFormatter = FormatStrFormatter('%.2f')
                    cb = plt.colorbar(cs0, cax=ax0_colorbar, ticks=[min(rangez), max(rangez)], format=cbFormatter, orientation='vertical')
                    cb.set_label(units,fontsize=8)#,labelpad=5)
                    cb.ax.xaxis.set_ticks_position('top')
                    for t in cb.ax.yaxis.get_ticklabels():
                        t.set_fontsize(8)

                    cb = plt.colorbar(cs1, cax=ax1_colorbar, ticks=[min(rangez), max(rangez)], format=cbFormatter, orientation='vertical')
                    cb.set_label(units,fontsize=8)#,labelpad=5)
                    cb.ax.xaxis.set_ticks_position('top')
                    for t in cb.ax.yaxis.get_ticklabels():
                        t.set_fontsize(8)
                else:
                    if plot_step:
                        xaxis = ax0_colorbar.xaxis
                        ax0_colorbar.xaxis.set_major_locator(plt.NullLocator())
                        ax0_colorbar.yaxis.set_ticks_position('right')
                        for t in ax0_colorbar.yaxis.get_ticklabels():
                            t.set_fontsize(8)
                    else:
                        cbFormatter = FormatStrFormatter('%.2f')
                        cb = plt.colorbar(cs0, cax=ax0_colorbar, ticks=[min(rangez), max(rangez)], format=cbFormatter, orientation='vertical')
                        cb.set_label(units,fontsize=8)#,labelpad=5)
                        cb.ax.xaxis.set_ticks_position('top')
                        for t in cb.ax.yaxis.get_ticklabels():
                            t.set_fontsize(8)


                # Rotate and show the date with date formatter in the last plot of all the groups
                logger.debug('rotate and show date with date formatter')
                if name is parm[-1] and group is self.plotGroupValid[-1]:
                    x_fmt = self.DateFormatter(self.scale_factor)
                    if plot_scatter:
                        ax = ax1_plot
                        # Don't show on the upper contour plot
                        ax0_plot.xaxis.set_ticks([])
                    else:
                        ax = ax0_plot
                    ax.xaxis.set_major_formatter(x_fmt)
                    # Rotate date labels
                    for label in ax.xaxis.get_ticklabels():
                        label.set_rotation(10)
                else:
                    ax0_plot.xaxis.set_ticks([])
                    if plot_scatter:  
                        ax1_plot.xaxis.set_ticks([])

                if plot_scatter:
                    j+=4
                else: 
                    j+=2


        # plot tracks
        ax = plt.Subplot(fig, map_gs[:])
        fig.add_subplot(ax, aspect='equal')

        logger.debug('computing activity extents')
        z = []
        maptracks = None

        z, points, maptracks = self.getMeasuredPPData(startDatetime, endDatetime, pn, self.plotDotParmName)

        # get the percentile ranges for this to autoscale
        pointsnp = np.array(points)
        lon = pointsnp[:,0]
        lat = pointsnp[:,1]

        if self.extent:
            ltmin = self.extent[1]
            ltmax = self.extent[3]
            lnmin = self.extent[0]
            lnmax = self.extent[2]
            lndiff = abs(lnmax - lnmin)
            ltdiff = abs(ltmax - ltmin)
            logger.debug("lon diff %f lat diff %f" %(lndiff, ltdiff))
            mindeg = .02
            paddeg = .01
            if lndiff < mindeg :
                lnmin -= mindeg
                lnmax += mindeg
            if ltdiff < mindeg:
                ltmin -= mindeg
                ltmax += mindeg
            e = (lnmin - paddeg, ltmin - paddeg, lnmax + paddeg, ltmax + paddeg)
        else:
            # default map to Monterey Bay region
            ltmin = 36.61
            ltmax = 36.97
            lnmin = -122.21
            lnmax = -121.73
            e = (lnmin, ltmin, lnmax, ltmax)

        logger.debug('Extent found %f,%f,%f,%f)' % (e[0], e[1],e[2],e[3]))
        # retry up to 5 times to get the basemap
        for i in range(0, 5):
            mp = Basemap(llcrnrlon=e[0], llcrnrlat=e[1], urcrnrlon=e[2], urcrnrlat=e[3], projection='cyl', resolution='l', ax=ax)
            try:
                ##mp.wmsimage('http://www.gebco.net/data_and_products/gebco_web_services/web_map_service/mapserv?', layers=['GEBCO_08_Grid'])                            # Works, but coarse
                mp.arcgisimage(server='http://services.arcgisonline.com/ArcGIS', service='Ocean_Basemap')
                mp.drawparallels(np.linspace(e[1],e[3],num=3), labels=[True,False,False,False], fontsize=8, linewidth=0)
                mp.drawmeridians(np.linspace(e[0],e[2],num=3), labels=[False,False,False,True], fontsize=8, linewidth=0)
            except Exception, e:
                logger.error('Could not download ocean basemap ')
                mp = None

            if mp is not None :
                break

        if mp is None :
            logger.debug('Error - cannot cannot fetch basemap')
            return

        try:
            logger.debug('plotting tracks')
            if self.animate:
                try:
                    track = LineString(points).simplify(tolerance=.001)
                    if track is not None:
                        ln,lt = zip(*track)
                        mp.plot(ln,lt,'-',c='k',alpha=0.5,linewidth=2, zorder=1)
                except TypeError, e:
                    logger.warn("%s\nCannot plot map track path to None", e)
            else:
                for track in maptracks:
                    if track is not None:
                        ln,lt = zip(*track)
                        mp.plot(ln,lt,'-',c='k',alpha=0.5,linewidth=2, zorder=1)

            # if have a valid series, then plot the dots
            if self.plotDotParmName is not None and len(z) > 0:
                if len(z) > 2000:
                    sz = len(z)
                    stride = int(sz/200)
                    z_stride = z[0:sz:stride]
                    lon_stride = lon[0:sz:stride]
                    lat_stride = lat[0:sz:stride]
                    mp.scatter(lon_stride,lat_stride,c=z_stride,marker='.',lw=0,alpha=1.0,cmap=self.cm_jetplus,zorder=2)
                    if stride > 1:
                        ax.text(0.70,0.1, ('%s (every %d points)' % (self.plotDotParmName, stride)), verticalalignment='bottom',
                             horizontalalignment='center',transform=ax.transAxes,color='black',fontsize=8)
                    else:
                        ax.text(0.70,0.1, ('%s (every point)' % (self.plotDotParmName)), verticalalignment='bottom',
                             horizontalalignment='center',transform=ax.transAxes,color='black',fontsize=8)

                else:
                    mp.scatter(lon,lat,c=z,marker='.',lw=0,alpha=1.0,cmap=self.cm_jetplus,zorder=2)
                    ax.text(0.70,0.1, ('%s (every point)' % (self.plotDotParmName)), verticalalignment='bottom',
                             horizontalalignment='center',transform=ax.transAxes,color='black',fontsize=8)

            # plot the binary markers
            markers = ['o','x','d','D','8','1','2','3','4']
            i = 1
            parm = [x.strip() for x in self.booleanPlotGroup.split(',')]
            for name in parm:
                logger.debug('Plotting boolean plot group paramter %s' % name)
                z, points, maptracks = self.getMeasuredPPData(startDatetime, endDatetime, self.platformName[0], name)
                pointsnp = np.array(points)
                lon = pointsnp[:,0]
                lat =  pointsnp[:,1]
                # scale up the size of point
                s = [20*val for val in z]
                if len(z) > 0:
                    mp.scatter(lon,lat,s=s,marker=markers[i],c='black',label=name,zorder=3)
                i = i + 1

            # plot the legend outside the plot in the upper left corner
            l = ax.legend(loc='upper left', bbox_to_anchor=(1,1), prop={'size':8}, scatterpoints=1)# only plot legend symbol once
            l.set_zorder(4) # put the legend on top

        except Exception, e:
            logger.warn(e)

        #mp.fillcontinents()
        #mp.drawcoastlines()

        if self.animate:
            # append frames output as pngs with an indexed frame number before the gif extension
            fname = '%s/frame_%02d.png' % (self.dirpath, self.frame)
        else:
            fname = self.outFilename

        logger.debug('Saving figure %s ' % fname)
        fig.savefig(fname,dpi=120)#,transparent=True)
        plt.close()
        self.frame += 1

        logger.debug('Done with contourPlot')

    # Register an handler for the timeout
    def handler(self,signum, frame):
        logger.debug("Exceeded maximum time allowed for gridding!")
        raise Exception("end of time")

    def gridData(self, x, y, z, xi, yi):
        try:
            logger.debug('Gridding')
            zi = griddata((x, y), np.array(z), (xi[None,:], yi[:,None]), method='nearest')
            logger.debug('Done gridding')
        except KeyError, e:
            logger.warn('Got KeyError. Could not grid the data')
            zi = None
            raise(e)
        return zi

    def gridDataRbf(self, tmin, tmax, dmin, dmax, x, y, z):
        from scipy.interpolate import Rbf
        xi=[]

        try:
            xi, yi = np.mgrid[tmin:tmax:1000j, dmin:dmax:100j]
            # use RBF
            rbf = Rbf(x, y, z, epsilon=2)
            zi = rbf(xi, yi)
        except Exception, e:
            logger.warn('Could not grid the data' +  str(e))
            zi = None
        return xi,yi,zi

    def createContourPlot(self,title,ax,x,y,z,rangey,rangez,startTime,endTime,sdt_count):
        tmin = time.mktime(startTime.timetuple())
        tmax = time.mktime(endTime.timetuple())
        tgrid_max = 1000  # Reasonable maximum width for time-depth-flot plot is about 1000 pixels
        dgrid_max = 200   # Height of time-depth-flot plot area is 200 pixels
        dinc = 0.5       # Average vertical resolution of AUV Dorado
        nlevels = 255     # Number of color filled contour levels
        zmin = rangez[0]
        zmax = rangez[1]
        dmin = rangey[0]
        dmax = rangey[1]
        scale_factor = 1

        # 2 points define a line, take half the number of simpledepthtime points
        sdt_count = int(max(sdt_count, 2) / 2)

        if sdt_count > tgrid_max:
            sdt_count = tgrid_max

        xi = np.linspace(tmin, tmax, sdt_count)
        #print 'xi = %s' % xi

        # Make depth spacing dinc m, limit to time-depth-flot resolution (dgrid_max)
        y_count = int((dmax - dmin) / dinc )
        if y_count > dgrid_max:
            y_count = dgrid_max

        yi = np.linspace(dmin, dmax, y_count)
        #print 'yi = %s' %yi

        try:
            scale_factor = float(tmax -tmin) / (dmax - dmin)
        except ZeroDivisionError, e:
            logger.warn('Not setting scale_factor.  Scatter plots will still work.')
            contour_flag = False
            scale_factor = 1
        else:
            logger.warn('self.scale_factor = %f' % scale_factor)
            xi = xi / scale_factor
            xg = [xe/scale_factor for xe in x]
            contour_flag = True
        zi = []
        cs = None

        # Register the signal function handler
        signal.signal(signal.SIGALRM, self.handler)

        # Define a timeout of 90 seconds for gridding functions
        signal.alarm(90)

        if not self.data:
            logger.warn('no data found to plot') 
            signal.alarm(0)
            raise Exception('no data')
        if contour_flag:
            try:
                logger.warn('Gridding data with sdt_count = %d, and y_count = %d' %(sdt_count, y_count))
                zi = self.gridData(xg, y, z, xi, yi)
                signal.alarm(0)
            except KeyError, e:
                logger.warn('Got KeyError. Could not grid the data')
                contour_flag = False
                scale_factor = 1
                try:
                    # use RBF
                    logger.warn('Trying radial basis function')
                    xi,yi,zi = self.gridDataRbf(tmin, tmax, dmin, dmax, xg, y, z)
                    contour_flag = True
                    signal.alarm(0)
                except Exception, e:
                    logger.warn('Could not grid the data' +  str(e))
            except Exception, e:
                logger.warn('Could not grid the data' +  str(e))
                contour_flag = False
                try:
                    # use RBF
                    logger.warn('Trying radial basis function')
                    xi,yi,zi  = self.gridDataRbf(tmin, tmax, dmin, dmax, xg, y, z)
                    contour_flag = True
                    signal.alarm(0)
                except Exception, e:
                    logger.warn('Could not grid the data' +  str(e))

        try:
            if scale_factor > 1 and contour_flag:
                ax.set_xlim(tmin / scale_factor, tmax / scale_factor)
            else:
                ax.set_xlim(tmin, tmax)

            self.scale_factor = scale_factor

            ax.set_ylim([dmax,dmin])
            ax.set_ylabel('depth (m)',fontsize=8)

            ax.tick_params(axis='both',which='major',labelsize=8)
            ax.tick_params(axis='both',which='minor',labelsize=8)

            if contour_flag:
                logger.debug('Contouring the data')
                cs = ax.contourf(xi, yi, zi, levels=np.linspace(zmin,zmax, nlevels), cmap=self.cm_jetplus, extend='both')
                # this will show the points where the contouring occurs
                #ax.scatter(x,y,marker='.',s=2,c='k',lw=0)
            else:
                logger.debug('Plotting the data')
                cs = ax.scatter(x,y,c=z,s=20,marker='.',vmin=zmin,vmax=zmax,lw=0,alpha=1.0,cmap=self.cm_jetplus)

            # limit the number of ticks
            max_yticks = 5
            yloc = plt.MaxNLocator(max_yticks)
            ax.yaxis.set_major_locator(yloc)

        except Exception,e:
            logger.error(e)

        return cs, zi

    def createScatterPlot(self,title,ax,x,y,z,rangey,rangez,startTime,endTime):
        tmin = time.mktime(startTime.timetuple())
        tmax = time.mktime(endTime.timetuple())
        nlevels = 255     # Number of color filled contour levels
        zmin = rangez[0]
        zmax = rangez[1]
        dmin = rangey[0]
        dmax = rangey[1]

        try:
            ax.set_xlim(tmin, tmax)
            self.scale_factor = 1

            ax.set_ylim([dmax,dmin])
            ax.set_ylabel('depth (m)',fontsize=8)

            ax.tick_params(axis='both',which='major',labelsize=8)
            ax.tick_params(axis='both',which='minor',labelsize=8)

            logger.debug('Plotting the data')
            cs = ax.scatter(x,y,c=z,s=20,marker='.',vmin=zmin,vmax=zmax,lw=0,alpha=1.0,cmap=self.cm_jetplus)

            # limit the number of ticks
            max_yticks = 5
            yloc = plt.MaxNLocator(max_yticks)
            ax.yaxis.set_major_locator(yloc)

        except Exception,e:
            logger.error(e)

        return cs

    def createStepPlot(self,title,label,ax,x,y,rangey,startTime,endTime):
        tmin = time.mktime(startTime.timetuple())
        tmax = time.mktime(endTime.timetuple())
        dmin = rangey[1]
        dmax = rangey[0]

        try:
            ax.set_xlim(tmin, tmax)
            self.scale_factor = 1

            ax.set_ylim([dmax,dmin])
            ax.set_ylabel('%s (bool)' % label,fontsize=8)

            ax.tick_params(axis='both',which='major',labelsize=8)
            ax.tick_params(axis='both',which='minor',labelsize=8)

            logger.debug('Plotting the step data')
            labels = []
            for val in y:
                if not val:
                    labels.append('False')
                else:
                    labels.append('True')
            cs = ax.step(x,y,lw=1,alpha=0.8,c='black',label=labels)

            # limit the number of ticks
            max_yticks = 5
            yloc = plt.MaxNLocator(max_yticks)
            ax.yaxis.set_major_locator(yloc)

        except Exception,e:
            logger.error(e)

        return cs

    def run(self):

        self.frame = 0

        endDatetimeLocal = self.endDatetime.astimezone(pytz.timezone('America/Los_Angeles'))
        startDatetimeLocal = self.startDatetime.astimezone(pytz.timezone('America/Los_Angeles'))

        self.extent = self.getActivityExtent(self.startDatetime, self.endDatetime)

        logger.debug('Loading data')
        dataStart, dataEnd = self.loadData(self.startDatetime, self.endDatetime)

        if not self.data:
            logger.debug('No valid data to plot')
            return

        # need to fix the scale over all the plots if animating
        if self.animate:
            self.autoscale = True

        if dataStart.tzinfo is None:
            dataStart =  pytz.utc.localize(dataStart)
        if dataEnd.tzinfo is None:
            dataEnd = pytz.utc.localize(dataEnd)

        if self.animate: 
            self.dirpath = tempfile.mkdtemp()
            zoomWindow = timedelta(hours=self.zoom) 
            zoomWindow = timedelta(hours=self.zoom)
            overlapWindow = timedelta(hours=self.overlap)
            endDatetime = dataStart + zoomWindow
            startDatetime = dataStart

            try:
                # Loop through sections of the data with temporal constraints based on the window and step command line parameters
                while endDatetime <= dataEnd :
                    dataEndDatetimeLocal = endDatetime.astimezone(pytz.timezone('America/Los_Angeles'))
                    dataStartDatetimeLocal = startDatetime.astimezone(pytz.timezone('America/Los_Angeles'))
                    logger.debug('Plotting data')

                    self.subtitle1 = '%s  to  %s PDT' % (dataStartDatetimeLocal.strftime('%Y-%m-%d %H:%M'), dataEndDatetimeLocal.strftime('%Y-%m-%d %H:%M'))
                    self.subtitle2 = '%s  to  %s UTC' % (startDatetime.strftime('%Y-%m-%d %H:%M'), endDatetime.strftime('%Y-%m-%d %H:%M'))
                    self.createPlot(startDatetime, endDatetime)

                    startDatetime = endDatetime - overlapWindow
                    endDatetime = startDatetime + zoomWindow

                i = 0

                cmd = "convert -loop 1 -delay 250 %s/frame*.png %s" % (self.dirpath,self.outFilename)
                logger.debug(cmd)
                os.system(cmd)
                shutil.rmtree(self.dirpath)

            except Exception, e:
                logger.error(e)

        else :
            try:
                if self.data is not None:
                    dataEndDatetimeLocal = dataEnd.astimezone(pytz.timezone('America/Los_Angeles'))
                    dataStartDatetimeLocal = dataStart.astimezone(pytz.timezone('America/Los_Angeles'))
                    logger.debug('Plotting data')
                    self.subtitle1 = '%s  to  %s PDT' % (dataStartDatetimeLocal.strftime('%Y-%m-%d %H:%M'), dataEndDatetimeLocal.strftime('%Y-%m-%d %H:%M'))
                    self.subtitle2 = '%s  to  %s UTC' % (dataStart.strftime('%Y-%m-%d %H:%M'), dataEnd.strftime('%Y-%m-%d %H:%M'))
                    self.createPlot(dataStart, dataEnd)
            except Exception, e:
                logger.error(e)
