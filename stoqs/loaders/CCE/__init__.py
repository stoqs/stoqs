#!/usr/bin/env python

'''
Contains classes for common routines for loading all Coordinated Canyon
Experiment data

Mike McCann
MBARI 26 April 2016
'''

import os
import sys

# Insert Django App directory (parent of config) into python path 
sys.path.insert(0, os.path.abspath(os.path.join(
                    os.path.dirname(__file__), "../../")))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
# django >=1.7
try:
    import django
    django.setup()
except AttributeError:
    pass

import matplotlib as mpl
mpl.use('Agg')               # Force matplotlib to not use any Xwindows backend
import DAPloaders
from loaders import LoadScript
from DAPloaders import Mooring_Loader
import matplotlib.pyplot as plt
from matplotlib.colors import rgb2hex
import numpy as np

def getStrideText(stride):
    '''
    Format stride into a string to be appended to the Activity name, if stride==1 return empty string
    '''
    if stride == 1:
        return ''
    else:
        return ' (stride=%d)' % stride


class CCELoader(LoadScript):
    '''
    Common routines for loading all CCE data
    '''
    # See http://matplotlib.org/examples/color/colormaps_reference.html
    colors = {}

    # Colors for BEDs 
    num_beds = 9
    beds_names = [('bed{:02d}').format(n) for n in range(num_beds+1)]
    reds = plt.cm.Reds
    for b, c in zip(beds_names, reds(np.arange(0, reds.N, reds.N/num_beds))):
        colors[b] = rgb2hex(c)[1:]
        # Duplicate color  for Trajectory 't' version
        colors[b + 't'] = rgb2hex(c)[1:]

    # color for BIN
    colors['ccebin'] = 'ff0000'

    # Colors for MS* moorings
    num_ms = 8
    ms_names = [('ccems{:1d}').format(n) for n in range(num_ms+1)]
    oranges = plt.cm.Oranges
    for b, c in zip(ms_names, oranges(np.arange(0, oranges.N, oranges.N/num_ms))):
        colors[b] = rgb2hex(c)[1:]


    def loadBEDS(self, stride=None, featureType='trajectory'):
        '''
        BEDS specific load functions; featureType can be 'trajectory' or 'timeSeries'.
        Use 'trajectory' for events that we've fudged into a trajectory netCDF file
        using the canyon's thalweg.  Use 'timeSeries' for events for which the BED
        does not significantly translate.
        '''
        stride = stride or self.stride
        for (aName, pName, file, plotTimeSeriesDepth, fg) in zip(
                            [ a.split('/')[-1] + ' (stride=%d)' % stride for a in self.bed_files], 
                            self.bed_platforms, self.bed_files, self.bed_depths, self.bed_framegrabs):
            url = os.path.join(self.bed_base, file)
            try:
                if featureType.lower() == 'trajectory':
                    # To get timeSeries plotting for trajectories (in the Parameter tab of the UI) 
                    # assign a plotTimeSeriesDepth value of the starting depth in meters.
                    DAPloaders.runBEDTrajectoryLoader(url, self.campaignName, self.campaignDescription,
                                                      aName, pName, self.colors[pName.lower()], 'bed',
                                                      'deployment', self.bed_parms, self.dbAlias, stride,
                                                      plotTimeSeriesDepth=plotTimeSeriesDepth,
                                                      grdTerrain=self.grdTerrain, framegrab=fg)
                elif featureType.lower() == 'timeseries':
                    DAPloaders.runTimeSeriesLoader(url, self.campaignName, self.campaignDescription,
                                                   aName, pName, self.colors[pName.lower()], 'bed', 
                                                   'deployment', self.bed_parms, self.dbAlias, stride)
                self.addPlatformResources('http://stoqs.mbari.org/x3d/beds/beds_housing_with_axes_src_scene.x3d',
                                          pName, scalefactor=10)
            except (DAPloaders.OpendapError, DAPloaders.InvalidSliceRequest):
                pass

    def loadCCEBIN(self, stride=None):
        '''
        Mooring CCEBIN specific load functions
        '''
        platformName = 'CCEBIN'
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.ccebin_files], self.ccebin_files):
            url = os.path.join(self.ccebin_base, f)

            dataStartDatetime = None
            if self.args.append:
                # Return datetime of last timevalue - if data are loaded from multiple 
                # activities return the earliest last datetime value
                dataStartDatetime = InstantPoint.objects.using(self.dbAlias).filter(
                                                activity__name=aName).aggregate(
                                                Max('timevalue'))['timevalue__max']
                if dataStartDatetime:
                    # Subract an hour to fill in missing_values at end from previous load
                    dataStartDatetime = dataStartDatetime - timedelta(seconds=3600)

            if 'adcp' in f:
                Mooring_Loader.getFeatureType = lambda self: 'timeseriesprofile'
            else:
                Mooring_Loader.getFeatureType = lambda self: 'timeseries'

            DAPloaders.runMooringLoader(url, self.campaignName, self.campaignDescription, aName,
                                        platformName, self.colors['ccebin'], 'mooring', 'Mooring Deployment',
                                        self.ccebin_parms, self.dbAlias, stride, self.ccebin_startDatetime,
                                        self.ccebin_endDatetime, dataStartDatetime)

        # For timeseriesProfile data we need to pass the nominaldepth of the plaform
        # so that the model is put at the correct depth in the Spatial -> 3D view.
        try:
            self.addPlatformResources('http://stoqs.mbari.org/x3d/cce_bin_assem/cce_bin_assem_src_scene.x3d',
                                      platformName, nominaldepth=self.ccebin_nominaldepth)
        except AttributeError:
            self.addPlatformResources('http://stoqs.mbari.org/x3d/cce_bin_assem/cce_bin_assem_src_scene.x3d',
                                      platformName)

# Dynamic method creation for any number of 'ccems' moorings
def make_load_ccems_method(name):
    def _generic_load_ccems(self, stride=None):
        # Generalize attribute value lookup
        plt_name = name.split('_')[1]
        platformName = plt_name[-3:].upper()
        base = getattr(self, plt_name + '_base')
        files = getattr(self, plt_name + '_files')
        parms = getattr(self, plt_name + '_parms')
        nominal_depth = getattr(self, plt_name + '_nominal_depth')
        start_datetime = getattr(self, plt_name + '_start_datetime')
        end_datetime = getattr(self, plt_name + '_end_datetime')

        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in files], files):
            url = os.path.join(base, f)

            # Monkeypatch featureType depending on file name (or parms...)
            if 'adcp' in f.lower():
                Mooring_Loader.getFeatureType = lambda self: 'timeseriesprofile'
            else:
                Mooring_Loader.getFeatureType = lambda self: 'timeseries'

            loader = Mooring_Loader(url = url, 
                                    campaignName = self.campaignName,
                                    campaignDescription = self.campaignDescription,
                                    dbAlias = self.dbAlias,
                                    activityName = aName,
                                    activitytypeName = 'Mooring Deployment',
                                    platformName = platformName,
                                    platformColor = self.colors[plt_name],
                                    platformTypeName = 'mooring',
                                    stride = stride,
                                    startDatetime = start_datetime,
                                    endDatetime = end_datetime,
                                    dataStartDatetime = None)

            loader.include_names = parms
            loader.auxCoords = {}
            for p in parms:
                loader.auxCoords[p] = {'time': 'time', 'latitude': 'lat',
                                       'longitude': 'lon', 'depth': 'depth'}
            loader.process_data()

    return _generic_load_ccems

# Add the dynamically created methods to the class
for name in ['load_ccems{:d}'.format(n) for n in range(8)]:
    _method = make_load_ccems_method(name)
    setattr(CCELoader, name, _method)


if __name__ == '__main__':
    '''
    Test operation of this class
    '''
    cl = CCELoader('stoqs_beds2013', 'Test CCE Load')
    cl.stride = 1
    cl.bed_base = 'http://odss-test.shore.mbari.org/thredds/dodsC/BEDS_2013/beds01/'
    cl.bed_files = ['BED00039.nc']
    cl.bed_parms = ['XA', 'YA', 'ZA', 'XR', 'YR', 'ZR', 'PRESS', 'BED_DEPTH']
    cl.loadBEDS()


