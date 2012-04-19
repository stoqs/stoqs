#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Use DAPloaders.py to load full resolution Dorado and Tethys data from April 2011
into the stoqs_april2011 database.

Mike McCann
MBARI 3 February 2012

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
from GulperLoader import load_gulps
from datetime import datetime
from stoqs import models as mod

dbAlias = 'stoqs_april2011'
campaignName = 'CANON - April 2011'

def loadDorado(stride=1):
    '''
    load full resolution Dorado and Tethys data from April 2011 experiment into the stoqs_april2011 database
    '''

    # Specific locations of data to be loaded - ideally the only thing that needs to be changed for another campaign

    # ------------------------- Dorado loads -------------------------
    ##baseUrl = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2011/netcdf/'
    baseUrl = 'http://odss.mbari.org/thredds/dodsC/CANON_april2011/dorado/'             # NCML to make salinity.units = biolume.units = "1"
    files =      [  'Dorado389_2011_110_12_110_12_decim.nc',
            'Dorado389_2011_111_00_111_00_decim.nc',
            'Dorado389_2011_115_10_115_10_decim.nc',
            'Dorado389_2011_116_00_116_00_decim.nc',
            'Dorado389_2011_117_01_117_01_decim.nc',
            'Dorado389_2011_118_00_118_00_decim.nc'
            ]
    for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in files], files):
        url = baseUrl + file
        DAPloaders.runDoradoLoader(url, campaignName, aName, 'dorado', 'auv', 'AUV mission', dbAlias, stride)
        load_gulps(aName, file, dbAlias)


def loadTethys(stride=1):
    # ------------------------- Tethys loads -------------------------
    # The Hyrax server seems to deliver data from variables with '.' in the name from the DODS access form, but pydap throws an exception
    ##baseUrl = 'http://dods.mbari.org/opendap/data/lrauv/Tethys/missionlogs/2011/'
    # Must use the TDS server as is has the NCML which removes the variables with '.' in the name
    ##stride = 4
    baseUrl = 'http://elvis.shore.mbari.org:8080/thredds/dodsC/lrauv/tethys/2011/'
    files =      [  '20110415_20110418/20110415T163108/slate.nc',
            '20110415_20110418/20110416T074851/slate.nc',
            '20110415_20110418/20110417T064753/slate.nc',
            '20110415_20110418/20110418T060227/slate.nc',
            '20110415_20110418/20110418T192351/slate.nc',
            '20110421_20110424/20110421T170430/slate.nc',
            '20110421_20110424/20110422T001932/slate.nc',
            '20110421_20110424/20110423T223119/slate.nc',
            '20110421_20110424/20110424T214938/slate.nc',
            '20110426_20110502/20110426T171129/slate.nc',
            '20110426_20110502/20110427T191236/slate.nc',
            '20110426_20110502/20110429T222225/slate.nc',
            '20110426_20110502/20110430T132028/slate.nc',
            '20110426_20110502/20110502T040031/slate.nc'
            ]
    parmList = ['sea_water_temperature', 'sea_water_salinity', 'sea_water_density', 'volume_scattering_470_nm', 'volume_scattering_650_nm',
                'volume_scattering_650_nm', 'mass_concentration_of_oxygen_in_sea_water', 'mole_concentration_of_nitrate_in_sea_water',
                'mass_concentration_of_chlorophyll_in_sea_water']
    for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in files], files):
        url = baseUrl + file
        DAPloaders.runLrauvLoader(url, campaignName, aName, 'tethys', 'auv', 'AUV mission', parmList, dbAlias, stride)


def loadAll(stride=1):
    '''
    Load all the data for this campaign
    '''
    loadDorado(stride)
    loadTethys(stride)
    ##loadMartin(stride)

if __name__ == '__main__':
    '''
    Load this campaign.  Can be called from an outside script to load multiple campaigns with:
        import loadCANON_april2011
        loadCANON_april2011.loadAll()
    '''
    stride = 1
    loadAll(stride)

