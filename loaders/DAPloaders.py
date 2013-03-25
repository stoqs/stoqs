#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2011, MBARI"
__credits__ = ["Chander Ganesan, Open Technology Group"]
__license__ = "GPL"
__version__ = "$Revision: 1.1 $".split()[1]
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

The DAPloaders module contains classes for reading data from OPeNDAP servers and
loading into the STOQS database.  It assumes that all data are on the 4 spatial-
temporal dimensions as defined in the COARDS/CF convention.  There are custom
derived classes here that understand, Mooring (Station and StationProfile), AUV 
and Glider (Trajectory) CDM Data Types.

Mike McCann
MBARI Dec 29, 2011

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

# Force lookup of models to THE specific stoqs module.
import os
import sys
from django.contrib.gis.geos import GEOSGeometry, LineString
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # settings.py is one dir up
from django.conf import settings

from django.contrib.gis.geos import Point
from django.db.utils import IntegrityError
from django.db import connection, transaction
from stoqs import models as m
from datetime import datetime, timedelta
from django.core.exceptions import ObjectDoesNotExist
from pydap.client import open_url
import pydap.model
import time
from decimal import Decimal
import math, numpy
from coards import to_udunits, from_udunits
import csv
import urllib2
import logging
import socket
import seawater.csiro as sw
from utils.utils import percentile, median, mode, simplify_points
from loaders import STOQS_Loader, SkipRecord, missing_value


# Set up logging
logger = logging.getLogger('__main__')
logger.setLevel(logging.INFO)

# When settings.DEBUG is True Django will fill up a hash with stats on every insert done to the database.
# "Monkey patch" the CursorWrapper to prevent this.  Otherwise we can't load large amounts of data.
# See http://stackoverflow.com/questions/7768027/turn-off-sql-logging-while-keeping-settings-debug
from django.db.backends import BaseDatabaseWrapper
from django.db.backends.util import CursorWrapper

if settings.DEBUG:
    BaseDatabaseWrapper.make_debug_cursor = lambda self, cursor: CursorWrapper(cursor, self)


class ParameterNotFound(Exception): 
    pass


class NoValidData(Exception): 
    pass


class Base_Loader(STOQS_Loader):
    '''
    A base class for data load operations.  This shouldn't be instantiated directly,
    instead a loader for a particular platform should inherit from it.  Since 
    each platform could have its own parameters, etc. each platform (at a minimum) 
    should declare the overridden names, ignored names, etc..
    The time bounds of an Activities can be specified in two ways:
    1. By specifying startDatetime and endDatetime.  This is handy for extracting a subset
       of data from an OPeNDAP data source, e.g. aggregated Mooring data, to populate a
       stoqs database that is specific for a month
    2. By setting startDatetime and endDatetime to None, in which case the start and end
       times are defined by the start and end of the data in the specified url
    A third time parameter (dataStartDatetime) can be specified.  This is used for when
    data is to be appended to an existing activity, such as for the realtime tethys loads
    as done by the monitorTethys.py script in the MBARItracking/sensortracks folder.
    '''
    parameter_dict={} # used to cache parameter objects 
    standard_names = {} # should be defined for each child class
    include_names=[] # names to include, if set it is used in conjunction with ignored_names
    # Note: if a name is both in include_names and ignored_names it is ignored.
    ignored_names=[]  # Should be defined for each child class
    global_ignored_names = ['longitude','latitude', 'time', 'Time',
                'LONGITUDE','LATITUDE','TIME', 'NominalDepth', 'esecs', 'Longitude', 'Latitude',
                'DEPTH','depth'] # A list of parameters that should not be imported as parameters
    global_dbAlias = ''
    def __init__(self, activityName, platformName, url, dbAlias='default', campaignName=None, 
                activitytypeName=None, platformColor=None, platformTypeName=None, 
                startDatetime=None, endDatetime=None, dataStartDatetime=None, stride=1 ):
        '''
        Given a URL open the url and store the dataset as an attribute of the object,
        then build a set of standard names using the dataset.
        The activity is saved, as all the data loaded will be a set of instantpoints
        that use the specified activity.
        stride is used to speed up loads by skipping data.
        
        @param activityName: A string describing this activity
        @param platformName: A string that is the name of the platform. If that name for a Platform exists in the DB, it will be used.
        @param platformColor: An RGB hex string represnting the color of the platform. 
        @param url: The OPeNDAP URL for the data source
        @param dbAlias: The name of the database alias as defined in settings.py
        @param campaignName: A string describing the Campaign in which this activity belongs, If that name for a Campaign exists in the DB, it will be used.
        @param activitytypeName: A string such as 'mooring deployment' or 'AUV mission' describing type of activity, If that name for a ActivityType exists in the DB, it will be used.
        @param platformTypeName: A string describing the type of platform, e.g.: 'mooring', 'auv'.  If that name for a PlatformType exists in the DB, it will be used.
        @param startDatetime: A Python datetime.dateime object specifying the start date time of data to load
        @param endDatetime: A Python datetime.dateime object specifying the end date time of data to load
        @param dataStartDatetime: A Python datetime.dateime object specifying the start date time of data to append to an existing Activity
        @param stride: The stride/step size used to retrieve data from the url.
        
        '''
        self.campaignName = campaignName
        self.activitytypeName = activitytypeName
        self.platformName = platformName
        self.platformColor = platformColor
        self.dbAlias = dbAlias
        global_dbAlias = dbAlias
        self.platformTypeName = platformTypeName
        self.activityName = activityName
        self.startDatetime = startDatetime
        self.endDatetime = endDatetime
        self.dataStartDatetime = dataStartDatetime  # For when we append data to an existing Activity
        self.stride = stride
        
        
        self.url = url
        self.varsLoaded = []
        try:
            self.ds = open_url(url)
        except socket.error,e:
            logger.error('Failed in attempt to open url = %s', url)
            raise e

        self.ignored_names += self.global_ignored_names # add global ignored names to platform specific ignored names.
        self.build_standard_names()

    def initDB(self):
        '''Do the intial Database activities that are required before the data are processed: getPlatorm and createActivity.
        Can be overridden by sub class.  An overriding method can do such things as setting startDatetime and endDatetime.
        '''

        if self.checkForValidData():
            self.platform = self.getPlatform(self.platformName, self.platformTypeName)
            self.addParameters(self.ds)
            self.createActivity()
        else:
            raise NoValidData

        self.addResources()

    def _genData(self):
        '''
        Create a generator to retrieve data.  This is less than ideal, since all the data is still retrieved at once,
        which could require quite a bit of buffering.  However, this should work for all data sources,
        and provides a uniform dictionary that contains attributes and their associated values without the need
        to individualize code for each data source.  It seems most of these shortcomings are related to the
        pydap module.
        
        Chances are the loading of data will be slow - primarily due to the fact that the pydap module
        doesn't seem to behave as a true iterator in that it seems to pre-fetch data.
        '''

        keys = self.ds.keys()
        parts = {}
        start = 0
        data = []
        scalars = {}

        '''
        Get list of indices to read based on the start & end time and stride specified.
        Get the list first based on the start and end, then sub-sample with the stride.
        '''
        try:
            timeAxis = self.ds.TIME
        except AttributeError:
            try:
                timeAxis = self.ds.Time
            except AttributeError:
                try:
                    timeAxis = self.ds.time
                except AttributeError:
                    timeAxis = self.ds.esecs
    
        logger.debug('self.dataStartDatetime, timeAxis.units = %s, %s', self.dataStartDatetime, timeAxis.units)
        s = to_udunits(self.dataStartDatetime, timeAxis.units)

        logger.info("For dataStartDatetime = %s, the udnits value is %f", self.dataStartDatetime, s)
        if self.endDatetime:
            'endDatetime may be None, in which case just read until the end'
            e = to_udunits(self.endDatetime, timeAxis.units)
            logger.info("For endDatetime = %s, the udnits value is %f", self.endDatetime, e)
        else:
            e = timeAxis[-1]
            logger.info("endDatetime not given, using the last value of timeAxis = %f", e)

        tf = (s <= timeAxis) & (timeAxis <= e)      # This re
        tIndx = numpy.nonzero(tf == True)[0]
        logger.debug("tIndx = %s", tIndx)
        logger.debug("tIndx[0] = %i, tIndx[-1] = %i", tIndx[0], tIndx[-1])
        
        '''
        Build iterators for each of the parameters that will be returned.  This will allow us to iterate
        and retrieve a dictionary for each "row" of data from the data source.
        '''
        for k in keys:
            v = self.ds[k]
            logger.debug("k in keys = %s, shape = %s, type = %s", k, self.ds[k].shape, type(v))
            if k.find('%2E') != -1:
                logger.debug("Skipping variable %s that has '.' in it as TDS can't retrieve it anyway. Even Hyrax can't properly deliver dot-named variables to pydap.", k)
                continue

            # Only build iterators for included names and the required non-parameter coordinate variables in ignored_names
            if (len(self.include_names) and k not in self.include_names) and k not in self.ignored_names:
                logger.debug("Skipping %s as is not in our include list and is not ignored (i.e. a coordinate)", k)
                continue
            
            if type(v) is pydap.model.GridType:
                try:
                    v = self.ds[k][tIndx[0]:tIndx[-1]:self.stride]      # Subselect along the time axis
                except ValueError, err:
                    logger.error('''\nGot error '%s' reading data from URL: %s.", err, self.url
                    If it is: 'string size must be a multiple of element size' and the URL is a TDS aggregation
                    then the cache files must be removed and the tomcat hosting TDS restarted.''')
                    sys.exit(1)
                except pydap.exceptions.ServerError as e:
                    logger.exception('%s', e)
                    sys.exit(-1)
                    continue

                logger.debug("Loading %s into parts dictionary", k)
                parts[k] = iter(v[k][:])                # Load the dictionary of everything for this
                                            # variable (axes, etc.) into the parts dict.
            else:
                logger.debug("%s is not pydap.model.GridType, it is %s", v, type(v))
                logger.debug("self.ds[k][:].ndim = %s", self.ds[k][:].ndim)
                # TDS may fail here with a NPE for aggregated Dorado data for variables that may be missing.
                # Hitting a shoter aggregation seems to avoid these problems.
                ##v = self.ds[k][:]         # Get array from the BaseType axis variable
                if self.ds[k][:].ndim == 1:
                    'We have a 1-dimensional coordinate variable, construct the proper constrant expression'
                    try:
                        # This works for Trajectory data, (AUV, drifter, Glider, etc.)
                        logger.info("Reading binary equiv from %s.ascii?%s[%d:%d:%d]", self.url, k, tIndx[0], self.stride, tIndx[-1])
                        v = self.ds[k][tIndx[0]:tIndx[-1]:self.stride]      # Subselect along the time axis for BaseType variables
                    except pydap.exceptions.ServerError:
                        logger.debug("Got pydap.exceptions.ServerError.  Continuning to next key.")
                        continue                        # skip over variables with '.' (%2e) in name, as from Tethys

                    logger.debug("Loading %s into parts dictionary", k)
                    logger.debug("v = %s", v)
                    try:
                        parts[k] = iter(v)  
                    except TypeError:
                        continue                    # Likely "iteration over a 0-d array" resulting from a stride that's too big

                elif self.ds[k][:].ndim == 0:
                    logger.debug("Loading %s into scalars dictionary", k.lower())
                    scalars[k] = float(v[0])
                else:
                    logger.warn("v.ndim = %s (not 0 or 1) in trying to get part of %s", v.ndim, v)
                    continue

                ##raw_input('paused')

        # Now, deliver the rows
        while True:
            values = {}
            for k in parts.keys():
                logger.debug("k in parts.keys() = %s", k)
                try:
                    values[k] = parts[k].next()
                except StopIteration: # Really just here for completeness...
                    raise StopIteration
            for k,v in scalars.iteritems(): # Add any scalar values in...
                logger.debug("k, in scalars.iteritems() = %s, %s", k, v)
                values[k] = v
                ##raw_input("PAUSED")

            if values:
                yield values
            else:
                raise StopIteration
   

    def process_data(self): 
      '''
      Wrapper so as to apply self.dbAlias in the decorator
      '''
      def innerProcess_data(self):
        '''
        Iterate over the data source and load the data in by creating new objects
        for each measurement.
        
        Note that due to the use of large-precision numerics, we'll convert all numbers to
        strings prior to performing the import.  Django uses the Decimal type (arbitrary precision
        numeric type), so we won't lose any precision.

        Return the number of MeasuredParameters loaded.
        '''

        self.initDB()

        loaded = 0
        linestringPoints=[]
        parmCount = {}
        parameterCount = {}
        mindepth = 8000.0
        maxdepth = -8000.0
        for key in self.include_names:
            parmCount[key] = 0

        for row in self._genData():
            logger.debug(row)
            try:
                row = self.preProcessParams(row)
                logger.debug("After preProcessParams():")
                logger.debug(row)
            except SkipRecord:
                logger.debug("Got SkipRecord Exception from self.preProcessParams().  Skipping")
                continue
            except Exception, e:
                logger.exception(e)
                sys.exit(-1)
            else:
                params = {} 
                try:
                    longitude, latitude, time, depth = (row.pop('longitude'), 
                                    row.pop('latitude'),
                                    datetime.utcfromtimestamp(row.pop('time')),
                                    row.pop('depth'))
                except ValueError:
                    logger.info('Bad time value')
                    continue

                # If a time subset of data are requested
                if self.startDatetime:
                    if time < self.startDatetime:
                        continue
                if self.endDatetime:
                    if time > self.endDatetime:
                        continue

                try:
                    measurement = self.createMeasurement(time = time,
                                    depth = depth,
                                    lat = latitude,
                                    long = longitude)
                    logger.debug("Appending to linestringPoints: measurement.geom = %s, %s" , measurement.geom.x, measurement.geom.y)
                    linestringPoints.append(measurement.geom)
                except SkipRecord:
                    logger.debug("Got SkipRecord Exception from self.createMeasurement().  Skipping")
                    continue
                except Exception, e:
                    logger.error(e)
                    sys.exit(-1)
                else:
                    logger.debug("longitude = %s, latitude = %s, time = %s, depth = %s", longitude, latitude, time, depth)
                    if depth < mindepth:
                        mindepth = depth
                    if depth > maxdepth:
                        maxdepth = depth

            for key, value in row.iteritems():
                try:
                    logger.debug('Checking for %s in self.include_names', key)
                    if len(self.include_names) and key not in self.include_names:
                        continue
                    elif key in self.ignored_names:
                        continue

                    # If the data have a Z dependence (e.g. mooring tstring/adcp) then value will be an array.
                    logger.debug("value = %s ", value)
                    if value == missing_value or value == 'null': # absence of a value
                        continue
                    try:
                        if math.isnan(value): # not a number for a math type
                            continue
                    except: 
                        pass
                    # End try
                    ##p2 = self.getParameterByName(key)
                    ##print "p2.name = %s" % p2.name
                    logger.debug("measurement._state.db = %s", measurement._state.db)
                    logger.debug("key = %s", key)
                    logger.debug("parameter._state.db = %s", self.getParameterByName(key)._state.db)
                    mp = m.MeasuredParameter(measurement = measurement,
                                parameter = self.getParameterByName(key),
                                datavalue = value)
                    try:
                        mp.save(using=self.dbAlias)
                    except Exception, e:
                        logger.error('Exception %s. Skipping this record.', e)
                        logger.error("Bad value (id=%(id)s) for %(key)s = %(value)s", {'key': key, 'value': value, 'id': mp.pk})
                        continue
                    else:
                        loaded += 1
                        logger.debug("Inserted value (id=%(id)s) for %(key)s = %(value)s", {'key': key, 'value': value, 'id': mp.pk})
                        parmCount[key] += 1
                        if parameterCount.has_key(self.getParameterByName(key)):
                            parameterCount[self.getParameterByName(key)] += 1
                        else:
                            parameterCount[self.getParameterByName(key)] = 0

                except ParameterNotFound:
                    print "Unable to locate parameter for %s, skipping" % (key,)
                except Exception, e:
                    logger.error(e)
                    sys.exit(-1)


            #   except Exception as e:
            #       print "Failed! %s" % (str(e),)
            #       print row
            #       raise e
                # end try
                if loaded:
                    if (loaded % 500) == 0:
                        logger.info("%d records loaded.", loaded)
            # End for key, value


        # End for row
        #
        # now linestringPoints contains all the points
        #
        logger.debug(linestringPoints)
        try:
            path = LineString(linestringPoints).simplify(tolerance=.001)
        except TypeError, e:
            logger.warn("%s\nSetting path to None", e)
            path = None        # Likely "Cannot initialize on empty sequence." resulting from too big a stride
        except Exception as e:
            logger.warn('%s', e)
            path = None        # Likely "GEOS_ERROR: IllegalArgumentException: point array must contain 0 or >1 elements"

        else:
            logger.debug("path = %s", path)
            if len(path) == 2:
                logger.info("Length of path = 2: path = %s", path)
                if path[0][0] == path[1][0] and path[0][1] == path[1][1]:
                    logger.info("And the 2 points are identical.  Adding a little bit of distance to the 2nd point so as to make a tiny line.")
                    newPoint = Point(path[0][0] + 0.001, path[0][1] + 0.001)
                    logger.debug(path[0])
                    logger.debug(newPoint)
                    path = LineString((path[0][0], path[0][1]), newPoint)
            logger.debug("path = %s", path)

        # Update the Activity with information we now have following the load
        # Careful with the structure of this comment.  It is parsed in views.py to give some useful links in showActivities()
        newComment = "%d MeasuredParameters loaded: %s. Loaded on %sZ" % (loaded, ' '.join(self.varsLoaded), datetime.utcnow())
        logger.debug("runDoradoLoader(): Updating its comment with newComment = %s", newComment)
    
        num_updated = m.Activity.objects.using(self.dbAlias).filter(id = self.activity.id).update(
                        comment = newComment,
                        maptrack = path,
                        mindepth = mindepth,
                        maxdepth = maxdepth,
                        num_measuredparameters = loaded,
                        loaded_date = datetime.utcnow())
        logger.debug("runDoradoLoader(): %d activitie(s) updated with new attributes." % num_updated)

        # 
        # Update the stats and store simple line values
        #
        self.updateActivityParameterStats(parameterCount)
        self.insertSimpleDepthTimeSeries()
        self.updateCampaignStartEnd()
        self.assignParameterGroup(parameterCount, groupName='Measured in situ')
        logger.info("Data load complete, %d records loaded.", loaded)


        return loaded, path, parmCount, mindepth, maxdepth

      return innerProcess_data(self)


class Trajectory_Loader(Base_Loader):
    include_names = ['temperature', 'conductivity']

    def initDB(self):
        'Needs to use the exact name for the time coordinate in the Trajectory data'
        if self.startDatetime == None or self.endDatetime == None:
            ds = open_url(self.url)
            if self.startDatetime == None:
                self.startDatetime = datetime.utcfromtimestamp(ds.time[0])
                self.dataStartDatetime = datetime.utcfromtimestamp(ds.time[0])
                logger.info("Setting startDatetime for the Activity from the ds url to %s", self.startDatetime)
            if self.endDatetime == None:
                self.endDatetime = datetime.utcfromtimestamp(ds.time[-1])
                logger.info("Setting endDatetime for the Activity from the ds url to %s", self.endDatetime)

        return super(Trajectory_Loader, self).initDB()

    def preProcessParams(self, row):
        'Compute on-the-fly any additional parameters for loading into the database'

        # Compute salinity if it's not in the record and we have temperature, conductivity, and pressure
        ##if row.has_key('temperature') and row.has_key('pressure') and row.has_key('latitude'):
        ##  conductivity_ratio = row['conductivity'] / 
        ##  row['salinity'] = sw.salt(conductivity_ratio, sw.T90conv(row['temperature']), row['pressure'])

        if row.has_key('salinity') and row.has_key('temperature') and row.has_key('depth') and row.has_key('latitude'):
            row['sea_water_sigma_t'] = sw.dens(row['salinity'], row['temperature'], sw.pres(row['depth'], row['latitude'])) - 1000.0

        return super(Trajectory_Loader, self).preProcessParams(row)


class Dorado_Loader(Trajectory_Loader):
    chl = pydap.model.BaseType()
    chl.attributes = {  'standard_name':    'mass_concentration_of_chlorophyll_in_sea_water',
                        'long_name':        'Chlorophyll',
                        'units':            'ug/l',
                        'name':             'mass_concentration_of_chlorophyll_in_sea_water'
                     }
    dens = pydap.model.BaseType()
    dens.attributes = { 'standard_name':    'sea_water_sigma_t',
                        'long_name':        'Sigma-T',
                        'units':            'kg m-3',
                        'name':             'sea_water_sigma_t'
                      }
    parmDict = {    'mass_concentration_of_chlorophyll_in_sea_water': chl,
                    'sea_water_sigma_t': dens
               }
    include_names = [   'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700', 
                        'fl700_uncorr', 'salinity', 'biolume',
                        'mass_concentration_of_chlorophyll_in_sea_water',
                        'sea_water_sigma_t' ]


    def initDB(self):
        self.addParameters(self.parmDict)
        for k in self.parmDict.keys():
            self.varsLoaded.append(k)       # Make sure to add the derived parameters to the list that gets put in the comment

        return super(Dorado_Loader, self).initDB()

    def preProcessParams(self, row):
        'Compute on-the-fly any additional parameters for loading into the database'

        # Magic formula for October 2010 CANON "experiment"
        if row.has_key('fl700_uncorr'):
            row['mass_concentration_of_chlorophyll_in_sea_water'] = 3.4431e+03 * row['fl700_uncorr']

        if row.has_key('salinity') and row.has_key('temperature') and row.has_key('depth') and row.has_key('latitude'):
            row['sea_water_sigma_t'] = sw.dens(row['salinity'], row['temperature'], sw.pres(row['depth'], row['latitude'])) - 1000.0

        return super(Dorado_Loader, self).preProcessParams(row)

    def addResources(self):
        '''In addition to the NC_GLOBAL attributes that are added in the base class also add the quick-look plots that are on the dods server.
        '''
        baseUrl = 'http://dods.mbari.org/data/auvctd/surveys'
        survey = self.url.split('/')[-1].split('.nc')[0].split('_decim')[0] # Works for both .nc and _decim.nc files
        yyyy = int(survey.split('_')[1])
        # Quick-look plots
        logger.debug("Getting or Creating ResourceType quick_look...")
        (resourceType, created) = m.ResourceType.objects.db_manager(self.dbAlias).get_or_create(
                        name = 'quick_look', description='Quick Look plot of data from this AUV survey')
        for ql in ['2column', 'biolume', 'hist_stats', 'lopc', 'nav_adjust', 'prof_stats']:
            url = '%s/%4d/images/%s_%s.png' % (baseUrl, yyyy, survey, ql)
            logger.debug("Getting or Creating Resource with name = %s, url = %s", ql, url )
            (resource, created) = m.Resource.objects.db_manager(self.dbAlias).get_or_create(
                        name=ql, uristring=url, resourcetype=resourceType)
            (ar, created) = m.ActivityResource.objects.db_manager(self.dbAlias).get_or_create(
                        activity=self.activity,
                        resource=resource)

        # kml, odv, mat
        (kmlResourceType, created) = m.ResourceType.objects.db_manager(self.dbAlias).get_or_create(
                        name = 'kml', description='Keyhole Markup Language file of data from this AUV survey')
        (odvResourceType, created) = m.ResourceType.objects.db_manager(self.dbAlias).get_or_create(
                        name = 'odv', description='Ocean Data View spreadsheet text file')
        (matResourceType, created) = m.ResourceType.objects.db_manager(self.dbAlias).get_or_create(
                        name = 'mat', description='Matlab data file')
        for res in ['kml', 'odv', 'odvGulper', 'mat', 'mat_gridded']:
            if res == 'kml':
                url = '%s/%4d/kml/%s.kml' % (baseUrl, yyyy, survey)
                rt = kmlResourceType
            elif res == 'odv':
                url = '%s/%4d/odv/%s.txt' % (baseUrl, yyyy, survey)
                rt = odvResourceType
            elif res == 'odvGulper':
                url = '%s/%4d/odv/%s_Gulper.txt' % (baseUrl, yyyy, survey)
                rt = odvResourceType
            elif res == 'mat':
                url = '%s/%4d/mat/%s.mat' % (baseUrl, yyyy, survey)
                rt = matResourceType
            elif res == 'mat_gridded':
                url = '%s/%4d/mat/%s_gridded.mat' % (baseUrl, yyyy, survey)
                rt = matResourceType
            else:
                logger.warn('No handler for res = %s', res)

            logger.debug("Getting or Creating Resource with name = %s, url = %s", res, url )
            (resource, created) = m.Resource.objects.db_manager(self.dbAlias).get_or_create(
                        name=res, uristring=url, resourcetype=rt)
            (ar, created) = m.ActivityResource.objects.db_manager(self.dbAlias).get_or_create(
                        activity=self.activity, resource=resource)

        return super(Dorado_Loader, self).addResources()


class Lrauv_Loader(Trajectory_Loader):
    dens = pydap.model.BaseType()
    dens.attributes = { 'standard_name':    'sea_water_sigma_t',
                        'long_name':        'Sigma-T',
                        'units':            'kg m-3',
                        'name':             'sea_water_sigma_t'
                      }
    parmDict = {'sea_water_sigma_t': dens}
    include_names = [   'mass_concentration_of_oxygen_in_sea_water',
                        'mole_concentration_of_nitrate_in_sea_water',
                        'mass_concentration_of_chlorophyll_in_sea_water',
                        'sea_water_salinity',
                        'sea_water_temperature',
                        'sea_water_sigma_t',
                    ]

    def initDB(self):
        'Needs to use the exact name for the time coordinate in the LRAUV data'
        if self.startDatetime == None or self.endDatetime == None:
            logger.info('Reading data from %s', self.url)
            ds = open_url(self.url)
            if self.startDatetime == None:
                self.startDatetime = datetime.utcfromtimestamp(ds.Time[0])
                self.dataStartDatetime = datetime.utcfromtimestamp(ds.Time[0])
                logger.info("Setting startDatetime for the Activity from the ds url to %s", self.startDatetime)
            if self.endDatetime == None:
                self.endDatetime = datetime.utcfromtimestamp(ds.Time[-1])
                logger.info("Setting endDatetime for the Activity from the ds url to %s", self.endDatetime)

        self.addParameters(self.parmDict)
        for k in self.parmDict.keys():
            self.varsLoaded.append(k)       # Make sure to add the derived parameters to the list that gets put in the comment

        return super(Lrauv_Loader, self).initDB()

    def preProcessParams(self, row):
        ##print "preProcessParams(): row = %s" % row
        for v in ('Time', 'TIME', 'latitude', 'longitude', 'depth'):
            if row.has_key(v):
                row[v.lower()] = row.pop(v) 

        if self.url.find('shore') == -1:
            # Full-resolution data (whose name does not contain 'shore') are in radians
            if row.has_key('latitude'):
                row['latitude'] = row['latitude'] * 180.0 / numpy.pi
            if row.has_key('longitude'):
                row['longitude'] = row['longitude'] * 180.0 / numpy.pi
            # Can't read CTD_NeilBrown.sea_water_temperature because of the '.'.  Use 'sea_water_temperature', but convert to C and assign units
            if row.has_key('sea_water_temperature'):
                row['sea_water_temperature'] = row['sea_water_temperature'] - 272.15
                self.ds['sea_water_temperature'].units = 'degC'

        return super(Lrauv_Loader, self).preProcessParams(row)



class Glider_Loader(Trajectory_Loader):
    include_names=['TEMP', 'PSAL', 'OPBS', 'FLU2']

    def createActivity(self):
        '''
        Use provided activity information to add the activity to the database.
        '''
        start = from_udunits(float(self.ds.TIME[0]), self.ds.TIME.units)
        end = from_udunits(float(self.ds.TIME[-1]), self.ds.TIME.units)
        self.activity=m.Activity(name=self.activityName,
                    platform=self.platform,
                    startdate=start,
                    enddate=end)
        if self.activitytypeName is not None:
            self.activity.activitytypeName = self.activitytypeName
        self.activity.save(using=self.dbAlias)
        
    def initDB(self):
        'Needs to use the exact name for the time coordinate in the Glider data'
        if self.startDatetime == None or self.endDatetime == None:
            ds = open_url(self.url)
            if self.startDatetime == None:
                logger.debug("self.ds.TIME[0] = %f, self.ds.TIME.units = %s", self.ds.TIME[0], self.ds.TIME.units)
                self.startDatetime = from_udunits(float(self.ds.TIME[0]), self.ds.TIME.units)
            if self.endDatetime == None:
                self.endDatetime = from_udunits(float(self.ds.TIME[-1]), self.ds.TIME.units)
                logger.info("Setting endDatetime for the Activity from the ds url to %s", self.endDatetime)

        if self.dataStartDatetime == None:
            self.dataStartDatetime = from_udunits(float(self.ds.TIME[0]), self.ds.TIME.units)
        else:
            logger.info("Using dataStartDatetime to read data from the source starting at %s", self.dataStartDatetime)

        return super(Glider_Loader, self).initDB()

    def preProcessParams(self, row):
        '''
        Convert from the days since 1950 to a usable timestamp.  Convert time, lat, long, and depth
        to lower case keys - since that is how we require them. 
        '''
        for v in ('TIME','LONGITUDE','LATITUDE', 'DEPTH'):
            logger.debug(v)
            if row.has_key(v):
                row[v.lower()]=row.pop(v) 
        if row.has_key('time'):
            row['time'] = to_udunits(from_udunits(float(row['time']), self.ds.TIME.units), 'seconds since 1970-01-01')
            logger.debug(row['time'])

        return super(Glider_Loader,self).preProcessParams(row)


class Mooring_Loader(Base_Loader):
    ##include_names=['sea_water_temperature', 'sea_water_salinity', 'Fluorescence',
        ##'Fluor_RefSignal', 'NTU_RefSignal', 'NTU', 'ThermistorTemp']
    include_names=['Temperature', 'Salinity', 'TEMP', 'PSAL', 'ATMP', 'AIRT', 'WDIR', 'WSDP']

    def preProcessParams(self, row):

        for v in ('Time','TIME','LATITUDE','LONGITUDE','DEPTH','Longitude','Latitude','NominalDepth'):
            logger.debug("v = %s", v)
            if row.has_key(v):
                value = row.pop(v)
                row[v.lower()] = value
        if not row.has_key('longitude'):
            for key in ('GPS_LONGITUDE_HR',):
                if row.has_key(key):
                    row['longitude'] = row.pop(key)
        if not row.has_key('latitude'):
            for key in ('GPS_LATITUDE_HR',):
                if row.has_key(key):
                    row['latitude'] = row.pop(key)
        if row.has_key('nominaldepth') and (not row.has_key('depth')):
            row['depth'] = row.pop('nominaldepth')
        if row.has_key('hr_time_adcp') and (not row.has_key('time')):
            row['time'] = row.pop('hr_time_adcp')
        if row.has_key('esecs') and (not row.has_key('time')):
            row['time'] = row.pop('esecs')
        if row.has_key('HR_DEPTH_adcp') and (not row.has_key('depth')):
            row['depth'] = row.pop('HR_DEPTH_adcp')
            # print row
        return super(Mooring_Loader,self).preProcessParams(row)


def runTrajectoryLoader(url, cName, aName, pName, pColor, pTypeName, aTypeName, parmList, dbAlias, stride):
    '''Run the DAPloader for Generic AUVCTD trajectory data and update the Activity with 
    attributes resulting from the load into dbAlias. Designed to be called from script
    that loads the data.  Following the load important updates are made to the database.'''

    logger.debug("Instantiating Trajectory_Loader for url = %s", url)
    loader = Trajectory_Loader(
            url = url,
            campaignName = cName,
            dbAlias = dbAlias,
            activityName = aName,
            activitytypeName = aTypeName,
            platformName = pName,
            platformColor = pColor,
            platformTypeName = pTypeName,
            stride = stride)

    logger.debug("Setting include_names to %s", parmList)
    loader.include_names = parmList
    (nMP, path, parmCountHash, mind, maxd) = loader.process_data()
    logger.debug("Loaded Activity with name = %s", aName)


def runDoradoLoader(url, cName, aName, pName, pColor, pTypeName, aTypeName, dbAlias, stride):
    '''Run the DAPloader for Dorado AUVCTD trajectory data and update the Activity with 
    attributes resulting from the load into dbAlias. Designed to be called from script
    that loads the data.  Following the load important updates are made to the database.'''

    logger.debug("Instantiating Dorado_Loader for url = %s", url)
    loader = Dorado_Loader(
            url = url,
            campaignName = cName,
            dbAlias = dbAlias,
            activityName = aName,
            activitytypeName = aTypeName,
            platformName = pName,
            platformColor = pColor,
            platformTypeName = pTypeName,
            stride = stride)

    (nMP, path, parmCountHash, mind, maxd) = loader.process_data()
    logger.debug("Loaded Activity with name = %s", aName)


def runLrauvLoader(url, cName, aName, pName, pColor, pTypeName, aTypeName, parmList, dbAlias, stride):
    '''Run the DAPloader for Long Range AUVCTD trajectory data and update the Activity with 
    attributes resulting from the load into dbAlias. Designed to be called from script
    that loads the data.  Following the load important updates are made to the database.'''

    logger.debug("Instantiating Lrauv_Loader for url = %s", url)
    loader = Lrauv_Loader(
            url = url,
            campaignName = cName,
            dbAlias = dbAlias,
            activityName = aName,
            activitytypeName = aTypeName,
            platformName = pName,
            platformColor = pColor,
            platformTypeName = pTypeName,
            stride = stride)

    if parmList:
        logger.debug("Setting include_names to %s", parmList)
        loader.include_names = parmList
    try:
        (nMP, path, parmCountHash, mind, maxd) = loader.process_data()
    except NoValidData, e:
        logger.warn(e)
    else:    
        logger.debug("Loaded Activity with name = %s", aName)


def runGliderLoader(url, cName, aName, pName, pColor, pTypeName, aTypeName, parmList, dbAlias, stride, startDatetime=None, endDatetime=None):
    '''Run the DAPloader for Spray Glider trajectory data and update the Activity with 
    attributes resulting from the load into dbAlias. Designed to be called from script
    that loads the data.  Following the load important updates are made to the database.'''

    logger.debug("Instantiating Glider_Loader for url = %s", url)
    loader = Glider_Loader(
            url = url,
            campaignName = cName,
            dbAlias = dbAlias,
            activityName = aName,
            activitytypeName = aTypeName,
            platformName = pName,
            platformColor = pColor,
            platformTypeName = pTypeName,
            stride = stride,
            startDatetime = startDatetime,
            endDatetime = endDatetime)

    if parmList:
        logger.debug("Setting include_names to %s", parmList)
        loader.include_names = parmList
    (nMP, path, parmCountHash, mind, maxd) = loader.process_data()
    logger.debug("Loaded Activity with name = %s", aName)


if __name__ == '__main__':
    ##bl=Base_Loader('Test Survey', 
            ##platform=m.Platform.objects.get(code='vnta'),
            ##url='http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/Dorado389_2010_081_02_081_02_decim.nc',
            ##stride=1)
    # The full aggregation of AUVCTD data has "holes" in variables that break the aggregation
    # Luckily the 2010 aggragetion of Dorado gets around this problem.
    ##bl=Trajectory_Loader('AUV Surveys - September 2010 (stride=1000)', 
    ##      url = 'http://elvis.shore.mbari.org/thredds/dodsC/agg/dorado_2010_ctd',
    ##      startDatetime = datetime(2010, 9, 14),
    ##      endDatetime = datetime(2010,9, 18),
    ##      dbAlias = 'stoqs_june2011',
    ##      platformName = 'dorado',
    ##      stride = 1000)

    ##bl=Mooring_Loader('Test Mooring', 
    ##      platform=m.Platform.objects.get(code='m1'),
    ##      url='http://elvis.shore.mbari.org/thredds/dodsC/agg/OS_MBARI-M1_R_TS',
    ##      startDatetime = datetime(2009,1,1),
    ##      endDatetime = datetime(2009,1,10),
    ##      stride=10)

    # A nice test data load for a northern Monterey Bay survey  
    ##baseUrl = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
    baseUrl = 'http://odss.mbari.org/thredds/dodsC/dorado/'             # NCML to make salinity.units = "1"
    file = 'Dorado389_2010_300_00_300_00_decim.nc'
    stride = 1000       # Make large for quicker runs, smaller for denser data
    dbAlias = 'default'

    runDoradoLoader(baseUrl + file, 'Test Load', file, 'dorado', 'auv', 'AUV Mission', dbAlias, stride)

