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
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
# django >=1.7
try:
    import django
    django.setup()
except AttributeError:
    pass

import DAPloaders
from loaders import LoadScript

class BEDSLoader(LoadScript):
    '''
    Common routines for loading all BEDS data
    '''

    brownish = {'bed00':       '8c010a',
                'bed01':       '8c510a',
                'bed02':       'bf812d',
                'bed03':       '4f812d',
             }
    colors = {  'bed00':       'ff0da0',
                'bed01':       'ffeda0',
                'bed02':       'ffeda0',
                'bed03':       '4feda0',
             }

    def loadBEDS(self, stride=None, featureType='trajectory'):
        '''
        BEDS specific load functions; featureType can be 'trajectory' or 'timeSeries'.  Use 'trajectory' for events that we've fudged
        into a trajectory netCDF file using the canyon's thalweg.  Use 'timeSeries' for events for which the BED does not significantly translate.
        '''
        stride = stride or self.stride
        for (aName, pName, file, plotTimeSeriesDepth) in zip(
                            [ a + ' (stride=%d)' % stride for a in self.bed_files], 
                            self.bed_platforms, self.bed_files, self.bed_depths):
            url = self.bed_base + file
            try:
                if featureType.lower() == 'trajectory':
                    # To get timeSeries plotting for trajectories (in the Parameter tab of the UI) assign a plotTimeSeriesDepth value of the starting depth in meters.
                    DAPloaders.runTrajectoryLoader(url, self.campaignName, self.campaignDescription, aName, pName, self.colors[pName.lower()], 'bed', 'deployment', 
                                            self.bed_parms, self.dbAlias, stride, plotTimeSeriesDepth=plotTimeSeriesDepth, grdTerrain=self.grdTerrain)
                elif featureType.lower() == 'timeseries':
                    print 'pName = %s' % pName
                    DAPloaders.runTimeSeriesLoader(url, self.campaignName, self.campaignDescription, aName, pName, self.colors[pName.lower()], 'bed', 'deployment', 
                                            self.bed_parms, self.dbAlias, stride)
            except (DAPloaders.OpendapError, DAPloaders.InvalidSliceRequest):
                pass

            # Leave commented out to indicate how this would be used (X3DOM can't handle old style timestamp routing that we used to do in VRML)
            ##self.addPlaybackResources(x3dplaybackurl, aName)

            self.addPlatformResources('http://dods.mbari.org/data/beds/x3d/beds_housing_with_axes.x3d', pName)

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


