__author__    = 'Mike McCann'
__copyright__ = '2012'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Module with various functions to supprt data visualization.  These can be quite verbose
with all of the Matplotlib customization required for nice looking graphics.

@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import tempfile
# Setup Matplotlib for running on the server
os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp()
import matplotlib
matplotlib.use('Agg')               # Force matplotlib to not use any Xwindows backend
import matplotlib.pyplot as plt
from matplotlib.mlab import griddata
from matplotlib import mpl
from pylab import polyfit, polyval
from django.conf import settings
from django.db.models.query import RawQuerySet
from django.db import connections
from datetime import datetime
from KML import readCLT
from stoqs import models
from utils.utils import postgresifySQL, pearsonr, round_to_n
from loaders.SampleLoaders import SAMPLED
from loaders import MEASUREDINSITU
import seawater.csiro as sw
import numpy as np
import logging
import string
import random
import time

logger = logging.getLogger(__name__)

class ContourPlots(object):
    '''
    Use matploptib to create nice looking contour plots
    '''
    def __init__(self, kwargs, request, qs, qs_mp, parameterMinMax, sampleQS, platformName):
        '''
        Save parameters that can be used by the different plotting methods here
        '''
        self.kwargs = kwargs
        self.request = request
        self.qs = qs
        self.qs_mp = qs_mp
        self.parameterMinMax = parameterMinMax
        self.sampleQS = sampleQS
        self.platformName = platformName

    def contourDatavaluesForFlot(self, tgrid_max=1000, dgrid_max=100, dinc=0.5, nlevels=255, contourFlag=True):
        '''
        Produce a .png image without axes suitable for overlay on a Flot graphic. Return a
        3 tuple of (sectionPngFile, colorbarPngFile, errorMessage)

        # griddata parameter defaults
        tgrid_max = 1000            # Reasonable maximum width for time-depth-flot plot is about 1000 pixels
        dgrid_max = 100             # Height of time-depth-flot plot area is 335 pixels
        dinc = 0.5                  # Average vertical resolution of AUV Dorado
        nlevels = 255               # Number of color filled contour levels
        '''

        # Use session ID so that different users don't stomp on each other with their section plots
        # - This does not work for Firefox which just reads the previous image from its cache
        if self.request.session.has_key('sessionID'):
            sessionID = self.request.session['sessionID']
        else:
            sessionID = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(7))
            self.request.session['sessionID'] = sessionID
        # - Use a new imageID for each new image
        imageID = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(10))
        sectionPngFile = self.kwargs['measuredparametersgroup'][0] + '_' + self.platformName + '_' + imageID + '.png'
        sectionPngFileFullPath = os.path.join(settings.MEDIA_ROOT, 'sections', sectionPngFile)
        colorbarPngFile = self.kwargs['measuredparametersgroup'][0] + '_' + self.platformName + '_colorbar_' + imageID + '.png'
        colorbarPngFileFullPath = os.path.join(settings.MEDIA_ROOT, 'sections', colorbarPngFile)
        
        # Estimate horizontal (time) grid spacing by number of points in selection, expecting that simplified depth-time
        # query has salient points, typically in the vertices of the yo-yos.  
        tmin = None
        tmax = None
        xi = None
        if self.kwargs.has_key('time'):
            if self.kwargs['time'][0] is not None and self.kwargs['time'][1] is not None:
                dstart = datetime.strptime(self.kwargs['time'][0], '%Y-%m-%d %H:%M:%S') 
                dend = datetime.strptime(self.kwargs['time'][1], '%Y-%m-%d %H:%M:%S') 
                tmin = time.mktime(dstart.timetuple())
                tmax = time.mktime(dend.timetuple())
        ##if not tmin and not tmax:
        ##    logger.debug('Time range not specified in query, getting it from the database')
        ##    tmin, tmax = self.getTime()

        if tmin and tmax:
            sdt_count = self.qs.filter(platform__name = self.platformName).values_list('simpledepthtime__depth').count()
            sdt_count = int(sdt_count / 2)                 # 2 points define a line, take half the number of simpledepthtime points
            logger.debug('Half of sdt_count from query = %d', sdt_count)
            if sdt_count > tgrid_max:
                sdt_count = tgrid_max

            xi = np.linspace(tmin, tmax, sdt_count)
            ##logger.debug('xi = %s', xi)

        # Make depth spacing dinc m, limit to time-depth-flot resolution (dgrid_max)
        dmin = None
        dmax = None
        yi = None
        if self.kwargs.has_key('depth'):
            if self.kwargs['depth'][0] is not None and self.kwargs['depth'][1] is not None:
                dmin = float(self.kwargs['depth'][0])
                dmax = float(self.kwargs['depth'][1])

        if dmin is not None and dmax is not None:
            y_count = int((dmax - dmin) / dinc )
            if y_count > dgrid_max:
                y_count = dgrid_max
            yi = np.linspace(dmin, dmax, y_count)
            ##logger.debug('yi = %s', yi)


        # Collect the scattered datavalues(time, depth) and grid them
        if xi is not None and yi is not None:
            # Estimate a scale factor to apply to the x values on drid data so that x & y values are visually equal for the flot plot
            # which is assumed to be 3x wider than tall.  Approximate horizontal coverage by Dorado is 1 m/s.
            try:
                scale_factor = float(tmax -tmin) / (dmax - dmin) / 3.0
            except ZeroDivisionError, e:
                logger.warn(e)
                return None, None, 'Bad depth range'
                
            logger.debug('scale_factor = %f', scale_factor)
            xi = xi / scale_factor

            try:
                os.remove(sectionPngFileFullPath)
            except Exception, e:
                logger.warn(e)

            logger.debug('Gridding data with sdt_count = %d, and y_count = %d', sdt_count, y_count)
            x = []
            y = []
            z = []
            logger.debug('type(self.qs_mp) = %s', type(self.qs_mp))
            i = 0
            for mp in self.qs_mp:
                x.append(time.mktime(mp['measurement__instantpoint__timevalue'].timetuple()) / scale_factor)
                y.append(mp['measurement__depth'])
                z.append(mp['datavalue'])
                i = i + 1
                if (i % 1000) == 0:
                    logger.debug('Appended %i measurements to x, y, and z', i)

            if self.kwargs.has_key('parametervalues'):
                if self.kwargs['parametervalues']:
                    contourFlag = False
          
            logger.debug('Number of x, y, z data values retrived from database = %d', len(z)) 
            if contourFlag:
                try:
                    zi = griddata(x, y, z, xi, yi, interp='nn')
                except KeyError, e:
                    logger.exception('Got KeyError. Could not grid the data')
                    return None, None, 'Got KeyError. Could not grid the data'
                except Exception, e:
                    logger.exception('Could not grid the data')
                    return None, None, 'Could not grid the data'

                logger.debug('zi = %s', zi)

            parm_info = self.parameterMinMax
            try:
                # Make the plot
                # contour the gridded data, plotting dots at the nonuniform data points.
                # See http://scipy.org/Cookbook/Matplotlib/Django
                fig = plt.figure(figsize=(6,3))
                ax = fig.add_axes((0,0,1,1))
                ax.set_xlim(tmin / scale_factor, tmax / scale_factor)
                ax.set_ylim(dmax, dmin)
                ax.get_xaxis().set_ticks([])
                clt = readCLT(os.path.join(settings.STATIC_ROOT, 'colormaps', 'jetplus.txt'))
                cm_jetplus = matplotlib.colors.ListedColormap(np.array(clt))
                if contourFlag:
                    ax.contourf(xi, yi, zi, levels=np.linspace(parm_info[1], parm_info[2], nlevels), cmap=cm_jetplus, extend='both')
                    ax.scatter(x, y, marker='.', s=2, c='k', lw = 0)
                else:
                    ax.scatter(x, y, c=z, s=20, cmap=cm_jetplus, lw=0, vmin=parm_info[1], vmax=parm_info[2])

                if self.sampleQS:
                    # Add sample locations and names
                    xsamp = []
                    ysamp = []
                    sname = []
                    for s in self.sampleQS.values('instantpoint__timevalue', 'depth', 'name'):
                        xsamp.append(time.mktime(s['instantpoint__timevalue'].timetuple()) / scale_factor)
                        ysamp.append(s['depth'])
                        sname.append(s['name'])
                    ax.scatter(xsamp, ysamp, marker='o', c='w', s=15, zorder=10)
                    for x,y,sn in zip(xsamp, ysamp, sname):
                        plt.annotate(sn, xy=(x,y), xytext=(5,-5), textcoords = 'offset points', fontsize=7)

                fig.savefig(sectionPngFileFullPath, dpi=120, transparent=True)
                plt.close()
            except Exception,e:
                logger.exception('Could not plot the data')
                return None, None, 'Could not plot the data'

            try:
                # Make colorbar as a separate figure
                cb_fig = plt.figure(figsize=(5, 0.8))
                cb_ax = cb_fig.add_axes([0.1, 0.8, 0.8, 0.2])
                logger.debug('parm_info = %s', parm_info)
                parm_units = models.Parameter.objects.filter(name=parm_info[0]).values_list('units')[0][0]
                logger.debug('parm_units = %s', parm_units)
                norm = mpl.colors.Normalize(vmin=parm_info[1], vmax=parm_info[2], clip=False)
                cb = mpl.colorbar.ColorbarBase( cb_ax, cmap=cm_jetplus,
                                                norm=norm,
                                                ticks=[parm_info[1], parm_info[2]],
                                                orientation='horizontal')
                cb.ax.set_xticklabels([str(parm_info[1]), str(parm_info[2])])
                cb.set_label('%s (%s)' % (parm_info[0], parm_units))
                logger.debug('ticklabels = %s', [str(parm_info[1]), str(parm_info[2])])
                cb_fig.savefig(colorbarPngFileFullPath, dpi=120, transparent=True)
                plt.close()
            except Exception,e:
                logger.exception('Could not plot the colormap')
                return None, None, 'Could not plot the colormap'

            return sectionPngFile, colorbarPngFile, ''
        else:
            logger.debug('xi and yi are None.  tmin, tmax, dmin, dmax = %f, %f, %f, %f, %f, %f ', tmin, tmax, dmin, dmax)
            return None, None, 'No depth-time region specified'


class ParameterParameter(object):
    '''
    Use matploplib to create nice looking property-property plots
    '''
    def __init__(self, request, pDict, mpq, pq, pMinMax):
        '''
        Save parameters that can be used by the different plotting methods here
        '''
        self.request = request
        self.pDict = pDict
        self.mpq = mpq
        self.pq = pq
        self.pMinMax = pMinMax
        self.depth = []
        self.x = []
        self.y = []
        self.z = []
        self.c = []

    def computeSigmat(self, limits, xaxis_name='sea_water_salinity', pressure=0):
        '''
        Given a tuple of limits = (xmin, xmax, ymin, ymax) and an xaxis_name compute 
        density for a range of values between the mins and maxes.  Return the X and Y values
        for Salinity/temperature and density converted to sigma-t.  A pressure argument may
        be provided for computing sigmat for that pressure.
        '''
        ns = 50
        nt = 50
        sigmat = []
        if xaxis_name == 'sea_water_salinity':
            s = np.linspace(limits[0], limits[1], ns, endpoint=False)
            t = np.linspace(limits[2], limits[3], nt, endpoint=False)
            for ti in t:
                row = []
                for si in s:
                    row.append(sw.dens(si, ti, pressure) - 1000.0)
                sigmat.append(row)

        elif xaxis_name == 'sea_water_temperature':
            t = np.linspace(limits[0], limits[1], nt, endpoint=False)
            s = np.linspace(limits[2], limits[3], ns, endpoint=False)
            for si in s:
                row = []
                for ti in t:
                    row.append(sw.dens(si, ti, pressure) - 1000.0)
                sigmat.append(row)

        else:
            raise Exception('Cannot compute sigma-t with xaxis_name = "%s"', xaxis_name)

        if xaxis_name == 'sea_water_salinity':
            return s, t, sigmat
        elif xaxis_name == 'sea_water_temperature':
            return t, s, sigmat

    def make2DPlot(self):
        '''
        Produce a .png image 
        '''
        try:
            # self.x and self.y may already be set for this instance by makeX3D()
            if not self.x and not self.y:
                # Construct special SQL for P-P plot that returns up to 3 data values for the up to 3 Parameters requested for a 2D plot
                sql = str(self.pq.qs_mp.query)
                sql = self.pq.addParameterParameterSelfJoins(sql, self.pDict)

                # Use cursor so that we can specify the database alias to use. Columns are always 0:x, 1:y, 2:c (optional)
                cursor = connections[self.request.META['dbAlias']].cursor()
                cursor.execute(sql)
                for row in cursor:
                    # SampledParameter datavalues are Decimal, convert everything to a float for numpy, row[0] is depth
                    self.depth.append(float(row[0]))
                    self.x.append(float(row[1]))
                    self.y.append(float(row[2]))
                    try:
                        self.c.append(float(row[3]))
                    except IndexError:
                        pass

            # Use session ID so that different users don't stomp on each other with their parameterparameter plots
            # - This does not work for Firefox which just reads the previous image from its cache
            if self.request.session.has_key('sessionID'):
                sessionID = self.request.session['sessionID']
            else:
                sessionID = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(7))
                self.request.session['sessionID'] = sessionID
            # - Use a new imageID for each new image
            imageID = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(10))
            ppPngFile = '%s_%s_%s_%s.png' % (self.pDict['x'], self.pDict['y'], self.pDict['c'], imageID)
            ppPngFileFullPath = os.path.join(settings.MEDIA_ROOT, 'parameterparameter', ppPngFile)
            logger.debug('ppPngFileFullPath = %s', ppPngFileFullPath)

            # Make the figure
            fig = plt.figure()
            plt.grid(True)
            ax = fig.add_subplot(111)
            clt = readCLT(os.path.join(settings.STATIC_ROOT, 'colormaps', 'jetplus.txt'))
            cm_jetplus = matplotlib.colors.ListedColormap(np.array(clt))
            if self.c:
                ax.scatter(self.x, self.y, c=self.c, s=10, cmap=cm_jetplus, lw=0, vmin=self.pMinMax['c'][1], vmax=self.pMinMax['c'][2])
                # Add colorbar
                cb_ax = fig.add_axes([0.2, 0.98, 0.6, 0.02]) 
                norm = mpl.colors.Normalize(vmin=self.pMinMax['c'][1], vmax=self.pMinMax['c'][2], clip=False)
                cb = mpl.colorbar.ColorbarBase( cb_ax, cmap=cm_jetplus,
                                                norm=norm,
                                                ticks=[self.pMinMax['c'][1], self.pMinMax['c'][2]],
                                                orientation='horizontal')
                cp = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['c']))
                cb.set_label('%s (%s)' % (cp.name, cp.units))
            else:
                ax.scatter(self.x, self.y, marker='.', s=10, c='k', lw = 0)

            # Labels the axes
            xp = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['x']))
            ax.set_xlabel('%s (%s)' % (xp.name, xp.units))
            yp = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['y']))
            ax.set_ylabel('%s (%s)' % (yp.name, yp.units))

            # Add Sigma-t contours if x/y is salinity/temperature, approximate depth to pressure - must fix for deep water...
            Z = None
            infoText = ''
            meanDepth = round(np.mean(self.depth))
            if xp.standard_name == 'sea_water_salinity' and yp.standard_name == 'sea_water_temperature':
                X, Y, Z = self.computeSigmat(ax.axis(), xaxis_name='sea_water_salinity', pressure=np.mean(self.depth))
            if xp.standard_name == 'sea_water_temperature' and yp.standard_name == 'sea_water_salinity':
                X, Y, Z = self.computeSigmat(ax.axis(), xaxis_name='sea_water_temperature', pressure=meanDepth)
            if Z is not None:
                CS = ax.contour(X, Y, Z, colors='k')
                plt.clabel(CS, inline=1, fontsize=10)
                infoText = 'Sigma-t levels computed for pressure = %.1f dbar<br>' % meanDepth
    
            # Assemble additional information about the correlation
            m, b = polyfit(self.x, self.y, 1)
            yfit = polyval([m, b], self.x)
            ax.plot(self.x, yfit, color='k', linewidth=0.5)
            c = np.corrcoef(self.x, self.y)[0,1]
            pr = pearsonr(self.x, self.y)
            ##test_pr = pearsonr([1,2,3], [1,5,7])
            ##logger.debug('test_pr = %f (should be 0.981980506062)', test_pr)
            infoText = infoText + 'Linear regression: %s = %s * %s + %s (r<sup>2</sup> = %s, p = %s, n = %d)' % (yp.name, 
                            round_to_n(m,4), xp.name, round_to_n(b,4), round_to_n(c**2,4), round_to_n(pr,4), len(self.x))

            # Save the figure
            fig.savefig(ppPngFileFullPath, dpi=120, transparent=True)
            plt.close()

        except TypeError, e:
            ##infoText = 'Parameter-Parameter: ' + str(type(e))
            infoText = 'Parameter-Parameter: ' + str(e)
            logger.exception('Cannot make 2D parameterparameter plot: %s', e)
            return None, infoText

        else:
            return ppPngFile, infoText

    def makeX3D(self):
        '''
        Produce X3D XML text and return it
        '''
        try:
            # Construct special SQL for P-P plot that returns up to 4 data values for the up to 4 Parameters requested for a 3D plot
            sql = str(self.pq.qs_mp.query)
            logger.debug('self.pDict = %s', self.pDict)
            sql = self.pq.addParameterParameterSelfJoins(sql, self.pDict)

            # Use cursor so that we can specify the database alias to use. Columns are always 0:x, 1:y, 2:c (optional)
            cursor = connections[self.request.META['dbAlias']].cursor()
            cursor.execute(sql)
            for row in cursor:
                # SampledParameter datavalues are Decimal, convert everything to a float for numpy, row[0] is depth
                self.depth.append(float(row[0]))
                self.x.append(float(row[1]))
                self.y.append(float(row[2]))
                self.z.append(float(row[3]))
                try:
                    self.c.append(float(row[4]))
                except IndexError:
                    pass

            # Construct x3D...
            infoText = ''
            ppX3DText = '''<x3d width="500px" height="400px">
  <scene>
    <shape>
      <appearance>
        <material diffuseColor='red'></material>
      </appearance>
      <box></box>
    </shape>
  </scene>
</x3d>
'''

        except:
            logger.exception('Cannot make parameterparameter X3D')
            raise Exception('Cannot make parameterparameter X3D')

        else:
            logger.debug('ppX3DText = %s', ppX3DText)
            return ppX3DText, infoText

