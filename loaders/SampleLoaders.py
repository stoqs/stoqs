#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

The SampleLoaders module contains classes and functions for loading Sample data into STOQS.

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
# Add parent dir to pythonpath so that we can see the loaders and stoqs modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../") )
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from stoqs import models as m
from loaders.seabird import get_year_lat_lon
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
from bs4 import BeautifulSoup

# Set up logging
logger = logging.getLogger('loaders')
logger.setLevel(logging.INFO)

# When settings.DEBUG is True Django will fill up a hash with stats on every insert done to the database.
# "Monkey patch" the CursorWrapper to prevent this.  Otherwise we can't load large amounts of data.
# See http://stackoverflow.com/questions/7768027/turn-off-sql-logging-while-keeping-settings-debug
from django.db.backends import BaseDatabaseWrapper
from django.db.backends.util import CursorWrapper

# Constant for ParameterGroup name - for utils/STOQSQmanager.py to use
SAMPLED = 'Sampled'

if settings.DEBUG:
    BaseDatabaseWrapper.make_debug_cursor = lambda self, cursor: CursorWrapper(cursor, self)

class ClosestTimeNotFoundException(Exception):
    pass

class SingleActivityNotFound(Exception):
    pass

def removeNonAscii(s): 
    return "".join(i for i in s if ord(i)<128)

def get_closest_instantpoint(aName, tv, dbAlias):
        '''
        Start with a tolerance of 1 second and double it until we get a non-zero count,
        get the values and find the closest one by finding the one with minimum absolute difference.
        '''
        tol = 1
        num_timevalues = 0
        logger.debug('Looking for tv = %s', tv)
        while tol < 86400:                                      # Fail if not found within 24 hours
            qs = m.InstantPoint.objects.using(dbAlias).filter(  activity__name__contains = aName,
                                                                timevalue__gte = (tv-timedelta(seconds=tol)),
                                                                timevalue__lte = (tv+timedelta(seconds=tol))
                                                             ).order_by('timevalue')
            if qs.count():
                num_timevalues = qs.count()
                break
            tol = tol * 2

        if not num_timevalues:
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

def load_gulps(activityName, file, dbAlias):
    '''
    file looks like 'Dorado389_2011_111_00_111_00_decim.nc'.  From hard-coded knowledge of MBARI's filesystem
    read the associated _gulper.txt file for the survey and load the gulps as samples in the dbAlias database.
    '''

    # Get the Activity from the Database
    try:
        activity = m.Activity.objects.using(dbAlias).get(name__contains=activityName)
        logger.debug('Got activity = %s', activity)
    except ObjectDoesNotExist:
        logger.warn('Failed to find Activity with name like %s.  Skipping GulperLoad.', activityName)
        return
    except MultipleObjectsReturned:
        logger.warn('Multiple objects returned for name__contains = %s.  Selecting one by random and continuing...', activityName)
        activity = m.Activity.objects.using(dbAlias).filter(name__contains=activityName)[0]
        

    # Use the dods server to read over http - works from outside of MABRI's Intranet
    baseUrl = 'http://dods.mbari.org/data/auvctd/surveys/'
    yyyy = file.split('_')[1].split('_')[0]
    survey = file.split(r'_decim')[0]
    # E.g.: http://dods.mbari.org/data/auvctd/surveys/2010/odv/Dorado389_2010_300_00_300_00_Gulper.txt
    gulperUrl = baseUrl + yyyy + '/odv/' + survey + '_Gulper.txt'

    try:
        reader = csv.DictReader(urllib2.urlopen(gulperUrl), dialect='excel-tab')
        logger.debug('Reading gulps from %s', gulperUrl)
    except urllib2.HTTPError:
        logger.warn('Failed to find odv-formatted Gulper file: %s.  Skipping GulperLoad.', gulperUrl)
        return

    # Get or create SampleType for Gulper
    (gulper_type, created) = m.SampleType.objects.using(dbAlias).get_or_create(name = 'Gulper')
    logger.debug('sampletype %s, created = %s', gulper_type, created)
    for row in reader:
        # Need to subtract 1 day from odv file as 1.0 == midnight on 1 January
        timevalue = datetime(int(yyyy), 1, 1) + timedelta(days = (float(row[r'YearDay [day]']) - 1))
        try:
            ip, seconds_diff = get_closest_instantpoint(activityName, timevalue, dbAlias)
            point = 'POINT(%s %s)' % (repr(float(row[r'Lon (degrees_east)']) - 360.0), row[r'Lat (degrees_north)'])
            stuple = m.Sample.objects.using(dbAlias).get_or_create( name = row[r'Bottle Number [count]'],
                                                                depth = row[r'DEPTH [m]'],
                                                                geom = point,
                                                                instantpoint = ip,
                                                                sampletype = gulper_type,
                                                                volume = 1800
                                                              )
            rtuple = m.Resource.objects.using(dbAlias).get_or_create( name = 'Seconds away from InstantPoint',
                                                                  value = seconds_diff
                                                                )

            # 2nd item of tuples will be True or False dependending on whether the object was created or gotten
            logger.info('Loaded Sample %s with Resource: %s', stuple, rtuple)
        except ClosestTimeNotFoundException:
            logger.warn('ClosestTimeNotFoundException: A match for %s not found for %s', timevalue, activity)


class SeabirdLoader(STOQS_Loader):
    '''
    Inherit database loading functions from STOQS_Loader and use its constructor
    '''

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

        # Sanity check to prevent accidental switching of lat & lon
        if lat < -90 or lat > 90:
            logger.exception("lat = %f.  Can't load this!", lat)
            sys.exit(-1)

        try:
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

    def load_btl(self, lat, lon, depth, timevalue, bottleName):
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
            ip, seconds_diff = get_closest_instantpoint(self.activityName, timevalue, self.dbAlias)
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
        else:
            logger.info('Loaded Bottle name = %s', bottleName)

    def process_btl_file(self, fh, year, lat, lon):
        '''
        Iterate through lines of iterator to Seabird .btl file and pull out data for loading into STOQS
        '''
        _debug = False
        tmpFile = NamedTemporaryFile(dir='/dev/shm', suffix='.btl').name
        if _debug: print 'tmpFile = ', tmpFile
        tmpFH = open(tmpFile, 'w')
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

                lastLine = line.rstrip()      # Save line without terminating linefeed

        tmpFH.close()
        try:
            fh.close()
        except AttributeError:
            pass    # fh is likely a list read in from a URL, ignore AttributeError

        # Create activity for this cast
        self.startDatetime = None
        self.endDatetime = None
        for r in csv.DictReader(open(tmpFile), delimiter=' ', skipinitialspace=True):
            dt = datetime(year, 1, 1, 0, 0, 0) + timedelta(days=float(r['TimeJ'])) - timedelta(days=1)
            if not self.startDatetime:
                self.startDatetime = dt
        self.endDatetime = dt
        self.platformName = 'wf_pctd'
        self.platformColor = '11665e'
        self.platformTypeName = 'ship'
        self.platform = self.getPlatform(self.platformName, self.platformTypeName)
        self.activitytypeName = 'CTD upcast'
        self.include_names = ['Sal00', 'T090C']

        # Bottle samples are to be loaded after downcast data are loaded so that we can use the same activity
        from stoqs import models as m
        try:
            activity = m.Activity.objects.using(self.dbAlias).get(name__contains=self.activityName)
            logger.debug('Got activity = %s', activity)
            self.activity = activity
        except ObjectDoesNotExist:
            logger.error('Failed to find Activity with name like %s.  Must load downcast data before loading bottles.', self.activityName)
            raise SingleActivityNotFound
        except MultipleObjectsReturned:
            logger.error('Multiple objects returned for name__contains = %s.  This should not happen.  Fix the database and the reason for this.', self.activityName)
            raise SingleActivityNotFound

        # Add T & S parameters for the data that we need to load so that we have InstantPoints at the bottle locations
        parmDict = {}
        Sal00 = BaseType()
        Sal00.attributes = {'units': 1 , 'long_name': 'salinity', 'standard_name': 'sea_water_salinity'} 
        T090C = BaseType()
        T090C.attributes = {'units': 'ITS-90, deg C', 'long_name': 'temperature', 'standard_name': 'sea_water_temperature'}
        parmDict = { 'Sal00': Sal00, 'T090C': T090C }
        self.addParameters(parmDict)

        for r in csv.DictReader(open(tmpFile), delimiter=' ', skipinitialspace=True):
            dt = datetime(year, 1, 1, 0, 0, 0) + timedelta(days=float(r['TimeJ'])) - timedelta(days=1)
            esDiff = dt - datetime(1970, 1, 1, 0, 0, 0)
            es = 86400 * esDiff.days + esDiff.seconds
            bName = self.activityName + '_' + r['Bottle']

            # Load data 
            parmNameValues = []
            for name in parmDict.keys():
                parmNameValues.append((name, float(r[name])))
            self.load_data(lat, lon, float(r['DepSM']), dt, parmNameValues)

            # Load Bottle sample
            self.load_btl(lat, lon, float(r['DepSM']), dt, bName)

        os.remove(tmpFile)

    def process_btl_files(self):
        '''
        Loop through all .btl files and insert a Sample record to the database for each bottle trip.  Assumes that c*.btl files 
        are available in a local pctd directory, if not then they are read from a THREDDS server.

        Processed c*.btl files look like (after xml header):

    Bottle        Date      Sal00      Sal11  Sigma-00  Sigma-11 Sbeox0ML/L   Sbeox0PSSbeox0Mm/Kg Potemp090C Potemp190C      TimeJ       PrDM      DepSM      C0S/m      C1S/m      T090C      T190C        Bat      Xmiss         V1    Sbeox0V         V2  FlECO-AFL         V3     Upoly0         V4        Par         V5       AltM         V6       Scan
  Position        Time                                                                                                                                                                                                                                                                                                                                          
      2    Sep 10 2012    34.0050    34.0045    26.3491    26.3486    1.63257   25.10932     71.039     8.9360     8.9366 255.145990    202.002    200.414   3.624756   3.624763     8.9575     8.9582     0.5715    86.6855     4.3660     0.9883     0.9888     0.3746     0.0350  0.0002000     0.0000 1.0000e-12     0.1303     100.00     5.0000      11246 (avg)
              20:30:15                                                                                                    1.7398e-05      0.071      0.071   0.000030   0.000058     0.0003     0.0008     0.0082     0.1775     0.0088     0.0004     0.0004     0.0146     0.0006  0.0000000     0.0000 0.0000e+00     0.0005       0.00     0.0000         35 (sdev)
      3    Sep 10 2012    33.9433    33.9424    26.2372    26.2363    1.91904   29.75985     83.513     9.3330     9.3342 255.147702    150.644    149.478   3.652452   3.652470     9.3495     9.3507     0.4231    89.9630     4.5288     1.0855     1.0858     0.3890     0.0355  0.0002000     0.0000 1.0000e-12     0.1293     100.00     5.0000      14795 (avg)
              20:32:43
        '''
        try:
            fileList = glob(os.path.join(self.parentInDir, 'pctd/c*.btl'))
        except AttributeError:
            fileList = []
        if fileList:
            # Read files from local pctd directory
            fileList.sort()
            for file in fileList:
                self.activityName = file.split('/')[-1].split('.')[-2] 
                year, lat, lon = get_year_lat_lon(file)
                fh = open(file)
                try:
                    self.process_btl_file(fh, year, lat, lon)
                except SingleActivityNotFound:
                    continue

        else:
            # Read files from the network - use BeautifulSoup to parse TDS's html response
            webBtlDir = self.tdsBase + 'catalog/' + self.pctdDir + 'catalog.html'
            logger.debug('Opening url to %s', webBtlDir)
            soup = BeautifulSoup(urllib2.urlopen(webBtlDir).read())
            linkList = soup.find_all('a')
            linkList.sort(reverse=True)
            for link in linkList:
                file = link.get('href')
                if file.endswith('.btl'):
                    logger.debug("file = %s", file)
                    # btlUrl looks something like: http://odss.mbari.org/thredds/fileServer/CANON_september2012/wf/pctd/c0912c53.btl
                    btlUrl = self.tdsBase + 'fileServer/' +  self.pctdDir + file.split('/')[-1]
                    hdrUrl = self.tdsBase + 'fileServer/' +  self.pctdDir + ''.join(file.split('/')[-1].split('.')[:-1]) + '.hdr'
                    logger.debug('btlUrl = %s', btlUrl)
    
                    self.activityName = file.split('/')[-1].split('.')[-2] 
                    year, lat, lon = get_year_lat_lon(hdrUrl = hdrUrl)
                    btlFH = urllib2.urlopen(btlUrl).read().splitlines()
                    self.process_btl_file(btlFH, year, lat, lon)


class SubSamplesLoader(STOQS_Loader):
    '''
    Inherit database loading functions from STOQS_Loader and use its constructor.
    This class is designed to load subsample information for Samples that have already
    been loaded into a STOQS database.  The input data will have a key field that will
    match to an existing Sample and SampledParameter data that will need to be loaded
    in.
    '''

    def load_subsample(self, parentSample, row):
        '''
        Populate the Sample, SampledParameter, SampleRelationship, and associated lookup tables 
        (SampleType, SamplePurpose, AnalysisMethod) with data in the row from the spreadsheet.
        '''
        if row['Parameter Value'] == '':        # Must have a value to proceed
            return

        (sampleType, created) = m.SampleType.objects.using(self.dbAlias).get_or_create(name='subsample')
        (samplePurpose, created) = m.SamplePurpose.objects.using(self.dbAlias).get_or_create(name=row['Sample Type'])

        fd = None
        if row['Filter Diameter [mm]']:
            fd = float(row['Filter Diameter [mm]'])
        fps = None
        if row['Filter Pore Size [uM]']:
            fps = float(row['Filter Pore Size [uM]'])
        sample = m.Sample(  instantpoint=parentSample.instantpoint,
                            depth=parentSample.depth,
                            geom=parentSample.geom,
                            volume=float(row['Sample Volume [mL]']),
                            filterdiameter=fd,
                            filterporesize=fps,
                            laboratory=row['Laboratory'],
                            researcher=row['Researcher'],
                            sampletype=sampleType,
                            samplepurpose=samplePurpose)
        sample.save(using=self.dbAlias)

        samplerelationship = m.SampleRelationship(child=sample, parent=parentSample)
        samplerelationship.save(using=self.dbAlias)
                   
        (parameter, created) = m.Parameter.objects.using(self.dbAlias).get_or_create(name=row['Parameter Name'], units=row['Parameter Units'])
    
        analysisMethod = None
        if row['Analysis Method']:
            (analysisMethod, created) = m.AnalysisMethod.objects.using(self.dbAlias).get_or_create(name=removeNonAscii(row['Analysis Method']))

        sp = m.SampledParameter(sample=sample, parameter=parameter, datavalue=row['Parameter Value'], analysismethod=analysisMethod)
        sp.save(using=self.dbAlias)
                                
    def process_subsample_file(self, fileName):
        '''
        Open .csv file and load the data, matching to existing Sample.
        The format of the file is as defined by Julio's work.  The first few records look like:

            Cruise,Bottle Number,Sample Type,Sample Volume [mL],Filter Diameter [mm],Filter Pore Size [uM],Parameter Name,Parameter Value,Parameter Units,MBARI BOG Taxon Code,Laboratory,Researcher,Analysis Method,Comment Name,Comment Value
            2011_074_02_074_02,0,random,1500,25,30,B1006 barnacles,0.218,OD A450 nm,,Vrijenhoek,Harvey,Sandwich Hybridization Assay,,
            2011_074_02_074_02,0,random,1500,25,30,M2B mussels,0.118,OD A450 nm,,Vrijenhoek,Harvey,Sandwich Hybridization Assay,,
        '''
        subCount = 0
        lastParentSampleID = 0
        parameterCount = {}
        for r in csv.DictReader(open(fileName)):
            logger.debug(r)
            if r['Cruise'] == '2011_257_00_257_01':
                r['Cruise'] = '2011_257_00_257_00'      # Correct a typo in spreadsheet
            try:
                parentSample = m.Sample.objects.using(self.dbAlias).select_related(depth=2
                                                      ).filter( instantpoint__activity__name__contains=r['Cruise'], 
                                                                name='%.1f' % float(r['Bottle Number']))[0]
            except IndexError:
                logger.warn('Parent Sample not found for Cruise = %s, Bottle Number = %s', r['Cruise'], r['Bottle Number'])
                continue

            if parentSample.id != lastParentSampleID:
                if lastParentSampleID:
                    logger.info('%d sub samples loaded', subCount)
                logger.info('Loading subsamples of parentSample (activity, bottle) = (%s, %s)', r['Cruise'], r['Bottle Number'])
                subCount = 0

            try:
                p = m.Parameter.objects.using(self.dbAlias).get(name=r['Parameter Name'])
            except e:
                logger.warn(e)
            else:
                try:
                    parameterCount[p] += 1
                except KeyError:
                    parameterCount[p] = 0

            subCount = subCount + 1
            self.load_subsample(parentSample, r)
            lastParentSampleID = parentSample.id
    
        logger.info('%d sub samples loaded', subCount)
        self.assignParameterGroup(parameterCount, groupName=SAMPLED)
        self.postProcess(parameterCount)

    def postProcess(self, parameterCount):
        '''
        Perform step(s) following subsample loads, namely inserting/updating records in the ActivityParameter
        table.  The updateActivityParameterStats() method in STOQS_Loader expects a hash of parameters
        that are unique to an activity that is an attribute of self.
        '''
        for p in parameterCount:
            for a in m.SampledParameter.objects.using(self.dbAlias).filter(parameter__name=p.name).values('sample__instantpoint__activity').distinct():
                self.activity = a
                self.updateActivityParameterStats(parameterCount, sampledFlag=True)


if __name__ == '__main__':

    # Accept optional arguments of dbAlias, input data directory name, and output directory name
    # If not specified then 'default' and the current directory is used
    try:
        dbAlias = sys.argv[1]
    except IndexError:
        dbAlias = 'stoqs_dorado2011_s100'

    # Test SubSamplesLoader
    ssl = SubSamplesLoader('', '', dbAlias=dbAlias)
    ssl.process_subsample_file('2011_AUVdorado_Samples_Database.csv')

    sys.exit(0)

    # Test SeabirdLoader
    sl = SeabirdLoader('activity name', 'wf_pctd', dbAlias=dbAlias)
    ##sl.parentInDir = '.'  # Set if reading data from a directory rather than a TDS URL
    # Catalog to .btl files is formed with sl.tdsBase + 'catalog/' + sl.pctdDir + 'catalog.html'
    sl.tdsBase= 'http://odss.mbari.org/thredds/' 
    sl.pctdDir = 'CANON_september2012/wf/pctd/'
    sl.campaignName = 'CANON - September 2012'
    sl.process_btl_files()


    # Test load_gulps: A nice test data load for a northern Monterey Bay survey  
    ##file = 'Dorado389_2010_300_00_300_00_decim.nc'
    ##dbAlias = 'default'
    file = 'Dorado389_2010_277_01_277_01_decim.nc'
    dbAlias = 'stoqs_oct2010'

    aName = file

    load_gulps(aName, file, dbAlias)




