'''
The SampleLoaders module contains classes and functions for loading Sample data into STOQS.

The btlLoader module has a load_btl() method that reads data from a Seabird
btl*.asc file and saves the bottle trip events as parent Samples in the STOQS database.

Mike McCann
MBARI 19 Setember 2012
'''

import os
import sys
# Add parent dir to pythonpath so that we can see the loaders and stoqs modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../") )
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError

from stoqs.models import (Activity, InstantPoint, Sample, SampleType, Resource,
                          SamplePurpose, SampleRelationship, Parameter, SampledParameter,
                          MeasuredParameter, AnalysisMethod)
from loaders.seabird import get_year_lat_lon
from loaders import STOQS_Loader, SkipRecord
from datetime import datetime, timedelta
from pydap.model import BaseType
import csv
import urllib2
import logging
from glob import glob
from tempfile import NamedTemporaryFile
import re
from bs4 import BeautifulSoup

# Set up logging for module functions
logger = logging.getLogger(__name__)
# Logging level set in stoqs/config/common.py, but may override here
##logger.setLevel(logging.INFO)

# When settings.DEBUG is True Django will fill up a hash with stats on every insert done to the database.
# "Monkey patch" the CursorWrapper to prevent this.  Otherwise we can't load large amounts of data.
# See http://stackoverflow.com/questions/7768027/turn-off-sql-logging-while-keeping-settings-debug
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.utils import CursorWrapper

if settings.DEBUG:
    BaseDatabaseWrapper.make_debug_cursor = lambda self, cursor: CursorWrapper(cursor, self)

# Constant for ParameterGroup name - for utils/STOQSQmanager.py to use
SAMPLED = 'Sampled'

# SampleTypes
GULPER = 'Gulper'
NISKIN = 'Niskin'
NETTOW = 'NetTow'
VERTICALNETTOW = 'VerticalNetTow'       # Must contain NETTOW string so that a filter for
HORIZONTALNETTOW = 'VerticalNetTow'     # name__contains=NETTOW returns both vertical and horizontal net tows
PLANKTONPUMP = 'PlanktonPump'

class ClosestTimeNotFoundException(Exception):
    pass

class SingleActivityNotFound(Exception):
    pass

class SubSampleLoadError(Exception):
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
        qs = InstantPoint.objects.using(dbAlias).filter(  activity__name__contains = aName,
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

def load_gulps(activityName, auv_file, dbAlias):
    '''
    auv_file looks like 'Dorado389_2011_111_00_111_00_decim.nc'.  From hard-coded knowledge of MBARI's filesystem
    read the associated _gulper.txt file for the survey and load the gulps as samples in the dbAlias database.
    '''

    # Get the Activity from the Database
    try:
        activity = Activity.objects.using(dbAlias).get(name__contains=activityName)
        logger.debug('Got activity = %s', activity)
    except ObjectDoesNotExist:
        logger.warn('Failed to find Activity with name like %s.  Skipping GulperLoad.', activityName)
        return
    except MultipleObjectsReturned:
        logger.warn('Multiple objects returned for name__contains = %s.  Selecting one by random and continuing...', activityName)
        activity = Activity.objects.using(dbAlias).filter(name__contains=activityName)[0]
        

    # Use the dods server to read over http - works from outside of MABRI's Intranet
    baseUrl = 'http://dods.mbari.org/data/auvctd/surveys/'
    yyyy = auv_file.split('_')[1].split('_')[0]
    survey = auv_file.split(r'_decim')[0]
    # E.g.: http://dods.mbari.org/data/auvctd/surveys/2010/odv/Dorado389_2010_300_00_300_00_Gulper.txt
    gulperUrl = baseUrl + yyyy + '/odv/' + survey + '_Gulper.txt'

    try:
        reader = csv.DictReader(urllib2.urlopen(gulperUrl), dialect='excel-tab')
        logger.debug('Reading gulps from %s', gulperUrl)
    except urllib2.HTTPError:
        logger.warn('Failed to find odv-formatted Gulper file: %s.  Skipping GulperLoad.', gulperUrl)
        return

    # Get or create SampleType for Gulper
    (gulper_type, created) = SampleType.objects.using(dbAlias).get_or_create(name=GULPER)
    logger.debug('sampletype %s, created = %s', gulper_type, created)
    for row in reader:
        # Need to subtract 1 day from odv file as 1.0 == midnight on 1 January
        try:
            timevalue = datetime(int(yyyy), 1, 1) + timedelta(days = (float(row[r'YearDay [day]']) - 1))
        except TypeError as e:
            logger.error('%s.  Skipping this Sample - you may want to fix the input file', e)
            continue
        try:
            ip, seconds_diff = get_closest_instantpoint(activityName, timevalue, dbAlias)
            point = 'POINT(%s %s)' % (repr(float(row[r'Lon (degrees_east)']) - 360.0), row[r'Lat (degrees_north)'])
            stuple = Sample.objects.using(dbAlias).get_or_create( name = row[r'Bottle Number [count]'],
                                                                depth = row[r'DEPTH [m]'],
                                                                geom = point,
                                                                instantpoint = ip,
                                                                sampletype = gulper_type,
                                                                volume = 1800
                                                              )
            rtuple = Resource.objects.using(dbAlias).get_or_create( name = 'Seconds away from InstantPoint',
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
    def __init__(self, activityName, platformName, dbAlias='default', campaignName=None,
                activitytypeName=None, platformColor=None, platformTypeName='CTD', stride=1, dodsBase=None):
        self.pctdDir = dodsBase.split('dodsC')[1]
        'Just use the STOQS_Loader constructor'
        super(SeabirdLoader, self).__init__(activityName, platformName, dbAlias, campaignName,
                activitytypeName, platformColor, platformTypeName, stride)

    def buildParmDict(self):
        '''
        Build parameter dictionary akin to that returned by pydap.  The parameters from the .btl file must
        match the parameters read from the .nc file.  See comments for mapping copied from pctdToNetCDF.py.
        '''

        # Match the mapping done in pctdToNetCDF.py:

        # self.pr_list.append(float(r['PrDM']))
        # self.depth = self.ncFile.createVariable('depth', 'float64', ('time',))
        # self.depth.long_name = 'DEPTH'
        # self.depth.standard_name = 'depth'
        # self.depth.units = 'm'
        # self.depth[:] = csiro.depth(self.pr_list, self.lat_list)      # Convert pressure to depth

        # self.t1_list.append(r['T190C'])
        # temp = self.ncFile.createVariable('TEMP', 'float64', ('time',))
        # temp.long_name = 'Temperature, 2 [ITS-90, deg C]'
        # temp.standard_name = 'sea_water_temperature'
        # temp.units = 'Celsius'

        # self.sal_list.append(r['Sal00'])
        # sal = self.ncFile.createVariable('PSAL', 'float64', ('time',))
        # sal.long_name = 'Salinity, Practical [PSU]'
        # sal.standard_name = 'sea_water_salinity'

        # self.xmiss_list.append(r['Xmiss'])
        # xmiss = self.ncFile.createVariable('xmiss', 'float64', ('time',))
        # xmiss.long_name = 'Beam Transmission, Chelsea/Seatech'
        # xmiss.units = '%'

        # self.ecofl_list.append(r['FlECO-AFL'])
        # ecofl = self.ncFile.createVariable('ecofl', 'float64', ('time',))
        # ecofl.long_name = 'Fluorescence, WET Labs ECO-AFL/FL'
        # ecofl.units = 'mg/m^3'

        # self.oxygen_list.append(r['Sbeox0ML/L'])
        # oxygen = self.ncFile.createVariable('oxygen', 'float64', ('time',))
        # oxygen.long_name = 'Oxygen, SBE 43'
        # oxygen.units = 'ml/l'

        parmDict = {}

        pr = BaseType('nameless')
        pr.attributes = {'colname': 'PrDM', 'units': 'm' , 'long_name': 'DEPTH', 'standard_name': 'depth'}

        temp = BaseType('nameless')
        temp.attributes = {'colname': 'T190C', 'units': 'ITS-90, deg C', 'long_name': 'temperature', 'standard_name': 'sea_water_temperature'}

        sal = BaseType('nameless')
        sal.attributes = {'colname': 'Sal00', 'units': '1' , 'long_name': 'salinity', 'standard_name': 'sea_water_salinity'} 

        xmiss = BaseType('nameless')
        xmiss.attributes = {'colname': 'Xmiss', 'units': '%', 'long_name': 'Beam Transmission, Chelsea/Seatech'}

        ecofl = BaseType('nameless')
        ecofl.attributes = {'colname': 'FlECO-AFL', 'units': 'mg/m^3', 'long_name': 'Fluorescence, WET Labs ECO-AFL/FL'}

        wetstar = BaseType('nameless')
        wetstar.attributes = {'colname': 'WetStar', 'units': 'mg/m^3', 'long_name': 'Fluorescence, WET Labs WETstar'}

        oxygen = BaseType('nameless')
        oxygen.attributes = {'colname': 'Sbeox0ML/L', 'units': 'ml/l', 'long_name': 'Oxygen, SBE 43'}

        # The colname attribute must be the keys that DictReader returns - the keys of this dictionary will be the Parameter names in stoqs
        parmDict = {'pressure': pr, 'TEMP': temp, 'PSAL': sal, 'xmiss': xmiss, 'ecofl': ecofl, 'oxygen': oxygen, 'wetstar': wetstar}

        return parmDict

    def load_data(self, lat, lon, depth, mtime, parmNameValues):
        '''
        Load the data values recorded at the bottle trips so that we have some InstantPoints to 
        hang off for our Samples.  This is necessary as typically data are continuously acquired on the 
        down cast and bottles are tripped on the upcast with data collected just at the time of the bottle trip.  
        @parmNameValues is a list of 2-tuples of (ParameterName, Value) measured at the time and location specified by
        @lat decimal degrees
        @lon decimal degrees
        @mtime Python datetime.datetime object
        @depth in meters
        '''

        # Sanity check to prevent accidental switching of lat & lon
        if lat < -90 or lat > 90:
            logger.exception("lat = %f.  Can't load this!", lat)
            sys.exit(-1)

        try:
            measurement = self.createMeasurement(mtime=mtime, depth=depth, lat=lat, lon=lon)
        except SkipRecord as e:
            logger.info(e)
        except Exception as e:
            logger.error(e)
            sys.exit(-1)
        else:
            logger.debug("longitude = %s, latitude = %s, mtime = %s, depth = %s", lon, lat, mtime, depth)

        loaded = 0
        for pn,value in parmNameValues:
            logger.debug("pn = %s", pn)
            try:
                mp, _ = MeasuredParameter.objects.using(self.dbAlias).get_or_create(measurement = measurement,
                                                  parameter = self.getParameterByName(pn), datavalue = value)
            except Exception as e:
                logger.error(e)
                logger.exception("Bad value (id=%(id)s) for %(pn)s = %(value)s", {'pn': pn, 'value': value, 'id': mp.pk})
            else:
                loaded += 1
                logger.debug("Inserted value (id=%(id)s) for %(pn)s = %(value)s", {'pn': pn, 'value': value, 'id': mp.pk})

    def load_btl(self, lat, lon, depth, timevalue, bottleName):
        '''
        Load a single Niskin Bottle sample
        '''

        # Get the Activity from the Database
        try:
            activity = Activity.objects.using(self.dbAlias).get(name__contains=self.activityName)
            logger.debug('Got activity = %s', activity)
        except ObjectDoesNotExist:
            logger.warn('Failed to find Activity with name like %s.  Skipping GulperLoad.', self.activityName)
            return
        except MultipleObjectsReturned:
            logger.warn('Multiple objects returned for name__contains = %s.  Selecting one by random and continuing...', self.activityName)
            activity = Activity.objects.using(self.dbAlias).filter(name__contains=self.activityName)[0]
        
        # Get or create SampleType for Niskin
        (sample_type, created) = SampleType.objects.using(self.dbAlias).get_or_create(name=NISKIN)
        logger.debug('sampletype %s, created = %s', sample_type, created)
        # Get or create SamplePurpose for Niskin
        (sample_purpose, created) = SamplePurpose.objects.using(self.dbAlias).get_or_create(name = 'StandardDepth')
        logger.debug('samplepurpose %s, created = %s', sample_purpose, created)
        try:
            ip, _ = get_closest_instantpoint(self.activityName, timevalue, self.dbAlias)
            point = 'POINT(%s %s)' % (lon, lat)
            Sample.objects.using(self.dbAlias).get_or_create( name = bottleName,
                                                                    depth = str(depth),     # Must be str to convert to Decimal
                                                                    geom = point,
                                                                    instantpoint = ip,
                                                                    sampletype = sample_type,
                                                                    samplepurpose = sample_purpose,
                                                                    volume = 20000.0
                                                                )
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
        logger.debug('tmpFile = %s', tmpFile)
        tmpFH = open(tmpFile, 'w')
        lastLine = ''
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
                    if _debug: print 'Writing ' + lastLine + line
                    tmpFH.write(lastLine + line + '\n')
                m = re.match('\d\d:\d\d:\d\d', line.strip())
                if m:
                    # Append Time string to last line & write to tmpFile
                    if _debug: print 'm.group(0) = ', m.group(0)
                    if _debug: print 'Writing ' + lastLine + m.group(0) + '\n'
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
        # Bottle records:
        # {'': None, 'Par': '1.0000e-12', 'PrDM': '201.442', 'Sbeox0Mm/Kg': '85.099', 'Potemp190C': '8.4225', 'Xmiss': '76.5307', 'Sigma-\xe911': '26.3792', 'DepSM': '199.859', 'Sbeox0PS': '29.72432', 'Sal11': '33.9416', 'V2': '1.0162', 'V1': '3.8616', 'C1S/m': '3.571764', 'T090C': '8.4430', 'V4': '0.0000', 'V5': '0.1305', 'V6': '2.6264', 'Date': 'Feb-04-2012', 'C0S/m': '3.571260', 'Bat': '1.0699', 'FlECO-AFL': '0.4249', 'Bottle': '1', 'Time': '09:20:05', 'Position': '(avg)', 'Sigma-\xe900': '26.3752', 'Sbeox0ML/L': '1.95575', 'Sal00': '33.9365', 'AltM': '52.53', 'Upoly0': '0.0002000', 'Scan': '14341', 'Sbeox0V': '1.0159', 'Potemp090C': '8.4223', 'V3': '0.0370', 'TimeJ': '35.722228', 'T190C': '8.4432'}

        for r in csv.DictReader(open(tmpFile), delimiter=' ', skipinitialspace=True):
            dt = datetime(year, 1, 1, 0, 0, 0) + timedelta(days=float(r['TimeJ'])) - timedelta(days=1)
            if not self.startDatetime:
                self.startDatetime = dt
        self.endDatetime = dt
        self.platform = self.getPlatform(self.platformName, self.platformTypeName)
        self.activitytypeName = 'CTD upcast'

        # Bottle samples are to be loaded after downcast data are loaded so that we can use the same activity
        try:
            activity = Activity.objects.using(self.dbAlias).get(name__contains=self.activityName)
            logger.debug('Got activity = %s', activity)
            self.activity = activity
        except ObjectDoesNotExist:
            logger.warn('Failed to find Activity with name like %s.  Expected that downcast was data before loading bottles.', self.activityName)
            logger.info('Creating Activity for these bottles')
            self.createActivity()
            ##raise SingleActivityNotFound('Failed to find Activity with name like %s' % self.activityName)
        except MultipleObjectsReturned:
            logger.error('Multiple objects returned for name__contains = %s.'
                         'This should not happen.  Fix the database and the reason for this.',
                         self.activityName)
            raise SingleActivityNotFound('Multiple objects returned for name__contains = %s' % self.activityName)

        parmDict = self.buildParmDict()
        logger.debug('Calling addParameters for parmDict = %s', parmDict)
        self.include_names = parmDict.keys()
        self.addParameters(parmDict)

        for r in csv.DictReader(open(tmpFile), delimiter=' ', skipinitialspace=True):
            dt = datetime(year, 1, 1, 0, 0, 0) + timedelta(days=float(r['TimeJ'])) - timedelta(days=1)
            ##esDiff = dt - datetime(1970, 1, 1, 0, 0, 0)
            ##es = 86400 * esDiff.days + esDiff.seconds
            bName = r['Bottle']

            logger.debug('r = %s', r)
            # Load data 
            parmNameValues = []
            for name in parmDict.keys():
                logger.debug('name = %s, parmDict[name].attributes = %s', name, parmDict[name].attributes)
                try:
                    parmNameValues.append((name, float(r[parmDict[name].attributes['colname']])))
                except KeyError as e:
                    # Accomodations for sub compact CTD
                    if parmDict[name].attributes['colname'] == 'T190C':
                        parmNameValues.append((name, float(r['Tv290C'])))
                    elif parmDict[name].attributes['colname'] == 'PrDM':
                        parmNameValues.append((name, float(r['PrdM'])))
                    elif parmDict[name].attributes['colname'] == 'FlECO-AFL':
                        continue
                    elif parmDict[name].attributes['colname'] == 'WetStar':
                        continue
                    else:
                        raise KeyError(e)

            self.load_data(lat, lon, float(r['DepSM']), dt, parmNameValues)

            # Load Bottle sample
            if _debug:
                logger.info('Calling load_btl(%s,%s,%s,%s,%s)', lat, lon, float(r['DepSM']), dt, bName)
            self.load_btl(lat, lon, float(r['DepSM']), dt, bName)

        os.remove(tmpFile)

    def process_btl_files(self, seabirdFileList=()):
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

        If seabirdFileList is given then process through those files in the list, otherwise process all .btl files in 
        self.parentInDir.  This is handy for debugging in that only the files in the list are processed.
        '''
        try:
            fileList = glob(os.path.join(self.parentInDir, 'pctd/*c*.btl'))
        except AttributeError:
            fileList = []
        if fileList:
            # Read files from local pctd directory
            fileList.sort()
            for bfile in fileList:
                self.activityName = bfile.split('/')[-1].split('.')[-2] 
                year, lat, lon = get_year_lat_lon(bfile)
                fh = open(bfile)
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
                bfile = link.get('href')
                if bfile.endswith('.btl'):
                    logger.debug("bfile = %s", bfile)
                    if bfile.split('/')[-1].split('.')[0] + '.nc' not in seabirdFileList:
                        logger.warn('Skipping %s as it is in not in seabirdFileList = %s', bfile, seabirdFileList)
                        continue

                    # btlUrl looks something like: http://odss.mbari.org/thredds/fileServer/CANON_september2012/wf/pctd/c0912c53.btl
                    btlUrl = self.tdsBase + 'fileServer/' +  self.pctdDir + bfile.split('/')[-1]
                    hdrUrl = self.tdsBase + 'fileServer/' +  self.pctdDir + ''.join(bfile.split('/')[-1].split('.')[:-1]) + '.hdr'
                    logger.info('btlUrl = %s', btlUrl)
    
                    self.activityName = bfile.split('/')[-1].split('.')[-2] 
                    year, lat, lon = get_year_lat_lon(hdrUrl = hdrUrl)
                    btlFH = urllib2.urlopen(btlUrl).read().splitlines()
                    try:
                        self.process_btl_file(btlFH, year, lat, lon)
                    except SingleActivityNotFound:
                        continue

        # TODO: Adjust Activity downcast + upcast(bottle trips) times to include all data


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
        parameter_value = row.get('Parameter Value')
        if not parameter_value:
            raise SubSampleLoadError("Must have a row['Parameter Value'] to load subsample")

        (sampleType, created) = SampleType.objects.using(self.dbAlias).get_or_create(name='subsample')
        (samplePurpose, created) = SamplePurpose.objects.using(self.dbAlias).get_or_create(name=row['Sample Type'])

        fd = None
        if row.get('Filter Diameter [mm]'):
            fd = float(row['Filter Diameter [mm]'])
        fps = None
        try:
            if row.get('Filter Pore Size [uM]'):
                fps = float(row['Filter Pore Size [uM]'])
        except KeyError:
            try:
                if row.get('Filter Pore Size [um]'):
                    fps = float(row['Filter Pore Size [um]'])
            except ValueError as e:
                # Likely a strange character present in a units string
                if row.get('Filter Pore Size [um]'):
                    fps = float(row.get('Filter Pore Size [um]').split()[0])
        except ValueError as e:
            # Likely a strange character present in a units string
            if row.get('Filter Pore Size [uM]'):
                fps = float(row.get('Filter Pore Size [uM]').split()[0])
            
        vol = row.get('Sample Volume [mL]')
        if not vol:
            if row.get('Sample Volume [m^3]'):
                vol = float(row.get('Sample Volume [m^3]')) * 1.e6     # A million ml per cubic meter
        if not vol:
            logger.warn('Sample Volume [mL] or Sample Volume [m^3] is not specified.'
                        ' Assigning default value of 280.'
                        ' PLEASE SPECIFY THE VOLUME IN THE SPREADSHEET.')
            vol = 280           # Default volume is 280 ml - this is a required field so display a warning

        sample = Sample(  instantpoint=parentSample.instantpoint,
                            depth=parentSample.depth,
                            geom=parentSample.geom,
                            name=parentSample.name,
                            volume=float(vol),
                            filterdiameter=fd,
                            filterporesize=fps,
                            laboratory=row['Laboratory'],
                            researcher=row['Researcher'],
                            sampletype=sampleType,
                            samplepurpose=samplePurpose)
        sample.save(using=self.dbAlias)

        samplerelationship = SampleRelationship(child=sample, parent=parentSample)
        samplerelationship.save(using=self.dbAlias)
                  
        parameter_name = row.get('Parameter Name')
        spaceRemoveMsg = ''
        if parameter_name.find(' ') != -1:
            spaceRemoveMsg = ("row['Parameter Name'] = %s contains a space. Replacing"
                              " with '_' before adding to STOQS." % parameter_name)
            logger.debug(spaceRemoveMsg)
            parameter_name = parameter_name.replace(' ', '_')

        if '(' in parameter_name or ')' in parameter_name:
            parenRemoveMsg = ("row['Parameter Name'] = %s contains ( or ). Removing"
                              " them before adding to STOQS." % parameter_name)
            logger.debug(parenRemoveMsg)
            parameter_name = parameter_name.replace('(', '').replace(')', '')

        parameter_units = row.get('Parameter Units')
        (parameter, created) = Parameter.objects.using(self.dbAlias).get_or_create(name=parameter_name, units=parameter_units)
        logger.debug('parameter, created = %s, %s', parameter, created)
        if created and spaceRemoveMsg:
            logger.info(spaceRemoveMsg)
    
        analysisMethod = None
        if row['Analysis Method']:
            (analysisMethod, created) = AnalysisMethod.objects.using(self.dbAlias
                    ).get_or_create(name=removeNonAscii(row['Analysis Method']))

        sp = SampledParameter(sample=sample, parameter=parameter, 
                datavalue=parameter_value, analysismethod=analysisMethod)
        try:
            sp.save(using=self.dbAlias)
        except ValidationError as e:
            logger.warn(str(e))

        return parameter
                                
    def delete_subsample(self, parentSample, row):
        '''
        Delete the subsample represented by the data in @row from the database
        '''
        parameter_value = row.get('Parameter Value')
        if not parameter_value:                 # Must have a value to proceed
            return

        fd = None
        if row['Filter Diameter [mm]']:
            fd = float(row['Filter Diameter [mm]'])
        fps = None
        if row['Filter Pore Size [uM]']:
            fps = float(row['Filter Pore Size [uM]'])

        samples = Sample.objects.using(self.dbAlias).filter(
                            instantpoint=parentSample.instantpoint,
                            depth=parentSample.depth,
                            geom=parentSample.geom,
                            volume=float(row['Sample Volume [mL]']),
                            filterdiameter=fd,
                            filterporesize=fps,
                            laboratory=row['Laboratory'],
                            researcher=row['Researcher'],
                            )
        if not samples:
            logger.debug('No samples returned from query of parentSample = %s and row = %s', parentSample, row)
            return

        if len(samples) == 1:
            logger.debug('Deleting subsample %s from database %s', samples[0], self.dbAlais)
            samples[0].delete(using=self.dbAlias)
        else:
            logger.warn('More than one subsample returned for query of parentSample = %s and row = %s', parentSample, row)
            logger.debug('samples.query = %s', str(samples.query))
            logger.warn('Removing them all...')
            for s in samples:
                logger.debug('s.id = %s', s.id)
                s.delete(using=self.dbAlias)

    def process_subsample_file(self, fileName, unloadFlag=False):
        '''
        Open .csv file and load the data, matching to existing Sample.
        The format of the file is as defined by Julio's work.  The first few records look like:

            Cruise,Bottle Number,Sample Type,Sample Volume [mL],Filter Diameter [mm],Filter Pore Size [uM],Parameter Name,Parameter Value,Parameter Units,MBARI BOG Taxon Code,Laboratory,Researcher,Analysis Method,Comment Name,Comment Value
            2011_074_02_074_02,0,random,1500,25,30,B1006 barnacles,0.218,OD A450 nm,,Vrijenhoek,Harvey,Sandwich Hybridization Assay,,
            2011_074_02_074_02,0,random,1500,25,30,M2B mussels,0.118,OD A450 nm,,Vrijenhoek,Harvey,Sandwich Hybridization Assay,,

        If @unloadFlag is True then delete the subsamples from @fileName from the database.  This is useful for testing.
        '''
        subCount = 0
        p = None
        loadedParentSamples = []
        parameterCount = {}
        for r in csv.DictReader(open(fileName)):
            logger.debug(r)
            aName = r['Cruise']

            if aName == '2011_257_00_257_01':
                aName = '2011_257_00_257_00'      # Correct a typo in Julio's spreadsheet

            try:
                # Try first with %.1f formatted bottle number for Gulper - TODO: Deprecate this!
                sample_name = '%.1f' % float(r['Bottle Number'])
                parentSample = Sample.objects.using(self.dbAlias).filter( 
                        instantpoint__activity__name__icontains=aName, 
                        name=sample_name)[0]
            except IndexError:
                try:
                    # Try without formatted %.1 for bottle number
                    sample_name = r['Bottle Number']
                    parentSample = Sample.objects.using(self.dbAlias).filter(
                            instantpoint__activity__name__icontains=aName, 
                            name=sample_name)[0]
                except IndexError:
                    logger.error('Parent Sample not found for Cruise (Activity Name) = %s, Bottle Number = %s', aName, r['Bottle Number'])
                    continue
                    ##sys.exit(-1)
            except KeyError:
                # Special for Plankton Pump, Comment Value is 'Relative Depth'
                sample_name = r.get('Comment Value')
                logger.debug('aName=%s, name=%s', aName, sample_name)
                try:
                    parentSample = Sample.objects.using(self.dbAlias).get(
                        sampletype__name=PLANKTONPUMP,
                        instantpoint__activity__name__icontains=aName, 
                        name=sample_name)
                except ObjectDoesNotExist:
                    logger.warn('Parent Sample not found for Activity %s, name %s. Skipping.', 
                            aName, sample_name)

            except ValueError as e:
                # Likely a 'NetTow' string in the Bottle Number column
                if r['Bottle Number'] == 'NetTow':
                    try:
                        # Convention is one NetTow per cast, given them all a name of '1'
                        sample_name = '1'
                        parentSample = Sample.objects.using(self.dbAlias).select_related(
                                'instantpoint__activity').filter(
                                instantpoint__activity__name__icontains=aName + '_NetTow1', )[0]
                    except IndexError as e:
                        logger.warn('Parent Sample not found for Activity %s. Skipping.', aName)
                        continue
                else:
                    raise e

            if unloadFlag:
                # Unload subsample
                self.delete_subsample(parentSample, r)
            else:
                if p and subCount and parentSample not in loadedParentSamples:
                    # Useful logger output when parentSample changes - more useful when spreadsheet is sorted by parentSample
                    logger.info('%d subsamples loaded of %s from %s', subCount, p.name, os.path.basename(fileName))

                    logger.info('Loading subsamples of parentSample (activity, bottle/name) = (%s, %s)', aName, sample_name)
                    subCount = 0

                try:
                    # Load subsample
                    p = self.load_subsample(parentSample, r)
                except SubSampleLoadError as e:
                    logger.warn(e)
                    continue
                else:
                    subCount = subCount + 1
                    try:
                        parameterCount[p] += 1
                    except KeyError:
                        parameterCount[p] = 0

                    loadedParentSamples.append(parentSample)
   
        if not unloadFlag: 
            # Last logger info message and finish up the loading for this file
            logger.info('%d subsamples loaded of %s from %s', subCount, p.name, os.path.basename(fileName))

            self.assignParameterGroup(parameterCount, groupName=SAMPLED)
            self.postProcess(parameterCount)

    def postProcess(self, parameterCount):
        '''
        Perform step(s) following subsample loads, namely inserting/updating records in the ActivityParameter
        table.  The updateActivityParameterStats() method in STOQS_Loader expects a hash of parameters
        that are unique to an activity that is an attribute of self.
        '''
        for row in SampledParameter.objects.using(self.dbAlias).values('sample__instantpoint__activity__pk').distinct():
            a_id = row['sample__instantpoint__activity__pk']
            logger.debug('a_id = %d', a_id)
            self.activity = Activity.objects.using(self.dbAlias).get(pk=a_id)
            self.updateActivityParameterStats(parameterCount, sampledFlag=True)


if __name__ == '__main__':

    # Accept optional arguments of dbAlias, input data directory name, and output directory name
    # If not specified then 'default' and the current directory is used
    try:
        dbAlias = sys.argv[1]
    except IndexError:
        dbAlias = 'stoqs_dorado2011_s100'

    try:
        unload = sys.argv[2]
    except IndexError:
        pass
    else:
        ssl = SubSamplesLoader('', '', dbAlias=dbAlias)
        ssl.process_subsample_file('2011_AUVdorado_Samples_Database.csv', True)
        sys.exit(0)
        

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
    auv_file = 'Dorado389_2010_277_01_277_01_decim.nc'
    dbAlias = 'stoqs_oct2010'

    aName = file

    load_gulps(aName, auv_file, dbAlias)

