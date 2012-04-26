#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Contains class for common routines for loading all CANON data

Mike McCann
MBARI 22 April 2012

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
import GulperLoader


class CANONLoader(object):
    '''
    Common routines for loading all CANON data
    '''
    stride = 1
    def __init__(self, dbAlias, campaignName):
        self.dbAlias = dbAlias
        self.campaignName = campaignName


    def loadDorado(self):
        '''
        Dorado specific load functions
        '''
        for (aName, file) in zip([ a + ' (stride=%d)' % self.stride for a in self.dorado_files], self.dorado_files):
            url = self.dorado_base + file
            DAPloaders.runDoradoLoader(url, self.campaignName, aName, 'dorado', 'auv', 'AUV mission', self.dbAlias, self.stride)
            GulperLoader.load_gulps(aName, file, self.dbAlias)


    def loadTethys(self):
        '''
        Tethys specific load functions
        '''
        for (aName, file) in zip([ a + ' (stride=%d)' % self.stride for a in self.tethys_files], self.tethys_files):
            url = self.tethys_base + file
            DAPloaders.runLrauvLoader(url, self.campaignName, aName, 'tethys', 'auv', 'AUV mission', self.tethys_parms, self.dbAlias, self.stride)

    def loadMartin(self):
        '''
        Martin specific load functions
        '''
        for (aName, file) in zip([ a + ' (stride=%d)' % self.stride for a in self.martin_files], self.martin_files):
            url = self.martin_base + file
            DAPloaders.runAuvctdLoader(url, self.campaignName, aName, 'martin', 'ff0000', 'ship', 'cruise', self.martin_parms, self.dbAlias, self.stride)


    def loadAll(self):
        '''
        Execute all the load functions
        '''
        try:
            self.loadDorado()
        except AttributeError as e:
            print e
            raw_input("WARNING: No dorado data for dbAlias = %s, campaignName = %s" % (self.dbAlias, self.campaignName))
            pass
        try:
            self.loadTethys()
        except AttributeError as e:
            print e
            raw_input("WARNING: No tethys data for dbAlias = %s, campaignName = %s, tethys_parms = %s" % (self.dbAlias, self.campaignName, self.tethys_parms))
            pass
        try:
            self.loadMartin()
        except AttributeError as e:
            print e
            raw_input("WARNING: No martin data for dbAlias = %s, campaignName = %s, martin_parms = %s" % (self.dbAlias, self.campaignName, self.martin_parms))
            pass

if __name__ == '__main__':
    '''
    Test operation of this class
    '''
    cl = CANONLoader('default', 'Test Load')
    cl.stride = 1000
    cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
    cl.dorado_files = ['Dorado389_2010_300_00_300_00_decim.nc']
    cl.loadAll()


