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
import matplotlib as mpl
mpl.use('Agg')               # Force matplotlib to not use any Xwindows backend
import matplotlib.pyplot as plt
from matplotlib.mlab import griddata
from matplotlib import figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from pylab import polyfit, polyval
from django.conf import settings
from django.db.models.query import RawQuerySet
from django.db import connections, DatabaseError
from datetime import datetime
from KML import readCLT
from stoqs import models
from utils.utils import postgresifySQL, pearsonr, round_to_n
from utils.MPQuery import MPQuerySet
from loaders.SampleLoaders import SAMPLED
from loaders import MEASUREDINSITU
import seawater.csiro as sw
import numpy as np
import logging
import string
import random
import time
import re

logger = logging.getLogger(__name__)

def makeColorBar(request, colorbarPngFileFullPath, parm_info, colormap, orientation='horizontal'):
    '''
    Utility function used by classes in this module to create a colorbar image accessible at @colorbarPngFileFullPath.
    The @requst object is needed to use the database alias.
    @parm_info is a 3 element list/tuple: (parameterId, minValue, maxValue).
    @colormap is a color the color lookup table.
    If @orientation is 'vertical' create a vertically oriented image, otherwise horizontal.
    '''

    if orientation == 'horizontal':
        cb_fig = plt.figure(figsize=(5, 0.8))
        cb_ax = cb_fig.add_axes([0.1, 0.8, 0.8, 0.2])
        norm = mpl.colors.Normalize(vmin=parm_info[1], vmax=parm_info[2], clip=False)
        ticks=round_to_n(list(np.linspace(parm_info[1], parm_info[2], num=4)), 4)
        cb = mpl.colorbar.ColorbarBase( cb_ax, cmap=colormap,
                                        norm=norm,
                                        ticks=ticks,
                                        orientation='horizontal')
        cb.ax.set_xticklabels(ticks)
        cp = models.Parameter.objects.using(request.META['dbAlias']).get(id=int(parm_info[0]))
        cb.set_label('%s (%s)' % (cp.name, cp.units))
        cb_fig.savefig(colorbarPngFileFullPath, dpi=120, transparent=True)
        plt.close()

    elif orientation == 'vertical':
        cb_fig = plt.figure(figsize=(0.6, 4))
        cb_ax = cb_fig.add_axes([0.1, 0.1, 0.15, 0.8])
        norm = mpl.colors.Normalize(vmin=parm_info[1], vmax=parm_info[2], clip=False)
        cb = mpl.colorbar.ColorbarBase( cb_ax, cmap=colormap,
                                        norm=norm,
                                        ticks=list(np.linspace(parm_info[1], parm_info[2], num=4)),
                                        orientation='vertical')
        cb.ax.set_yticklabels([str(parm_info[1]), str(parm_info[2])])
        logger.debug('Getting units for parm_info[0] = %s', parm_info[0])
        cp = models.Parameter.objects.using(request.META['dbAlias']).get(id=int(parm_info[0]))
        cb.set_label('%s (%s)' % (cp.name, cp.units), fontsize=10)
        for label in cb.ax.get_yticklabels():
            label.set_fontsize(10)
            label.set_rotation('vertical')
        cb_fig.savefig(colorbarPngFileFullPath, dpi=120, transparent=True)
        plt.close()

    else:
        raise Exception('orientation must be either horizontal or vertical')


class MeasuredParameter(object):
    '''
    Use matploptib to create nice looking contour plots
    '''
    def __init__(self, kwargs, request, qs, qs_mp, parameterMinMax, sampleQS, platformName, parameterID=None, parameterGroups=[MEASUREDINSITU]):
        '''
        Save parameters that can be used by the different product generation methods here
        parameterMinMax is like: (pName, pMin, pMax)
        '''
        self.kwargs = kwargs
        self.request = request
        self.qs = qs
        self.qs_mp = qs_mp                      # Calling routine passes the _no_order version of the QuerySet
        self.parameterMinMax = parameterMinMax
        self.sampleQS = sampleQS
        self.platformName = platformName
        self.parameterID = parameterID
        self.parameterGroups = parameterGroups

        self.scale_factor = None
        self.clt = readCLT(os.path.join(settings.STATIC_ROOT, 'colormaps', 'jetplus.txt'))
        self.cm_jetplus = mpl.colors.ListedColormap(np.array(self.clt))
        # - Use a new imageID for each new image
        self.imageID = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(10))
        if self.parameterID:
            self.colorbarPngFile = str(self.parameterID) + '_' + self.platformName + '_colorbar_' + self.imageID + '.png'
        else:
            self.colorbarPngFile = self.kwargs['measuredparametersgroup'][0] + '_' + self.platformName + '_colorbar_' + self.imageID + '.png'

        self.colorbarPngFileFullPath = os.path.join(settings.MEDIA_ROOT, 'sections', self.colorbarPngFile)
        self.x = []
        self.y = []
        self.z = []
        self.lat = []
        self.lon = []
        self.depth = []
        self.value = []

    def _fillXYZ(self, mp):
        '''
        Fill up the x, y, and z member lists
        '''
        if self.scale_factor:
            self.x.append(time.mktime(mp['measurement__instantpoint__timevalue'].timetuple()) / self.scale_factor)
        else:
            self.x.append(time.mktime(mp['measurement__instantpoint__timevalue'].timetuple()))
        self.y.append(mp['measurement__depth'])
        self.depth_by_act.setdefault(mp['measurement__instantpoint__activity__name'], []).append(mp['measurement__depth'])
        self.z.append(mp['datavalue'])
        self.value_by_act.setdefault(mp['measurement__instantpoint__activity__name'], []).append(mp['datavalue'])
    
        if 'measurement__geom' in mp.keys():
            self.lon.append(mp['measurement__geom'].x)
            self.lon_by_act.setdefault(mp['measurement__instantpoint__activity__name'], []).append(mp['measurement__geom'].x)
            self.lat.append(mp['measurement__geom'].y)
            self.lat_by_act.setdefault(mp['measurement__instantpoint__activity__name'], []).append(mp['measurement__geom'].y)

    def loadData(self):
        '''
        Read the data from the database into member variables for use by the methods that output various products
        '''
        logger.debug('type(self.qs_mp) = %s', type(self.qs_mp))

        # Save to '_by_act' dictionaries so that X3D and end each IndexedLinestring with a '-1'
        self.depth_by_act = {}
        self.value_by_act = {}
        self.lon_by_act = {}
        self.lat_by_act = {}

        MP_MAX_POINTS = 10000          # Set by visually examing high-res Tethys data for what looks good
        stride = int(self.qs_mp.count() / MP_MAX_POINTS)
        if stride < 1:
            stride = 1
        self.strideInfo = ''
        if stride != 1:
            self.strideInfo = 'stride = %d' % stride

        i = 0
        logger.debug('self.qs_mp.query = %s', str(self.qs_mp.query))
        if SAMPLED in self.parameterGroups:
            for mp in self.qs_mp:
                if self.scale_factor:
                    self.x.append(time.mktime(mp['sample__instantpoint__timevalue'].timetuple()) / self.scale_factor)
                else:
                    self.x.append(time.mktime(mp['sample__instantpoint__timevalue'].timetuple()))
                self.y.append(mp['sample__depth'])
                self.depth_by_act.setdefault(mp['sample__instantpoint__activity__name'], []).append(mp['sample__depth'])
                self.z.append(mp['datavalue'])
                self.value_by_act.setdefault(mp['sample__instantpoint__activity__name'], []).append(mp['datavalue'])
    
                if 'sample__geom' in mp.keys():
                    self.lon.append(mp['sample__geom'].x)
                    self.lon_by_act.setdefault(mp['sample__instantpoint__activity__name'], []).append(mp['sample__geom'].x)
                    self.lat.append(mp['sample__geom'].y)
                    self.lat_by_act.setdefault(mp['sample__instantpoint__activity__name'], []).append(mp['sample__geom'].y)
    
                i = i + 1
                if (i % 1000) == 0:
                    logger.debug('Appended %i samples to self.x, self.y, and self.z', i)
        else:
            logger.debug('Reading data with a stride of %s', stride)
            if self.qs_mp.isRawQuerySet:
                # RawQuerySet does not support normal slicing
                counter = 0
                logger.debug('Slicing with mod division on a counter...')
                for mp in self.qs_mp:
                    if counter % stride == 0:
                        self._fillXYZ(mp)
                        i = i + 1
                        if (i % 1000) == 0:
                            logger.debug('Appended %i measurements to self.x, self.y, and self.z', i)
                    counter = counter + 1
            else:
                logger.debug('Slicing Pythonicly...')
                for mp in self.qs_mp[::stride]:
                    self._fillXYZ(mp)
                    i = i + 1
                    if (i % 1000) == 0:
                        logger.debug('Appended %i measurements to self.x, self.y, and self.z', i)

        self.depth = self.y
        self.value = self.z

    def renderDatavaluesForFlot(self, tgrid_max=1000, dgrid_max=100, dinc=0.5, nlevels=255, contourFlag=True):
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

        if self.parameterID:
            sectionPngFile = str(self.parameterID) + '_' + self.platformName + '_' + self.imageID + '.png'
        else:
            sectionPngFile = self.kwargs['measuredparametersgroup'][0] + '_' + self.platformName + '_' + self.imageID + '.png'

        sectionPngFileFullPath = os.path.join(settings.MEDIA_ROOT, 'sections', sectionPngFile)
        
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
            # Estimate a scale factor to apply to the x values on grid data so that x & y values are visually equal for the flot plot
            # which is assumed to be 3x wider than tall.  Approximate horizontal coverage by Dorado is 1 m/s.
            try:
                self.scale_factor = float(tmax -tmin) / (dmax - dmin) / 3.0
            except ZeroDivisionError, e:
                logger.warn(e)
                logger.debug('Not setting self.scale_factor.  Scatter plots will still work.')
                contourFlag = False
            else:                
                logger.debug('self.scale_factor = %f', self.scale_factor)
                xi = xi / self.scale_factor

            try:
                os.remove(sectionPngFileFullPath)
            except Exception, e:
                logger.warn('Could not remove file: %s', e)

            if not self.x and not self.y and not self.z:
                self.loadData()

            logger.debug('self.kwargs = %s', self.kwargs)
            if self.kwargs.has_key('parametervalues'):
                if self.kwargs['parametervalues']:
                    contourFlag = False
          
            if self.kwargs.has_key('showdataas'):
                if self.kwargs['showdataas']:
                    if self.kwargs['showdataas'][0] == 'scatter':
                        contourFlag = False
          
            logger.debug('Number of x, y, z data values retrived from database = %d', len(self.z)) 
            if contourFlag:
                try:
                    logger.debug('Gridding data with sdt_count = %d, and y_count = %d', sdt_count, y_count)
                    zi = griddata(self.x, self.y, self.z, xi, yi, interp='nn')
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
                if self.scale_factor:
                    ax.set_xlim(tmin / self.scale_factor, tmax / self.scale_factor)
                else:
                    ax.set_xlim(tmin, tmax)
                ax.set_ylim(dmax, dmin)
                ax.get_xaxis().set_ticks([])
                if contourFlag:
                    ax.contourf(xi, yi, zi, levels=np.linspace(parm_info[1], parm_info[2], nlevels), cmap=self.cm_jetplus, extend='both')
                    ax.scatter(self.x, self.y, marker='.', s=2, c='k', lw = 0)
                else:
                    logger.debug('parm_info = %s', parm_info)
                    ax.scatter(self.x, self.y, c=self.z, s=20, cmap=self.cm_jetplus, lw=0, vmin=parm_info[1], vmax=parm_info[2])

                if self.sampleQS and SAMPLED not in self.parameterGroups:
                    # Add sample locations and names, but not if the underlying data are from the Samples themselves
                    xsamp = []
                    ysamp = []
                    sname = []
                    for s in self.sampleQS.values('instantpoint__timevalue', 'depth', 'name'):
                        if self.scale_factor:
                            xsamp.append(time.mktime(s['instantpoint__timevalue'].timetuple()) / self.scale_factor)
                        else:
                            xsamp.append(time.mktime(s['instantpoint__timevalue'].timetuple()))
                        ysamp.append(s['depth'])
                        sname.append(s['name'])
                    ax.scatter(xsamp, np.float64(ysamp), marker='o', c='w', s=15, zorder=10)
                    for x,y,sn in zip(xsamp, ysamp, sname):
                        plt.annotate(sn, xy=(x,y), xytext=(5,-5), textcoords = 'offset points', fontsize=7)

                fig.savefig(sectionPngFileFullPath, dpi=120, transparent=True)
                plt.close()
            except Exception,e:
                logger.exception('Could not plot the data')
                return None, None, 'Could not plot the data'

            try:
                makeColorBar(self.request, self.colorbarPngFileFullPath, parm_info, self.cm_jetplus)
            except Exception,e:
                logger.exception('Could not plot the colormap')
                return None, None, 'Could not plot the colormap'

            return sectionPngFile, self.colorbarPngFile, self.strideInfo
        else:
            logger.warn('xi and yi are None.  tmin, tmax, dmin, dmax = %s, %s, %s, %s, %s, %s ', tmin, tmax, dmin, dmax)
            return None, None, 'Select a time-depth range'

    def dataValuesX3D(self):
        '''
        Return scatter-like data values as X3D geocoordinates and colors
        '''
        showGeoX3DDataFlag = False
        if self.kwargs.has_key('showgeox3ddata'):
            if self.kwargs['showgeox3ddata']:
                if self.kwargs['showgeox3ddata']:
                    showGeoX3DDataFlag = True

        VERT_EXAG = 10

        x3dResults = {}
        if not showGeoX3DDataFlag:
            return x3dResults

        if not self.lon and not self.lat and not self.depth and not self.value:
            logger.debug('Calling self.loadData()...')
            self.loadData()
        try:
            points = ''
            colors = ''
            indices = ''
            index = 0
            for act in self.value_by_act.keys():
                logger.debug('Reading data from act = %s', act)
                for lon,lat,depth,value in zip(self.lon_by_act[act], self.lat_by_act[act], self.depth_by_act[act], self.value_by_act[act]):
                    # 10x vertical exaggeration - must match the GeoElevationGrid
                    points = points + '%.5f %.5f %.1f ' % (lat, lon, -depth * VERT_EXAG)

                    cindx = int(round((value - float(self.parameterMinMax[1])) * (len(self.clt) - 1) / 
                                        (float(self.parameterMinMax[2]) - float(self.parameterMinMax[1]))))
                    if cindx < 0:
                        cindx = 0
                    if cindx > len(self.clt) - 1:
                        cindx = len(self.clt) - 1

                    colors = colors + '%.3f %.3f %.3f ' % (self.clt[cindx][0], self.clt[cindx][1], self.clt[cindx][2])
                    indices = indices + '%i ' % index
                    index = index + 1

                # End the IndexedLinestring with -1 so that end point does not connect to the beg point
                indices = indices + '-1 ' 

            try:
                makeColorBar(self.request, self.colorbarPngFileFullPath, self.parameterMinMax, self.cm_jetplus)
            except Exception,e:
                logger.exception('Could not plot the colormap')
                x3dResults = 'Could not plot the colormap'
            else:
                x3dResults = {'colors': colors.rstrip(), 'points': points.rstrip(), 'info': '', 'index': indices.rstrip(), 'colorbar': self.colorbarPngFile}

        except Exception,e:
            logger.exception('Could not create measuredparameterx3d')
            x3dResults = 'Could not create measuredparameterx3d'

        return x3dResults


class ParameterParameter(object):
    '''
    Use matploplib to create nice looking property-property plots
    '''
    def __init__(self, request, pDict, mpq, pq, pMinMax):
        '''
        Save parameters that can be used by the different plotting methods here
        @pMinMax is like: (pID, pMin, pMax)
        '''
        self.request = request
        self.pDict = pDict
        self.mpq = mpq
        self.pq = pq
        self.pMinMax = pMinMax
        self.clt = readCLT(os.path.join(settings.STATIC_ROOT, 'colormaps', 'jetplus.txt'))
        self.depth = []
        self.x = []
        self.y = []
        self.z = []
        self.c = []

    def computeSigmat(self, limits, xaxis_name='sea_water_salinity', pressure=0):
        '''
        Given a tuple of limits = (xmin, xmax, ymin, ymax) and an xaxis_name compute 
        density for a range of values between the mins and maxes.  Return the X and Y values
        for salinity/temperature and density converted to sigma-t.  A pressure argument may
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

    def _getCountSQL(self, sql):
        '''
        Modify Parameter-Parameter SQL to return the count for the query
        '''
        p = re.compile('SELECT .+ FROM')
        csql = p.sub('''SELECT count(*) FROM''', sql.replace('\n', ' '))
        logger.debug('csql = %s', csql)
        return csql

    def make2DPlot(self):
        '''
        Produce a Parameter-Parameter .png image with axis limits set to the 1 and 99 percentiles and draw outside the lines
        '''
        try:
            # self.x and self.y may already be set for this instance by makeX3D()
            if not self.x and not self.y:
                # Construct special SQL for P-P plot that returns up to 3 data values for the up to 3 Parameters requested for a 2D plot
                sql = str(self.pq.qs_mp.query)
                logger.debug('sql = %s', sql)
                sql = self.pq.addParameterParameterSelfJoins(sql, self.pDict)

                # Use cursor so that we can specify the database alias to use. Columns are always 0:x, 1:y, 2:c (optional)
                cursor = connections[self.request.META['dbAlias']].cursor()

                # Get count and set a stride value if more than a PP_MAX_POINTS which Matplotlib cannot plot, about 100,000 points
                try:
                    cursor.execute(self._getCountSQL(sql))
                except DatabaseError, e:
                    infoText = 'Parameter-Parameter: ' + str(e) + ' Also, make sure you have no Parameters selected in the Filter.'
                    logger.exception('Cannot execute count sql query for Parameter-Parameter plot: %s', e)
                    return None, infoText, sql
                pp_count = cursor.fetchone()[0]
                logger.debug('pp_count = %d', pp_count)
                PP_MAX_POINTS = 100000
                stride_val = int(pp_count / PP_MAX_POINTS)
                if stride_val < 1:
                    stride_val = 1
                logger.debug('stride_val = %d', stride_val)

                # Get the Parameter-Parameter points
                try:
                    cursor.execute(sql)
                except DatabaseError, e:
                    infoText = 'Parameter-Parameter: ' + str(e) + ' Also, make sure you have no Parameters selected in the Filter.'
                    logger.exception('Cannot execute sql query for Parameter-Parameter plot: %s', e)
                    return None, infoText, sql

                counter = 0
                for row in cursor:
                    if counter % stride_val == 0:
                        # SampledParameter datavalues are Decimal, convert everything to a float for numpy, row[0] is depth
                        self.depth.append(float(row[0]))
                        self.x.append(float(row[1]))
                        self.y.append(float(row[2]))
                        try:
                            self.c.append(float(row[3]))
                        except IndexError:
                            pass
                    counter = counter + 1

            # If still no self.x and self.y then selection is not valid for the chosen x and y
            if self.x == [] or self.y == []:
                return None, 'No Parameter-Parameter data values returned.', sql
            
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
            if not os.path.exists(os.path.dirname(ppPngFileFullPath)):
                try:
                    os.makedirs(os.path.dirname(ppPngFileFullPath))
                except Exception,e:
                    logger.exception('Failed to create path for ' +
                                     'parameterparameter (%s) file', ppPngFile)
                    return None, 'Failed to create path for parameterparameter (%s) file' % ppPngFile, sql
            logger.debug('ppPngFileFullPath = %s', ppPngFileFullPath)

            # Make the figure
            fig = plt.figure()
            plt.grid(True)
            ax = fig.add_subplot(111)
            ax.set_xlim(self.pMinMax['x'][1], self.pMinMax['x'][2])
            ax.set_ylim(self.pMinMax['y'][1], self.pMinMax['y'][2])

            self.clt = readCLT(os.path.join(settings.STATIC_ROOT, 'colormaps', 'jetplus.txt'))
            cm_jetplus = mpl.colors.ListedColormap(np.array(self.clt))
            if self.c:
                logger.debug('self.pMinMax = %s', self.pMinMax)
                logger.debug('Making colored scatter plot of %d points', len(self.x))
                ax.scatter(self.x, self.y, c=self.c, s=10, cmap=cm_jetplus, lw=0, vmin=self.pMinMax['c'][1], vmax=self.pMinMax['c'][2], clip_on=False)
                # Add colorbar to the image
                cb_ax = fig.add_axes([0.2, 0.98, 0.6, 0.02]) 
                norm = mpl.colors.Normalize(vmin=self.pMinMax['c'][1], vmax=self.pMinMax['c'][2], clip=False)
                cb = mpl.colorbar.ColorbarBase( cb_ax, cmap=cm_jetplus,
                                                norm=norm,
                                                ticks=list(np.linspace(self.pMinMax['c'][1], self.pMinMax['c'][2], num=4)),
                                                orientation='horizontal')
                cp = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['c']))
                cb.set_label('%s (%s)' % (cp.name, cp.units))
            else:
                logger.debug('Making scatter plot of %d points', len(self.x))
                ax.scatter(self.x, self.y, marker='.', s=10, c='k', lw = 0, clip_on=False)

            # Label the axes
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
            if stride_val > 1:
                infoText = infoText.replace(')', ' of %d, stride = %d)' % (pp_count, stride_val))

            # Save the figure
            try:
                fig.savefig(ppPngFileFullPath, dpi=120, transparent=True)
            except Exception, e:
                infoText = 'Parameter-Parameter: ' + str(e)
                logger.exception('Cannot make 2D parameterparameter plot: %s', e)
                plt.close()
                return None, infoText, sql
            else:
                plt.close()

        except TypeError, e:
            ##infoText = 'Parameter-Parameter: ' + str(type(e))
            infoText = 'Parameter-Parameter: ' + str(e)
            logger.exception('Cannot make 2D parameterparameter plot: %s', e)
            return None, infoText, sql

        else:
            return ppPngFile, infoText, sql

    def makeX3D(self):
        '''
        Produce X3D XML text and return it
        '''
        x3dResults = {}
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

            if self.c:
                self.c.reverse()    # Modifies self.c in place - needed for popping values off in loop below

            points = ''
            colors = ''
            for x,y,z in zip(self.x, self.y, self.z):
                # Scale to 10000 on each axis, bounded by min/max values - must be 10000 as X3D in stoqs/templates/stoqsquery.html is hard-coded with 10000
                # This gives us enough resolution for modern displays and eliminates decimal point characters
                xs = 10000 * (x - float(self.pMinMax['x'][1])) / (float(self.pMinMax['x'][2]) - float(self.pMinMax['x'][1])) 
                ys = 10000 * (y - float(self.pMinMax['y'][1])) / (float(self.pMinMax['y'][2]) - float(self.pMinMax['y'][1])) 
                zs = 10000 * (z - float(self.pMinMax['z'][1])) / (float(self.pMinMax['z'][2]) - float(self.pMinMax['z'][1])) 
                points = points + '%d %d %d ' % (int(xs), int(ys), int(zs))
                if self.c:
                    cindx = int(round((self.c.pop() - float(self.pMinMax['c'][1])) * (len(self.clt) - 1) / 
                                    (float(self.pMinMax['c'][2]) - float(self.pMinMax['c'][1]))))
                    if cindx < 0:
                        cindx = 0
                    if cindx > len(self.clt) - 1:
                        cindx = len(self.clt) - 1
                    colors = colors + '%.3f %.3f %.3f ' % (self.clt[cindx][0], self.clt[cindx][1], self.clt[cindx][2])
                else:
                    colors = colors + '0 0 0 '

            # Label the axes
            xp = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['x']))
            self.pMinMax['x'].append(('%s (%s)' % (xp.name, xp.units)))
            yp = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['y']))
            self.pMinMax['y'].append(('%s (%s)' % (yp.name, yp.units)))
            zp = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['z']))
            self.pMinMax['z'].append(('%s (%s)' % (zp.name, zp.units)))

            colorbarPngFile = ''
            if colors:
                cp = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['c']))
                try:
                    cm_jetplus = mpl.colors.ListedColormap(np.array(self.clt))
                    imageID = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(10))
                    colorbarPngFile = '%s_%s_%s_%s_3dcolorbar_%s.png' % (self.pDict['x'], self.pDict['y'], self.pDict['z'], self.pDict['c'], imageID )
                    colorbarPngFileFullPath = os.path.join(settings.MEDIA_ROOT, 'parameterparameter', colorbarPngFile)
                    makeColorBar(self.request, colorbarPngFileFullPath, self.pMinMax['c'], cm_jetplus)

                except Exception,e:
                    logger.exception('Could not plot the colormap')
                    return None, None, 'Could not plot the colormap'

            x3dResults = {'colors': colors, 'points': points, 'info': '', 'x': self.pMinMax['x'], 'y': self.pMinMax['y'], 'z': self.pMinMax['z'], 'colorbar': colorbarPngFile}

        except:
            logger.exception('Cannot make parameterparameter X3D')
            x3dResults = {'colors': [], 'points': [], 'info': 'Cannot make 3D plot.', 'x': [], 'y': [], 'z': [], 'median': ''}

        return x3dResults

