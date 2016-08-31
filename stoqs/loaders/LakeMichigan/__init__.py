#!/usr/bin/env python

__author__    = 'Danelle Cline'
__copyright__ = '2016'
__license__   = 'GPL v3'
__contact__   = 'dcline at mbari.org'

'''
Contains class for common routines for loading all LakeMichigan data

Danelle Cline
MBARI 21 July 2016

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

try:
    import django
    django.setup()
except AttributeError:
    pass

import DAPloaders
from loaders import LoadScript
from stoqs.models import InstantPoint
from django.db.models import Max
from datetime import timedelta
from argparse import Namespace
import logging


def getStrideText(stride):
    '''
    Format stride into a string to be appended to the Activity name, if stride==1 return empty string
    '''
    if stride == 1:
        return ''
    else:
        return ' (stride=%d)' % stride


class LakeMILoader(LoadScript):
    '''
    Common routines for loading all LakeMI data
    '''
    brownish = {'tethys':       'bf812d',
                }
    colors = {
                'tethys':       'fed976',
             }


    def loadTethys(self, stride=None):
        '''
        Tethys specific load functions
        '''
        pName = 'tethys'
        stride = stride or self.stride
        for (aName, f) in zip([ a + getStrideText(stride) for a in self.tethys_files], self.tethys_files):
            url = self.tethys_base + f
            dataStartDatetime = None
            startDatetime = self.tethys_startDatetime
            endDatetime = self.tethys_endDatetime

            try:
                DAPloaders.runLrauvLoader(url, self.campaignName, self.campaignDescription, aName,
                                          pName, self.colors['tethys'], 'auv', 'AUV mission',
                                          self.tethys_parms, self.dbAlias, stride,
                                          grdTerrain=self.grdTerrain, command_line_args=self.args, 
                                          endDatetime=endDatetime, startDatetime=startDatetime, timezone='America/New_York')
            except DAPloaders.NoValidData:
                self.logger.info("No valid data in %s" % url)

        self.addPlatformResources('http://stoqs.mbari.org/x3d/lrauv/lrauv_tethys.x3d', pName)


    def loadAll(self, stride=None):
        '''
        Execute all the load functions
        '''
        stride = stride or self.stride
        loaders = [ 'loadTethys']
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
    # Instance variable settings
    cl = LakeMILoader('default', 'Test Load')
    cl.stride = 1000
    cl.lrauv_base = 'http://dods.mbari.org/opendap/data/lrauv/tethys/missionlogs/2015/20150908_20150916/20150910T025658/'
    cl.lrauv_files = ['201509100257_201509101400_10S_sci.nc']

    # Execute the load
    cl.process_command_line()

    cl.loadAll()

