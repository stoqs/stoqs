__author__ = 'dcline'

import sys

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE']='settings'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))  # settings.py is one dir up
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.dates as dts
import matplotlib.gridspec as gridspec
import matplotlib.ticker as ticker
import numpy as np
import re
import pylab as pl
import time
import pytz
import stoqs.models
import logging

from collections import defaultdict
from datetime import datetime, timedelta
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
from matplotlib.mlab import griddata
from scipy.interpolate import griddata
from mpl_toolkits.basemap import Basemap
from stoqs.models import Activity, ActivityParameter, ParameterResource, Platform, SimpleDepthTime, MeasuredParameter, Measurement, Parameter

# Set up global variables for logging output to STDOUT
logger = logging.getLogger('monitorTethysHotSpotLogger')
fh = logging.StreamHandler()
f = logging.Formatter("%(levelname)s %(asctime)sZ %(filename)s %(funcName)s():%(lineno)d %(message)s")
fh.setFormatter(f)
logger.addHandler(fh)
logger.setLevel(logging.DEBUG)

class Contour(object):

    '''
    Create plots for visualizing data from LRAUV vehicles
    '''
    def __init__(self, startDatetime, endDatetime, database, platformName, parmGroup, title, outFilename, animate):
        self.startDatetime = startDatetime
        self.endDatetime = endDatetime
        self.platformName = platformName
        self.parmGroup = parmGroup
        self.title = title
        self.animate = animate
        self.outFilename = outFilename
        self.database = database
        self.platformName = platformName


    def getTimeSeriesData(self, startDatetime, endDatetime):
        '''
        Return time series of a Parameter from a Platform
        '''
        data_dict = defaultdict(lambda: {'datetime': [], 'lon': [], 'lat': [], 'depth': [], 'datavalue':[]})

        if not self.parmGroup :
            raise Exception('Must specify list parmGroup')

        for pln in self.platformName:
            for g in self.parmGroup:
                parameters = [x.strip() for x in g.split(',')]
                for pname in parameters:
                    qs = MeasuredParameter.objects.using(self.database)

                    qs = qs.filter(measurement__instantpoint__timevalue__gte=startDatetime)
                    qs = qs.filter(measurement__instantpoint__timevalue__lte=endDatetime)
                    qs = qs.filter(parameter__name=pname)
                    qs = qs.filter(measurement__instantpoint__activity__platform__name=pln)
                    sdt_count = qs.values_list('measurement__instantpoint__simpledepthtime__depth').count()
                    qs = qs.values('measurement__instantpoint__timevalue', 'measurement__depth', 'measurement__geom', 'datavalue').order_by('measurement__instantpoint__timevalue')
                    data_dict[pln+pname]['sdt_count'] = sdt_count

                    for rs in qs:
                        geom = rs['measurement__geom']
                        lat = geom.y
                        lon = geom.x
                        data_dict[pln+pname]['lat'].insert(0, lat)
                        data_dict[pln+pname]['lon'].insert(0, lon)
                        data_dict[pln+pname]['datetime'].insert(0, rs['measurement__instantpoint__timevalue'])
                        data_dict[pln+pname]['depth'].insert(0, rs['measurement__depth'])
                        data_dict[pln+pname]['datavalue'].insert(0, rs['datavalue'])

        return data_dict

    def loadData(self, startDatetime, endDatetime):

        try:
            self.data = self.getTimeSeriesData(startDatetime, endDatetime)
        except Exception, e:
            self.data = []
            logger.warn(e)

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

    def plotNightDay(self,ax,xdates,startDatetime,endDatetime):

        endDatetimeUTC = pytz.utc.localize(endDatetime)
        endDatetimeLocal = endDatetimeUTC.astimezone(pytz.timezone('America/Los_Angeles'))
        startDatetimeUTC = pytz.utc.localize(startDatetime)
        startDatetimeLocal = startDatetimeUTC.astimezone(pytz.timezone('America/Los_Angeles'))
        sunriseLocal24hr = startDatetimeLocal.replace(hour=6,minute=0,second=0,microsecond=0)
        sunsetLocal24hr = startDatetimeLocal.replace(hour=20,minute=0,second=0,microsecond=0)

        secs = time.mktime(sunriseLocal24hr.timetuple())
        sunrise = time.gmtime(secs)
        secs = time.mktime(sunsetLocal24hr.timetuple())
        sunset = time.gmtime(secs)
        dark_end = []
        dark_start = []
        i = 0
        delta = timedelta(minutes=10)

        for dt in xdates:

            # If at night
            if dt >= sunset or dt <= sunrise:
                # If within 10 minutes of sunset
                if dt >= sunset - delta and dt <= sunset + delta :
                    dark_start =  dt
                # If within 10 minutes of sunrise or last time
                elif dt >= sunrise - delta and dt <= sunrise + delta or dt == xdates[-1] :
                    dark_end =  dt
                else:
                    dark_start = dt

                # If have start and end time defined color using zoom effect
                if dark_start and dark_end and (dark_start - dark_end) > timedelta(hours=1):
                    if self.scale_factor:
                        dark_end_scaled = time.mktime(dark_end.timetuple())/self.scale_factor
                        dark_start_scaled = time.mktime(dark_start.timetuple())/self.scale_factor
                    else:
                        dark_end_scaled = time.mktime(dark_end.timetuple())
                        dark_start_scaled = time.mktime(dark_start.timetuple())

                    self.zoomEffect(ax, dark_start_scaled, dark_end_scaled)
                    dark_start = []
                    dark_end = []

    def createPlot(self, startDatetime, endDatetime):

        if not self.data:
            logger.debug('no data found to plot')
            return

        # GridSpecs for contour subplots
        outer_gs = gridspec.GridSpec(nrows=1+len(self.parmGroup), ncols=1)#, height_ratios=[1,3])
        map_gs  = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=outer_gs[0])

        STATIC_ROOT = '/var/www/html/stoqs/static'      # Warning: Hard-coded
        clt = self.readCLT(os.path.join(STATIC_ROOT, 'colormaps', 'jetplus.txt'))
        self.cm_jetplus = mpl.colors.ListedColormap(np.array(clt))

        # fix depth range
        rangey = [0.0,90.0]

        # start a new figure - size is in inches
        fig = plt.figure(figsize=(8, 10))
        plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)
        fig.suptitle(self.title+'\n'+self.subtitle, fontsize=8)

        # add contour plots for each parameter group
        i = 0

        latlon_series = ''
        chl_series = None
        for group in self.parmGroup:
            i += 1
            parm = [x.strip() for x in group.split(',')]
            lower_gs = gridspec.GridSpecFromSubplotSpec(nrows=len(parm)*2, ncols=1, subplot_spec=outer_gs[i])
            j = 0
            for name in parm:
                title = name
                if name.find('chlorophyll') != -1 :
                    rangez = [0.0, 5.0]
                    units = ' (ug/l)'
                    if chl_series is None:
                        chl_series = name
                if name.find('salinity') != -1 :
                    rangez = [33.9, 34.3]
                    units = ''
                if name.find('temperature') != -1 :
                    rangez = [10, 15]
                    units = ' ($^\circ$C)'

                pn = self.platformName[0]

                x = [time.mktime(xe.timetuple()) for xe in self.data[pn+name]['datetime']]
                y = self.data[pn+name]['depth']
                z = self.data[pn+name]['datavalue']
                sdt_count = self.data[pn+name]['sdt_count']

                ax0 = plt.Subplot(fig, lower_gs[j])
                ax1 = plt.Subplot(fig, lower_gs[j+1])
                fig.add_subplot(ax0)
                fig.add_subplot(ax1)

                # if data found, plot with contour plot (if fails, falls back to the scatter plot)
                if len(x) > 0:
                    if chl_series is None:
                        latlon_series = name
                    else:
                        latlon_series = chl_series
                    cs0 = self.createContourPlot(title + pn,ax0,x,y,z,rangey,rangez,startDatetime,endDatetime,sdt_count)
                    cs1 = self.createScatterPlot(title + pn,ax1,x,y,z,rangey,rangez,startDatetime,endDatetime)
                else: # otherwise add in some fake data and plot a placeholder time/depth plot
                    tmin = time.mktime(startDatetime.timetuple())
                    tmax = time.mktime(endDatetime.timetuple())
                    x.append(tmin)
                    x.append(tmax)
                    y.append(np.NaN)
                    y.append(np.NaN)
                    z.append(np.NaN)
                    z.append(np.NaN)
                    cs0 = self.createScatterPlot(title + pn,ax0,x,y,z,rangey,rangez,startDatetime,endDatetime)
                    cs1 = self.createScatterPlot(title + pn,ax1,x,y,z,rangey,rangez,startDatetime,endDatetime)

                ax1.text(0.95,0.02, name, verticalalignment='bottom',
                         horizontalalignment='right',transform=ax1.transAxes,color='black',fontsize=8)

                # For a colorbar create an axes on the right side of ax. The width of cax will be 1%
                # of ax and the padding between cax and ax will be fixed at 0.2 inch.
                divider = make_axes_locatable(ax0)
                cax = divider.append_axes("right", size="1%", pad=0.1)
                cbFormatter = FormatStrFormatter('%.2f')
                cb = plt.colorbar(cs0, cax=cax, ticks=[min(rangez), max(rangez)], format=cbFormatter, orientation='vertical')
                cb.set_label(units,fontsize=8)#,labelpad=5)
                cb.ax.xaxis.set_ticks_position('top')
                for t in cb.ax.yaxis.get_ticklabels():
                    t.set_fontsize(8)

                divider = make_axes_locatable(ax1)
                cax = divider.append_axes("right", size="1%", pad=0.1)
                cbFormatter = FormatStrFormatter('%.2f')
                cb = plt.colorbar(cs0, cax=cax, ticks=[min(rangez), max(rangez)], format=cbFormatter, orientation='vertical')
                cb.set_label(units,fontsize=8)#,labelpad=5)
                cb.ax.xaxis.set_ticks_position('top')
                for t in cb.ax.yaxis.get_ticklabels():
                    t.set_fontsize(8)


                #self.plotNightDay(ax,x,startDatetime,endDatetime)
                # clear the x axes in everything but the last name in the group
                if name is not parm[-1]:
                    ax1.xaxis.set_ticks([])

                # always clear the x axes in the contour plot since this is placed above
                ax0.xaxis.set_ticks([])

                # Rotate and show the date with date formatter in the last plot
                if name is parm[-1]:
                    x_fmt = self.DateFormatter(self.scale_factor)
                    ax1.xaxis.set_major_formatter(x_fmt)
                    # Rotate date labels
                    for label in ax1.xaxis.get_ticklabels():
                        label.set_rotation(5)

                j+=2


        # plot tracks
        ax = plt.Subplot(fig, map_gs[:])
        fig.add_subplot(ax)#, aspect='equal')
        ltmin = 36.61
        ltmax = 36.97
        lnmin = -122.21
        lnmax = -121.73

        # pick lat/lon from last data series that had valid data and convert geometry objects to lat/lon
        lat = self.data[self.platformName[0]+latlon_series]['lat']
        lon = self.data[self.platformName[0]+latlon_series]['lon']

        # retry up to 5 times to get the basemap
        for i in range(0, 5):
            mp = Basemap(llcrnrlon=lnmin, llcrnrlat=ltmin, urcrnrlon=lnmax, urcrnrlat=ltmax, projection='cyl', resolution='l', ax=ax)
            try:
                ##mp.wmsimage('http://www.gebco.net/data_and_products/gebco_web_services/web_map_service/mapserv?', layers=['GEBCO_08_Grid'])                            # Works, but coarse
                mp.arcgisimage(server='http://services.arcgisonline.com/ArcGIS', service='Ocean_Basemap')
            except Exception, e:
                logger.error('Could not download ocean basemap ')
                mp = None

            if mp is not None :
                break

        if mp is None :
            logger.debug('Error - cannot cannot fetch basemap') 
            return


        if chl_series is not None:
            mp.plot(lon,lat,'-',c='k',alpha=0.5,linewidth=1, zorder=1)
            z = self.data[self.platformName[0]+chl_series]['datavalue']
            if len(z) > 50:
                sz = len(z)
                stride = int(sz/50)
                z_stride = z[0:sz:stride]
                lon_stride = lon[0:len(lon):stride]
                lat_stride = lat[0:len(lat):stride]
                mp.scatter(lon_stride,lat_stride,c=z_stride,s=20,marker='.',vmin=rangez[0],vmax=rangez[1],lw=0,alpha=1.0,cmap=self.cm_jetplus,zorder=2)
                if stride > 1:
                    ax.text(0.70,0.0, ('%s (every %d points)' % (chl_series, stride)), verticalalignment='bottom',
                         horizontalalignment='center',transform=ax.transAxes,color='black',fontsize=8)
                else:
                    ax.text(0.70,0.0, ('%s (every point)' % (chl_series)), verticalalignment='bottom',
                         horizontalalignment='center',transform=ax.transAxes,color='black',fontsize=8)

            else:
                mp.scatter(lon,lat,c=z,s=20,marker='.',vmin=rangez[0],vmax=rangez[1],lw=0,alpha=1.0,cmap=self.cm_jetplus,zorder=2)
                ax.text(0.70,0.0, ('%s (every point)' % (chl_series)), verticalalignment='bottom',
                         horizontalalignment='center',transform=ax.transAxes,color='black',fontsize=8)
        else:
            mp.plot(lon,lat,'-',c='k',alpha=0.5,linewidth=1,zorder=1)

        #mp.fillcontinents()
        #mp.drawcoastlines()

        if self.animate:
            # Get rid of the file extension if it's a png and append with indexed frame number
            fname = re.sub('\.png$','', self.outFilename)
            fname = '%s_frame_%02d.png' % (fname, self.frame)
        else:
            fname = self.outFilename
            
        logger.debug('Saving figure %s ' % fname)
        fig.savefig(fname,dpi=120)#,transparent=True)
        plt.close()
        self.frame += 1
        logger.debug('Done with contourPlot')


    def createContourPlot(self,title,ax,x,y,z,rangey,rangez,startTime,endTime,sdt_count):
        tmin = time.mktime(startTime.timetuple())
        tmax = time.mktime(endTime.timetuple())
        tgrid_max = 1000  # Reasonable maximum width for time-depth-flot plot is about 1000 pixels
        dgrid_max = 100   # Height of time-depth-flot plot area is 335 pixels
        dinc = 0.5       # Average vertical resolution of AUV Dorado
        nlevels = 255     # Number of color filled contour levels
        zmin = rangez[0]
        zmax = rangez[1]
        dmin = rangey[0]
        dmax = rangey[1]
        self.scale_factor = 1
        contour_flag = True

        if contour_flag:
            try:
                logger.debug('Gridding data')
                xi, yi = np.mgrid[tmin:tmax:1000j, dmin:dmax:100j]
                zi = griddata((x,y), z, (xi, yi), method='cubic')
            except KeyError, e:
                logger.warn('Got KeyError. Could not grid the data')
                contour_flag = False
            except Exception, e:
                logger.warn('Could not grid the data' +  str(e))
                contour_flag = False

        try:
            ax.set_xlim(tmin, tmax)
            ax.set_ylim([dmax,dmin])
            ax.set_ylabel('depth (m)',fontsize=8)

            ax.tick_params(axis='both',which='major',labelsize=8)
            ax.tick_params(axis='both',which='minor',labelsize=8)

            if contour_flag:
                logger.debug('Contouring the data')
                cs = ax.contourf(xi, yi, zi, levels=np.linspace(zmin,zmax, nlevels), cmap=self.cm_jetplus, extend='both')
                # this will show the points where the contouring occurs
                ax.scatter(x,y,marker='.',s=2,c='k',lw=0)
            else:
                logger.debug('Plotting the data')
                cs = ax.scatter(x,y,c=z,s=10,marker='.',vmin=zmin,vmax=zmax,lw=0,alpha=1.0,cmap=self.cm_jetplus)

            # limit the number of ticks
            max_yticks = 5
            yloc = plt.MaxNLocator(max_yticks)
            ax.yaxis.set_major_locator(yloc)

        except Exception,e:
            logger.error(e)

        return cs

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

            ax.set_ylim([dmax,dmin])
            ax.set_ylabel('depth (m)',fontsize=8)

            ax.tick_params(axis='both',which='major',labelsize=8)
            ax.tick_params(axis='both',which='minor',labelsize=8)

            logger.debug('Plotting the data')
            cs = ax.scatter(x,y,c=z,s=10,marker='.',vmin=zmin,vmax=zmax,lw=0,alpha=1.0,cmap=self.cm_jetplus)

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

        self.subtitle = '%s  to  %s PDT' % (startDatetimeLocal.strftime('%Y-%m-%d %H:%M'), endDatetimeLocal.strftime('%Y-%m-%d %H:%M'))

        if self.animate:
            zoomWindow = timedelta(hours=self.zoom)
            overlapWindow = timedelta(hours=self.overlap)
            endDatetime = self.startDatetime + self.zoom
            end = self.endDatetime
            try:
                # Loop through sections of the data with temporal query constraints based on the window and step command line parameters
                while endDatetime <= end :
                    self.loadData(startDatetime, endDatetime)
                    self.createPlot(startDatetime, endDatetime)
                    startDatetime = endDatetime - overlapWindow
                    endDatetime = startDatetime + zoomWindow

                # Do a linear transition of transparency for a stronger indication of activity
                '''i = 0
                for a in hstack((arange(0, 1.0, 0.1), arange(1.0, 0, -0.1))):
                    # Use background color of bootstrap's .well class
                    cmd = "convert -size 1x1 xc:#f5f5f5 -fill 'rgba(192,211,228,%.2f)' -draw 'point 0,0' pulse_%03d.gif" % (a, i)
                    print cmd
                    os.system(cmd)
                    i = i + 1

                cmd = "convert -loop 0 -delay 1 pulse*.gif ajax-loader-pulse.gif"
                print cmd
                os.system(cmd)'''

            except Exception, e:
                logger.error(e)

        else :
            try:
                self.loadData(self.startDatetime, self.endDatetime)
                self.createPlot(self.startDatetime, self.endDatetime)
            except Exception, e:
                logger.error(e)
