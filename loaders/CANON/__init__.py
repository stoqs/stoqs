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

class Util(object):
    '''
    Utility methods used for creating netCDF files and loading data into STOQS
    '''
    @staticmethod
    def convert_up_to_down(file):
        '''
        Convert an upcast SeaBird pctd file to a downcast file
        '''
        newName = '.'.join(file.split('.')[:-1]) + 'up.asc'
        outFile = open(newName, 'w')
        lines = []
        i = 0
        for line in open(file):
            if i == 0:
                outFile.write(line)
            else:
                lines.append(line)
            i = i + 1

        for line in reversed(lines):
                outFile.write(line)

        outFile.close()

        return newName


class CANONLoader(object):
    '''
    Common routines for loading all CANON data
    '''
    stride = 1
    brownish = {'dorado':       '8c510a',
                'tethys':       'bf812d',
                'daphne':       'dfc27d',
                'fulmar':       'f6e8c3',
                'waveglider':   'c7eae5',
                'nps_g29':      '80cdc1',
                'l_662':        '35978f',
                'martin':       '01665e',
                'flyer':     '11665e',
                'espdrift':       '21665e',
             }
    colors = {  'dorado':       'ffeda0',
                'other':        'ffeda0',
                'tethys':       'fed976',
                'daphne':       'feb24c',
                'fulmar':       'fd8d3c',
                'waveglider':   'fc4e2a',
                'nps_g29':      'e31a1c',
                'l_662':        'bd0026',
                'martin':       '800026',
                'flyer':     '801026',
                'espdrift':       '802026',
             }

    def __init__(self, dbAlias, campaignName):
        self.dbAlias = dbAlias
        self.campaignName = campaignName


    def loadDorado(self):
        '''
        Dorado specific load functions
        '''
        for (aName, file) in zip([ a + ' (stride=%d)' % self.stride for a in self.dorado_files], self.dorado_files):
            url = self.dorado_base + file
            DAPloaders.runDoradoLoader(url, self.campaignName, aName, 'dorado', self.colors['dorado'], 'auv', 'AUV mission', 
                                        self.dbAlias, self.stride)
            GulperLoader.load_gulps(aName, file, self.dbAlias)


    def loadTethys(self):
        '''
        Tethys specific load functions
        '''
        for (aName, file) in zip([ a + ' (stride=%d)' % self.stride for a in self.tethys_files], self.tethys_files):
            url = self.tethys_base + file
            DAPloaders.runLrauvLoader(url, self.campaignName, aName, 'tethys', self.colors['tethys'], 'auv', 'AUV mission', 
                                        self.tethys_parms, self.dbAlias, self.stride)

    def loadDaphne(self):
        '''
        Daphne specific load functions
        '''
        for (aName, file) in zip([ a + ' (stride=%d)' % self.stride for a in self.daphne_files], self.daphne_files):
            url = self.daphne_base + file
            # Set stride to 1 for telemetered data
            DAPloaders.runLrauvLoader(url, self.campaignName, aName, 'daphne', self.colors['daphne'], 'auv', 'AUV mission', 
                                        self.daphne_parms, self.dbAlias, 1)

    def loadMartin(self):
        '''
        Martin specific load functions
        '''
        for (aName, file) in zip([ a + ' (stride=%d)' % self.stride for a in self.martin_files], self.martin_files):
            url = self.martin_base + file
            DAPloaders.runTrajectoryLoader(url, self.campaignName, aName, 'martin', self.colors['martin'], 'ship', 'cruise', 
                                        self.martin_parms, self.dbAlias, self.stride)

    def loadFulmar(self):
        '''
        Fulmar specific load functions
        '''
        for (aName, file) in zip([ a + ' (stride=%d)' % self.stride for a in self.fulmar_files], self.fulmar_files):
            url = self.fulmar_base + file
            DAPloaders.runTrajectoryLoader(url, self.campaignName, aName, 'fulmar', self.colors['fulmar'], 'ship', 'cruise', 
                                        self.fulmar_parms, self.dbAlias, self.stride)

    def loadNps_g29(self):
        '''
        Glider specific load functions
        '''
        for (aName, file) in zip([ a + ' (stride=%d)' % self.stride for a in self.nps_g29_files], self.nps_g29_files):
            url = self.nps_g29_base + file
            print "url = %s" % url
            DAPloaders.runGliderLoader(url, self.campaignName, aName, 'nps_g29', self.colors['nps_g29'], 'glider', 'Glider Mission', 
                                        self.nps_g29_parms, self.dbAlias, self.stride)

    def loadL_662(self):
        '''
        Glider specific load functions
        '''
        for (aName, file) in zip([ a + ' (stride=%d)' % self.stride for a in self.l_662_files], self.l_662_files):
            url = self.l_662_base + file
            print "url = %s" % url
            DAPloaders.runGliderLoader(url, self.campaignName, aName, 'l_662', self.colors['l_662'], 'glider', 'Glider Mission', 
                                        self.l_662_parms, self.dbAlias, self.stride, self.l_662_startDatetime, self.l_662_endDatetime)

    def loadWaveglider(self):
        '''
        Glider specific load functions
        '''
        for (aName, file) in zip([ a + ' (stride=%d)' % self.stride for a in self.waveglider_files], self.waveglider_files):
            url = self.waveglider_base + file
            print "url = %s" % url
            DAPloaders.runGliderLoader(url, self.campaignName, aName, 'waveglider', self.colors['waveglider'], 'glider', 'Glider Mission', 
                                        self.waveglider_parms, self.dbAlias, self.stride)
    def loadESPdrift(self):
        '''
        ESPdrift specific load functions
        '''
        for (aName, file) in zip([ a + ' (stride=%d)' % self.stride for a in self.espdrift_files], self.espdrift_files):
            url = self.espdrift_base + file
            print "url = %s" % url
            DAPloaders.runTrajectoryLoader(url, self.campaignName, aName, 'espdrift', self.colors['espdrift'], 'espdrift', 'ESP drift Mission', 
                                        self.espdrift_parms, self.dbAlias, self.stride)

    def loadWFuctd(self):
        '''
        WF uctd specific load functions
        '''
        for (aName, file) in zip([ a + ' (stride=%d)' % self.stride for a in self.wfuctd_files], self.wfuctd_files):
            url = self.wfuctd_base + file
            print "url = %s" % url
            DAPloaders.runTrajectoryLoader(url, self.campaignName, aName, 'wf_uctd', self.colors['flyer'], 'wf_uctd', 'Western Flyer Underway CTD Data', 
                                        self.wfuctd_parms, self.dbAlias, self.stride)

    def loadWFpctd(self):
        '''
        WF pctd specific load functions
        '''
        for (aName, file) in zip([ a + ' (stride=%d)' % self.stride for a in self.wfpctd_files], self.wfpctd_files):
            url = self.wfpctd_base + file
            print "url = %s" % url
            DAPloaders.runTrajectoryLoader(url, self.campaignName, aName, 'wf_pctd', self.colors['flyer'], 'wf_pctd', 'Western Flyer Underway CTD Data', 
                                        self.wfpctd_parms, self.dbAlias, self.stride)
    def loadAll(self):
        '''
        Execute all the load functions
        '''
        loaders = [ 'loadDorado', 'loadTethys', 'loadDaphne', 'loadMartin', 'loadFulmar', 'loadNps_g29', 'loadWaveglider', 'loadL_662', 'loadESPdrift',
                    'loadWFuctd', 'loadWFpctd']
        for loader in loaders:
            if hasattr(self, loader):
                # Call the loader if it exists
                try:
                    getattr(self, loader)()
                except AttributeError as e:
                    print e
                    print "WARNING: No data from %s for dbAlias = %s, campaignName = %s" % (loader, self.dbAlias, self.campaignName)
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


