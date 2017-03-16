#!/usr/bin/env python
'''
Use DAPloaders.py to load full resolution AUV and shipboard CTD (Castaway) 
data from the Mar Menor AUV Experiment - November 2011 into the stoqs_nov2011
database.

Mike McCann
MBARI 9 November 2011
'''

import os
import sys
from . import DAPloaders

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

def loadMissions(baseUrl, fileList, activityName, campaignName, pName, pColor, pTypeName, aTypeName, parmList, dbName, stride = 1):
    '''Load missions from OPeNDAP url from either a list of files from a base or a single URL with a given activityName '''
    c_desc = 'Mar Menor In Situ (AUV and Castaway) data loads'
    if fileList: 
        for (aName, f) in zip([ a + ' (stride=%d)' % stride for a in files], fileList):
            url = baseUrl + f
            print(("loadMissions(): Calling runLoader() with parmList = %s" % parmList))
            DAPloaders.runTrajectoryLoader(url, campaignName, c_desc, aName, pName, pColor, pTypeName, aTypeName, parmList, dbName, stride)
    elif activityName:
        url = baseUrl
        DAPloaders.runTrajectoryLoader(url, campaignName, c_desc, activityName, pName, pColor, pTypeName, aTypeName, parmList, dbName, stride)
    else:
        print("loadMissions(): Must specify either a fileList or an activityName")


if __name__ == '__main__':

    # Specific locations of data to be loaded - ideally the only thing that needs to be changed for another campaign
    dbName = 'stoqs_marmenor_nov2011'
    campaignName = 'Mar Menor - November 2011'

    # Sparus, e.g.: http://odss.mbari.org:8080/thredds/dodsC/marmenor/insitu/UniversityOfGirona/exp4_5Nov2011_data.nc.html
    baseUrl = 'http://odss.mbari.org:8080/thredds/dodsC/marmenor/insitu/'
    files =      [  'UniversityOfGirona/exp1_3Nov2011_data.nc',
            'UniversityOfGirona/exp2_3Nov2011_data.nc',
            'UniversityOfGirona/exp3_5Nov2011_data.nc',
            'UniversityOfGirona/exp4_5Nov2011_data.nc',
            ]
    parms = ['temperature', 'conductivity']
    loadMissions(baseUrl, files, '', campaignName, 'sparus', 'ff00ff', 'auv', 'AUV Mission', parms, dbName)

    # University of Villanova
    baseUrl = 'http://odss.mbari.org:8080/thredds/dodsC/marmenor/insitu/'
    files =      [  'UniversityOfVillanova/GuanayII_2011-11-3_Salinity_v2.nc',
            'UniversityOfVillanova/GuanayII-4nov.nc',
            ]
    parms = ['temperature', 'conductivity', 'salinity']
    loadMissions(baseUrl, files, '', campaignName, 'guanayii', 'ffff00', 'auv', 'AUV Mission', parms, dbName)

    # University of Porto
    baseUrl = 'http://odss.mbari.org:8080/thredds/dodsC/marmenor/insitu/'
    files =      [  'UniversityOfPorto/092152_quad_1m.nc',
            'UniversityOfPorto/085825_rect_6_8.nc',
            'UniversityOfPorto/085422_quad_surface.nc',
            'UniversityOfPorto/083743_rect_1m.nc',
            'UniversityOfPorto/081952_quad_100m_superficie.nc',
            ]
    parms = ['temperature', 'conductivity', 'salinity']
    loadMissions(baseUrl, files, '', campaignName, 'seacon-2', '0f0f0f', 'auv', 'AUV Mission', parms, dbName)

    # Castaway: http://odss.mbari.org:8080/thredds/dodsC/agg/Castaway.html
    baseUrl = 'http://odss.mbari.org:8080/thredds/dodsC/agg/Castaway'
    aName = 'All Castaway CTD casts done from the Sorell on 5 November 2011'
    parms = ['temperature', 'conductivity', 'salinity']
    loadMissions(baseUrl, '', aName, campaignName, 'Castaway', 'ff0000', 'ship', 'CTD Casts', parms, dbName)

