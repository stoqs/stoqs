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
import re

import DAPloaders
from SampleLoaders import SeabirdLoader, load_gulps, SubSamplesLoader 
from loaders import LoadScript
import logging
import colorsys

logger = logging.getLogger('__main__')

def getStrideText(stride):
    '''
    Format stride into a string to be appended to the Activity name, if stride==1 return empty string
    '''
    if stride == 1:
        return ''
    else:
        return ' (stride=%d)' % stride


class OSLoader(LoadScript):
    '''
    Common routines for loading all CANON data
    '''
    def getColor(self, numColors):
        '''Rotate through numCOlors hues to return a next rgb color value
        '''
        for hue in range(numColors):
            hue = 1. * hue / numColors
            col = [int(x) for x in colorsys.hsv_to_rgb(hue, 1.0, 230)]
            yield "{0:02x}{1:02x}{2:02x}".format(*col)

    def load_mooring(self, stride=None):
        '''Mooring load function. 
        '''
        stride = stride or self.stride
        for (aName, file) in zip([ a + getStrideText(stride) for a in self.glider_ctd_files], self.glider_ctd_files):
            url = self.glider_ctd_base + file
            pName = aName.split('/')[-1].split('.')[0]
            p = re.compile('-\d+T\d+_Time')
            pName = p.sub('', pName)
            if pName.find('-') != -1:
                logger.warn("Replacing '-' characters in platform name %s with '_'s", pName)
                pName = pName.replace('-', '_')

            pColor = self.getColor(32)
            logger.info("Executing runMooringLoader with url = %s", url)
            DAPloaders.runMooringLoader(url, self.campaignName, aName, pName, pColor, 'mooring', 'Mooring Deployment', 
                                        self.glider_ctd_parms, self.dbAlias, stride, self.glider_ctd_startDatetime, self.glider_ctd_endDatetime)


if __name__ == '__main__':
    '''Test operation of this class
    '''
    osl = OSLoader('default', 'Test Load')
    osl.stride = 1000
    osl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
    osl.dorado_files = ['Dorado389_2010_300_00_300_00_decim.nc']

    # Execute the load
    osl.process_command_line()

    osl.load_mooring()



