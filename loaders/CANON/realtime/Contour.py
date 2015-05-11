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
import matplotlib.ticker as ticker
import numpy as np
import re
import pylab as pl
import time
import pytz
import stoqs.models

from collections import defaultdict
from datetime import datetime, timedelta
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
from matplotlib.mlab import griddata
from mpl_toolkits.basemap import Basemap
from stoqs.models import Activity, ActivityParameter, ParameterResource, Platform, SimpleDepthTime, MeasuredParameter, Measurement, Parameter

class Contour(object):

    '''
    Create plots for visualizing data from LRAUV vehicles
    '''
    def __init__(self, startDatetime, endDatetime, database, platformName, parms, title, outFilename, animate):
        self.startDatetime = startDatetime
        self.endDatetime = endDatetime
        self.platformName = platformName
        self.parms = parms
        self.title = title
        self.animate = animate
        self.outFilename = outFilename
        self.database = database
        self.platformName = platformName
        self.parameterName = parms


    def getTimeSeriesData(self, startDatetime, endDatetime):
        '''
        Return time series of a Parameter from a Platform
        '''
        data_dict = defaultdict(lambda: {'datetime': [], 'lon': [], 'lat': [], 'depth': [], 'datavalue':[]})

        if not self.parameterName :
            raise Exception('Must specify list parameterNames')

        for pln in self.platformName:
            for pname in self.parameterName :
                qs = MeasuredParameter.objects.using(self.database)

                qs = qs.filter(measurement__instantpoint__timevalue__gte=startDatetime)
                qs = qs.filter(measurement__instantpoint__timevalue__lte=endDatetime)
                qs = qs.filter(parameter__name=pname)
                qs = qs.filter(measurement__instantpoint__activity__platform__name=pln)

                qs = qs.values('measurement__instantpoint__timevalue', 'measurement__depth', 'measurement__geom', 'datavalue').order_by('measurement__instantpoint__timevalue')

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
            print "WARNING:", e

    def formatDate(self, x, pos=None):
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


    def createPlot(self, startDatetime, endDatetime):

        if not self.data:
            print 'no data found to plot'
            return

        # GridSpecs for contour subplots
        outer_gs = gridspec.GridSpec(nrows=4, ncols=1)#, height_ratios=[1,3])
        map_gs  = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=outer_gs[0])

        STATIC_ROOT = '/var/www/html/stoqs/static'      # Warning: Hard-coded
        clt = self.readCLT(os.path.join(STATIC_ROOT, 'colormaps', 'jetplus.txt'))
        self.cm_jetplus = mpl.colors.ListedColormap(np.array(clt))

        # fix depth range
        rangey = [0.0,70.0]

        # start a new figure - size is in inches
        fig = plt.figure(figsize=(8, 10))
        fig.suptitle(self.title+'\n'+self.subtitle, fontsize=8)

        # add contour plots for each parameter in each database
        i = 1
        parameters = self.parms
        
        for name in parameters:
            title = name
            if name.find('chlorophyll') != -1 :
                rangez = [0.0, 5.0]
                title += ' (ug/l)'
            if name.find('salinity') != -1 :
                rangez = [33.5, 33.9]
            if name.find('temperature') != -1 :
                rangez = [10, 15]
                title += ' ($^\circ$C)'
                
            cblabel = False
            lower_gs = gridspec.GridSpecFromSubplotSpec(nrows=2, ncols=1, subplot_spec=outer_gs[i])
            j = 0
            i += 1
            for pn in self.platformName:
                x = [time.mktime(xe.timetuple()) for xe in self.data[pn+name]['datetime']]
                y = self.data[pn+name]['depth']
                z = self.data[pn+name]['datavalue']
    
                # Create the contour plot and label according to the database name
                ax = plt.Subplot(fig, lower_gs[j])
                fig.add_subplot(ax)

                # Plot interpolated data with contour plot (if not possible, changes to the scatter plot)
                if name.find('_i'):
                    cs0 = self.createContourPlot(title + pn,ax,x,y,z,rangey,rangez,startDatetime,endDatetime)
                else:
                    cs0 = self.createScatterPlot(title + pn,ax,x,y,z,rangey,rangez,startDatetime,endDatetime)

                ax.xaxis.set_ticks([])
                ax.text(0.95,0.02, pn, verticalalignment='bottom',
                         horizontalalignment='right',transform=ax.transAxes,color='blue',fontsize=12)
                ax.xaxis.set_ticks([])
                
                if not cblabel and cs0:
                    cblabel = True
                    # For a colorbar create an axes on the top side of ax. The width of cax will be 3%
                    # of ax and the padding between cax and ax will be fixed at 0.1 inch.
                    divider = make_axes_locatable(ax)
                    cax = divider.append_axes("top", size="10%", pad=0.1)
                    cbFormatter = FormatStrFormatter('%.2f')
                    cb = plt.colorbar(cs0, cax=cax, ticks=[min(rangez), max(rangez)], format=cbFormatter, orientation='horizontal')
                    cb.set_label(title,fontsize=8,labelpad=-15)
                    cb.ax.xaxis.set_ticks_position('top')
                    for t in cb.ax.get_xticklabels():
                        t.set_fontsize(8)
    
                j += 1
            
        # Show the date in the last plot
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(self.formatDate))  

        #self.plotNightDay(ax1,ax2,ax3,ax4,sti,eti)'''

        # plot tracks
        ax = plt.Subplot(fig, map_gs[:])
        fig.add_subplot(ax)#, aspect='equal')
        ltmin = 36.61
        ltmax = 36.97
        lnmin = -122.21
        lnmax = -121.73

        # arbitrarily pick lat/lon from first data series and convert geometry objects to lat/lon
        # this should actually be the same for all
        lat = self.data[self.platformName[0]+name]['lat']
        lon = self.data[self.platformName[0]+name]['lon']

        # retry up to 5 times to get the basemap
        for i in range(0, 5):
            mp = Basemap(llcrnrlon=lnmin, llcrnrlat=ltmin, urcrnrlon=lnmax, urcrnrlat=ltmax, projection='cyl', resolution='l', ax=ax)
            try:
                ##mp.wmsimage('http://www.gebco.net/data_and_products/gebco_web_services/web_map_service/mapserv?', layers=['GEBCO_08_Grid'])                            # Works, but coarse
                mp.arcgisimage(server='http://services.arcgisonline.com/ArcGIS', service='Ocean_Basemap')
            except Exception, e:
                print 'Could not download ocean basemap '
                mp = None

            if mp is not None :
                break

        if mp is None :
            print 'Error - cannot cannot fetch basemap' # TODO add logger message here
            return

        mp.plot(lon, lat, '-',  linewidth=3)
        #mp.fillcontinents()
        #mp.drawcoastlines()

        if self.animate:
            # Get rid of the file extension if it's a png and append with indexed frame number
            fname = re.sub('\.png$','', self.outFilename)
            fname = '%s_frame_%02d.png' % (fname, self.frame)
        else:
            fname = self.outFilename
            
        print 'Saving figure ' + fname
        fig.savefig(fname,dpi=120)#,transparent=True)
        plt.close()
        self.frame += 1
        print "Done with createPlot"




    def createContourPlot(self,title,ax,x,y,z,rangey,rangez,startTime,endTime,hasCB=False):
        tmin = time.mktime(startTime.timetuple())
        tmax = time.mktime(endTime.timetuple())
        tgrid_max = 1000  # Reasonable maximum width for time-depth-flot plot is about 1000 pixels
        dgrid_max = 100   # Height of time-depth-flot plot area is 335 pixels
        dinc = 0.05       # Average vertical resolution of AUV Dorado
        nlevels = 255     # Number of color filled contour levels
        sdt_count = int(len(x)/2)
        zmin = rangez[0]
        zmax = rangez[1]
        dmin = rangey[0]
        dmax = rangey[1]
        scale_factor = 1

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
            scale_factor = float(tmax -tmin) / (dmax - dmin) / 3.0
        except ZeroDivisionError, e:
            print 'Not setting scale_factor.  Scatter plots will still work.'
            contour_flag = False
            scale_factor = 1
        else:
            print 'self.scale_factor = %f' % scale_factor
            xi = xi / scale_factor
            xg = [xe/scale_factor for xe in x]
            contour_flag = True

        if contour_flag:
            try:
                print 'Gridding data with sdt_count = %d, and y_count = %d' %(sdt_count, y_count)
                zi = griddata(xg, y, z, xi, yi, interp='nn')
            except KeyError, e:
                print 'Got KeyError. Could not grid the data'
            except Exception, e:
                print 'Could not grid the data'
                contour_flag = False
                scale_factor = 1

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
                print 'Contouring the data'
                cs = ax.contourf(xi, yi, zi, levels=np.linspace(zmin,zmax, nlevels), cmap=self.cm_jetplus, extend='both')
                # this will show the points where the contouring occurs
                ax.scatter(xg,y,marker='.',s=2,c='k',lw=0)
            else:
                print 'Plotting the data'
                cs = ax.scatter(x,y,c=z,s=20,vmin=zmin,vmax=zmax,cmap=self.cm_jetplus)

        except Exception,e:
            print 'Unexpected error: ' +  str(e)

        return cs

    def createScatterPlot(self,title,ax,x,y,z,rangey,rangez,startTime,endTime,hasCB=False):
        tmin = time.mktime(startTime.timetuple())
        tmax = time.mktime(endTime.timetuple())
        nlevels = 255     # Number of color filled contour levels
        sdt_count = int(len(x)/2)
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

            print 'Plotting the data'
            cs = ax.scatter(x,y,c=z,s=20,vmin=zmin,vmax=zmax,cmap=self.cm_jetplus)

        except Exception,e:
            print 'Unexpected error: ' +  str(e)

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
                print 'Unexpected error: ' +  str(e)

        else :
            try:
                self.loadData(self.startDatetime, self.endDatetime)
                self.createPlot(self.startDatetime, self.endDatetime)
            except Exception, e:
                print 'Unexpected error: ' +  str(e)
