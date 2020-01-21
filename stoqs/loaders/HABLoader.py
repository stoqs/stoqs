#!/usr/bin/env python

__author__ = "Danelle Cline"
__copyright__ = "Copyright 2012, MBARI"
__license__ = "GPL"
__maintainer__ = "Danelle Cline"
__email__ = "dcline at mbari.org"
__status__ = "Development"
__doc__ = '''

This loader loads water sample data from the Southern California Coastal Ocean Observing System (SCCOS)
Harmful Algal Bloom project into the STOQS database. Each row is saved as a Sample, and each
sample measurement (column), e.g. nitrate, chlorophyll, etc. is saved as a Measurement.

To run the loader

1. Downloaded a csv from http://www.sccoos.org/query/?project=Harmful%20Algal%20Blooms&
   Selecting some, or all desired measurements, and save to CSV file format
2. Create a stoqs database called stoqs_habs
3. Load with:

   HABLoader.py <filename.csv> stoqs_habs

@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

# Force lookup of models to THE specific stoqs module.
import os
import sys
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE']='settings.local'
project_dir = os.path.dirname(__file__)
# Add parent dir to pythonpath so that we can see the loaders and stoqs modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../") )
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from stoqs import models as m
from loaders import STOQS_Loader, SkipRecord
from datetime import datetime, timedelta
from pydap.model import BaseType
from django.contrib.gis.geos import fromstr, Point, LineString

import time
import numpy
import csv
import urllib.request, urllib.error, urllib.parse
import logging
from glob import glob
from tempfile import NamedTemporaryFile
import re
import pprint
import pytz

# Set up logging
logger = logging.getLogger('loaders')
logger.setLevel(logging.ERROR)

# When settings.DEBUG is True Django will fill up a hash with stats on every insert done to the database.
# "Monkey patch" the CursorWrapper to prevent this.  Otherwise we can't load large amounts of data.
# See http://stackoverflow.com/questions/7768027/turn-off-sql-logging-while-keeping-settings-debug
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.utils import CursorWrapper


if settings.DEBUG:
    BaseDatabaseWrapper.make_debug_cursor = lambda self, cursor: CursorWrapper(cursor, self)

class ClosestTimeNotFoundException(Exception):
    pass

class SingleActivityNotFound(Exception):
    pass


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

class HABLoader(STOQS_Loader):
    '''
    Inherit database loding functions from STOQS_Loader and use its constructor
    '''
    parameter_dict={} # used to cache parameter objects 
    standard_names = {} # should be defined for each child class
    include_names=[] # names to include, if set it is used in conjunction with ignored_names
    # Note: if a name is both in include_names and ignored_names it is ignored.
    ignored_names=[]  # Should be defined for each child class
    loaded = 0
    mindepth = 8000.0
    maxdepth = -8000.0
    parmCount = {}
    parameterCount = {}
    
    def __init__(self, activityName, platformName,  dbAlias='default', campaignName=None, 
                activitytypeName=None, platformColor=None, platformTypeName=None, 
                startDatetime=None, endDatetime=None, dataStartDatetime=None ):
        '''
        Build a set of standard names using the dataset.
        The activity is saved, as all the data loaded will be a set of instantpoints
        that use the specified activity.
        
        @param activityName: A string describing this activity
        @param platformName: A string that is the name of the platform. If that name for a Platform exists in the DB, it will be used.
        @param platformColor: An RGB hex string represnting the color of the platform. 
        @param dbAlias: The name of the database alias as defined in settings.py
        @param campaignName: A string describing the Campaign in which this activity belongs, If that name for a Campaign exists in the DB, it will be used.
        @param activitytypeName: A string such as 'mooring deployment' or 'AUV mission' describing type of activity, If that name for a ActivityType exists in the DB, it will be used.
        @param platformTypeName: A string describing the type of platform, e.g.: 'mooring', 'auv'.  If that name for a PlatformType exists in the DB, it will be used.
        @param startDatetime: A Python datetime.dateime object specifying the start date time of data to load
        @param endDatetime: A Python datetime.dateime object specifying the end date time of data to load
        @param dataStartDatetime: A Python datetime.dateime object specifying the start date time of data to append to an existing Activity
        
        '''
        self.campaignName = campaignName
        self.activitytypeName = activitytypeName
        self.platformName = platformName
        self.platformColor = platformColor
        self.dbAlias = dbAlias
        self.platformTypeName = platformTypeName
        self.activityName = activityName
        self.startDatetime = startDatetime
        self.endDatetime = endDatetime
        self.dataStartDatetime = dataStartDatetime  # For when we append data to an existing Activity
        
    def initDB(self):
        '''Do the intial Database activities that are required before the data are processed: getPlatorm and createActivity.
        '''
        self.platform = self.getPlatform(self.platformName, self.platformTypeName)
        self.createActivity()
        self.add_parameters(self.ds)     
        #self.addResources()

    def load_measurement(self, lat, lon, depth, mtime, parmNameValues):
        '''
        Load the data values recorded for each loaction
        @parmNameValues is a list of 2-tuples of (ParameterName, Value) measured at the time and location specified by
        @lat decimal degrees
        @lon decimal degrees
        @mtime Python datetime.datetime object
        @depth in meters
        '''
        mt = None
        try:
            mt = self.createMeasurement(mtime = mtime,
                                        depth = depth,
                                        lat = lat,
                                        lon = lon)
            logger.info("measurement._state.db = %s", mt._state.db)
            
            if depth < self.mindepth:
                self.mindepth = depth
            if depth > self.maxdepth:
                self.maxdepth = depth
        except SkipRecord as e:
            logger.info(e)
        except Exception as e:
            logger.error(e)
            sys.exit(-1)
        else:
            logger.info("longitude = %s, latitude = %s, mtime = %s, depth = %s", lon, lat, mtime, depth)
            
        for pn,value in parmNameValues:
            logger.info("pn = %s", pn)
            logger.info("parameter._state.db = %s", self.getParameterByName(pn)._state.db)
            mp = m.MeasuredParameter(measurement = mt,
                                     parameter = self.getParameterByName(pn),
                                     datavalue = value) 
            
            try:
                mp.save(using=self.dbAlias)

            except ParameterNotFound:
                logger.error("Unable to locate parameter for %s, skipping", pn)
                continue
            except Exception as e:
                logger.error('Exception %s. Skipping this record.', e)
                logger.error("Bad value (id=%(id)s) for %(pn)s = %(value)s", {'pn': pn, 'value': value, 'id': mp.pk})
                continue
            else:
                self.loaded += 1
                logger.info("Inserted value (id=%(id)s) for %(pn)s = %(value)s", {'pn': pn, 'value': value, 'id': mp.pk})
                self.parmCount[pn] += 1
                if self.getParameterByName(pn) in self.parameterCount:
                    self.parameterCount[self.getParameterByName(pn)] += 1
                else:
                    self.parameterCount[self.getParameterByName(pn)] = 0

    
    def load_sample(self, lon, lat, depth, timevalue, bottleName):
        '''
        Load a single water sample
        '''
        # Get the Activity from the Database
        try:
            activity = m.Activity.objects.using(self.dbAlias).get(name__contains=self.activityName)
            logger.debug('Got activity = %s', activity)
        except ObjectDoesNotExist:
            logger.warn('Failed to find Activity with name like %s.  Skipping load.', self.activityName)
            return
        except MultipleObjectsReturned:
            logger.warn('Multiple objects returned for name__contains = %s.  Selecting one by random and continuing...', self.activityName)
            activity = m.Activity.objects.using(self.dbAlias).filter(name__contains=self.activityName)[0]
        
        # Get or create SampleType
        (sample_type, created) = m.SampleType.objects.using(self.dbAlias).get_or_create(name = 'Pier')
        logger.debug('sampletype %s, created = %s', sample_type, created)

        # Get or create SamplePurpose
        (sample_purpose, created) = m.SamplePurpose.objects.using(self.dbAlias).get_or_create(name = 'StandardDepth')
        logger.debug('samplepurpose %s, created = %s', sample_purpose, created)
        try:
            ip, seconds_diff = get_closest_instantpoint(self.activityName, timevalue, self.dbAlias)
            point = Point(lon, lat)
            stuple = m.Sample.objects.using(self.dbAlias).get_or_create( name = bottleName,
                                                                    depth = str(depth),     # Must be str to convert to Decimal
                                                                    geom = point,
                                                                    instantpoint = ip,
                                                                    sampletype = sample_type,
                                                                    samplepurpose = sample_purpose,
                                                                    volume = 20000.0
                                                                )
            rtuple = m.Resource.objects.using(self.dbAlias).get_or_create( name = 'Seconds away from InstantPoint',
                                                                    value = seconds_diff
                                                                    )

            # 2nd item of tuples will be True or False dependending on whether the object was created or gotten
            logger.info('Loaded Sample %s with Resource: %s', stuple, rtuple)
        except ClosestTimeNotFoundException:
            logger.info('ClosestTimeNotFoundException: A match for %s not found for %s', timevalue, activity)
        else:
            logger.info('Loaded Bottle name = %s', bottleName)      

    def process_csv_file(self, fh):
        '''
        Iterate through lines of iterator to csv file and pull out data for loading into STOQS
        '''
        ds = {}
        DA = BaseType('nameless')
        DA.attributes = {'units': 'ng ml-1 ' , 
                         'long_name': 'Domoic Acid', 
                         'standard_name': 'domoic_acid',
                         'type': 'float', 
                         'description': 'Domoic acid' ,
                         'origin': 'www.sccoos.org' }
        PD = BaseType('nameless')
        PD.attributes = {'units': 'cells l-1', 
                         'long_name': 'Pseudo-nitzschia delicatissima group', 
                         'standard_name': 'pseudo_nitzschia_delicatissima', 
                         'name':  'pseudo_nitzschia_delicatissima' ,
                         'type':  'float' ,
                         'description': 'Pseudo-nitzschia delicatissima group (cells/L)' ,
                         'origin': 'www.sccoos.org' 
                         } 
        PA = BaseType('nameless')
        PA.attributes = {'units': 'cells l-1', 
                         'long_name': 'Pseudo-nitzschia seriata group', 
                         'standard_name': 'pseudo_nitzschia_seriata', 
                         'name':  'pseudo_nitzschia_seriata' ,
                         'type':  'float' ,
                         'description': 'Pseudo-nitzschia seriata group (cells/L)' ,
                         'origin': 'www.sccoos.org' 
                         }
        alexandrium = BaseType('nameless')
        alexandrium.attributes = {'units': 'cells l-1', 
                         'long_name': 'Alexandrium', 
                         'standard_name': 'alexandrium', 
                         'name':  'alexandrium' ,
                         'type':  'float' ,
                         'description': 'Alexandrium spp. (cells/L)' ,
                         'origin': 'www.sccoos.org' 
                         }
        phosphate = BaseType('nameless')
        phosphate.attributes = {'units': 'm-3 mol l-1', 
                         'long_name': 'Phosphate', 
                         'standard_name': 'phosphate_dissolved_in_seawater', 
                         'name':  'Phosphate' ,
                         'type':  'float' ,
                         'description': 'Phosphate (uM)' ,
                         'origin': 'www.sccoos.org' 
                         }
        ammonia = BaseType('nameless')
        ammonia.attributes = {'units': 'm-3 mol l-1', 
                         'long_name': 'Ammonia', 
                         'standard_name': 'ammonia_dissolved_in_seawater', 
                         'name':  'ammonia_dissolved_in_sewater' ,
                         'type':  'float' ,
                         'description': 'Ammonia (uM)' ,
                         'origin': 'www.sccoos.org' 
                         }
        silicate = BaseType('nameless')
        silicate.attributes = {'units': 'm-3 mol l-1', 
                         'long_name': 'Silicate', 
                         'standard_name': 'silicate_dissolved_in_seawater', 
                         'name':  'silicate_dissolved_in_seawater' ,
                         'type':  'float' ,
                         'description': 'Silicate (uM)' ,
                         'origin': 'www.sccoos.org' 
                         }
        chlorophyll = BaseType('nameless')
        chlorophyll.attributes = {'units': 'kg m-3', 
                         'long_name': 'Chlorophyll', 
                         'standard_name': 'mass_concentration_of_chlorophyll_in_sea_water', 
                         'name':  'mass_concentration_of_chlorophyll_in_sea_water' ,
                         'type':  'float' ,
                         'description': 'Chlorophyll (kg/m3)' ,
                         'origin': 'www.sccoos.org' 
                         }

        prorocentrum = BaseType('nameless')
        prorocentrum.attributes = {'units': 'cells l-1', 
                         'long_name': 'Prorocentrum', 
                         'standard_name': 'mass_concentration_of_prorocentrum_in_sea_water', 
                         'name':  'mass_concentration_of_prorocentrum_in_sea_water' ,
                         'type':  'float' ,
                         'description': 'Prorocentrum spp. (cells/L)' ,
                         'origin': 'www.sccoos.org' 
                         }

        self.ds = { 'Domoic Acid (ng/mL)': DA, 'Pseudo-nitzschia seriata group (cells/L)': PA,
                    'Pseudo-nitzschia delicatissima group (cells/L)': PD,
                    'Phosphate (uM)': phosphate,
                    'Silicate (uM)': silicate, 'Ammonia (uM)': ammonia,
                    'Chlorophyll (mg/m3)': chlorophyll, 'Chlorophyll 1 (mg/m3)': chlorophyll,
                    'Chlorophyll 2 (mg/m3)': chlorophyll ,
                    'Alexandrium spp. (cells/L)': alexandrium 
                    }
                    
   
        self.include_names = ['Pseudo-nitzschia seriata group (cells/L)',
                              'Pseudo-nitzschia delicatissima group (cells/L)',
                              'Domoic Acid (ng/mL)',
                              'Chlorophyll (mg/m3)', 'Chlorophyll 1 (mg/m3)', 'Chlorophyll 2 (mg/m3)',
                              'Prorocentrum spp. (cells/L)', 'Silicate (uM)', 'Ammonia (uM)',
                              'Nitrate (uM)', 'Phosphate (uM)', 
                              'Alexandrium spp. (cells/L)']

        self.initDB()

        for pn in self.include_names:
            self.parmCount[pn] = 0

        reader = csv.reader(fh)
        for line in fh:
            # Skip all lines that don't begin with '"' nor ' ' then open that with csv.DictReader
            if not line.startswith('"') and not line.startswith(' '):
                titles = next(reader)
                reader = csv.DictReader(fh, titles)
                for r in reader:
                    year = int(r['year'])
                    month = int(r['month'])
                    day = int(r['day'])
                    time = r['time']
                    lat = float(r['latitude'])
                    lon = float(r['longitude'])
                    depth = float(r['depth (m)'])
                    location = r['location']
                    hours = int(time.split(':')[0])
                    mins = int(time.split(':')[1])
                    secs = int(time.split(':')[2])

                    parmNameValues = []
                    for name in list(self.ds.keys()):                  
                        if name.startswith('Chlorophyll'):
                            parmNameValues.append((name, 1e-5*float(r[name])))
                        else:
                           parmNameValues.append((name, float(r[name])))

                    # Check to make sure all data from this file are from the same location.
                    # The program could be modified to read data in one file from multiple locations by reading data into a hash keyed by location name 
                    # and then stepping through each key of the hash saving the data for each location into it's own activity.  For now just require
                    # each data file to have data from just one location.
                    try: 
                        if lat != lastlat or lon != lastlon:
                            logger.error("lat and lon are not the same for location = %s and lastlocation = %s.  The input data should have just one location." % (location, lastlocation))
                            sys.exit(-1)
                    except NameError as e:
                        # Expected first time through when lastlon & lastlat don't yet exist
                        pass

                    # Load data 
                    dt = datetime(year, month, day, hours, mins, secs)    
                    self.load_measurement(lon, lat, depth, dt, parmNameValues)

                    # Load sample
                    bName = dt.isoformat()
                    self.load_sample(lon, lat, depth, dt, bName)

                    lastlat = lat
                    lastlon = lon
                    lastlocation = location


        logger.info("Data load complete, %d records loaded.", self.loaded)        
        fh.close()
  
        # Update the Activity with information we now have following the load
        # Careful with the structure of this comment.  It is parsed in views.py to give some useful links in showActivities()
        newComment = "%d MeasuredParameters loaded. Loaded on %sZ" % (self.loaded, datetime.utcnow())
        logger.info("runHABLoader(): Updating its comment with newComment = %s", newComment)
        aName = location
    
        num_updated = m.Activity.objects.using(self.dbAlias).filter(id = self.activity.id).update(
                        name = aName,
                        comment = newComment,
                        maptrack = None,
                        mappoint = Point(lon, lat),
                        mindepth = self.mindepth,
                        maxdepth = self.maxdepth,
                        num_measuredparameters = self.loaded,
                        loaded_date = datetime.utcnow())
        self.updateActivityParameterStats(self.parameterCount)
        self.updateCampaignStartEnd() 
      

    def process(self, file):
        '''
        Insert a Sample record to the database for each location in csv file.  
        Assumes that *.csv file exists on the local filesystem 

        *.csv file look like:

"Project: Harmful Algal Blooms"
"Calibrated: No"
"Requested start: 2011-10-05 13:00:00"
"Requested end: 2012-11-28 21:03:00"
"Request time: Wed, 28 Nov 2012 21:03:31 +0000"
"Other Notes: All times provided in UTC"

year,month,day,time,latitude,longitude,depth (m),location,Domoic Acid (ng/mL),Pseudo-nitzschia delicatissima group (cells/L),Pseudo-nitzschia seriata group (cells/L)
2011,10,05,13:00:00,36.958,-122.017,0.0,Santa Cruz Wharf,0.92 ,NaN,47200.0000 
2011,10,12,12:55:00,36.958,-122.017,0.0,Santa Cruz Wharf,0.06 ,NaN,0.0000 
2011,10,19,13:09:00,36.958,-122.017,0.0,Santa Cruz Wharf,0.26 ,NaN,13450.0000 
2011,10,26,14:10:00,36.958,-122.017,0.0,Santa Cruz Wharf,0.05 ,NaN,900.0000 

'''
        fh = open(file)
        try:
            self.process_csv_file(fh)
        except SingleActivityNotFound:
            logger.error('Invalid csv file %s', file)
            exit(-1)

if __name__ == '__main__':

    _debug = True

    try:
        file = sys.argv[1]
    except IndexError:
        logger.error('Must specify csv file as first argument')
        exit(-1)

    try:
        dbAlias = sys.argv[2]
    except IndexError:
        dbAlias = 'stoqs_habs'

    #datetime.now(pytz.utc)
    campaignName = 'SCCOS HABS 2011-2012'
    activityName = 'Sample'
    activitytypeName = 'WaterAnalysis'
    platformName = 'Pier'
    platformColor = '11665e'
    platformTypeName = 'pier'
    start = datetime(2011, 0o1, 0o1)
    end = datetime(2012,12,31)
    
    sl = HABLoader(activityName, platformName,  dbAlias, campaignName, activitytypeName,platformColor, platformTypeName, start, end)
    sl.process(file)


