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

import os
import sys

# Insert Django App directory (parent of config) into python path 
sys.path.insert(0, os.path.abspath(os.path.join(
                    os.path.dirname(__file__), "../../")))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.local'
os.environ['DJANGO_CONFIGURATION'] = 'Local'

# Must install config and setup Django before importing models
from configurations import importer
importer.install()
# django >=1.7
try:
    import django
    django.setup()
except AttributeError:
    pass

from django.contrib.gis.geos import GEOSGeometry, LineString, Point
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
import seawater.eos80 as sw
from utils.utils import percentile, median, mode, simplify_points
from loaders import STOQS_Loader, LoadScript, SkipRecord, missing_value, MEASUREDINSITU, FileNotFound
from loaders.DAPloaders import Base_Loader
import numpy as np
from collections import defaultdict
import pymssql


# Set up logging
logger = logging.getLogger('__main__')
logger.setLevel(logging.INFO)

rovColors = {   'vnta': 'ff0000',
                'tibr': 'ffff00',
                'docr': 'ff00ff',
            }

class DiveInfoServletException(Exception):
    pass


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
                grdTerrain=None, args=None):
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
        if stride > 1:
            self.activityName = activityName + '(stride=%d)' %stride
        else:
            self.activityName = activityName
        self.startDatetime = startDatetime
        self.endDatetime = endDatetime
        self.dataStartDatetime = dataStartDatetime  # For when we append data to an existing Activity
        self.auxCoords = auxCoords
        self.stride = stride
        self.grdTerrain = grdTerrain
        self.args = args

        self.conn = pymssql.connect(host='solstice.shore.mbari.org:1433', user='everyone', password='guest', database='expd', as_dict=True)
        if self.platformName == 'vnta':
            self.rovDataView = 'VentanaRovCtdBinData'
        elif self.platformName == 'tibr':
            self.rovDataView = 'TiburonRovCtdBinData'
        elif self.platformName == 'docr':
            self.rovDataView = 'DocRickettsRovCtdBinData'

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
                            'units':            '',
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

    def _nodeServletStartAndEndTimes(self):
        '''Looks like:
        http://coredata.shore.mbari.org/rovctd/diveinfo/rovdiveinfoservlet?platform=docr&dive=671
        expdid,diveid,shipname,rovname,divenumber,divestartdtg,diveenddtg,chiefscientist,maxpressure,ctdpcount,minshiplat,maxshiplat,minshiplon,maxshiplon,avgshiplat,avgshiplon
        5119,6029,wfly,docr,671,2014-10-12T15:16:14Z,2014-10-13T01:38:47Z,Ken Smith,4033.09,2491,35.133035,35.142912,-122.98278,-122.978173,35.13703829,-122.98072495
        '''

        url = 'http://coredata.shore.mbari.org/rovctd/diveinfo/rovdiveinfoservlet?platform=%s&dive=%d' % (self.platformName, self.diveNumber)
        ##url = 'http://134.89.10.17:8081/rovdiveinfoservlet?platform=%s&dive=%d' % (self.platformName, self.diveNumber)
        
        for r in csv.DictReader(urllib2.urlopen(url)):
            sdt = datetime.strptime(r['divestartdtg'], '%Y-%m-%dT%H:%M:%SZ')
            edt = datetime.strptime(r['diveenddtg'], '%Y-%m-%dT%H:%M:%SZ')
            start = time.mktime(sdt.timetuple())
            end = time.mktime(edt.timetuple())
   
        try: 
            return sdt, edt
        except UnboundLocalError:
            raise DiveInfoServletException('Cannot get start and end time using %s' % url)

    def _pymssqlStartAndEndTimes(self):
        '''Returns start and end Python datetimes for the dive
        '''
        sql = '''SELECT expdid, diveid, shipname, rovname, divenumber,
 dbo.iso8601Format(divestartdtg) as divestartdtg,
 dbo.iso8601Format(diveenddtg) as diveenddtg,
 chiefscientist, maxpressure, ctdpcount,
 minshiplat,maxshiplat,minshiplon,maxshiplon,avgshiplat,avgshiplon
FROM divesummary
WHERE rovname = '%s'
 AND DiveNumber = %d
ORDER BY divenumber''' % (self.platformName, self.diveNumber)

        cur = self.conn.cursor()
        cur.execute(sql)
        r = cur.fetchone()
        try:
            sdt = datetime.strptime(r['divestartdtg'].strip(), '%Y-%m-%dT%H:%M:%SZ')
            edt = datetime.strptime(r['diveenddtg'].strip(), '%Y-%m-%dT%H:%M:%SZ')
        except TypeError:
            raise DiveInfoServletException('Cannot get start and end times for %s%d' % (self.platformName[0].upper(), self.diveNumber))

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
            if self.args.useNode:
                self.startDatetime, self.endDatetime = self._nodeServletStartAndEndTimes()
            else:
                self.startDatetime, self.endDatetime = self._pymssqlStartAndEndTimes()
            self.createActivity()

    def getTotalRecords(self):
        '''Return number of rows from that the servlet returns for this dive - overriding method in base class
        '''
        return self.count

    def inBBOX(self, lon, lat):
        '''Return True if point is in bbox or if bbox not specified on command line
        '''
        if self.args.bbox:
            bb = [float(e) for e in self.args.bbox]
            if lon > bb[0] and lon < bb[2] and lat > bb[1] and lat < bb[3]:
                return True
            else:
                return False
        else:
            return True

    def _nodeServletLines(self):
        '''Assigns line-feed terminated rows of data suitable for DictReader and returns list of dictionaries
        '''

        self.lines = ''
        try:
            logger.info('Reading lines from %s', self.url)
            response = urllib2.urlopen(self.url)
            self.lines = response.read().replace('\r', '')
        except KeyboardInterrupt as e:
            logger.error('Interrupted when trying to read lines from %s', self.url)
            import pdb
            pdb.set_trace()
            logger.error('lines = \n%s', self.lines)
            logger.exception(e)
            sys.exit(-1)
        except Exception as e:
            logger.error('Failed on urlopen() from %s', self.url)
            logger.error('Data received: lines = \n%s', self.lines)
            logger.exception(e)

        return csv.DictReader(self.lines.split('\n'))

    def _pymssqlLines(self):
        '''Performs direct SQL query to return records of data dictionaries, just like _nodeServletLines()
        '''
        sql = '''SELECT epochsecs,elon,elat,dbo.Depth(p,rlat) as d,rlon,rlat,ptsflag,o2flag,lightflag,light,analog2,p,s,o2altflag,t,latlonflag,o2alt as o2alt,analog4,analog3,o2 as o2,analog1,dbo.BeamAttn(light,0.25) as beac
FROM %(rovDataView)s, Dive
WHERE epochsecs is not null
 AND dive.rovname = '%(rov)s'
 AND dive.DiveNumber = %(diveNumber)d
 AND DatetimeGMT between dive.divestartdtg and dive.diveenddtg
ORDER BY epochsecs''' % {'rovDataView': self.rovDataView, 'rov': self.platformName, 'diveNumber': self.diveNumber}
        logger.info(sql)
        cur = self.conn.cursor()
        cur.execute(sql)
        return cur

    def _buildValuesByParm(self):
        '''Reads entire response to fill a dictionary so that we can yield by Parameter rather than by Measurement - as process_data expects
        Node query example:
        http://coredata.shore.mbari.org/rovctd/data/rovctddataservlet?platform=docr&dive=671&&domain=epochsecs&r1=p&r2=t&r3=s&r4=o2sbeml&r5=light&r6=beac
        '''

        self.vSeen = defaultdict(lambda: 0)
        self.valuesByParm = defaultdict(lambda: [])

        if self.args.useNode:
            ##self.url = 'http://coredata.shore.mbari.org/rovctd/data/rovctddataservlet?'
            self.url = 'http://134.89.10.17:8081/rovctddataservlet?'
            self.url += 'platform=%s&dive=%d&domain=epochsecs' % (self.platformName, self.diveNumber)
            for i,v in enumerate(['elon', 'elat', 'd', 'rlon', 'rlat'] + self.vDict.keys()):
                self.url += '&r%d=%s' % (i + 1, v)

            records = self._nodeServletLines()
        else:
            # Fudge a url string for the SQL query - string after '/' displayed in INFO when loading
            self.url = 'SQL://solstice/rov=%s&dive=%d' % (self.args.rov, self.diveNumber)
            records = self._pymssqlLines()

        try:
            ##for i, r in enumerate(csv.DictReader(lines.split('\n'))):
            for i, r in enumerate(records):
                if i % self.args.stride:
                    continue
    
                try:
                    if int(r['latlonflag']) < self.args.qcFlag:
                        continue
                except ValueError:
                    # Some flag values are not set - assume that it would be the default value: 2
                    logger.warn('latlonflag flag value not set in row %d for %s' % (i, self.activityName))
                except TypeError:
                    # Some flag values are not set - assume that it would be the default value: 2
                    logger.warn('latlonflag flag is NoneType value in row %d for %s' % (i, self.activityName))

                for v in self.vDict.keys():
                    values = {}
                    if v not in self.include_names:
                        continue

                    try:
                        values[self.vDict[v]] = float(r[v])
                    except ValueError:
                        continue
                    except TypeError:
                        continue
                    else:
                        try:
                            if v in ('p', 't', 's'):
                                if int(r['ptsflag']) < self.args.qcFlag:
                                    continue
                            elif v == 'o2':
                                if int(r['o2flag']) < self.args.qcFlag:
                                    continue
                            elif v == 'o2alt':
                                if int(r['o2altflag']) < self.args.qcFlag:
                                    continue
                            elif v == 'light':
                                if int(r['lightflag']) < self.args.qcFlag:
                                    continue
                        except ValueError:
                            # Some flag values are not set - assume that they would be the default value: 2
                            logger.warn('QC flag value not set for v = %s in row %d for %s' % (v, i, self.activityName))
    
                    values['time'] = float(r['epochsecs'])
    
                    try:
                        values['depth'] = float(r['d'])
                    except ValueError:
                        continue

                    try:
                        # Use edited positions if not '' or None, otherwise use raw positions
                        try:
                            values['latitude'] = float(r['elat'])
                        except ValueError:
                            values['latitude'] = float(r['rlat'])
                        except TypeError:
                            values['latitude'] = float(r['rlat'])
                        try:
                            values['longitude'] = float(r['elon'])
                        except ValueError:
                            values['longitude'] = float(r['rlon'])
                        except TypeError:
                            values['longitude'] = float(r['rlon'])

                        if not self.inBBOX(values['longitude'], values['latitude']):
                            continue
                    except ValueError:
                        logger.error('No position for record r = %s', r)
                        continue

                    values['timeUnits'] = 'seconds since 1970-01-01 00:00:00'
    
                    self.valuesByParm[v].append(values)
                    self.vSeen[v] += 1

        except KeyboardInterrupt as e:
            logger.error('Interrupted while in DictReader() with r = %s', r)
            import pdb
            pdb.set_trace()
            logger.info('lines = \n%s', self.lines)
            logger.exception(e)
            sys.exit(-1)
        except Exception as e:
            logger.error('Failed on DictReader() from lines from %s', self.url)
            if self.args.useNode:
                logger.error('lines = \n%s', self.lines)
            logger.exception(e)

        self.count = np.sum(self.vSeen.values())

    def _genROVCTD(self):
        '''
        Generator of ROVCTD trajectory data. The data values are a function of time and position as returned
        by the web service. Yield values by Parameter.
        '''
        for p,d in self.valuesByParm.iteritems():
            for values in d:
                yield values

    def addResources(self):
        '''
        Add Resources for this activity, namely standard links provided in the 
        Expedition Database.
        '''
        # For now just override the base class method which expects an OPeNDAP data source
        pass

def processDiveList(args):
    '''Given a list of dives to load
    '''
    for diveName in args.dives:
        if diveName[0].lower() == 'v':
            pName = 'vnta'
        elif diveName[0].lower() == 't':
            pName = 'tibr'
        elif diveName[0].lower() == 'd':
            pName = 'docr'
        dNumber = int(diveName[1:])

        # Instantiate Loader for this dive
        loader = ROVCTD_Loader( 
                    diveNumber = dNumber,
                    campaignName = args.campaignName,
                    campaignDescription = args.campaignDescription,
                    dbAlias = args.database,
                    activityName = diveName,
                    activitytypeName = 'ROV Dive',
                    platformName = pName,
                    platformColor = rovColors[pName],
                    platformTypeName = 'rov',
                    stride = args.stride,
                    args = args,
                    grdTerrain = os.path.join(os.path.dirname(__file__), 'Monterey25.grd')  # File expected in loaders directory
                )

        # Load the data
        loader._buildValuesByParm()
        try:
            (nMP, path, parmCountHash, mind, maxd) = loader.process_data(loader._genROVCTD, 'trajectory')
        except DiveInfoServletException as e:
            logger.error(e)

def processDiveRange(args):
    '''Given an ROV Name and start and end dive number
    '''
    for dNumber in range(args.start, args.end + 1):
        # Instantiate Loader for this dive
        loader = ROVCTD_Loader( 
                    diveNumber = dNumber,
                    campaignName = args.campaignName,
                    campaignDescription = args.campaignDescription,
                    dbAlias = args.database,
                    activityName = args.rov[0].upper() + str(dNumber),
                    activitytypeName = 'ROV Dive',
                    platformName = args.rov,
                    platformColor = rovColors[args.rov],
                    platformTypeName = 'rov',
                    stride = args.stride,
                    args = args,
                    grdTerrain = os.path.join(os.path.dirname(__file__), 'Monterey25.grd')  # File expected in loaders directory
                )

        # Load the data
        loader._buildValuesByParm()
        try:
            (nMP, path, parmCountHash, mind, maxd) = loader.process_data(loader._genROVCTD, 'trajectory')
        except DiveInfoServletException as e:
            logger.error(e)

def process_command_line():
    '''The argparse library is included in Python 2.7 and is an added package for STOQS.
    '''
    import argparse
    from argparse import RawTextHelpFormatter

    examples = 'Examples:' + '\n\n'
    examples += "Initial test dives requested by Rob:\n"
    examples += sys.argv[0] + " --database stoqs_rovctd_mw97 --dives V1236 V1247 V1321 V1575 V1610 V1668 T257 V1964 V2069"
    examples += " V2329 V2354 V2421 V2636 V2661 V2715 V2983 V3006 V3079 V3334 V3363 V3417 V3607 V3630 V3646 D449 D478 V3736"
    examples += " V3766 V3767 V3774 D646 --bbox -122.1 36.65 -122.0 36.75"
    examples += " --campaignName 'Midwater Transect dives 1997 - 2014'"
    examples += " --campaignDescription 'Midwater Transect dives made with Ventana and Doc Ricketts from 1997 - 2014. Three to four dives/year selected, representing spring, summer and fall (~ beginning upwelling, upwelling and post-upwelling)'"
    examples += "\n"
    examples += "\n"
    examples += "All dives in Monterey Bay:\n"
    examples += sys.argv[0] + " --database stoqs_rovctd_mb --rov vnta --start 43 --end 4000 --campaignName 'Monterey Bay ROVCTD data' "
    examples += "--campaignDescription 'All dives in Monterey Bay' --bbox -122.5 36 -121.75 37.0\n"
    examples += sys.argv[0] + " --database stoqs_rovctd_mb --rov tibr --start 42 --end 1163 --campaignName 'Monterey Bay ROVCTD data' "
    examples += "--campaignDescription 'All dives in Monterey Bay' --bbox -122.5 36 -121.75 37.0\n"
    examples += sys.argv[0] + " --database stoqs_rovctd_mb --rov docr --start 1 --end 1000 --campaignName 'Monterey Bay ROVCTD data' "
    examples += "--campaignDescription 'All dives in Monterey Bay' --bbox -122.5 36 -121.75 37.0\n"
    examples += "\n"
    examples += "All dives in the Gulf of California:\n"
    examples += sys.argv[0] + " --database stoqs_rovctd_goc --rov vnta --start 43 --end 4000 --campaignName 'Gulf of California ROVCTD data' "
    examples += "--campaignDescription 'All dives in Gulf of California' --bbox -120 18 -100 33\n"
    examples += sys.argv[0] + " --database stoqs_rovctd_goc --rov tibr --start 42 --end 1163 --campaignName 'Gulf of California ROVCTD data' "
    examples += "--campaignDescription 'All dives in Gulf of California' --bbox -120 18 -100 33\n"
    examples += sys.argv[0] + " --database stoqs_rovctd_goc --rov docr --start 1 --end 1000 --campaignName 'Gulf of California ROVCTD data' "
    examples += "--campaignDescription 'All dives in Gulf of California' --bbox -120 18 -100 33\n"
    examples += "\n"
    examples += "Assumes that a STOQS database has already been set up following steps 4-7 from the LOADING file.\n"
    examples += "\n"
    examples += '\nIf running from cde-package replace ".py" with ".py.cde".'

    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                     description='Load ROVCTD data into a STOQS database',
                                     epilog=examples)

    parser.add_argument('-d', '--database', action='store', help='Database alias', required=True)
    parser.add_argument('--dives', action='store', help='Space separated list of dives in format <ROV_letter><number>', nargs='*', default=[])
    parser.add_argument('--rov', action='store', help='ROV name', choices=['vnta','tibr','docr'])
    parser.add_argument('--start', action='store', help='Staring dive number', type=int)
    parser.add_argument('--end', action='store', help='Ending dive number', type=int)
    parser.add_argument('--campaignName', action='store', help='Short name describing this collection of dives', required=True)
    parser.add_argument('--campaignDescription', action='store', help='Longer name explaining purpose for having these dives assembeled together', default='')
    parser.add_argument('--qcFlag', action='store', help="Load only data that have flags of this value and above. QC flags: 0=bad, 1=suspect, 2=default, 3=human checked ", type=int, choices=[0,1,2,3], default=2)
    parser.add_argument('--stride', action='store', help='Longer name explaining purpose for having these dives together', type=int, default=1)
    parser.add_argument('--bbox', action='store', help='Bounding box for measurements to include in degrees: ll_lon ll_lat ur_lon ur_lat', nargs=4, default=[])
    parser.add_argument('--useNode', action='store_true', help='To use the Node.js server, otherwise query database directly', default=False)

    args = parser.parse_args()
    commandline = ' '.join(sys.argv)

    return args, commandline


if __name__ == '__main__':
    
    args, commandline = process_command_line()

    if args.dives:
        processDiveList(args)
    elif args.rov and args.start and args.end:
        processDiveRange(args)
    else:
        print 'Need a list of dives or a range of dives.'


    ls = LoadScript(args.database, args.campaignName, args.campaignDescription,
                    x3dTerrains = {
                                    'http://dods.mbari.org/terrain/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                                        'position': '-2822317.31255 -4438600.53640 3786150.85474',
                                        'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                                        'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                                        'VerticalExaggeration': '10',
                                        'speed': '0.1',
                                    }
                    },
                    grdTerrain = os.path.join(os.path.dirname(__file__), 'Monterey25.grd')  # File expected in loaders directory
            )

    # Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
    ls.addTerrainResources()

    print "All Done."

