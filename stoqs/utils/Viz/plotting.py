'''
Module with various functions to supprt data visualization.  These can be quite verbose
with all of the Matplotlib customization required for nice looking graphics.
'''

import os
import tempfile
# Setup Matplotlib for running on the server
os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp()
import matplotlib as mpl
mpl.use('Agg')               # Force matplotlib to not use any Xwindows backend
import cmocean
import math
import matplotlib.pyplot as plt
import statsmodels.api as sm
from matplotlib import rcParams
from scipy.interpolate import griddata
from scipy.stats import ttest_ind
from matplotlib.colors import hex2color, LogNorm
from operator import itemgetter
from pylab import polyval
from collections import namedtuple
from django.conf import settings
from django.db import connections, DatabaseError, transaction
from datetime import datetime
from stoqs import models
from utils.utils import pearsonr, round_to_n, EPOCH_STRING
from loaders.SampleLoaders import SAMPLED, NETTOW, VERTICALNETTOW, PLANKTONPUMP, ESP_FILTERING
from loaders import MEASUREDINSITU, X3DPLATFORMMODEL, X3D_MODEL, X3D_MODEL_SCALEFACTOR
import seawater.eos80 as sw
import numpy as np
from numpy import polyfit
from PIL import Image, ImageOps
import logging
import string
import random
import time
import re
import warnings

logger = logging.getLogger(__name__)

MP_MAX_POINTS = 10000          # Set by visually examing high-res Tethys data for what looks good
PA_MAX_POINTS = 10000000       # Set to avoid memory error on development system

cmocean_lookup = {  'sea_water_temperature':                                'thermal',
                    'sea_water_salinity':                                   'haline',
                    'sea_water_sigma_t':                                    'dense',
                    'mass_concentration_of_chlorophyll_in_sea_water':       'algae',
                    'mass_concentration_of_oxygen_in_sea_water':            'oxy',
                    'downwelling_photosynthetic_photon_flux_in_sea_water':  'solar',
                    'surface_downwelling_shortwave_flux_in_air':            'solar',
                    'platform_pitch_angle':                                 'balance',
                    'platform_roll_angle':                                  'balance',
                    'northward_sea_water_velocity':                         'balance',
                    'eastward_sea_water_velocity':                          'balance',
                    'northward_wind':                                       'balance',
                    'eastward_wind':                                        'balance',
                 }

def _getCoordUnits(name):
    '''
    Assign units given a standard coordinate name
    '''
    if name == 'longitude':
        units = 'degrees_east'
    elif name == 'latitude':
        units = 'degrees_north'
    elif name == 'depth':
        units = 'm'
    elif name == 'time':
        units = 'days since %s' % EPOCH_STRING
    else:
        units = ''

    return units

def readCLT(fileName):
    '''
    Read the color lookup table from disk and return a python list of rgb tuples.
    '''

    cltList = []
    
    rgb_file = open(fileName, 'r')
    for rgb in rgb_file:
        ##logger.debug("rgb = %s", rgb)
        (r, g, b) = rgb.strip().split()
        cltList.append([float(r), float(g), float(b)])

    rgb_file.close()

    return cltList

class BaseParameter(object):

    def __init__(self):
        # Default colormap - a perceptually uniform, color blind safe one
        self.cm_name = 'cividis'
        self.num_colors = 256
        self.cmin = None
        self.cmax = None
        self.cm = plt.get_cmap(self.cm_name)
        self.clt = [self.cm(i) for i in range(256)]
    
    def set_colormap(self):
        '''Assign colormap as passed as argument (via standard_name lookup) or from UI request
        '''
        if hasattr(self.request, 'GET'):
            # Override colormap with selection from the UI
            if self.request.GET.get('cm'):
                self.cm_name = self.request.GET.get('cm')
            if self.request.GET.get('num_colors') is not None:
                self.num_colors = int(self.request.GET.get('num_colors'))
            if self.request.GET.get('cmin') is not None:
                self.cmin = float(self.request.GET.get('cmin'))
            if self.request.GET.get('cmax') is not None:
                self.cmax = float(self.request.GET.get('cmax'))

            if self.request.GET.get('sn_colormap'):
                if self.standard_name in cmocean_lookup.keys():
                    self.cm_name = cmocean_lookup[self.standard_name]
                    if self.cm_name in ('balance', 'curl', 'delta', 'diff', 'tarn'):
                        # Center the colormap limits for the ones that are balanced
                        bminmax = round_to_n(min(abs(self.pMinMax[1]), abs(self.pMinMax[2])), 2)
                        self.cmin = -bminmax
                        self.cmax = bminmax

        try:
            self.cm = plt.get_cmap(self.cm_name)
        except ValueError:
            # Likely a cmocean colormap
            self.cm = getattr(cmocean.cm, self.cm_name)

        # Iterating over cm items works for LinearSegmentedColormap and ListedColormap
        self.clt = [self.cm(i) for i in range(256)]

    def set_ticks_bounds_norm(self, parm_info, use_ui_cmincmax=True, use_ui_num_colors=True):
        '''Common parameters for colormap, scatter and contour plotting
        '''
        c_min, c_max = parm_info[1:]
        if use_ui_cmincmax:
            if self.cmin is not None:
                c_min = self.cmin
            if self.cmax is not None:
                c_max = self.cmax

        if use_ui_num_colors:
            num_colors = self.num_colors
        else:
            num_colors = 256

        self.ticks = round_to_n(list(np.linspace(c_min, c_max, num=6)), 4)
        self.bounds = np.linspace(c_min, c_max, num_colors + 1)
        self.norm = mpl.colors.BoundaryNorm(self.bounds, num_colors)

        if num_colors == 8:
            self.ticks = self.bounds[::2]
        if num_colors < 8:
            self.ticks = self.bounds

    def makeColorBar(self, colorbarPngFileFullPath, parm_info, orientation='horizontal'):
        '''
        Utility function used by classes in this module to create a colorbar image accessible at @colorbarPngFileFullPath.
        The @requst object is needed to use the database alias.
        @parm_info is a 3 element list/tuple: (parameterId, minValue, maxValue).
        @colormap is a color the color lookup table.
        If @orientation is 'vertical' create a vertically oriented image, otherwise horizontal.
        '''

        if parm_info[1] == parm_info[2]:
            raise Exception(('Parameter has same min and max value: {}').format(parm_info))

        drawedges = False
        if self.num_colors <= 16:
            drawedges = True

        if orientation == 'horizontal':
            cb_fig = plt.figure(figsize=(5, 0.8))
            cb_ax = cb_fig.add_axes([0.1, 0.8, 0.8, 0.2])
            self.set_ticks_bounds_norm(parm_info)
            cb = mpl.colorbar.ColorbarBase( cb_ax, cmap=self.cm,
                                            norm=self.norm,
                                            ticks=self.ticks,
                                            boundaries=self.bounds,
                                            ##extend='both',
                                            ##extendfrac='auto',
                                            drawedges=drawedges,
                                            orientation='horizontal')
            try:
                cp = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(parm_info[0]))
                if cp.units:
                    if cp.units in cp.name:
                        cb.set_label(cp.name)
                    else:
                        cb.set_label(f"{cp.name} ({cp.units})")
                else:
                    cb.set_label(cp.name)
            except (ValueError, models.Parameter.DoesNotExist):
                # Likely a coordinate variable
                cp = models.Parameter
                cp.name = parm_info[0]
                cp.standard_name = parm_info[0]
                cp.units = _getCoordUnits(parm_info[0])
                cb.set_label('%s (%s)' % (cp.name, cp.units))

            cb_fig.savefig(colorbarPngFileFullPath, dpi=120, transparent=True)
            plt.close()

        else:
            raise Exception("Only 'horizontal' orientation is supported")


class MeasuredParameter(BaseParameter):
    '''
    Use matploptib to create nice looking contour plots
    '''
    logger = logging.getLogger(__name__)
    def __init__(self, kwargs, request, qs, qs_mp, contour_qs_mp, pMinMax, sampleQS, 
                 platformName, parameterID=None, parameterGroups=(MEASUREDINSITU), 
                 contourPlatformName=None, contourParameterID=None, contourParameterGroups=(MEASUREDINSITU)):
        '''
        Save parameters that can be used by the different product generation methods here
        pMinMax is like: (pName, pMin, pMax)
        '''
        super(self.__class__, self).__init__()

        self.kwargs = kwargs
        self.request = request
        self.qs = qs
        # Calling routine passes different qs_mp when order or no parameter in filter is needed
        self.qs_mp = qs_mp
        self.contour_qs_mp = contour_qs_mp

        self.pMinMax = pMinMax
        self.standard_name = None
        if parameterID:
            self.standard_name = (models.Parameter.objects.using(self.request.META['dbAlias'])
                                             .get(id=parameterID).standard_name)
        self.set_colormap()

        if self.cmin is not None and self.pMinMax:
            self.pMinMax[1] = self.cmin
        if self.cmax is not None and self.pMinMax:
            self.pMinMax[2] = self.cmax

        self.sampleQS = sampleQS
        self.platformName = platformName
        self.parameterID = parameterID
        self.parameterGroups = parameterGroups
        self.contourParameterID = contourParameterID
        self.contourParameterGroups = contourParameterGroups
        self.scale_factor = None

        # - Use a new imageID for each new image
        self.imageID = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(10))
        if self.parameterID:
            self.colorbarPngFile = str(self.parameterID) + '_' + self.platformName + '_colorbar_' + self.imageID + '.png'
        elif self.kwargs['measuredparametersgroup']:
            self.colorbarPngFile = self.kwargs['measuredparametersgroup'][0] + '_' + self.platformName + '_colorbar_' + self.imageID + '.png'
        else:
            # Likely contour line only plot being requested
            self.colorbarPngFile = ''

        if self.colorbarPngFile:
            self.colorbarPngFileFullPath = os.path.join(settings.MEDIA_ROOT, 'sections', self.colorbarPngFile)
        else:
            self.colorbarPngFileFullPath = ''
        self.x = []
        self.y = []
        self.z = []
        self.lat = []
        self.lon = []
        self.depth = []
        self.value = []

        self.xspan = []
        self.yspan = []
        self.zspan = []
        self.latspan = []
        self.lonspan = []
        self.depthspan = []

    def _fillXYZ(self, mp, sampled=False, spanned=False, activitytype=None):
        '''
        Fill up the x, y, and z member lists for measured (default) or sampled data values. 
        If spanned is True then fill xspan, yspan, and zspan member lists with NetTow like data.
        '''
        if sampled:
            if self.scale_factor:
                self.x.append(mp['sample__instantpoint__timevalue'].timestamp() / self.scale_factor)
            else:
                self.x.append(mp['sample__instantpoint__timevalue'].timestamp())
            self.y.append(mp['sample__depth'])
            self.depth_by_act.setdefault(mp['sample__instantpoint__activity__name'], []).append(float(mp['sample__depth']))
            self.z.append(mp['datavalue'])
            self.value_by_act.setdefault(mp['sample__instantpoint__activity__name'], []).append(float(mp['datavalue']))

            if 'sample__geom' in list(mp.keys()):
                self.lon.append(mp['sample__geom'].x)
                self.lon_by_act.setdefault(mp['sample__instantpoint__activity__name'], []).append(mp['sample__geom'].x)
                self.lat.append(mp['sample__geom'].y)
                self.lat_by_act.setdefault(mp['sample__instantpoint__activity__name'], []).append(mp['sample__geom'].y)

            if spanned and activitytype == VERTICALNETTOW:
                # Save a (start, end) tuple for each coordinate/value, VERTICALNETTOWs start at maxdepth
                if self.scale_factor:
                    self.xspan.append(
                            (mp['sample__instantpoint__activity__startdate'].timestamp() / self.scale_factor,
                             mp['sample__instantpoint__activity__enddate'].timestamp() / self.scale_factor)
                                     )
                else:
                    self.xspan.append(
                            (mp['sample__instantpoint__activity__startdate'].timestamp(),
                             mp['sample__instantpoint__activity__enddate'].timestamp())
                                     )
                self.yspan.append(
                        (mp['sample__instantpoint__activity__maxdepth'],
                         mp['sample__instantpoint__activity__mindepth'])
                                 )
                self.depth_by_act_span.setdefault(mp['sample__instantpoint__activity__name'], []).append(
                        (mp['sample__instantpoint__activity__maxdepth'],
                         mp['sample__instantpoint__activity__mindepth'])
                                 )
                self.zspan.append(float(mp['datavalue']))
                self.value_by_act_span.setdefault(mp['sample__instantpoint__activity__name'], []).append(float(mp['datavalue']))

                if 'sample__geom' in list(mp.keys()):
                    # Implemented for VERTICALNETTOW data where start and end geom are identical
                    self.lonspan.append((mp['sample__geom'].x, mp['sample__geom'].x))
                    self.lon_by_act_span.setdefault(mp['sample__instantpoint__activity__name'], []).append(
                            (mp['sample__geom'].x, mp['sample__geom'].x))
                    self.latspan.append((mp['sample__geom'].y, mp['sample__geom'].y))
                    self.lat_by_act_span.setdefault(mp['sample__instantpoint__activity__name'], []).append(
                            (mp['sample__geom'].y, mp['sample__geom'].y))

            # TODO: Implement for other types of spanned data, e.g. use Activity.maptrack to 
            # get start and end geom for other Horizontal or Oblique NetTows
                
        else:
            if self.scale_factor:
                self.x.append(mp['measurement__instantpoint__timevalue'].timestamp() / self.scale_factor)
            else:
                self.x.append(mp['measurement__instantpoint__timevalue'].timestamp())
            self.y.append(mp['measurement__depth'])
            self.depth_by_act.setdefault(mp['measurement__instantpoint__activity__name'], []).append(mp['measurement__depth'])
            self.z.append(mp['datavalue'])
            self.value_by_act.setdefault(mp['measurement__instantpoint__activity__name'], []).append(mp['datavalue'])
        
            if 'measurement__geom' in list(mp.keys()):
                self.lon.append(mp['measurement__geom'].x)
                self.lon_by_act.setdefault(mp['measurement__instantpoint__activity__name'], []).append(mp['measurement__geom'].x)
                self.lat.append(mp['measurement__geom'].y)
                self.lat_by_act.setdefault(mp['measurement__instantpoint__activity__name'], []).append(mp['measurement__geom'].y)

    def loadData(self, qs_mp):
        '''
        Read the data from the database into member variables for use by the methods that output various products
        '''
        self.logger.debug('type(qs_mp) = %s', type(qs_mp))

        # Save to '_by_act' dictionaries so that X3D can end each IndexedLinestring with a '-1'
        self.depth_by_act = {}
        self.value_by_act = {}
        self.lon_by_act = {}
        self.lat_by_act = {}

        self.depth_by_act_span = {}
        self.value_by_act_span = {}
        self.lon_by_act_span = {}
        self.lat_by_act_span = {}

        stride = int(qs_mp.count() / MP_MAX_POINTS)
        if stride < 1:
            stride = 1
        self.strideInfo = ''
        if stride != 1:
            self.strideInfo = 'stride = %d' % stride

        self.logger.debug('qs_mp.query = %s', str(qs_mp.query))
        if SAMPLED in self.parameterGroups:
            for i, mp in enumerate(qs_mp):
                self._fillXYZ(mp, sampled=True)
                if (i % 10) == 0:
                    self.logger.debug('Appended %i samples to self.x, self.y, and self.z', i)

            # Build span data members for VERTICALNETTOW activity types
            # TODO: Implement other types as they are needed
            qs = qs_mp.filter(sample__instantpoint__activity__activitytype__name__contains=VERTICALNETTOW)
            for i,mp in enumerate(qs):
                self._fillXYZ(mp, sampled=True, spanned=True, activitytype=VERTICALNETTOW)
                if (i % 10) == 0:
                    self.logger.debug('Appended %i samples to self.xspan, self.yspan, and self.zspan', i)
        else:
            self.logger.debug('Reading data with a stride of %s', stride)
            if qs_mp.isRawQuerySet:
                # RawQuerySet does not support normal slicing
                i = 0
                self.logger.debug('Slicing with mod division on a counter...')
                for counter, mp in enumerate(qs_mp):
                    if counter == 0:
                        self.logger.debug('Starting to call _fillXYZ()')
                    if counter % stride == 0:
                        self._fillXYZ(mp)
                        i = i + 1
                        if (i % 1000) == 0:
                            self.logger.debug('Appended %i measurements to self.x, self.y, and self.z', i)
            else:
                self.logger.debug('Slicing Pythonicly...')
                for i, mp in enumerate(qs_mp[::stride]):
                    if 1 == 0:
                        self.logger.debug('Starting to call _fillXYZ()')
                    self._fillXYZ(mp)
                    if (i % 1000) == 0:
                        self.logger.debug('Appended %i measurements to self.x, self.y, and self.z', i)

        self.depth = self.y
        self.value = self.z

    def _get_samples_for_markers(self, act_type_name=None, spanned=False, exclude_act_type_name=None):
        '''
        Return time, depth, and name of Samples for plotting as symbols.
        Restrict to activitytype__name if act_type_name is specified.
        '''
        # Add sample locations and names, but not if the underlying data are from the Samples themselves
        xsamp = []
        ysamp = []
        sname = []
        qs = self.sampleQS.values('instantpoint__timevalue', 'instantpoint__activity__name', 'depth', 'name')
        if act_type_name:
            qs = qs.filter(instantpoint__activity__activitytype__name__contains=act_type_name)
        else:
            if exclude_act_type_name:
                qs = qs.exclude(instantpoint__activity__activitytype__name__contains=exclude_act_type_name)

        for s in qs:
            if self.scale_factor:
                xsamp.append(s['instantpoint__timevalue'].timestamp() / self.scale_factor)
            else:
                xsamp.append(s['instantpoint__timevalue'].timestamp())
            ysamp.append(s['depth'])
            if act_type_name:
                # Convention is to use Activity information for things like NetTows
                sname.append(s['instantpoint__activity__name'])
            else:
                sname.append(s['name'])

        if spanned and (act_type_name == VERTICALNETTOW or act_type_name == PLANKTONPUMP):
            xsamp = []
            ysamp = []
            sname = []
            # Build tuples of start and end for the samples so that lines may be drawn, maxdepth is first for VERTICALNETTOW
            qs = qs.values('instantpoint__activity__startdate', 'instantpoint__activity__enddate', 
                           'instantpoint__activity__maxdepth', 'instantpoint__activity__mindepth', 
                           'instantpoint__activity__name', 'name').distinct()
            for s in qs:
                if self.scale_factor:
                    xsamp.append((s['instantpoint__activity__startdate'].timestamp() / self.scale_factor,
                                  s['instantpoint__activity__enddate'].timestamp() / self.scale_factor))
                else:
                    xsamp.append((s['instantpoint__activity__startdate'].timestamp(),
                                  s['instantpoint__activity__enddate'].timestamp()))

                ysamp.append((s['instantpoint__activity__maxdepth'], s['instantpoint__activity__mindepth']))
                sname.append(s['instantpoint__activity__name'])

        if spanned and (act_type_name == ESP_FILTERING):
            xsamp = []
            ysamp = []
            sname = []
            # Collect all Measurment locations for the Sample Activity
            self.logger.debug(f"Getting Samples for {act_type_name}")
            for sample in (self.sampleQS.select_related('instantpoint__activity')
                               .filter(instantpoint__activity__activitytype__name=act_type_name)):
                act = sample.instantpoint.activity
                xpoints = []
                ypoints = []
                self.logger.debug(f"Getting Measurements for {act}")

                if self.scale_factor:
                    scfac = self.scale_factor
                else:
                    scfac = 1.0

                # Get already simplified depth and time points from simpledepthtime
                for td in (self.qs.filter(instantpoint__sample=sample)
                                  .values_list('simpledepthtime__epochmilliseconds',
                                               'simpledepthtime__depth')
                                  .order_by('simpledepthtime__epochmilliseconds')):
                    xpoints.append(td[0] / scfac / 1000.0)
                    ypoints.append(td[1])

                xsamp.append(xpoints)
                ysamp.append(ypoints)
                sname.append(act.name)

        return xsamp, ysamp, sname

    def _get_color(self, datavalue, cmin, cmax, clt=None):
        '''
        Return RGB color value for data_value given member's color lookup table and cmin, cmax lookup table limits
        '''
        if not clt:
            clt = self.cm
        indx = int(round((float(datavalue) - cmin) * ((len(clt.colors) - 1) / float(cmax - cmin))))
        if indx < 0:
            indx=0
        if indx >= len(clt.colors):
            indx = len(clt.colors) - 1
        return clt.colors[indx]

    def _make_image(self, tmin, tmax, dmin, dmax, xi, yi, cx, cy, cz, clx, cly, clz,
                    contourFlag, cmocean_lookup_str, measurement_markers=True):
        '''Generate image from collected member variables
        '''
        if self.parameterID or self.contourParameterID:
            if self.kwargs.get('activitynames'):
                sectionPngFile = '{}_{}_{}_{}_{}.png'.format(self.parameterID, self.contourParameterID, self.platformName, 
                                                             self.kwargs['activitynames'][0].split('.nc')[0], self.imageID)
            else:
                sectionPngFile = '{}_{}_{}_{}.png'.format(self.parameterID, self.contourParameterID, self.platformName, self.imageID)
        elif self.kwargs['measuredparametersgroup']:
            sectionPngFile = self.kwargs['measuredparametersgroup'][0] + '_' + self.platformName + '_' + self.imageID + '.png'
        else:
            # Return silently with no error message - simply can't make a plot without a Parameter
            return None, None, None, self.cm_name, cmocean_lookup_str, self.standard_name

        sectionPngFileFullPath = os.path.join(settings.MEDIA_ROOT, 'sections', sectionPngFile)
        try:
            os.remove(sectionPngFileFullPath)
        except OSError:
            # Silently ignore
            pass

        if 'showdataas' in self.kwargs:
            if self.kwargs['showdataas']:
                if self.kwargs['showdataas'][0] == 'contour':
                    contourFlag = True
      

        if len(cz) == 0 and len(clz) == 0:
            return None, None, 'No data returned from selection', self.cm_name, cmocean_lookup_str, self.standard_name

        if contourFlag:
            try:
                self.logger.debug('Gridding data with self.sdt_count = %d, and self.y_count = %d', self.sdt_count, self.y_count)
                # See https://scipy-cookbook.readthedocs.io/items/Matplotlib_Gridding_irregularly_spaced_data.html
                zi = griddata((cx, cy), cz, (xi[None,:], yi[:,None]), method='cubic', rescale=True)
            except KeyError as e:
                self.logger.exception('Got KeyError. Could not grid the data')
                return None, None, 'Got KeyError. Could not grid the data', self.cm_name, cmocean_lookup_str, self.standard_name
            except Exception as e:
                self.logger.exception('Could not grid the data')
                return None, None, 'Could not grid the data', self.cm_name, cmocean_lookup_str, self.standard_name

            self.logger.debug('zi = %s', zi)

        if self.qs_mp is not None:
            COLORED_DOT_SIZE_THRESHOLD = 5000
            if self.qs_mp.count() > COLORED_DOT_SIZE_THRESHOLD:
                coloredDotSize = 10
            else:
                coloredDotSize = 20

        parm_info = self.pMinMax
        full_screen = False
        if self.request.GET.get('full_screen'):
            full_screen = True
        try:
            # Make the plot
            # contour the gridded data, plotting dots at the nonuniform data points.
            # See http://scipy.org/Cookbook/Matplotlib/Django
            if full_screen:
                fig = plt.figure(figsize=(12,6))
            else:
                fig = plt.figure(figsize=(6,3))
            ax = fig.add_axes((0,0,1,1))
            if self.scale_factor:
                ax.set_xlim(tmin / self.scale_factor, tmax / self.scale_factor)
            else:
                ax.set_xlim(tmin, tmax)
            ax.set_ylim(dmax, dmin)
            ax.get_xaxis().set_ticks([])
            self.set_ticks_bounds_norm(parm_info)
            if self.parameterID is not None:
                if contourFlag:
                    ax.contourf(xi, yi, zi, cmap=self.cm, norm=self.norm, extend='both',
                            levels=np.linspace(parm_info[1], parm_info[2], self.num_colors+1))
                    if measurement_markers:
                        ax.scatter(cx, cy, marker='.', s=2, c='k', lw = 0)
                else:
                    self.logger.debug('parm_info = %s', parm_info)
                    ax.scatter(cx, cy, c=cz, s=coloredDotSize, cmap=self.cm, lw=0, norm=self.norm)
                    # Draw any spanned data, e.g. NetTows
                    self.logger.debug(f"Drawing spanned data: {len(self.xspan)} samples")
                    for xs,ys,z in zip(self.xspan, self.yspan, self.zspan):
                        try:
                            ax.plot(xs, ys, c=self._get_color(z, parm_info[1], parm_info[2]), lw=3)
                        except ZeroDivisionError:
                            # Likely all data is same value and color lookup table can't be computed
                            return None, None, "Can't plot identical data values of %f" % z, self.cm_name, cmocean_lookup_str, self.standard_name

            if self.sampleQS and SAMPLED not in self.parameterGroups:
                # Sample markers for everything but Net Tows
                xsamp, ysamp, sname = self._get_samples_for_markers(exclude_act_type_name=NETTOW)
                self.logger.debug(f"Drawing scatter of Net Tows: {len(xsamp)} samples")
                ax.scatter(xsamp, np.float64(ysamp), marker='o', c='w', s=15, zorder=10, edgecolors='k')
                for x,y,sn in zip(xsamp, ysamp, sname):
                    plt.annotate(sn, xy=(x,y), xytext=(5,-10), textcoords='offset points', fontsize=7)

                # Annotate NetTow Samples at Sample record location - points
                xsamp, ysamp, sname = self._get_samples_for_markers(act_type_name=NETTOW)
                self.logger.debug(f"Annotating scatter of Net Tows: {len(xsamp)} samples")
                ax.scatter(xsamp, np.float64(ysamp), marker='o', c='w', s=15, zorder=10, edgecolors='k')
                for x,y,sn in zip(xsamp, ysamp, sname):
                    plt.annotate(sn, xy=(x,y), xytext=(5,-5), textcoords='offset points', fontsize=7)

                # Sample markers for Vertical Net Tows (put circle at surface) - lines
                xspan, yspan, sname = self._get_samples_for_markers(act_type_name=VERTICALNETTOW, spanned=True)
                self.logger.debug(f"Plotting Vertical Net Tows: {len(xsamp)} samples")
                for xs,ys in zip(xspan, yspan):
                    ax.plot(xs, ys, c='k', lw=2)
                    ax.scatter([xs[1]], [0], marker='o', c='w', s=15, zorder=10, edgecolors='k')

                # Sample markers for Plankton Pumps - lines
                xspan, yspan, sname = self._get_samples_for_markers(act_type_name=PLANKTONPUMP, spanned=True)
                self.logger.debug(f"Sample markers for Plankton Pumps: {len(xspan)} samples")
                for xs,ys in zip(xspan, yspan):
                    ax.plot(xs, ys, c='k', lw=2)
                    ax.scatter([xs[1]], [ys[1]], marker='o', c='w', s=15, zorder=10, edgecolors='k')

                # Sample markers for ESP Archives - thick transparent lines
                xspan, yspan, sname = self._get_samples_for_markers(act_type_name=ESP_FILTERING, spanned=True)
                self.logger.debug(f"Sample markers for ESP Archives: {len(xspan)} samples")
                for xs,ys in zip(xspan, yspan):
                    ax.plot(xs, ys, c='k', lw=1, alpha=0.5)

            if self.contourParameterID is not None:
                zli = griddata((clx, cly), clz, (xi[None,:], yi[:,None]), method='cubic', rescale=True)
                CS = ax.contour(xi, yi, zli, colors='white')
                ax.clabel(CS, fontsize=9, inline=1)

            if self.kwargs.get('showgeox3dmeasurement') and contourFlag and self.kwargs.get('activitynames'):
                self.logger.debug(f"Writing curtain X3D file {sectionPngFileFullPath} with dpi=480")
                fig.savefig(sectionPngFileFullPath, dpi=480, transparent=True)
            elif full_screen:
                self.logger.debug(f"Writing full_screen file {sectionPngFileFullPath} with dpi=240")
                fig.savefig(sectionPngFileFullPath, dpi=240, transparent=True)
            else:
                self.logger.debug(f"Writing file {sectionPngFileFullPath} with dpi=120")
                fig.savefig(sectionPngFileFullPath, dpi=120, transparent=True)
            plt.close()
        except Exception as e:
            self.logger.exception('Could not plot the data')
            return None, None, 'Could not plot the data', self.cm_name, cmocean_lookup_str, self.standard_name

        if self.colorbarPngFileFullPath:
            try:
                self.makeColorBar(self.colorbarPngFileFullPath, parm_info)
            except Exception as e:
                self.logger.exception('%s', e)
                return None, None, 'Could not plot the colormap', self.cm_name, cmocean_lookup_str, self.standard_name

        return sectionPngFile, self.colorbarPngFile, self.strideInfo, self.cm_name, cmocean_lookup_str, self.standard_name

    def _plot_limits(self):
        '''Return 4 tuple of time and depth min and max for generating plots for Flot or X3D
        '''
        # Estimate horizontal (time) grid spacing by number of points in selection, expecting that simplified depth-time
        # query has salient points, typically in the vertices of the yo-yos. 
        # If the time tuple has values then use those, they represent a zoomed in portion of the Temporal-Depth flot plot
        # in the UI.  If they are not specified then use the Flot plot limits specified separately in the flotlimits tuple.
        tmin = None
        tmax = None
        if 'time' in self.kwargs:
            if self.kwargs['time'][0] is not None and self.kwargs['time'][1] is not None:
                dstart = datetime.strptime(self.kwargs['time'][0], '%Y-%m-%d %H:%M:%S') 
                dend = datetime.strptime(self.kwargs['time'][1], '%Y-%m-%d %H:%M:%S') 
                tmin = dstart.timestamp()
                tmax = dend.timestamp()

        if not tmin and not tmax:
            if self.kwargs['flotlimits'][0] is not None and self.kwargs['flotlimits'][1] is not None:
                tmin = float(self.kwargs['flotlimits'][0]) / 1000.0
                tmax = float(self.kwargs['flotlimits'][1]) / 1000.0

        # If the depth tuple has values then use those, they represent a zoomed in portion of the Temporal-Depth flot plot
        # in the UI.  If they are not specified then use the Flot plot limits specified separately in the flotlimits tuple.
        dmin = None
        dmax = None
        if 'depth' in self.kwargs:
            if self.kwargs['depth'][0] is not None and self.kwargs['depth'][1] is not None:
                dmin = float(self.kwargs['depth'][0])
                dmax = float(self.kwargs['depth'][1])

        if not dmin and not dmax:
            if self.kwargs['flotlimits'][2] is not None and self.kwargs['flotlimits'][3] is not None:
                dmin = float(self.kwargs['flotlimits'][2])
                dmax = float(self.kwargs['flotlimits'][3])

        return tmin, tmax, dmin, dmax

    def renderDatavaluesNoAxes(self, tgrid_max=1000, dgrid_max=100, dinc=0.5, contourFlag=False,
                               loadDataOnly=False, forFlot=True, measurement_markers=True):
        '''
        Produce a .png image without axes suitable for overlay on a Flot graphic or as X3D curtain plots 

        # griddata parameter defaults
        tgrid_max = 1000            # Reasonable maximum width for time-depth-flot plot is about 1000 pixels
        dgrid_max = 100             # Height of time-depth-flot plot area is 335 pixels
        dinc = 0.5                  # Average vertical resolution of AUV Dorado
        '''

        cmocean_lookup_str = ''
        for sn, cm in cmocean_lookup.items():
            cmocean_lookup_str += f"{sn}: {cm}\n"

        # Use session ID so that different users don't stomp on each other with their section plots
        # - This does not work for Firefox which just reads the previous image from its cache
        if 'sessionID' in self.request.session:
            sessionID = self.request.session['sessionID']
        else:
            sessionID = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(7))
            self.request.session['sessionID'] = sessionID

        tmin, tmax, dmin, dmax = self._plot_limits() 

        xi = None
        if tmin and tmax:
            self.sdt_count = self.qs.filter(platform__name__in=self.platformName.split(',')).values_list('simpledepthtime__depth').count()
            self.sdt_count = int(self.sdt_count / 2)                 # 2 points define a line, take half the number of simpledepthtime points
            self.logger.debug('Half of self.sdt_count from query = %d', self.sdt_count)
            if self.sdt_count > tgrid_max or self.sdt_count == 0:
                self.sdt_count = tgrid_max

            xi = np.linspace(tmin, tmax, self.sdt_count)
            ##self.logger.debug('xi = %s', xi)

        # Make depth spacing dinc m, limit to time-depth-flot resolution (dgrid_max)
        yi = None
        if dmin is not None and dmax is not None:
            self.y_count = int((dmax - dmin) / dinc )
            if self.y_count > dgrid_max:
                self.y_count = dgrid_max
            yi = np.linspace(dmin, dmax, self.y_count)
            ##self.logger.debug('yi = %s', yi)

        # Collect the scattered datavalues(time, depth) and grid them
        if xi is not None and yi is not None:
            # Estimate a scale factor to apply to the x values on grid data so that x & y values are visually equal for the flot plot
            # which is assumed to be 3x wider than tall.  Approximate horizontal coverage by Dorado is 1 m/s.
            try:
                self.scale_factor = float(tmax -tmin) / (dmax - dmin) / 3.0
            except ZeroDivisionError as e:
                self.logger.warn(e)
                self.logger.debug('Not setting self.scale_factor.  Scatter plots will still work.')
            else:                
                self.logger.debug('self.scale_factor = %f', self.scale_factor)
                xi = xi / self.scale_factor

            if not self.x and not self.y and not self.z and self.qs_mp is not None:
                self.loadData(self.qs_mp)

            # Copy x, y, z values for color plot (scatter or "contour")
            cx = list(self.x)
            cy = list(self.y)
            cz = list(self.z)
            self.logger.debug('Number of cx, cy, cz data values retrieved from database = %d', len(cz)) 

            clx = []
            cly = []
            clz = []
            if self.contourParameterID is not None:
                self.x = []
                self.y = []
                self.z = []
                self.loadData(self.contour_qs_mp)
                # Copy x, y, z values for contour line plot
                clx = list(self.x)
                cly = list(self.y)
                clz = list(self.z)
                self.logger.debug('Number of clx, cly, clz data values retrieved from database = %d', len(clz)) 

            if not forFlot:
                # Serves to clip the rendered image to the limits of data, as needed for X3D curtains
                # Operate only on Plot Data Color selections 
                # Continue onto _make_image() if no cx or cy data, there may be clx, cly
                if cx:
                    if self.scale_factor:
                        tmin = cx[0] * self.scale_factor
                        tmax = cx[-1] * self.scale_factor
                    else:
                        tmin = cx[0]
                        tmax = cx[-1]
                if cy:
                    dmin = np.min(cy)
                    dmax = np.max(cy)

            # Save important values as member variables for construction of IndexedFaceSets for curtainX3D visualizations.
            self.tmin = tmin
            self.tmax = tmax
            self.dmin = dmin
            self.dmax = dmax

            if loadDataOnly:
                return None, None, 'loadDataOnly specified', self.cm_name, cmocean_lookup_str, self.standard_name
            else:
                return self._make_image(tmin, tmax, dmin, dmax, xi, yi, cx, cy, cz, clx, cly, clz, contourFlag,
                                        cmocean_lookup_str, measurement_markers=measurement_markers)
        else:
            self.logger.warn('xi and yi are None.  tmin, tmax, dmin, dmax = %s, %s, %s, %s', tmin, tmax, dmin, dmax)
            return None, None, 'Select a time-depth range', self.cm_name, cmocean_lookup_str, self.standard_name

    def _get_slices(self, time_array, slice_minutes):
        # Find the indices at slice_minutes intervals, always include the first and last indices
        # time_array is something like self.x with a scale_factor as applied for contour plotting
        if not self.scale_factor:
            self.scale_factor = 1
        slice_esecs = [time_array[0] * self.scale_factor]
        slice_indices = [0]
        prev_esec = time_array[0] * self.scale_factor
        for index, x in enumerate(time_array):
            if x * self.scale_factor > prev_esec + slice_minutes * 60:
                slice_esecs.append(x * self.scale_factor)
                slice_indices.append(index)
                prev_esec = x * self.scale_factor

        slice_indices.append(len(time_array) - 1)
        slice_esecs.append(time_array[-1] * self.scale_factor)

        return slice_indices, slice_esecs

    def _get_ils(self, act, istart, iend, vert_ex, lon_attr, lat_attr, depth_attr, value_attr):

        lon_sliced = getattr(self, lon_attr)[act][istart:iend]
        lat_sliced = getattr(self, lat_attr)[act][istart:iend]
        depth_sliced = getattr(self, depth_attr)[act][istart:iend]
        value_sliced = getattr(self, value_attr)[act][istart:iend]

        points = ''
        colors = ''
        indices = ''
        index = 0
        for lon, lat, depth, value in zip(lon_sliced, lat_sliced, depth_sliced, value_sliced):
            try:
                cindx = int(round((value - float(self.pMinMax[1])) * (len(self.clt) - 1) / 
                                  (float(self.pMinMax[2]) - float(self.pMinMax[1]))))
            except ValueError as e:
                # Likely: 'cannot convert float NaN to integer' as happens when rendering something like altitude outside of terrain coverage
                continue
            except ZeroDivisionError as e:
                logger.error("Can't make color lookup table with min and max being the same, self.pMinMax = %s", self.pMinMax)
                raise e

            if cindx < 0:
                cindx = 0
            if cindx > len(self.clt) - 1:
                cindx = len(self.clt) - 1

            if lon_attr.endswith('_span'):
                points = points + '%.5f %.5f %.1f %.5f %.5f %.1f ' % (lats[0], lons[0],
                        -depths[0] * vert_ex, lats[1], lons[1], -depths[1] * vert_ex)
                colors = colors + '%.3f %.3f %.3f %.3f %.3f %.3f ' % (self.clt[cindx][0], self.clt[cindx][1], self.clt[cindx][2],
                                                                      self.clt[cindx][0], self.clt[cindx][1], self.clt[cindx][2])
                indices = indices + '%i %i ' % (index, index + 1)
                index = index + 2
            else:
                points = points + '%.5f %.5f %.1f ' % (lat, lon, -depth * vert_ex)
                colors = colors + '%.3f %.3f %.3f ' % (self.clt[cindx][0], self.clt[cindx][1], self.clt[cindx][2])
                indices = indices + '%i ' % index
                index = index + 1

        # End the IndexedLinestring with -1 so that end point does not 
        # connect to the beg point, end with space for multiple activities
        indices = indices + '-1 ' 

        return points, colors, indices

    def dataValuesX3D(self, platform_name, vert_ex=10.0, slice_minutes=10):
        '''
        Return scatter-like data values as X3D geocoordinates and colors.
        This is called per platform and returns a hash organized by activity and slice_minutes Shapes.
        '''
        x3d_results = {}
        shape_id_dict = {}
        logger.debug("Building X3D data values with vert_ex = %f", vert_ex)
        if not self.lon and not self.lat and not self.depth and not self.value:
            self.logger.debug('Calling self.loadData()...')
            self.loadData(self.qs_mp)
        try:
            for act in list(self.value_by_act.keys()):
                self.logger.debug('Reading data from act = %s', act)
                # Get indices and times of the Shape slices to be animated - organize shapes by end time of the slice
                slice_indices, slice_esecs = self._get_slices(self.x, slice_minutes)
                self.logger.debug(f"Slicing pairwise {len(self.lon_by_act[act])} lat & lon points at indices {slice_indices} for {slice_minutes} minute intervals")
                for istart, iend, end_esecs in zip(slice_indices, slice_indices[1:], slice_esecs[1:]):
                    shape_id = f"ils_{platform_name}_{int(end_esecs)}"
                    shape_id_dict[int(end_esecs)] = [shape_id]
                    self.logger.debug(f"Getting IndexedLineSet data for shape_id: {shape_id}")
                    iendp1 = iend + 1
                    if iendp1 > len(self.lon_by_act[act]) - 1:
                        iendp1 = iend
                    points, colors, indices = self._get_ils(act, istart, iendp1, vert_ex, 
                                                            'lon_by_act', 'lat_by_act', 'depth_by_act', 'value_by_act')
                    x3d_results[shape_id] = {'colors': colors.rstrip(), 'points': points.rstrip(), 'index': indices.rstrip()}

            # Make pairs of points for spanned NetTow-like data
            for act in list(self.value_by_act_span.keys()):
                self.logger.debug('Reading spanned NetTow-like data from act = %s', act)
                istart = 0
                iend = len(self.lon_by_act_span[act])
                # TODO: test and fix getting start time for _span data
                shape_id = f"ils_{platform_name}_{int(end_esecs)}_span"
                shape_id_dict[int(end_esecs)] = [shape_id]
                points, colors, indices = self._get_ils(act, istart, iend, vert_ex, 
                                                        'lon_by_act_span', 'lat_by_act_span', 'depth_by_act_span', 'value_by_act_span')
                x3d_results[shape_id] = {'colors': colors.rstrip(), 'points': points.rstrip(), 'index': indices.rstrip()}

        except Exception as e:
            self.logger.exception('Could not create measuredparameterx3d: %s', e)

        return x3d_results, shape_id_dict

    def curtainX3D(self, platform_names, vert_ex=10.0, slice_minutes=10):
        '''Return X3D elements of image texture mapped onto geospatial geometry of vehicle track.
        platform_names may be a comma separated list of Platform names that may contain sampling platforms.
        Constraints for data in the image come from the settings in self.kwargs set by what calls this.
        Images will be constructed by Activity in order to provide a temporal bounds, maintaining some
        detail in the image.  Shapes will be keyed by 'ifs_<platform>_<esecs>' as in the IndexedLineSet
        shapes.
        '''
        x3d_results = {}
        shape_id_dict = {}

        # 1. Image: Build image with potential Sampling Platforms included
        saved_platforms = self.kwargs['platforms']
        self.kwargs['platforms'] = platform_names.split(',')
        sectionPngFile, colorbarPngFile, _, _, _, _ = self.renderDatavaluesNoAxes(forFlot=False, measurement_markers=False)
        if not sectionPngFile:
            self.kwargs['platforms'] = saved_platforms
            return x3d_results, shape_id_dict

        sectionPngFileFullPath = os.path.join(settings.MEDIA_ROOT, 'sections', sectionPngFile)

        sectionPngFileTrimmed = sectionPngFile.replace('.png', '_trimmed.png')
        sectionPngFileTrimmedFullPath = os.path.join(settings.MEDIA_ROOT, 'sections', sectionPngFileTrimmed)
        im = Image.open(sectionPngFileFullPath)
        # Trim one pixel from edges to get rid of black lines from Matplotlib
        new_bounds = [2, 2] + [d - 1 for d in im.size]
        im_trimmed = im.crop(new_bounds)
        self.logger.info(f"Saving trimmed image file: {sectionPngFileTrimmedFullPath}")
        im_trimmed.save(sectionPngFileTrimmedFullPath)

        # 2. Geometry: We want position data for only the main platform, in case we also have a Sampling Platform
        if len(self.kwargs['platforms']) > 1:
            # Now, use renderDatavaluesNoAxes() to fill member variables without Sampling Platforms
            self.kwargs['platforms'] = [self.kwargs['platforms'][0]]
            self.logger.debug(f"renderDatavaluesNoAxes(loadDataOnly=True) for self.kwargs['platforms'] = {self.kwargs['platforms']}")
            sectionPngFile, colorbarPngFile, _, _, _, _ = self.renderDatavaluesNoAxes(forFlot=False, loadDataOnly=True,
                                                                                      measurement_markers=False)
            if not sectionPngFile:
                self.kwargs['platforms'] = saved_platforms
                return x3d_results, shape_id_dict

        # Get indices and times of the quadrilaterals for our image texture mapping - organize shapes by end time of the slice
        slice_indices, slice_esecs = self._get_slices(self.x, slice_minutes)
        self.logger.debug(f"Slicing {len(self.lon)} lat & lon points at indices {slice_indices} for {slice_minutes} minute intervals")
        last_frac = 0.0
        for sindex, eindex, end_esecs in zip(slice_indices, slice_indices[1:], slice_esecs[1:]):
            shape_id = f"ifs_{self.kwargs['platforms'][0]}_{int(end_esecs)}"
            shape_id_dict[int(end_esecs)] = [shape_id]
            self.logger.debug(f"Getting IndexedFace data for shape_id: {shape_id}")

            # Make counter-clockwise planar slices at slice_minutes values along the geometry
            # Construct the geometry according to the 4 edges of the image: time moves left to right in image
            # Bottom; lon, lat in order; Top: lon, lat in reverse order - indices: 0 to len(lon_sliced) * 2
            points = ''
            points += '{:.5f} {:.5f} {:.1f} '.format(self.lat[sindex], self.lon[sindex], -self.dmax * vert_ex)
            points += '{:.5f} {:.5f} {:.1f} '.format(self.lat[eindex], self.lon[eindex], -self.dmax * vert_ex)
            points += '{:.5f} {:.5f} {:.1f} '.format(self.lat[eindex], self.lon[eindex], -self.dmin * vert_ex)
            points += '{:.5f} {:.5f} {:.1f} '.format(self.lat[sindex], self.lon[sindex], -self.dmin * vert_ex)
           
            indices = '0 1 2 3 ' 
            ifs_cindex = ifs_tcindex = indices + '-1'

            # The s,t texture coordinate points for slice_minutes quadrilateral slices of the image
            tc_points = ''
            fraction = (end_esecs - self.tmin) / (self.tmax - self.tmin)
            self.logger.debug(f"fraction = {fraction}")
            tc_points += '{last_frac:.5f} 0 {frac:.5f} 0 '.format(last_frac=last_frac, frac=fraction)
            tc_points += '{frac:.5f} 1 {last_frac:.5f} 1 '.format(last_frac=last_frac, frac=fraction)
            last_frac = fraction

            self.logger.debug(f"len(points.strip().split(' '))/3 = {len(points.strip().split(' '))/3}") 
            self.logger.debug(f"len(tc_points.strip().split(' '))/2 = {len(tc_points.strip().split(' '))/2}") 
            self.logger.debug(f"len(indices.strip().split(' '))/1 = {len(indices.strip().split(' '))/1}") 
            self.logger.debug(f"Faces: len(ifs_tcindex.strip().split(' '))/5 = {len(ifs_tcindex.strip().split(' '))/5}") 

            x3d_results[shape_id] = {'points': points.rstrip(), 'ifs_cindex': ifs_cindex.rstrip(), 'ifs_tcindex': ifs_tcindex.rstrip(),
                                     'tc_points': tc_points.rstrip(), 'info': '', 'image': sectionPngFileTrimmed}

        self.kwargs['platforms'] = saved_platforms
        return x3d_results, shape_id_dict

class PPDatabaseException(Exception):
    def __init__(self, message, sql):
        Exception.__init__(self, message)
        self.sql = sql


class ParameterParameter(BaseParameter):
    '''
    Use matploplib to create nice looking property-property plots
    '''
    logger = logging.getLogger(__name__)
    def __init__(self, kwargs, request, pDict, mpq, pq, pMinMax):
        '''
        Save parameters that can be used by the different plotting methods here
        @pMinMax is like: (pID, pMin, pMax)
        '''
        super(self.__class__, self).__init__()

        self.kwargs = kwargs
        self.request = request
        self.pDict = pDict
        self.mpq = mpq
        self.pq = pq

        self.pMinMax = pMinMax

        self.standard_name = None
        try:
            if self.pMinMax['c'][0]:
                self.standard_name = (models.Parameter.objects.using(self.request.META['dbAlias'])
                                            .get(id=int(self.pMinMax['c'][0])).standard_name)
        except (IndexError, KeyError):
            # No value for self.pMinMax['c'][0], let self.standard_name = None
            pass
        except ValueError:
            # Likely self.pMinMax['c'][0] is a coordinate name string
            self.standard_name = self.pMinMax['c'][0]

        self.set_colormap()

        try:
            if self.kwargs['parameterparameter'][3] == self.kwargs['parameterplot'][0]:
                # Set from UI values only if pc is the same as the Plot Data Parameter
                if self.cmin is not None:
                    self.pMinMax['c'][1] = self.cmin
                if self.cmax is not None:
                    self.pMinMax['c'][2] = self.cmax
        except IndexError:
            # Likely no color parameter selected
            pass

        self.depth = []
        self.x_id = []
        self.y_id = []
        self.x = []
        self.y = []
        self.z = []
        self.c = []
        self.lon = []
        self.lat = []
        self.sdepth = []
        self.sx = []
        self.sy = []
        self.sample_names = []

    def computeSigmat(self, limits, xaxis_name='sea_water_salinity', pressure=0):
        '''
        Given a tuple of limits = (xmin, xmax, ymin, ymax) and an xaxis_name compute potential
        density for a range of values between the mins and maxes.  Return the X and Y values
        for salinity/temperature and density converted to sigma-t. A pressure value may be passed
        to compute relative to a pressure other than 0.
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
                    row.append(sw.pden(si, ti, pressure) - 1000.0)
                sigmat.append(row)

        elif xaxis_name == 'sea_water_temperature':
            t = np.linspace(limits[0], limits[1], nt, endpoint=False)
            s = np.linspace(limits[2], limits[3], ns, endpoint=False)
            for si in s:
                row = []
                for ti in t:
                    row.append(sw.pden(si, ti, pressure) - 1000.0)
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
        p = re.compile('SELECT .+? FROM')           # Non-greedy, match to the first 'FROM'
        csql = p.sub('''SELECT count(*) FROM''', sql.replace('\n', ' '))
        self.logger.debug('csql = %s', csql)
        return csql

    def _getXYCData(self, strideFlag=True, latlonFlag=False, returnIDs=False, sampleFlag=True):
        @transaction.atomic(using=self.request.META['dbAlias'])
        def inner_getXYCData(self, strideFlag, latlonFlag):
            '''
            Construct SQL and iterate through cursor to get X, Y, and possibly C Parameter Parameter data
            '''
            # Construct special SQL for P-P plot that returns up to 3 data values for the up to 3 Parameters requested for a 2D plot
            sql = str(self.pq.qs_mp.query)
            sql = self.pq.addParameterParameterSelfJoins(sql, self.pDict)
            if sampleFlag:
                sample_sql = self.pq.addSampleConstraint(sql)

            # Use cursors so that we can specify the database alias to use.
            cursor = connections[self.request.META['dbAlias']].cursor()
            sample_cursor = connections[self.request.META['dbAlias']].cursor()

            # Get count and set a stride value if more than a PP_MAX_POINTS which Matplotlib cannot plot, about 100,000 points
            try:
                cursor.execute(self._getCountSQL(sql))
            except DatabaseError as e:
                infoText = 'Parameter-Parameter: Cannot get count. Make sure you have no Parameters selected in the Filter.'
                self.logger.warn(e)
                raise PPDatabaseException(infoText, sql)

            pp_count = cursor.fetchone()[0]
            self.logger.debug('pp_count = %d', pp_count)
            stride_val = 1
            if strideFlag:
                PP_MAX_POINTS = 50000
                stride_val = int(pp_count / PP_MAX_POINTS)
                if stride_val < 1:
                    stride_val = 1
                self.logger.debug('stride_val = %d', stride_val)

            if latlonFlag:
                if sql.find('stoqs_measurement') != -1:
                    self.logger.debug('Adding lon lat to SELECT')
                    sql = sql.replace('DISTINCT', 'DISTINCT ST_X(stoqs_measurement.geom) AS lon, ST_Y(stoqs_measurement.geom) AS lat,\n')
                elif sql.find('stoqs_sample') != -1:
                    self.logger.debug('Adding lon lat to SELECT')
                    sql = sql.replace('DISTINCT', 'DISTINCT ST_X(stoqs_sample.geom) AS lon, ST_Y(stoqs_sample.geom) AS lat,\n')

                if sampleFlag:
                    sample_sql = sample_sql.replace('DISTINCT', 'DISTINCT ST_X(stoqs_sample.geom) AS lon, ST_Y(stoqs_sample.geom) AS lat,\n')

            if returnIDs:
                if sql.find('stoqs_measurement') != -1:
                    self.logger.debug('Adding ids to SELECT for stoqs_measurement')
                    sql = sql.replace('DISTINCT', 'DISTINCT mp_x.id, mp_y.id,\n')

            # Get the Parameter-Parameter points
            try:
                self.logger.debug('Executing sql = %s', sql)
                cursor.execute(sql)
            except DatabaseError as e:
                infoText = 'Parameter-Parameter: Query failed. Make sure you have no Parameters selected in the Filter.'
                self.logger.warn('Cannot execute sql query for Parameter-Parameter plot: %s', e)
                raise PPDatabaseException(infoText, sql)

            if sampleFlag: 
                # Get the Sample points
                try:
                    self.logger.debug('Executing sample_sql = %s', sample_sql)
                    sample_cursor.execute(sample_sql)
                except DatabaseError as e:
                    infoText = 'Parameter-Parameter: Sample Query failed.'
                    self.logger.warn('Cannot execute sample_sql query for Parameter-Parameter plot: %s', e)
                    raise PPDatabaseException(infoText, sample_sql)

            # Populate MeasuredParameter x,y,c member variables
            counter = 0
            self.logger.debug('Looping through rows in cursor with a stride of %d...', stride_val)
            for row in cursor:
                if counter % stride_val == 0:
                    # SampledParameter datavalues are Decimal, convert everything to a float for numpy
                    lrow = list(row)
                    if None in lrow or np.nan in lrow:
                        continue
                    if returnIDs:
                        self.x_id.append(int(lrow.pop(0)))
                        self.y_id.append(int(lrow.pop(0)))

                    if latlonFlag:
                        self.lon.append(float(lrow.pop(0)))
                        self.lat.append(float(lrow.pop(0)))
                        
                    self.depth.append(float(lrow.pop(0)))
                    self.x.append(float(lrow.pop(0)))
                    self.y.append(float(lrow.pop(0)))
                    try:
                        self.c.append(float(lrow.pop(0)))
                    except IndexError:
                        # Permit x and y, without a c selected
                        pass
                counter = counter + 1
                if counter % 1000 == 0:
                    self.logger.debug('Made it through %d of %d points', counter, pp_count)

            if self.x == [] or self.y == []:
                raise PPDatabaseException('No data returned from query', sql)

            if sampleFlag:
                # Populate SampledParameter x,y,c member variables
                self.logger.debug('Looping through rows in sample_cursor')
                for row in sample_cursor:
                    lrow = list(row)
                    if latlonFlag:
                        self.lon.append(float(lrow.pop(0)))
                        self.lat.append(float(lrow.pop(0)))

                    # Need only the x and y values for sample points                
                    self.sdepth.append(float(lrow.pop(0)))
                    self.sx.append(float(lrow.pop(0)))
                    self.sy.append(float(lrow.pop(0)))
                    self.sample_names.append(lrow.pop(0))

            return stride_val, sql, pp_count

        return inner_getXYCData(self, strideFlag, latlonFlag)

    def make2DPlot(self):
        '''
        Produce a Parameter-Parameter .png image with axis limits set to the 1 and 99 percentiles and draw outside the lines
        '''
        pplrFlag = self.request.GET.get('pplr', False)
        ppfrFlag = self.request.GET.get('ppfr', False)
        ppslFlag = self.request.GET.get('ppsl', False)
        ppnsFlag = self.request.GET.get('ppns', False)
     
        sql = ''
        try:
            # self.x and self.y may already be set for this instance by makeX3D()
            if not self.x and not self.y:
                if ppnsFlag:
                    stride_val, sql, pp_count = self._getXYCData(strideFlag=False)
                else:
                    stride_val, sql, pp_count = self._getXYCData(strideFlag=True)

            # If still no self.x and self.y then selection is not valid for the chosen x and y
            if self.x == [] or self.y == []:
                return None, 'No Parameter-Parameter data values returned.', sql
            
            # Use session ID so that different users don't stomp on each other with their parameterparameter plots
            # - This does not work for Firefox which just reads the previous image from its cache
            if 'sessionID' in self.request.session:
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
                except Exception as e:
                    self.logger.exception('Failed to create path for ' +
                                     'parameterparameter (%s) file', ppPngFile)
                    return None, 'Failed to create path for parameterparameter (%s) file' % ppPngFile, sql

            # Make the figure
            fig = plt.figure(figsize=(7,7))
            plt.grid(True)
            ax = plt.gca()
            if not ppfrFlag:
                ax.set_xlim(self.pMinMax['x'][1], self.pMinMax['x'][2])
                ax.set_ylim(self.pMinMax['y'][1], self.pMinMax['y'][2])

            if self.c:
                self.logger.debug('self.pMinMax = %s', self.pMinMax)
                self.logger.debug('Making colored scatter plot of %d points', len(self.x))
                self.set_ticks_bounds_norm(self.pMinMax['c'], use_ui_cmincmax=False, use_ui_num_colors=False)
                try:
                    if self.kwargs['parameterparameter'][3] == self.kwargs['parameterplot'][0]:
                        self.set_ticks_bounds_norm(self.pMinMax['c'])
                except IndexError:
                    # Likely no color parameter selected
                    pass

                ax.scatter(self.x, self.y, c=self.c, s=10, cmap=self.cm, lw=0,
                           clip_on=False, norm=self.norm)
                # Add colorbar to the image
                cb_ax = fig.add_axes([0.2, 0.98, 0.6, 0.02]) 
                cb = mpl.colorbar.ColorbarBase( cb_ax, cmap=self.cm,
                                                norm=self.norm,
                                                ticks=self.ticks,
                                                boundaries=self.bounds,
                                                orientation='horizontal')
                try:
                    cp = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['c']))
                    if cp.units:
                        if cp.units in cp.name:
                            cb.set_label(cp.name)
                        else:
                            cb.set_label(f"{cp.name} ({cp.units})")
                    else:
                        cb.set_label(cp.name)
                except ValueError:
                    # Likely a coordinate variable
                    cp = models.Parameter
                    cp.name = self.pDict['c']
                    cp.standard_name = self.pDict['c']
                    cp.units = _getCoordUnits(self.pDict['c'])
                    cb.set_label('%s (%s)' % (cp.name, cp.units))
            else:
                self.logger.debug('Making scatter plot of %d points', len(self.x))
                warnings.filterwarnings("ignore", message="omni_normtest is not valid with less than 8 observations; 6 samples were given")
                ax.scatter(self.x, self.y, marker='.', s=10, c='k', lw = 0, clip_on=False)

            # Label the axes
            try:
                xp = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['x']))
                ax.set_xlabel(f"{xp.name} ({xp.units})")
                if xp.units:
                    if xp.units in xp.name:
                        ax.set_xlabel(xp.name)
            except ValueError:
                # Likely a coordinate variable
                xp = models.Parameter
                xp.name = self.pDict['x']
                xp.standard_name = self.pDict['x']
                xp.units = _getCoordUnits(self.pDict['x'])
                ax.set_xlabel('%s (%s)' % (xp.name, xp.units))

            try:
                yp = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['y']))
                ax.set_ylabel(f"{yp.name} ({yp.units})")
                if yp.units:
                    if yp.units in yp.name:
                        ax.set_ylabel(yp.name)
            except ValueError:
                # Likely a coordinate variable
                yp = models.Parameter
                yp.name = self.pDict['y']
                yp.standard_name = self.pDict['y']
                yp.units = _getCoordUnits(self.pDict['y'])
                if self.pDict['y'] == 'depth':
                    ax.invert_yaxis()
                ax.set_ylabel('%s (%s)' % (yp.name, yp.units))

            # Add Sigma-t contours if x/y is salinity/temperature, approximate depth to pressure - must fix for deep water...
            Z = None
            infoText = 'n = %d' % len(self.x)
            if stride_val > 1:
                infoText += ' (of %d, stride = %d - Check No stride for unstrided plot)' % (pp_count, stride_val)
            infoText += '<br>%s ranges: fixed [%f, %f], actual [%f, %f]<br>%s ranges: fixed [%f, %f], actual [%f, %f]' % (
                            xp.name, self.pMinMax['x'][1], self.pMinMax['x'][2], np.min(self.x), np.max(self.x),
                            yp.name, self.pMinMax['y'][1], self.pMinMax['x'][2], np.min(self.y), np.max(self.y))
            if xp.standard_name == 'sea_water_salinity' and yp.standard_name == 'sea_water_temperature':
                X, Y, Z = self.computeSigmat(ax.axis(), xaxis_name='sea_water_salinity')
            if xp.standard_name == 'sea_water_temperature' and yp.standard_name == 'sea_water_salinity':
                X, Y, Z = self.computeSigmat(ax.axis(), xaxis_name='sea_water_temperature')
            if Z is not None:
                CS = ax.contour(X, Y, Z, colors='k')
                plt.clabel(CS, inline=1, fontsize=10)
   
            if pplrFlag: 
                # Do linear regression with statsmodels.api which provides the summary detail that Roberto suggested is good to have
                # See: https://datatofish.com/statsmodels-linear-regression/
                X = sm.add_constant(self.x)
                results = sm.OLS(self.y, X).fit()
                ax.plot(self.x, results.predict(X), color='r', linewidth=0.5)
                infoText += "<br><br>OLS linear regression: {} = {} * {} + {}".format(yp.name, round_to_n(results.params[1],4), 
                                                                                      xp.name, round_to_n(results.params[0],4))
                infoText += f"<br><br>{results.summary()}"

            # Add any sample locations
            if ppslFlag:
                if self.sx and self.sy:
                    if self.c:
                        try:
                            ax.scatter(self.sx, self.sy, marker='o', c=np.array(self.c), s=25, cmap=self.cm, 
                                       vmin=self.pMinMax['c'][1], vmax=self.pMinMax['c'][2], clip_on=False, edgecolors='k')
                        except ValueError as e:
                            # Likely because a Measured Parameter has been selected for color and len(self.c) != len(self.sx)
                            ax.scatter(self.sx, self.sy, marker='o', c='w', s=25, zorder=10, clip_on=False, edgecolors='k')
                    else:
                        ax.scatter(self.sx, self.sy, marker='o', c='w', s=25, zorder=10, clip_on=False, edgecolors='k')
                    for i, txt in enumerate(self.sample_names):
                        ax.annotate(txt, xy=(self.sx[i], self.sy[i]), xytext=(3.0, 3.0), textcoords='offset points')
            
            # Save the figure
            try:
                self.logger.debug('Saving to file ppPngFileFullPath = %s', ppPngFileFullPath)
                fig.savefig(ppPngFileFullPath, dpi=120, transparent=True)
            except Exception as e:
                infoText = 'Parameter-Parameter: ' + str(e)
                self.logger.exception('Cannot make 2D parameterparameter plot: %s', e)
                plt.close()
                return None, infoText, sql

        except TypeError as e:
            ##infoText = 'Parameter-Parameter: ' + str(type(e))
            infoText = 'Parameter-Parameter: ' + str(e)
            self.logger.exception('Cannot make 2D parameterparameter plot: %s', e)
            plt.close()
            return None, infoText, sql

        else:
            plt.close()
            return ppPngFile, infoText, sql

    def makeX3D(self):
        @transaction.atomic(using=self.request.META['dbAlias'])
        def inner_makeX3D(self):
            '''
            Produce X3D XML text and return it
            '''
            x3dResults = {}

            if ((models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['x'])).name == 'AXIS_X' and
                 models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['y'])).name == 'AXIS_Y' and
                 models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['z'])).name == 'AXIS_Z') or
                (models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['x'])).name == 'ROT_X' and
                 models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['y'])).name == 'ROT_Y' and
                 models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['z'])).name == 'ROT_Z') or
                (models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['x'])).name == 'XA (g)' and
                 models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['y'])).name == 'YA (g)' and
                 models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['z'])).name == 'ZA (g)')):
                # Override axis limits for BED rotational data to always make a sphere
                self.pMinMax['x'] = [self.pMinMax['x'][0], -1, 1]
                self.pMinMax['y'] = [self.pMinMax['y'][0], -1, 1]
                self.pMinMax['z'] = [self.pMinMax['z'][0], -1, 1]
                
            try:
                # Construct special SQL for P-P plot that returns up to 4 data values for the up to 4 Parameters requested for a 3D plot
                sql = str(self.pq.qs_mp.query)
                self.logger.debug('self.pDict = %s', self.pDict)
                sql = self.pq.addParameterParameterSelfJoins(sql, self.pDict)

                # Use cursor so that we can specify the database alias to use. Columns are always 0:x, 1:y, 2:c (optional)
                cursor = connections[self.request.META['dbAlias']].cursor()
                cursor.execute(sql)
                for row in cursor:
                    if None in row or np.nan in row:
                        continue
                    # SampledParameter datavalues are Decimal, convert everything to a float for numpy, row[0] is depth
                    self.depth.append(float(row[0]))
                    self.x.append(float(row[1]))
                    self.y.append(float(row[2]))
                    self.z.append(float(row[3]))
                    try:
                        self.c.append(float(row[4]))
                    except IndexError:
                        # Permit x, y, and z without a c selected
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
                try:
                    xp = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['x']))
                    if xp.units:
                        if xp.units in xp.name:
                            self.pMinMax['x'].append(('%s' % (xp.name, )))
                        else:
                            self.pMinMax['x'].append(('%s (%s)' % (xp.name, xp.units)))
                    else:
                        self.pMinMax['x'].append(('%s' % (xp.name, )))
                except ValueError:
                    # Likely a coordinate variable
                    xp = models.Parameter
                    xp.name = self.pDict['x']
                    xp.standard_name = self.pDict['x']
                    xp.units = _getCoordUnits(self.pDict['x'])
                    self.pMinMax['x'].append(('%s (%s)' % (xp.name, xp.units)))

                try:
                    yp = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['y']))
                    if yp.units:
                        if yp.units in yp.name:
                            self.pMinMax['y'].append(('%s' % (yp.name, )))
                        else:
                            self.pMinMax['y'].append(('%s (%s)' % (yp.name, yp.units)))
                    else:
                        self.pMinMax['y'].append(('%s' % (yp.name, )))
                except ValueError:
                    # Likely a coordinate variable
                    yp = models.Parameter
                    yp.name = self.pDict['y']
                    yp.standard_name = self.pDict['y']
                    yp.units = _getCoordUnits(self.pDict['y'])
                    self.pMinMax['y'].append(('%s (%s)' % (yp.name, yp.units)))

                try:
                    zp = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['z']))
                    if zp.units:
                        if zp.units in zp.name:
                            self.pMinMax['z'].append(('%s' % (zp.name, )))
                        else:
                            self.pMinMax['z'].append(('%s (%s)' % (zp.name, zp.units)))
                    else:
                        self.pMinMax['z'].append(('%s' % (zp.name, )))
                except ValueError:
                    # Likely a coordinate variable
                    zp = models.Parameter
                    zp.name = self.pDict['z']
                    zp.standard_name = self.pDict['z']
                    zp.units = _getCoordUnits(self.pDict['z'])
                    self.pMinMax['z'].append(('%s (%s)' % (zp.name, zp.units)))

                colorbarPngFile = ''
                if self.pDict['c']:
                    try:
                        cp = models.Parameter.objects.using(self.request.META['dbAlias']).get(id=int(self.pDict['c']))
                    except ValueError:
                        # Likely a coordinate variable
                        cp = models.Parameter
                        cp.name = self.pDict['c']
                        cp.standard_name = self.pDict['c']
                        cp.units = _getCoordUnits(self.pDict['c'])
                    try:
                        imageID = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(10))
                        colorbarPngFile = '%s_%s_%s_%s_3dcolorbar_%s.png' % (self.pDict['x'], self.pDict['y'], self.pDict['z'], self.pDict['c'], imageID )
                        colorbarPngFileFullPath = os.path.join(settings.MEDIA_ROOT, 'parameterparameter', colorbarPngFile)
                        self.makeColorBar(colorbarPngFileFullPath, self.pMinMax['c'])

                    except Exception:
                        self.logger.exception('Could not plot the colormap')
                        return None, None, 'Could not plot the colormap'

                x3dResults = {'colors': colors, 'points': points, 'info': '', 'x': self.pMinMax['x'], 'y': self.pMinMax['y'], 'z': self.pMinMax['z'], 
                              'colorbar': colorbarPngFile, 'sql': sql}

            except DatabaseError:
                self.logger.exception('Cannot make parameterparameter X3D')
                raise DatabaseError('Cannot make parameterparameter X3D')

            return x3dResults

        return inner_makeX3D(self)

