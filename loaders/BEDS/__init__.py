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

    def __init__(self, base_dbAlias, base_campaignName, stride=1):
        self.base_dbAlias = base_dbAlias
        self.base_campaignName = base_campaignName
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
    def process_command_line(self):
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS. 
        Process command line arguments to support these kind of database loads:
            - Optimal stride
            - Test version
            - Uniform stride

        Load scripts should have execution code that looks like:

            # Execute the load
            cl.process_command_line()
        
            if cl.args.test:
                ##cl.loadDorado(stride=100)
                cl.loadM1ts(stride=10)
                cl.loadM1met(stride=10)
            
            elif cl.args.optimal_stride:
                cl.loadDorado(stride=2)
                cl.loadM1ts(stride=1)
                cl.loadM1met(stride=1)
        
            else:
                cl.loadDorado(stride=cl.args.stride)
                cl.loadM1ts(stride=cl.args.stride)
                cl.loadM1met(stride=cl.args.stride)
        '''
        import argparse

        parser = argparse.ArgumentParser(description='STOQS load defaults: dbAlias="%s" campaignName="%s"'
                                         % (self.base_dbAlias, self.base_campaignName))
        parser.add_argument('--dbAlias', action='store', help='Database alias, if different from default (must be defined in privateSettings)')
        parser.add_argument('--campaignName', action='store', help='Campaign Name, if different from default')
        parser.add_argument('--optimal_stride', action='store_true', help='Run load for optimal stride configuration as defined in "if cl.args.optimal_stride:" section of load script')
        parser.add_argument('--test', action='store_true', help='Run load for test configuration as defined in "if cl.args.test:" section of load script')
        parser.add_argument('--stride', action='store', type=int, default=1, help='Stride value (default=1)')

        self.args = parser.parse_args()

        # Modify base dbAlias with conventional suffix if dbAlias not specified on command line
        if not self.args.dbAlias:
            if self.args.optimal_stride:
                self.dbAlias = self.base_dbAlias + '_s'
            elif self.args.test:
                self.dbAlias = self.base_dbAlias + '_t'
            elif self.args.stride:
                if self.args.stride == 1:
                    self.dbAlias = self.base_dbAlias
                else:
                    self.dbAlias = self.base_dbAlias + '_s%d' % self.args.stride

        # Modify base campaignName with conventional suffix if campaignName not specified on command line
        if not self.args.campaignName:
            if self.args.optimal_stride:
                self.campaignName = self.base_campaignName + ' with optimal strides'
            elif self.args.test:
                self.campaignName = self.base_campaignName + ' for testing'
            elif self.args.stride:
                if self.args.stride == 1:
                    self.campaignName = self.base_campaignName
                else:
                    self.campaignName = self.base_campaignName + ' with uniform stride of %d' % self.args.stride




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


