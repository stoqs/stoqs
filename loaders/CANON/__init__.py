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
from SampleLoaders import SeabirdLoader, load_gulps

class CANONLoader(object):
    '''
    Common routines for loading all CANON data
    '''
    brownish = {'dorado':       '8c510a',
                'tethys':       'bf812d',
                'daphne':       'dfc27d',
                'fulmar':       'f6e8c3',
                'waveglider':   'c7eae5',
                'nps_g29':      '80cdc1',
                'l_662':        '35978f',
                'm1':           '35f78f',
                'martin':       '01665e',
                'flyer':        '11665e',
                'espdrift':     '21665e',
             }
    colors = {  'dorado':       'ffeda0',
                'other':        'ffeda0',
                'tethys':       'fed976',
                'daphne':       'feb24c',
                'fulmar':       'fd8d3c',
                'waveglider':   'fc4e2a',
                'nps_g29':      'e31a1c',
                'l_662':        'bd0026',
                'm1':           'bd2026',
                'hehape':       'bd2026',
                'rusalka':      'bd4026',
                'carmen':       'bd8026',
                'martin':       '800026',
                'flyer':        '801026',
                'carson':       '881026',
                'espdrift':     '802026',
                'espmack':      '804026',
                'espbruce':     '808026',
             }

    def __init__(self, base_dbAlias, base_campaignName, stride=1):
        self.base_dbAlias = base_dbAlias
        self.base_campaignName = base_campaignName
        self.stride = stride

    def loadDorado(self, stride=None):
        '''
        Dorado specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.dorado_files], self.dorado_files):
            url = self.dorado_base + file
            DAPloaders.runDoradoLoader(url, self.campaignName, aName, 'dorado', self.colors['dorado'], 'auv', 'AUV mission', 
                                        self.dbAlias, stride)
            load_gulps(aName, file, self.dbAlias)


    def loadTethys(self, stride=None):
        '''
        Tethys specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.tethys_files], self.tethys_files):
            url = self.tethys_base + file
            DAPloaders.runLrauvLoader(url, self.campaignName, aName, 'tethys', self.colors['tethys'], 'auv', 'AUV mission', 
                                        self.tethys_parms, self.dbAlias, stride)

    def loadDaphne(self, stride=None):
        '''
        Daphne specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.daphne_files], self.daphne_files):
            url = self.daphne_base + file
            # Set stride to 1 for telemetered data
            DAPloaders.runLrauvLoader(url, self.campaignName, aName, 'daphne', self.colors['daphne'], 'auv', 'AUV mission', 
                                        self.daphne_parms, self.dbAlias, stride)

    def loadMartin(self, stride=None):
        '''
        Martin specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.martin_files], self.martin_files):
            url = self.martin_base + file
            DAPloaders.runTrajectoryLoader(url, self.campaignName, aName, 'martin', self.colors['martin'], 'ship', 'cruise', 
                                        self.martin_parms, self.dbAlias, stride)

    def loadFulmar(self, stride=None):
        '''
        Fulmar specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.fulmar_files], self.fulmar_files):
            url = self.fulmar_base + file
            DAPloaders.runTrajectoryLoader(url, self.campaignName, aName, 'fulmar', self.colors['fulmar'], 'ship', 'cruise', 
                                        self.fulmar_parms, self.dbAlias, stride)

    def loadNps_g29(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.nps_g29_files], self.nps_g29_files):
            url = self.nps_g29_base + file
            print "url = %s" % url
            DAPloaders.runGliderLoader(url, self.campaignName, aName, 'nps_g29', self.colors['nps_g29'], 'glider', 'Glider Mission', 
                                        self.nps_g29_parms, self.dbAlias, stride)

    def loadL_662(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.l_662_files], self.l_662_files):
            url = self.l_662_base + file
            print "url = %s" % url
            DAPloaders.runGliderLoader(url, self.campaignName, aName, 'l_662', self.colors['l_662'], 'glider', 'Glider Mission', 
                                        self.l_662_parms, self.dbAlias, stride, self.l_662_startDatetime, self.l_662_endDatetime)

    def loadM1ts(self, stride=None):
        '''
        Mooring M1ts specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.m1ts_files], self.m1ts_files):
            url = self.m1ts_base + file
            print "url = %s" % url
            DAPloaders.runMooringLoader(url, self.campaignName, aName, 'm1', self.colors['m1'], 'mooring', 'Mooring Deployment', 
                                        self.m1ts_parms, self.dbAlias, stride, self.m1ts_startDatetime, self.m1ts_endDatetime)

    def loadM1met(self, stride=None):
        '''
        Mooring M1met specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.m1met_files], self.m1met_files):
            url = self.m1met_base + file
            print "url = %s" % url
            DAPloaders.runMooringLoader(url, self.campaignName, aName, 'm1', self.colors['m1'], 'mooring', 'Mooring Deployment', 
                                        self.m1met_parms, self.dbAlias, stride, self.m1met_startDatetime, self.m1met_endDatetime)

    def loadHeHaPe(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.hehape_files], self.hehape_files):
            url = self.hehape_base + file
            print "url = %s" % url
            DAPloaders.runGliderLoader(url, self.campaignName, aName, 'hehape', self.colors['hehape'], 'glider', 'Glider Mission', 
                                        self.hehape_parms, self.dbAlias, stride)

    def loadRusalka(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.rusalka_files], self.rusalka_files):
            url = self.rusalka_base + file
            print "url = %s" % url
            DAPloaders.runGliderLoader(url, self.campaignName, aName, 'rusalka', self.colors['rusalka'], 'glider', 'Glider Mission', 
                                        self.rusalka_parms, self.dbAlias, stride)

    def loadCarmen(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.carmen_files], self.carmen_files):
            url = self.carmen_base + file
            print "url = %s" % url
            DAPloaders.runGliderLoader(url, self.campaignName, aName, 'carmen', self.colors['carmen'], 'glider', 'Glider Mission', 
                                        self.carmen_parms, self.dbAlias, stride)

    def loadWaveglider(self, stride=None):
        '''
        Glider specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.waveglider_files], self.waveglider_files):
            url = self.waveglider_base + file
            print "url = %s" % url
            DAPloaders.runGliderLoader(url, self.campaignName, aName, 'waveglider', self.colors['waveglider'], 'glider', 'Glider Mission', 
                                        self.waveglider_parms, self.dbAlias, stride, self.waveglider_startDatetime, self.waveglider_endDatetime)
    def loadESPdrift(self, stride=None):
        '''
        ESPdrift specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.espdrift_files], self.espdrift_files):
            url = self.espdrift_base + file
            print "url = %s" % url
            DAPloaders.runTrajectoryLoader(url, self.campaignName, aName, 'espdrift', self.colors['espdrift'], 'espdrift', 'ESP drift Mission', 
                                        self.espdrift_parms, self.dbAlias, stride)

    def loadESPmack(self, stride=None):
        '''
        ESPmack specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.espmack_files], self.espmack_files):
            url = self.espmack_base + file
            print "url = %s" % url
            DAPloaders.runTrajectoryLoader(url, self.campaignName, aName, 'espmack', self.colors['espmack'], 'espmack', 'ESP mack Mission', 
                                        self.espmack_parms, self.dbAlias, stride)

    def loadESPbruce(self, stride=None):
        '''
        ESPbruce specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.espbruce_files], self.espbruce_files):
            url = self.espbruce_base + file
            print "url = %s" % url
            DAPloaders.runTrajectoryLoader(url, self.campaignName, aName, 'espbruce', self.colors['espbruce'], 'espbruce', 'ESP bruce Mission', 
                                        self.espbruce_parms, self.dbAlias, stride)

    def loadWFuctd(self, stride=None, platformName='wf_uctd', activitytypeName='Western Flyer Underway CTD Data'):
        '''
        WF uctd specific load functions.  Override defaults for @platformName and activitytypeName if it's desired
        to consider uctd and pctd coming from the same platform.  You may want to do this to use the data 
        visualization capabilities in STOQS.
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.wfuctd_files], self.wfuctd_files):
            url = self.wfuctd_base + file
            print "url = %s" % url
            DAPloaders.runTrajectoryLoader(url, self.campaignName, aName, platformName, self.colors['flyer'], platformName, activitytypeName,
                                        self.wfuctd_parms, self.dbAlias, stride)

    def loadWFpctd(self, stride=None, platformName='wf_pctd', activitytypeName='Western Flyer Profile CTD Data'):
        '''
        WF pctd specific load functions. Override defaults for @platformName and activitytypeName if it's desired
        to consider uctd and pctd coming from the same platform.  You may want to do this to use the data 
        visualization capabilities in STOQS.
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a.split('.')[0] + ' (stride=%d)' % stride for a in self.wfpctd_files], self.wfpctd_files):
            url = self.wfpctd_base + file
            print "url = %s" % url
            DAPloaders.runTrajectoryLoader(url, self.campaignName, aName, platformName, self.colors['flyer'], platformName, activitytypeName, 
                                        self.wfpctd_parms, self.dbAlias, stride)
        # Now load all the bottles           
        sl = SeabirdLoader('activity name', platformName, dbAlias=self.dbAlias, campaignName=self.campaignName, platformColor=self.colors['flyer'])
        sl.tdsBase= self.tdsBase
        sl.pctdDir = self.pctdDir
        sl.process_btl_files()

    def loadRCuctd(self, stride=None):
        '''
        RC uctd specific load functions
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in self.rcuctd_files], self.rcuctd_files):
            url = self.rcuctd_base + file
            print "url = %s" % url
            DAPloaders.runTrajectoryLoader(url, self.campaignName, aName, 'rc_uctd', self.colors['carson'], 'rc_uctd', 'Rachel Carson Underway CTD Data', 
                                        self.rcuctd_parms, self.dbAlias, stride)

    def loadRCpctd(self, stride=None):
        '''
        RC pctd specific load functions
        '''
        stride = stride or self.stride
        platformName = 'rc_pctd'
        for (aName, file) in zip([ a.split('.')[0] + ' (stride=%d)' % stride for a in self.rcpctd_files], self.rcpctd_files):
            url = self.rcpctd_base + file
            print "url = %s" % url
            DAPloaders.runTrajectoryLoader(url, self.campaignName, aName, platformName, self.colors['carson'], platformName, 'Rachel Carson Profile CTD Data', 
                                        self.rcpctd_parms, self.dbAlias, stride)
        # load all the bottles           
        sl = SeabirdLoader(aName[:5], platformName, dbAlias=self.dbAlias, campaignName=self.campaignName, platformColor=self.colors['carson'], platformTypeName='ship')
        sl.tdsBase= self.tdsBase
        sl.pctdDir = self.pctdDir
        sl.process_btl_files()


    def loadAll(self, stride=None):
        '''
        Execute all the load functions
        '''
        stride = stride or self.stride
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

    def process_command_line(self):
        '''
        The argparse library is a requirement for STOQS.  Support original positional arguments of stride and dbAlias plus
        these kind of database loads:
            - Optimal stride
            - Test version
            - Uniform stride
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
    # Instance variable settings
    cl = CANONLoader('default', 'Test Load')
    cl.stride = 1000
    cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
    cl.dorado_files = ['Dorado389_2010_300_00_300_00_decim.nc']

    # Execute the load
    cl.process_command_line()

    cl.loadAll()


