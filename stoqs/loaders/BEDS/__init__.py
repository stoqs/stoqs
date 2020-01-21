#!/usr/bin/env python

__author__    = 'Mike McCann'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Contains class for common routines for loading all BEDS data

Mike McCann
MBARI 13 May 2013

@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys

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

import DAPloaders
from loaders import LoadScript
import matplotlib as mpl
mpl.use('Agg')               # Force matplotlib to not use any Xwindows backend
import matplotlib.pyplot as plt
from matplotlib.colors import rgb2hex
import numpy as np

class BEDSLoader(LoadScript):
    '''
    Common routines for loading all BEDS data
    '''
    num_beds = 9
    beds_names = [('bed{:02d}').format(n) for n in range(num_beds+1)]

    # See http://matplotlib.org/examples/color/colormaps_reference.html
    colors = {}
    reds = plt.cm.Reds
    for b, c in zip(beds_names, reds(np.arange(0, reds.N, reds.N/num_beds))):
        colors[b] = rgb2hex(c)[1:]
        # Duplicate color  for Trajectory 't' version
        colors[b + 't'] = rgb2hex(c)[1:]


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
                self.addPlatformResources('https://stoqs.mbari.org/x3d/beds/beds_housing_with_axes_src_scene.x3d',
                                          pName, scalefactor=10)
            except (DAPloaders.OpendapError, DAPloaders.InvalidSliceRequest):
                pass


if __name__ == '__main__':
    '''
    Test operation of this class
    '''
    cl = BEDSLoader('stoqs_beds2013', 'Test BEDS Load')
    cl.stride = 1
    cl.bed_base = 'http://odss-test.shore.mbari.org/thredds/dodsC/BEDS_2013/beds01/'
    cl.bed_files = ['BED00039.nc']
    cl.bed_parms = ['XA', 'YA', 'ZA', 'XR', 'YR', 'ZR', 'PRESS', 'BED_DEPTH']
    cl.loadBEDS()


