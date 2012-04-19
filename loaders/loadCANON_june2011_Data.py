#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Use DAPloaders.py to load full resolution Dorado and Tethys data from June 2011
into the stoqs_june2011 database.

Mike McCann
MBARI 2 April 2012

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
from datetime import datetime
from stoqs import models as mod
from GulperLoader import load_gulps

dbAlias = 'stoqs_june2011'
campaignName = 'CANON - June 2011'

def loadDorado(stride=1):
    '''
    load full resolution Dorado and Tethys data from June 2011 experiment into the stoqs_june2011 database
    '''

    # Specific locations of data to be loaded - ideally the only thing that needs to be changed for another campaign

    # ------------------------- Dorado loads -------------------------
    baseUrl = 'http://odss.mbari.org/thredds/dodsC/CANON_june2011/dorado/'             # NCML to make salinity.units = biolume.units = "1"
    files = [   'Dorado389_2011_164_05_164_05_decim.nc',
                'Dorado389_2011_165_00_165_00_decim.nc',
                'Dorado389_2011_166_00_166_00_decim.nc',
                'Dorado389_2011_171_01_171_01_decim.nc',
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
    files = [ 
                '20110610_20110616/20110610T212639/slate.nc',
                '20110610_20110616/20110611T232740/slate.nc',
                '20110610_20110616/20110612T191007/slate.nc',
                '20110610_20110616/20110613T001706/slate.nc',
                '20110610_20110616/20110613T053217/slate.nc',
                '20110610_20110616/20110614T093150/slate.nc',
                '20110610_20110616/20110614T201835/slate.nc',
                '20110610_20110616/20110615T030544/slate.nc',
                '20110610_20110616/20110616T000907/slate.nc',
                '20110618_20110623/20110618T211745/slate.nc',
                '20110618_20110623/20110619T231706/slate.nc',
                '20110618_20110623/20110620T143623/slate.nc',
                '20110618_20110623/20110620T190006/slate.nc',
                '20110618_20110623/20110621T185433/slate.nc'
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
        import loadCANON_june2011
        loadCANON_june2011.loadAll()
    '''
    stride = 100
    loadAll(stride)

