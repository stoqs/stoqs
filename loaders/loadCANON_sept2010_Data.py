#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Use DAPloaders.py to load full resolution Dorado and ESP data from September 2010
drifter following experiment into the stoqs_sept2010 database.

Mike McCann
MBARI 29 June 2011

@var __date__: Date of last svn commit
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

dbAlias = 'stoqs_sept2010'
campaignName = 'ESP Drifter Tracking - September 2010'

def loadMissions(baseUrl, fileList, activityName, campaignName, pName, pTypeName, aTypeName, dbAlias, stride = 1):
    '''Load missions from OPeNDAP url from either a list of files from a base or a single URL with a given activityName '''

    if fileList: 
        for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in fileList], fileList):
            url = baseUrl + file
            DAPloaders.runDoradoLoader(url, campaignName, aName, pName, pTypeName, aTypeName, dbAlias, stride)
    elif activityName:
        url = baseUrl
        DAPloaders.runCSVLoader(url, campaignName, activityName, pName, pTypeName, aTypeName, dbAlias, stride)
    else:
        print "loadMissions(): Must specify either a fileList or an activityName"

def loadDorado(stride=1):
    '''
    List of Dorado surveys for September 2010 ESP drifter experiment 
    '''
    # Specific locations of data to be loaded - ideally the only thing that needs to be changed for another campaign


    # ------------------------- Dorado loads -------------------------
    ##baseUrl = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
    baseUrl = 'http://odss.mbari.org/thredds/dodsC/CANON_sept2010/dorado/'                         # NCML to make salinity.units = biolume.units = "1"
    files =      [  'Dorado389_2010_257_01_258_04_decim.nc',
            'Dorado389_2010_258_05_258_08_decim.nc',
            'Dorado389_2010_259_00_259_03_decim.nc',
            'Dorado389_2010_260_00_260_00_decim.nc',
            'Dorado389_2010_261_00_261_00_decim.nc'
            ]
    loadMissions(baseUrl, files, '', campaignName, 'dorado', 'auv', 'AUV Mission', dbAlias, stride)

def loadAll(stride=1):
    '''
    Load all the data for this campaign
    '''
    loadDorado(stride)

if __name__ == '__main__':
    '''
    Load this campaign.  Can be called from an outside script to load multiple campaigns with:
        import loadCANON_sept2010
        loadCANON_sept2010.loadAll()
    '''
    stride = 1000
    loadAll(stride)
