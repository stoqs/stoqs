#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

The btlLoader module has a load_btl() method that reads data from a Seabird
btl*.asc file and saves the bottle trip events as parent Samples in the STOQS database.

Mike McCann
MBARI 19 Setember 2012

@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

# Force lookup of models to THE specific stoqs module.
import os
import sys
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)
# Add grandparent dir to pythonpath so that we can see the CANON and toNetCDF modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../") )
# Add great-grandparent dir to pythonpath so that we can see the stoqs module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../") )
# Add great-great-grandparent dir to pythonpath so that we can see the stoqs module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../") )
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from stoqs import models as m
from CANON.toNetCDF import BaseWriter
from CANON.toNetCDF.wfpctdToNetcdf import ParserWriter
from loaders import STOQS_Loader, SkipRecord
from datetime import datetime, timedelta
from pydap.model import BaseType
import time
import numpy
import csv
import urllib2
import logging
from glob import glob
from tempfile import NamedTemporaryFile
import re
import pprint

# Set up logging
logger = logging.getLogger('loaders')
logger.setLevel(logging.INFO)

# When settings.DEBUG is True Django will fill up a hash with stats on every insert done to the database.
# "Monkey patch" the CursorWrapper to prevent this.  Otherwise we can't load large amounts of data.
# See http://stackoverflow.com/questions/7768027/turn-off-sql-logging-while-keeping-settings-debug
from django.db.backends import BaseDatabaseWrapper
from django.db.backends.util import CursorWrapper

if settings.DEBUG:
    BaseDatabaseWrapper.make_debug_cursor = lambda self, cursor: CursorWrapper(cursor, self)

class ClosestTimeNotFoundException(Exception):
    pass


class SampleLoader(BaseWriter, STOQS_Loader):

    def load_data(self, lat, lon, depth, time, parmNameValues):
        '''
        Load the data values recorded at the bottle trips so that we have some InstantPoints to 
        hang off for our Samples.  This is necessary as data are acquired on the down cast and
        bottles are tripped on the upcast.  
        @parmNameValues is a list of 2-tuples of (ParameterName, Value) measured at the time and location specified by
        @lat decimal degrees
        @lon decimal degrees
        @time Python datetime.datetime object
        @depth in meters
        '''
        try:
            print time, depth, lat, lon
            measurement = self.createMeasurement(time = time,
                            depth = depth,
                            lat = lat,
                            long = lon)
        except SkipRecord, e:
            logger.info(e)
        except Exception, e:
            logger.error(e)
            sys.exit(-1)
        else:
            logger.debug("longitude = %s, latitude = %s, time = %s, depth = %s", lon, lat, time, depth)

        logger.debug("measurement._state.db = %s", measurement._state.db)
        loaded = 0
        for pn,value in parmNameValues:
            logger.debug("pn = %s", pn)
            logger.debug("parameter._state.db = %s", self.getParameterByName(pn)._state.db)
            mp = m.MeasuredParameter(measurement = measurement,
                        parameter = self.getParameterByName(pn),
                        datavalue = value)
            try:
                mp.save(using=self.dbAlias)
            except Exception, e:
                logger.error('Exception %s. Skipping this record.', e)
                logger.error("Bad value (id=%(id)s) for %(pn)s = %(value)s", {'pn': pn, 'value': value, 'id': mp.pk})
                continue
            else:
                loaded += 1
                logger.debug("Inserted value (id=%(id)s) for %(pn)s = %(value)s", {'pn': pn, 'value': value, 'id': mp.pk})

    def get_closest_instantpoint(self, aName, tv, dbAlias):
        '''
        Start with a tolerance of 1 second and double it until we get a non-zero count,
        get the values and find the closest one by finding the one with minimum absolute difference.
        '''
        tol = 1
        num_timevalues = 0
        logger.debug('Looking for tv = %s', tv)
        while tol < 86400:                                      # Fail if not found within 24 hours
            qs = m.InstantPoint.objects.using(self.dbAlias).filter(  activity__name__contains = aName,
                                                                timevalue__gte = (tv-timedelta(seconds=tol)),
                                                                timevalue__lte = (tv+timedelta(seconds=tol))
                                                             ).order_by('timevalue')
            if qs.count():
                num_timevalues = qs.count()
                break
            tol = tol * 2

        if not num_timevalues:
            logger.info('Last query tried: %s', str(qs.query))
            raise ClosestTimeNotFoundException

        logger.debug('Found %d time values with tol = %d', num_timevalues, tol)
        timevalues = [q.timevalue for q in qs]
        logger.debug('timevalues = %s', timevalues)
        i = 0
        i_min = 0
        secdiff = []
        minsecdiff = tol
        for t in timevalues:
            secdiff.append(abs(t - tv).seconds)
            if secdiff[i] < minsecdiff:
                minsecdiff = secdiff[i]
                i_min = i
            logger.debug('i = %d, secdiff = %d', i, secdiff[i])
            i = i + 1

        logger.debug('i_min = %d', i_min)
        return qs[i_min], secdiff[i_min]

    def load_btl(self, lon, lat, depth, timevalue, bottleName):
        '''
        Load a single Niskin Bottle sample
        '''

        # Get the Activity from the Database
        try:
            activity = m.Activity.objects.using(self.dbAlias).get(name__contains=self.activityName)
            logger.debug('Got activity = %s', activity)
        except ObjectDoesNotExist:
            logger.warn('Failed to find Activity with name like %s.  Skipping GulperLoad.', self.activityName)
            return
        except MultipleObjectsReturned:
            logger.warn('Multiple objects returned for name__contains = %s.  Selecting one by random and continuing...', self.activityName)
            activity = m.Activity.objects.using(self.dbAlias).filter(name__contains=self.activityName)[0]
        
        # Get or create SampleType for Niskin
        (sample_type, created) = m.SampleType.objects.using(self.dbAlias).get_or_create(name = 'Niskin')
        logger.debug('sampletype %s, created = %s', sample_type, created)
        # Get or create SamplePurpose for Niskin
        (sample_purpose, created) = m.SamplePurpose.objects.using(self.dbAlias).get_or_create(name = 'StandardDepth')
        logger.debug('samplepurpose %s, created = %s', sample_purpose, created)
        try:
            ip, seconds_diff = self.get_closest_instantpoint(self.activityName, timevalue, self.dbAlias)
            point = 'POINT(%s %s)' % (lon, lat)
            stuple = m.Sample.objects.using(self.dbAlias).get_or_create( name = bottleName,
                                                                    depth = str(depth),     # Must be str to convert to Decimal
                                                                    geom = point,
                                                                    instantpoint = ip,
                                                                    sampletype = sample_type,
                                                                    samplepurpose = sample_purpose,
                                                                    volume = 20000.0
                                                                )
            ##rtuple = m.Resource.objects.using(self.dbAlias).get_or_create( name = 'Seconds away from InstantPoint',
            ##                                                        value = seconds_diff
            ##                                                        )

            # 2nd item of tuples will be True or False dependending on whether the object was created or gotten
            ##logger.info('Loaded Sample %s with Resource: %s', stuple, rtuple)
        except ClosestTimeNotFoundException:
            logger.warn('ClosestTimeNotFoundException: A match for %s not found for %s', timevalue, activity)

    def process_btl_files(self):
        '''
        Loop through all .btl files and insert a Sample record to the database for each bottle trip

        Processed c*.btl files look like (after xml header):

    Bottle        Date      Sal00      Sal11  Sigma-00  Sigma-11 Sbeox0ML/L   Sbeox0PSSbeox0Mm/Kg Potemp090C Potemp190C      TimeJ       PrDM      DepSM      C0S/m      C1S/m      T090C      T190C        Bat      Xmiss         V1    Sbeox0V         V2  FlECO-AFL         V3     Upoly0         V4        Par         V5       AltM         V6       Scan
  Position        Time                                                                                                                                                                                                                                                                                                                                          
      2    Sep 10 2012    34.0050    34.0045    26.3491    26.3486    1.63257   25.10932     71.039     8.9360     8.9366 255.145990    202.002    200.414   3.624756   3.624763     8.9575     8.9582     0.5715    86.6855     4.3660     0.9883     0.9888     0.3746     0.0350  0.0002000     0.0000 1.0000e-12     0.1303     100.00     5.0000      11246 (avg)
              20:30:15                                                                                                    1.7398e-05      0.071      0.071   0.000030   0.000058     0.0003     0.0008     0.0082     0.1775     0.0088     0.0004     0.0004     0.0146     0.0006  0.0000000     0.0000 0.0000e+00     0.0005       0.00     0.0000         35 (sdev)
      3    Sep 10 2012    33.9433    33.9424    26.2372    26.2363    1.91904   29.75985     83.513     9.3330     9.3342 255.147702    150.644    149.478   3.652452   3.652470     9.3495     9.3507     0.4231    89.9630     4.5288     1.0855     1.0858     0.3890     0.0355  0.0002000     0.0000 1.0000e-12     0.1293     100.00     5.0000      14795 (avg)
              20:32:43
        '''

        _debug = False
        fileList = glob(os.path.join(self.parentInDir, 'pctd/c*.btl'))
        fileList.sort()
        for file in fileList:
            if _debug: print "file = %s" % file
            tmpFile = NamedTemporaryFile(dir='/dev/shm', suffix='.btl').name
            if _debug: print 'tmpFile = ', tmpFile
            tmpFH = open(tmpFile, 'w')

            year, lat, lon = ParserWriter.get_year_lat_lon(file)
            print year, lat, lon

            fh = open(file)
            for line in fh:
                # Write to tempfile all lines that don't begin with '*' nor '#' then open that with csv.DictReader
                # Concatenate broken lines that begin with 'Position...' and with HH:MM:SS, remove (avg|sdev)
                if not line.startswith('#') and not line.startswith('*'):
                    m = re.match('.+(Sbeox0PS)(Sbeox0Mm)', line.strip())
                    if m:
                        line = re.sub('(?<=)(Sbeox0PS)(Sbeox0Mm)(?=)', lambda m: "%s %s" % (m.group(1), m.group(2)), line)
                        if _debug: print 'Fixed header: line = ', line
                    if line.strip() == 'Position        Time':
                        # Append 2nd line of header to first line & write to tmpFile
                        tmpFH.write(lastLine + line)
                    m = re.match('\d\d:\d\d:\d\d', line.strip())
                    if m:
                        # Append Time string to last line & write to tmpFile
                        if _debug: print 'm.group(0) = ', m.group(0)
                        tmpFH.write(lastLine + ' ' + m.group(0) + '\n')
                    m = re.match('.+[A-Z][a-z][a-z] \d\d \d\d\d\d', line.strip())
                    if m:
                        # Replace spaces with dashes in the date field
                        line = re.sub('(?<= )([A-Z][a-z][a-z]) (\d\d) (\d\d\d\d)(?= )', lambda m: "%s-%s-%s" % (m.group(1), m.group(2), m.group(3)), line)
                        if _debug: print 'Spaces to dashes: line = ', line
                        # Remove (avg) or (sdev) field
                        ##line = line[:line.find('(')]
                        ##if _debug: print 'Remove (...: line = ', line

                    lastLine = line.rstrip()      # Save line without terminating linefeed

            tmpFH.close()

            # Create activity for this cast
            self.startDatetime = None
            self.endDatetime = None
            for r in csv.DictReader(open(tmpFile), delimiter=' ', skipinitialspace=True):
                dt = datetime(year, 1, 1, 0, 0, 0) + timedelta(days=float(r['TimeJ'])) - timedelta(days=1)
                if not self.startDatetime:
                    self.startDatetime = dt
            self.endDatetime = dt
            self.campaignName = 'CANON - September 2012'
            self.platformName = 'wfpctd'
            self.platformColor = '11665e'
            self.platformTypeName = 'ship'
            self.platform = self.getPlatform(self.platformName, self.platformTypeName)
            self.activitytypeName = 'CTD upcast'
            self.activityName = file.split('/')[-1].split('.')[-2] 
            self.include_names = ['Sal00', 'T090C']
            self.createActivity()

            # Add some parameters for the data that we need to load so that we have InstantPoints at the bottle locations
            parmDict = {}
            Sal00 = BaseType()
            Sal00.attributes = {'units': 1 , 'long_name': 'salinity', 'standard_name': 'sea_water_salinity'} 
            T090C = BaseType()
            T090C.attributes = {'units': 'ITS-90, deg C', 'long_name': 'temperature', 'standard_name': 'sea_water_temperature'}
            parmDict = { 'Sal00': Sal00, 'T090C': T090C }
            self.addParameters(parmDict)

            for r in csv.DictReader(open(tmpFile), delimiter=' ', skipinitialspace=True):
                # Date Time =  Sep-10-2012 20:38:17 - this is local time, but use TimeJ for GMT
                ##es = time.mktime(time.strptime(r['Date'] + ' ' + r['Time'], '%b-%d-%Y %H:%M:%S'))
                ##print 'Time from Date + Time =',  datetime.fromtimestamp(es)
                dt = datetime(year, 1, 1, 0, 0, 0) + timedelta(days=float(r['TimeJ'])) - timedelta(days=1)
                ##print 'Time from TimeJ = ', dt
                esDiff = dt - datetime(1970, 1, 1, 0, 0, 0)
                es = 86400 * esDiff.days + esDiff.seconds

                # activity name will be the same as the .asc file that was converted to .nc
                bName = file.split('/')[-1].split('.')[-2] + '_' + r['Bottle']

                # Load data 
                parmNameValues = []
                for name in parmDict.keys():
                    parmNameValues.append((name, float(r[name])))
                logger.debug('Calling load_data with parmNameValues = %s', pprint.pprint(parmNameValues))
                self.load_data(lon, lat, float(r['DepSM']), dt, parmNameValues)

                # Load Bottle sample
                self.load_btl(lon, lat, float(r['DepSM']), dt, bName)

            fh.close()
            os.remove(tmpFile)


if __name__ == '__main__':

    # Accept optional arguments of dbAlias, input data directory name, and output directory name
    # If not specified then 'default' and the current directory is used
    try:
        dbAlias = sys.argv[1]
    except IndexError:
        dbAlias = 'default'
    try:
        inDir = sys.argv[2]
    except IndexError:
        inDir = '.'
    try:
        outDir = sys.argv[3]
    except IndexError:
        outDir = '.'
    
    sl = SampleLoader(parentInDir=inDir, parentOutDir=outDir)
    sl.dbAlias = dbAlias
    sl.process_btl_files()

