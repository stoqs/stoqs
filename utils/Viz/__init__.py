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
from django.conf import settings
from django.db.models.query import RawQuerySet
from datetime import datetime
from KML import readCLT
from stoqs import models
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


class ParameterParameterPlots(object):
    '''
    Use matploptib to create nice looking property-property plots
    '''
    def __init__(self, kwargs, request, qs, qs_mp, parameterMinMax, sampleQS, platformName):
        '''
        Save parameters that can be used by the different plotting methods here
        '''
        self.kwargs = kwargs
        self.request = request
        self.qs = qs
        self.qs_mp = qs_mp
        self.platformName = platformName

    def makePlot(self):
        '''
        Produce a .png image 
        '''
        pass
