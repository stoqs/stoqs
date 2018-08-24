#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Contains class for common routines for loading all MarMenor data

Mike McCann
MBARI 14 June 2012

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


class MarMenorLoader(object):
    '''
    Common routines for loading all CANON data
    '''
    stride = 1
    colors = {  'sparus':       'ffeda0',
                'castaway':     'ffeda0',
                'tethys':       'fed976',
                'daphne':       'feb24c',
                'fulmar':       'fd8d3c',
                'waveglider':   'fc4e2a',
                'nps_g29':      'e31a1c',
                'l_662':        'bd0026',
                'martin':       '800026',
             }

    def __init__(self, dbAlias, campaignName):
        self.dbAlias = dbAlias
        self.campaignName = campaignName


    def loadSparus(self):
        '''
        Sparus specific load functions
        '''
        for (aName, file) in zip([ a + ' (stride=%d)' % self.stride for a in self.sparus_files], self.sparus_files):
            url = self.sparus_base + file
            DAPloaders.runTrajectoryLoader(url, self.campaignName, aName, 'sparus', self.colors['sparus'], 'auv', 'AUV mission', 
                                        self.sparus_parms, self.dbAlias, self.stride)
    def loadCastaway(self):
        '''
        Sparus specific load functions
        '''
        for (aName, file) in zip([ a + ' (stride=%d)' % self.stride for a in self.castaway_files], self.castaway_files):
            url = self.castaway_base + file
            DAPloaders.runTrajectoryLoader(url, self.campaignName, aName, 'castaway', self.colors['castaway'], 'mooring', 'CTD Profile', 
                                        self.castaway_parms, self.dbAlias, self.stride)


    def loadAll(self):
        '''
        Execute all the load functions
        '''
        loaders = ['loadSparus', ]
        loaders = ['loadCastaway', ]
        for loader in loaders:
            if hasattr(self, loader):
                # Call the loader if it exists
                try:
                    getattr(self, loader)()
                except AttributeError as e:
                    print(e)
                    print(("WARNING: No data from %s for dbAlias = %s, campaignName = %s" % (loader, self.dbAlias, self.campaignName)))
                    pass


if __name__ == '__main__':
    '''
    Test operation of this class
    '''
    mml = MarMenorLoader('stoqs_marmenor_nov2011', 'AUV 2011')
    mml.castaway_base = 'http://localhost:8080/thredds/dodsC/agg/Castaway/20111105'
    mml.castaway_files = [ '.nc']
#                          'foo1.nc'
#                         ]
    mml.castaway_parms = ['Pressure', 'Temperature', 'Conductivity']
    mml.loadAll()


