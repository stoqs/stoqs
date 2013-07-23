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
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # settings.py is one dir up

import DAPloaders

class BEDSLoader(object):
    '''
    Common routines for loading all BEDS data
    '''

    brownish = {'bed00':       '8c510a',
                'bed01':       'bf812d',
                'bed02':       '4f812d',
             }
    colors = {  'bed00':       'ffeda0',
                'bed01':       'ffeda0',
                'bed02':       '4feda0',
             }

    def __init__(self, dbAlias, campaignName, stride=1):
        self.dbAlias = dbAlias
        self.campaignName = campaignName
        self.stride = stride


    def loadBEDS(self, stride=None):
        '''
        BEDS specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.bed_files], self.bed_files):
            url = self.bed_base + file
            DAPloaders.runTimeSeriesLoader(url, self.campaignName, aName, 'bed00', self.colors['bed00'], 'bed', 'deployment', 
                                        self.bed_parms, self.dbAlias, stride)


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


