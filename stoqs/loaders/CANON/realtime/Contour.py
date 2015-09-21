__author__ = 'dcline'

import sys

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

from django.contrib.gis.geos import fromstr, MultiPoint
from collections import OrderedDict
from collections import defaultdict
from django.db import connections
from datetime import datetime, timedelta
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
#from matplotlib.mlab import griddata
from scipy.interpolate import griddata
from scipy.spatial import ckdtree
from scipy.interpolate import Rbf
from mpl_toolkits.basemap import Basemap
from stoqs.models import Activity, ActivityParameter, ParameterResource, Platform, SimpleDepthTime, MeasuredParameter, Measurement, Parameter
from utils.utils import percentile

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
    def __init__(self, startDatetime, endDatetime, database, platformName, plotGroup, title, outFilename, animate, autoscale):
        self.startDatetime = startDatetime
        self.endDatetime = endDatetime
        self.platformName = platformName
        self.plotGroup = plotGroup
        self.plotGroupValid = []
        self.title = title
        self.animate = animate
        self.outFilename = outFilename
        self.database = database
        self.platformName = platformName
        self.autoscale = autoscale


    def getTimeSeriesData(self, startDatetime, endDatetime):
        '''
        Return time series of a list of Parameters from a Platform
        '''
        data_dict = defaultdict(lambda: {'datetime': [], 'lon': [], 'lat': [], 'depth': [], 'datavalue':[]})

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
        plot_scatter = True 
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
                if sz > 2000:
                    plot_scatter = False


        plot_scatter = True

        # pad the depth by 20 meters to make room for parameter name to be displayed at bottom
        rangey = [0.0, int(maxy) + 20]

        latlon_series = None
        chl_series = None
        i = 0
        # add contour plots for each parameter group
        for group in self.plotGroupValid:
            parm = [x.strip() for x in group.split(',')]
            if plot_scatter:
                contour_gs = gridspec.GridSpecFromSubplotSpec(nrows=len(parm)*2, ncols=1, subplot_spec=lower_gs[i])
            else:
                contour_gs = gridspec.GridSpecFromSubplotSpec(nrows=len(parm), ncols=1, subplot_spec=lower_gs[i])
            j = 0
            i += 1
            for name in parm:
                title = name
                x = [time.mktime(xe.timetuple()) for xe in self.data[pn+name]['datetime']]
                y = self.data[pn+name]['depth']
                z = self.data[pn+name]['datavalue']
                sdt_count = self.data[pn+name]['sdt_count']

                units = ''

                if len(z):
                    if self.autoscale:
                        numpvar = np.array(z)
                        numpvar.sort()
                        listvar = list(numpvar)
                        p010 = percentile(listvar, 0.010)
                        p990 = percentile(listvar, 0.990)
                        rangez = [p010,p990]
                    else:
                        rangez = [min(z), max(z)]
                else:
                    rangez = [0, 0]

                if name.find('chlorophyll') != -1 :
                    if not self.autoscale:
                        rangez = [0.0, 10.0]
                    units = ' (ug/l)'
                if name.find('salinity') != -1 :
                    if not self.autoscale:
                        rangez = [33.3, 34.9]
                    units = ''
                if name.find('temperature') != -1 :
                    if not self.autoscale:
                        rangez = [10.0, 14.0]
                    units = ' ($^\circ$C)'
  
                gs  = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=contour_gs[j])
                ax0 = plt.Subplot(fig, gs[:])
                fig.add_subplot(ax0)
                if plot_scatter:  
                    gs  = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=contour_gs[j+1])
                    ax1 = plt.Subplot(fig, gs[:])
                    fig.add_subplot(ax1)

                # if data found, plot with contour plot (if fails, falls back to the scatter plot)
                if len(x) > 0:
                    cs0, zi = self.createContourPlot(title + pn,ax0,x,y,z,rangey,rangez,startDatetime,endDatetime,sdt_count)
                    if plot_scatter:
                        cs1 = self.createScatterPlot(title + pn,ax1,x,y,z,rangey,rangez,startDatetime,endDatetime)
                    if latlon_series is None:
                        latlon_series = name
                    if chl_series is None and name.find('chlorophyll') != -1:
                        chl_series = name

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
                    if plot_scatter: 
                        cs1 = self.createScatterPlot(title + pn,ax1,x,y,z,rangey,rangez,startDatetime,endDatetime)

                if plot_scatter:
                    ax1.text(0.95,0.02, name, verticalalignment='bottom',
                                horizontalalignment='right',transform=ax1.transAxes,color='black',fontsize=8)
                else:
                    ax0.text(0.95,0.02, name, verticalalignment='bottom',
                        horizontalalignment='right',transform=ax0.transAxes,color='black',fontsize=8)

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

                if plot_scatter:
                    divider = make_axes_locatable(ax1)
                    cax = divider.append_axes("right", size="1%", pad=0.1)
                    cbFormatter = FormatStrFormatter('%.2f')
                    cb = plt.colorbar(cs0, cax=cax, ticks=[min(rangez), max(rangez)], format=cbFormatter, orientation='vertical')
                    cb.set_label(units,fontsize=8)#,labelpad=5)
                    cb.ax.xaxis.set_ticks_position('top')
                    for t in cb.ax.yaxis.get_ticklabels():
                        t.set_fontsize(8)

                #self.plotNightDay(ax,x,startDatetime,endDatetime)

                # Rotate and show the date with date formatter in the last plot of all the groups
                if name is parm[-1] and group is self.plotGroupValid[-1]:
                    x_fmt = self.DateFormatter(self.scale_factor)
                    if plot_scatter: 
                        ax = ax1
                        # Don't show on the upper contour plot 
                        ax0.xaxis.set_ticks([])  
                    else: 
                        ax = ax0  
                    ax.xaxis.set_major_formatter(x_fmt)
                    # Rotate date labels
                    for label in ax.xaxis.get_ticklabels():
                        label.set_rotation(10)
                else:
                    ax0.xaxis.set_ticks([])
                    if plot_scatter:  
                        ax1.xaxis.set_ticks([])

                if plot_scatter:
                    j+=2 
                else: 
                    j+=1 


        # plot tracks
        ax = plt.Subplot(fig, map_gs[:])
        fig.add_subplot(ax, aspect='equal')

        logger.debug('Getting activity extents')
        z = []
        maptracks = None

        if chl_series is not None:
            z, points, maptracks = self.getMeasuredPPData(startDatetime, endDatetime, self.platformName[0], chl_series)
        else:
            z, points, maptracks = self.getMeasuredPPData(startDatetime, endDatetime, self.platformName[0], latlon_series)

        # get the percentile ranges for this to autoscale
        pointsnp = np.array(points)
        lon = pointsnp[:,0]
        lat = pointsnp[:,1]

        if len(lat) > 0:
            ltmin = min(lat)
            ltmax = max(lat)
            lnmin = min(lon)
            lnmax = max(lon)
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
            for track in maptracks:
                if track is not None:
                    ln,lt = zip(*track)
                    mp.plot(ln,lt,'-',c='k',alpha=0.5,linewidth=2, zorder=1)

            # if have a valid chl series, then plot the dots
            if chl_series is not None and len(z) > 0:
                if len(z) > 2000:
                    sz = len(z)
                    stride = int(sz/200)
                    z_stride = z[0:sz:stride]
                    lon_stride = lon[0:sz:stride]
                    lat_stride = lat[0:sz:stride]
                    # scale the size of the point by chlorophyll value
                    s = [10*chl for chl in z_stride]
                    mp.scatter(lon_stride,lat_stride,c=z_stride,s=s,marker='.',vmin=rangez[0],vmax=rangez[1],lw=0,alpha=1.0,cmap=self.cm_jetplus,zorder=2)
                    if stride > 1:
                        ax.text(0.70,0.1, ('%s (every %d points)' % (chl_series, stride)), verticalalignment='bottom',
                             horizontalalignment='center',transform=ax.transAxes,color='black',fontsize=8)
                    else:
                        ax.text(0.70,0.1, ('%s (every point)' % (chl_series)), verticalalignment='bottom',
                             horizontalalignment='center',transform=ax.transAxes,color='black',fontsize=8)

                else:
                    # scale the size of the point by chlorophyll value
                    s = [10*chl for chl in z]
                    mp.scatter(lon,lat,c=z,s=s,marker='.',vmin=rangez[0],vmax=rangez[1],lw=0,alpha=1.0,cmap=self.cm_jetplus,zorder=2)
                    ax.text(0.70,0.1, ('%s (every point)' % (chl_series)), verticalalignment='bottom',
                             horizontalalignment='center',transform=ax.transAxes,color='black',fontsize=8)

        except Exception, e:
            logger.warn(e)

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


    def run(self):

        self.frame = 0

        endDatetimeLocal = self.endDatetime.astimezone(pytz.timezone('America/Los_Angeles'))
        startDatetimeLocal = self.startDatetime.astimezone(pytz.timezone('America/Los_Angeles'))

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
                logger.debug('Loading data')
                dataStart, dataEnd = self.loadData(self.startDatetime, self.endDatetime)
                if self.data is not None:
                    if dataStart.tzinfo is None:
                        dataStart =  pytz.utc.localize(dataStart)
                    if dataEnd.tzinfo is None:
                        dataEnd = pytz.utc.localize(dataEnd)
                    dataEndDatetimeLocal = dataEnd.astimezone(pytz.timezone('America/Los_Angeles'))
                    dataStartDatetimeLocal = dataStart.astimezone(pytz.timezone('America/Los_Angeles'))
                    logger.debug('Plotting data')
                    self.subtitle1 = '%s  to  %s PDT' % (dataStartDatetimeLocal.strftime('%Y-%m-%d %H:%M'), dataEndDatetimeLocal.strftime('%Y-%m-%d %H:%M'))
                    self.subtitle2 = '%s  to  %s UTC' % (dataStart.strftime('%Y-%m-%d %H:%M'), dataEnd.strftime('%Y-%m-%d %H:%M'))
                    self.createPlot(dataStart, dataEnd)
            except Exception, e:
                logger.error(e)
