#!/usr/bin/env python

'''
Contains classes for common routines for loading all Coordinated Canyon
Experiment data

Mike McCann
MBARI 26 April 2016
'''

import os
import sys
import webob

# Insert Django App directory (parent of config) into python path 
sys.path.insert(0, os.path.abspath(os.path.join(
                    os.path.dirname(__file__), "../../")))
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
# django >=1.7
try:
    import django
    django.setup()
except AttributeError:
    pass

import matplotlib as mpl
mpl.use('Agg')               # Force matplotlib to not use any Xwindows backend
from loaders import LoadScript
from DAPloaders import (Mooring_Loader, logger, runBEDTrajectoryLoader, runTimeSeriesLoader,
                        OpendapError, InvalidSliceRequest, NoValidData)
import matplotlib.pyplot as plt
from matplotlib.colors import rgb2hex
import numpy as np
from pydap.client import open_url

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
    num_beds = 11
    beds_names = [('bed{:02d}').format(n) for n in range(num_beds+1)]
    reds = plt.cm.Reds
    for b, c in zip(beds_names, reds(np.arange(0, reds.N, reds.N/num_beds, dtype=int))):
        colors[b] = rgb2hex(c)[1:]
        # Duplicate color  for Trajectory 't' version
        colors[b + 't'] = rgb2hex(c)[1:]

    # Override with Roberto's Kaleidagraph colors - from email on 29 November 2017
    colors['bed09'] = 'D3F33C'
    colors['bed09t'] = 'D3F33C'
    colors['bed09s'] = 'D3F33C'
    colors['bed08'] = 'D94C7B'
    colors['bed08t'] = 'D94C7B'
    colors['bed04'] = 'F0660F'
    colors['bed04t'] = 'F0660F'
    colors['bed03'] = '90E7F0'
    colors['bed03t'] = '90E7F0'
    colors['bed10'] = 'BC8FD9'
    colors['bed10t'] = 'BC8FD9'
    colors['bed11'] = 'A4A4A4'
    colors['bed11t'] = 'A4A4A4'
    colors['bed11s'] = 'A4A4A4'

    # color for SIN
    colors['ccesin'] = 'ff0000'

    # Colors for MS* moorings
    num_ms = 7
    ms_names = [('ccems{:1d}').format(n) for n in range(num_ms+1)]
    oranges = plt.cm.Oranges
    for b, c in zip(ms_names, oranges(np.linspace(oranges.N/num_ms, oranges.N, num=num_ms+1, dtype=int))):
        colors[b] = rgb2hex(c)[1:]

    def get_start_bed_depths(self):
        '''Return matching list of starting depths from NetCDF files in self.bed_files
        '''
        depths = []
        for file in self.bed_files:
            url = os.path.join(self.bed_base, file)
            logger.info(f'{url}')
            ds = open_url(url)
            if ds.attributes['NC_GLOBAL']['featureType'].lower() == 'timeseries':
                depths.append(ds['depth'][0][0])
            else:
                depths.append(float(ds['depth']['depth'][0][0].data))

        return depths

    def loadBEDS(self, stride=None, featureType='trajectory', critSimpleDepthTime=1):
        '''
        BEDS specific load functions; featureType can be 'trajectory' or 'timeSeries'.
        Use 'trajectory' for events that we've fudged into a trajectory netCDF file
        using the canyon's thalweg.  Use 'timeSeries' for events for which the BED
        does not significantly translate.
        '''
        stride = stride or self.stride
        for (aName, pName, file, plotTimeSeriesDepth, fg) in zip(
                            [ '/'.join(a.split('/')[-2:]) + ' (stride=%d)' % stride for a in self.bed_files], 
                            self.bed_platforms, self.bed_files, self.bed_depths, self.bed_framegrabs):
            url = os.path.join(self.bed_base, file)
            try:
                if featureType.lower() == 'trajectory':
                    # To get timeSeries plotting for trajectories (in the Parameter tab of the UI) 
                    # assign a plotTimeSeriesDepth value of the starting depth in meters.
                    runBEDTrajectoryLoader(url, self.campaignName, self.campaignDescription,
                                           aName, pName, self.colors[pName.lower()], 'bed',
                                           'deployment', self.bed_parms, self.dbAlias, stride,
                                           plotTimeSeriesDepth=plotTimeSeriesDepth,
                                           grdTerrain=self.grdTerrain, framegrab=fg)
                elif featureType.lower() == 'timeseries':
                    runTimeSeriesLoader(url, self.campaignName, self.campaignDescription,
                                        aName, pName, self.colors[pName.lower()], 'bed', 
                                        'deployment', self.bed_parms, self.dbAlias, stride)
                self.addPlatformResources('https://stoqs.mbari.org/x3d/beds/beds_housing_with_axes_src_scene.x3d',
                                          pName, scalefactor=10)
            except (OpendapError, InvalidSliceRequest, webob.exc.HTTPError):
                pass

    def loadCCESIN(self, stride=None):
        '''
        Mooring CCESIN specific load functions
        '''
        platformName = 'CCESIN'
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.ccesin_files], self.ccesin_files):
            url = os.path.join(self.ccesin_base, f)
            ccesin_start_datetime = getattr(self, 'ccesin_start_datetime', None)
            ccesin_end_datetime = getattr(self, 'ccesin_end_datetime', None)

            loader = Mooring_Loader(url = url, 
                                    campaignName = self.campaignName,
                                    campaignDescription = self.campaignDescription,
                                    dbAlias = self.dbAlias,
                                    activityName = aName,
                                    activitytypeName = 'Mooring Deployment',
                                    platformName = platformName,
                                    platformColor = self.colors[platformName.lower()],
                                    platformTypeName = 'mooring',
                                    stride = stride,
                                    startDatetime = ccesin_start_datetime,
                                    endDatetime = ccesin_end_datetime,
                                    command_line_args = self.args)

            loader.include_names = self.ccesin_parms
            loader.auxCoords = {}
            if 'adcp' in f.lower() or 'aquadopp' in f.lower():
                Mooring_Loader.getFeatureType = lambda self: 'timeseriesprofile'
                # The timeseries variables 'Hdg_1215', 'Ptch_1216', 'Roll_1217' should have a coordinate of
                # a singleton depth variable, but EPIC files has this as a sensor_depth variable attribute.  
                # Need special handling in the loader for these data.
                for p in ['u_1205', 'v_1206', 'w_1204', 'AGC_1202']:
                    loader.auxCoords[p] = {'time': 'time', 'latitude': 'lat', 'longitude': 'lon', 'depth': 'depth'}
                for p in ['Hdg_1215', 'Ptch_1216', 'Roll_1217']:
                    loader.auxCoords[p] = {'time': 'time', 'latitude': 'lat', 'longitude': 'lon'}
            else:
                Mooring_Loader.getFeatureType = lambda self: 'timeseries'

            try:
                loader.process_data()
            except NoValidData as e:
                self.logger.info(str(e))
                continue

            # For timeseriesProfile data we need to pass the nominaldepth of the plaform
            # so that the model is put at the correct depth in the Spatial -> 3D view.
            try:
                self.addPlatformResources('https://stoqs.mbari.org/x3d/cce_bin_assem/cce_bin_assem_src_scene.x3d',
                                          platformName, nominaldepth=self.ccesin_nominaldepth)
            except AttributeError:
                self.addPlatformResources('https://stoqs.mbari.org/x3d/cce_bin_assem/cce_bin_assem_src_scene.x3d',
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
        start_datetime = getattr(self, plt_name + '_start_datetime', None)
        end_datetime = getattr(self, plt_name + '_end_datetime', None)

        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in files], files):
            if '_ProcessedWaves' in f:
                if stride != 1:
                    # Most files are high time frequency ADCP data, so accept the generic stride
                    # Override for files like MBCCE_MS0_AWAC_20160408_ProcessedWaves.nc, which has 2 hour sampling
                    stride = 1
                    aName = f
                    self.logger.info(f"Overriding stride -> = {stride} for file {f}")
                else:
                    self.logger.info(f"Skipping {f} with stride = 1 as the entire 2 hour data set is loaded")

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

            if 'adcp' in f.lower() or 'aquadopp' in f.lower():
                Mooring_Loader.getFeatureType = lambda self: 'timeseriesprofile'
            else:
                Mooring_Loader.getFeatureType = lambda self: 'timeseries'

            for p in parms:
                # The timeseries variables 'Hdg_1215', 'Ptch_1216', 'Roll_1217' should have a coordinate of
                # a singleton depth variable, but EPIC files has this as a sensor_depth variable attribute.  
                # Need special handling in the loader for these data.
                if p in ['u_1205', 'v_1206', 'w_1204', 'AGC_1202']:
                    loader.auxCoords[p] = {'time': 'time', 'latitude': 'lat', 'longitude': 'lon', 'depth': 'depth'}
                if p in ['Hdg_1215', 'Ptch_1216', 'Roll_1217']:
                    loader.auxCoords[p] = {'time': 'time', 'latitude': 'lat', 'longitude': 'lon'}
                else:
                    loader.auxCoords[p] = {'time': 'time', 'latitude': 'lat',
                                           'longitude': 'lon', 'depth': 'depth'}
            try:
                loader.process_data()
            except NoValidData as e:
                self.logger.info(str(e))
                continue

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
