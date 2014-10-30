#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2014, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

The ROVCTDloader module contains classes for reading data from MBARI's internal
rovtcd web service which returns data by ROV name and dive number from the EXPD
database which holds data from all of MBARI's ROV dives staring in 1989. The data
are read from this service and then loaded into STOQS database(s).

Mike McCann
MBARI 24 October 2014

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

# Force lookup of models to THE specific stoqs module.
import os
import sys
from django.contrib.gis.geos import GEOSGeometry, LineString, Point
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # settings.py is one dir up
from django.conf import settings

from django.db.utils import IntegrityError, DatabaseError
from django.db import connection, transaction
from stoqs import models as m
from datetime import datetime, timedelta
from django.core.exceptions import ObjectDoesNotExist
from pydap.client import open_url
import pydap.model
import time
from decimal import Decimal
import math, numpy
from coards import to_udunits, from_udunits, ParserError
import csv
import urllib2
import logging
import socket
import seawater.csiro as sw
from utils.utils import percentile, median, mode, simplify_points
from loaders import STOQS_Loader, SkipRecord, missing_value, MEASUREDINSITU, FileNotFound
from loaders.DAPloaders import Base_Loader
import numpy as np
from collections import defaultdict


# Set up logging
logger = logging.getLogger('__main__')
logger.setLevel(logging.INFO)

class ROVCTD_Loader(Base_Loader):
    '''
    Loader for ROVCTTD data.  Use all of the well-tested methods used in DAPloaders.py; add
    our own generator for rows of data from the web service for rovtcd data.
    '''
    include_names = ['p', 't', 's', 'o2', 'o2alt', 'light', 'beac', 'analog1', 'analog2', 'analog3', 'analog4']
    vDict = {   'p': 'p',
                't': 't',
                's': 's',
                'o2': 'o2',
                'o2alt': 'o2alt',
                'light': 'light',
                'beac': 'beac',
                'analog1': 'analog1',
                'analog2': 'analog2',
                'analog3': 'analog3',
                'analog4': 'analog4',
                'ptsflag': 'ptsflag',
                'o2flag': 'o2flag',
                'o2altflag': 'o2altflag',
                'lightflag': 'lightflag',
                'latlonflag': 'latlonflag',
            }

    def __init__(self, activityName, platformName, diveNumber, dbAlias='default', campaignName=None, campaignDescription=None,
                activitytypeName=None, platformColor=None, platformTypeName=None,
                startDatetime=None, endDatetime=None, dataStartDatetime=None, auxCoords=None, stride=1,
                grdTerrain=None ):
        '''
        Given an ROV name (platformName) and a diveNumber retrieve the data and load into a STOQS database.  This is quite similar
        to DAPloaders Base_Loader, but different enough to warrant its own implementation - mainly replacing the url argument with
        a diveNumber argument.
        
        @param activityName: A string describing this activity
        @param platformName: A string that is the name of the platform. If that name for a Platform exists in the DB, it will be used.
        @param platformColor: An RGB hex string represnting the color of the platform. 
        @param diveNumber: The dive number from the Expedition database
        @param dbAlias: The name of the database alias as defined in settings.py
        @param campaignName: A string describing the Campaign in which this activity belongs, If that name for a Campaign exists in the DB, it will be used.
        @param campaignDescription: A string expanding on the campaignName. It should be a short phrase expressing the where and why of a campaign.
        @param activitytypeName: A string such as 'mooring deployment' or 'AUV mission' describing type of activity, If that name for a ActivityType exists in the DB, it will be used.
        @param platformTypeName: A string describing the type of platform, e.g.: 'mooring', 'auv'.  If that name for a PlatformType exists in the DB, it will be used.
        @param startDatetime: A Python datetime.dateime object specifying the start date time of data to load
        @param endDatetime: A Python datetime.dateime object specifying the end date time of data to load
        @param dataStartDatetime: A Python datetime.dateime object specifying the start date time of data to append to an existing Activity
        @param auxCoords: a dictionary of coordinate standard_names (time, latitude, longitude, depth) pointing to exact names of those coordinates. Used for variables missing the coordinates attribute.
        @param stride: The stride/step size used to retrieve data from the constructed url.

        '''

        self.platformName = platformName
        self.diveNumber = diveNumber
        self.campaignName = campaignName
        self.campaignDescription = campaignDescription
        self.activitytypeName = activitytypeName
        self.platformColor = platformColor
        self.dbAlias = dbAlias
        global_dbAlias = dbAlias
        self.platformTypeName = platformTypeName
        self.activityName = activityName
        self.startDatetime = startDatetime
        self.endDatetime = endDatetime
        self.dataStartDatetime = dataStartDatetime  # For when we append data to an existing Activity
        self.auxCoords = auxCoords
        self.stride = stride
        self.grdTerrain = grdTerrain

    def makeParmDict(self):
        '''Make a pydap-type parameter dictionary for passing into self.addParameters()
        '''
        p = pydap.model.BaseType()
        p.attributes = {    'standard_name':    'sea_water_pressure',
                            'long_name':        'Pressure',
                            'units':            'decibars',
                            'name':             'PRES',
                       }

        t = pydap.model.BaseType()
        t.attributes = {    'standard_name':    'sea_water_temperature',
                            'long_name':        'Temperature',
                            'units':            'Celsius',
                            'name':             'TEMP',
                       }

        s = pydap.model.BaseType()
        s.attributes = {    'standard_name':    'sea_water_salinity',
                            'long_name':        'Salinity',
                            'name':             'PSAL',
                       }

        o2 = pydap.model.BaseType()
        o2.attributes = { 
                            'long_name':        'Oxygen',
                            'units':            'ml/l',
                            'name':             'DOXY',
                       }

        o2alt = pydap.model.BaseType()
        o2alt.attributes = { 
                            'long_name':        'Oxygen',
                            'units':            'ml/l',
                            'name':             'DOXYALT',
                       }

        light = pydap.model.BaseType()
        light.attributes = { 
                            'long_name':        'Transmissometer',
                            'units':            '%',
                            'name':             'LIGHT',
                       }

        beac = pydap.model.BaseType()
        beac.attributes = { 
                            'long_name':        'transmissometer beam attenuation coeff',
                            'name':             'BEAMC',
                       }

        analog1 = pydap.model.BaseType()
        analog1.attributes = { 
                            'long_name':        'A/D channel 1',
                            'units':            'volts',
                       }

        analog2 = pydap.model.BaseType()
        analog2.attributes = { 
                            'long_name':        'A/D channel 2',
                            'units':            'volts',
                       }

        analog3 = pydap.model.BaseType()
        analog3.attributes = { 
                            'long_name':        'A/D channel 3',
                            'units':            'volts',
                       }

        analog4 = pydap.model.BaseType()
        analog4.attributes = { 
                            'long_name':        'A/D channel 4',
                            'units':            'volts',
                       }

        self.parmDict = {   'p': p,
                            't': t,
                            's': s,
                            'o2': o2,
                            'o2alt': o2alt,
                            'light': light,
                            'beac': beac,
                            'analog1': analog1,
                            'analog2': analog2,
                            'analog3': analog3,
                            'analog4': analog4,
                        }

    def _getStartAndEndTimeFromInfoServlet(self):
        '''Looks like:
        http://coredata.shore.mbari.org/rovctd/diveinfo/rovdiveinfoservlet?platform=docr&dive=671
        expdid,diveid,shipname,rovname,divenumber,divestartdtg,diveenddtg,chiefscientist,maxpressure,ctdpcount,minshiplat,maxshiplat,minshiplon,maxshiplon,avgshiplat,avgshiplon
        5119,6029,wfly,docr,671,2014-10-12T15:16:14Z,2014-10-13T01:38:47Z,Ken Smith,4033.09,2491,35.133035,35.142912,-122.98278,-122.978173,35.13703829,-122.98072495
        '''

        url = 'http://coredata.shore.mbari.org/rovctd/diveinfo/rovdiveinfoservlet?platform=%s&dive=%d' % (self.platformName, self.diveNumber)
        
        for r in csv.DictReader(urllib2.urlopen(url)):
            sdt = datetime.strptime(r['divestartdtg'], '%Y-%m-%dT%H:%M:%SZ')
            edt = datetime.strptime(r['diveenddtg'], '%Y-%m-%dT%H:%M:%SZ')
            start = time.mktime(sdt.timetuple())
            end = time.mktime(edt.timetuple())

        return sdt, edt

    def initDB(self):
        '''
        '''
        # Create Platform and add Parameters
        self.platform = self.getPlatform(self.platformName, self.platformTypeName)
        self.makeParmDict()
        self.addParameters(self.parmDict)

        # Ensure that startDatetime and startDatetime are defined as they are required fields of Activity
        if not self.startDatetime or not self.endDatetime:
            self.startDatetime, self.endDatetime = self._getStartAndEndTimeFromInfoServlet()
            self.createActivity()

    def _genROVCTD(self):
        '''
        Generator of ROVCTD trajectory data. The data values are a function of time and position as returned
        by the web service. Yield a row for each measurement along with the spatial/temporal coordinates of
        that measurement.
        Example URL to get data: 
        http://coredata.shore.mbari.org/rovctd/data/rovctddataservlet?platform=docr&dive=671&&domain=epochsecs&r1=p&r2=t&r3=s&r4=o2sbeml&r5=light&r6=beac
        '''

        self.url = 'http://coredata.shore.mbari.org/rovctd/data/rovctddataservlet?'
        self.url += 'platform=%s&dive=%d&domain=epochsecs' % (self.platformName, self.diveNumber)
        for i,v in enumerate(['elon', 'elat', 'd', 'rlon', 'rlat'] + self.vDict.keys()):
            self.url += '&r%d=%s' % (i + 1, v)

        logger.info(self.url)
        self.vSeen = defaultdict(lambda: 0)

        # Read entire response to fill a dictionary so that we can yield by Parameter rather than by Measurement - as process_data expects
        valuesByParm = defaultdict(lambda: [])
        for r in csv.DictReader(urllib2.urlopen(self.url)):
            for v in self.vDict.keys():
                values = {}
                if v not in self.include_names:
                    continue
                try:
                    values[self.vDict[v]] = float(r[v])
                except ValueError:
                    continue
                values['time'] = float(r['epochsecs'])
                try:
                    values['depth'] = float(r['d'])
                except ValueError:
                    continue
                try:
                    values['latitude'] = float(r['elat'])
                except ValueError:
                    values['latitude'] = float(r['rlat'])
                try:
                    values['longitude'] = float(r['elon'])
                except ValueError:
                    values['longitude'] = float(r['rlon'])
                values['timeUnits'] = 'seconds since 1970-01-01 00:00:00'

                valuesByParm[v].append(values)
                self.vSeen[v] += 1

        # Now yield the rows the same as is done in DAPloaders.py
        for p,d in valuesByParm.iteritems():
            for values in d:
                yield values

    def addResources(self):
        '''
        Add Resources for this activity, namely standard links provided in the 
        Expedition Database.
        '''
        pass


#
# Helper methods that expose a common interface for executing the loaders for specific platforms
#
def runROVCTDLoader(dNumber, cName, cDesc, aName, pName, pColor, pTypeName, aTypeName, parmList, dbAlias, stride, grdTerrain=None):
    '''
    Run the DAPloader for Dorado AUVCTD trajectory data and update the Activity with 
    attributes resulting from the load into dbAlias. Designed to be called from script
    that loads the data.  Following the load important updates are made to the database.
    '''
    logger.debug("Instantiating ROVCTD_Loader for %s%d" % (pName, dNumber))
    loader = ROVCTD_Loader(
            diveNumber = dNumber,
            campaignName = cName,
            campaignDescription = cDesc,
            dbAlias = dbAlias,
            activityName = aName,
            activitytypeName = aTypeName,
            platformName = pName,
            platformColor = pColor,
            platformTypeName = pTypeName,
            stride = stride,
            grdTerrain = grdTerrain)

    if parmList:
        logger.debug("Setting include_names to %s", parmList)
        loader.include_names = parmList

    (nMP, path, parmCountHash, mind, maxd) = loader.process_data(loader._genROVCTD, 'trajectory')


if __name__ == '__main__':
    
    stride = 1
    dbAlias = 'stoqs_rovctd_t'

    # OLD Service:
    # http://mww.mbari.org/expd/queries/rovctd-data.asp?date_type=dive&return_type=comma&pltfrm=docr&dive=671
    # usec,rovCtdDtg,rovCtdDtgFlag,vehicle,depth,depthFlag,temper,temperFlag,salin,salinFlag,oxyg,oxygFlag,light,lightFlag,sound,soundFlag,sigmatheta,sigmathetaFlag,lat,latFlag,lon,lonFlag
    # 1413126975,10/12/2014 15:16:15,2,docr,3.57,0,18.438,0,33.154,0,4.901,0,78.07,2,1515.018,0,23.7525,0,36.417282,2,-122.298445,2
    # 1413126990,10/12/2014 15:16:30,2,docr,6.45,2,18.414,2,33.15,2,5.333,2,87.08,2,1514.992,2,23.7555,2,36.417282,2,-122.298445,2

    # NEW Service:
    # http://coredata.shore.mbari.org/rovctd/data/rovctddataservlet?platform=docr&dive=671&&domain=epochsecs&r1=p&r2=t&r3=s&r4=o2sbeml&r5=light&r6=beac
    # epochsecs,p,t,s,o2sbeml,light,beac
    # 1413126975,3.6,18.438,33.154,4.901,78.07,0.9903
    # 1413126990,6.5,18.414,33.15,5.333,87.08,0.5534

    #runROVCTDLoader(1236, 'ROVCTD', 'Tesing ROVCTD Loader', 'vnta1236', 'vnta', 'ff0000', 'rov', 'ROV Dive', [], dbAlias, stride)
    runROVCTDLoader(1247, 'ROVCTD', 'Tesing ROVCTD Loader', 'vnta1236', 'vnta', 'ff0000', 'rov', 'ROV Dive', [], dbAlias, stride)


