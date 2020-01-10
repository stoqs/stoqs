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

# Insert Django App directory (parent of config) into python path
sys.path.insert(0, os.path.abspath(os.path.join(
                os.path.dirname(__file__), "../../")))
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
import django
django.setup()

import re
import DAPloaders
from SampleLoaders import SeabirdLoader, load_gulps, SubSamplesLoader 
from loaders import LoadScript
import logging

logger = logging.getLogger('__main__')

def getStrideText(stride):
    '''
    Format stride into a string to be appended to the Activity name, if stride==1 return empty string
    '''
    if stride == 1:
        return ''
    else:
        return ' (stride=%d)' % stride


class IOOSLoader(LoadScript):
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
                'nps29':        '0b9131',
                'nps34':        '36d40f',
                'm1':           'bd2026',
                'oa':           '0f9cd4',
                'oa2':          '2d2426',
                'hehape':       'bd2026',
                'rusalka':      'bd4026',
                'carmen':       'bd8026',
                'martin':       '800026',
                'flyer':        '801026',
                'carson':       '730a46',
                'espdrift':     '802026',
                'espmack':      '804026',
                'espbruce':     '808026',
                'Stella201':    '26f080',
                'Stella202':    'F02696',
                'Stella203':    'F08026',
                'Stella204':    'AAAA26',
                'stella203':    'F08026',
                'stella204':    'AAAA26',
                'Stella205':    '2696f0',
                'nemesis':      'FFF026',
                'ucsc294':      'FFBA26',
                'slocum_294':   'FFBA26',
                'slocum_nemesis':'FFF026',
                'ucsc260':      'FF8426',
                'slocum_260':   'FF8426',
                'wg_oa':        '0f9cd4',
                'wg_tex':       '9626ff',
             }


    def load_glider_ctd(self, stride=None):
        '''
        Glider load functions.  Requires apriori knowledge of glider file names so we can extract platform and color name
        To be used with gliders that follow the same naming convention, i.e. nemesis_ctd.nc, ucsc260_ctd.nc
        and that load the exact same parameters, i.e. TEMP, PSAL or TEMP, PSAL, FLU2 or TEMP, FLU2, OPBS etc
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

            logger.info("Executing runGliderLoader with url = %s", url)
            DAPloaders.runGliderLoader(url, self.campaignName, aName, pName, 'FFBA26', 'glider', 'Glider Mission', 
                                        self.glider_ctd_parms, self.dbAlias, stride, self.glider_ctd_startDatetime, self.glider_ctd_endDatetime)


if __name__ == '__main__':
    '''
    Test operation of this class
    '''
    il = IOOSLoader('default', 'Test Load')
    il.stride = 1000
    il.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
    il.dorado_files = ['Dorado389_2010_300_00_300_00_decim.nc']

    # Execute the load
    il.process_command_line()

    il.load_glider_ctd()



