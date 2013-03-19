#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2011, MBARI"
__credits__ = ["Chander Ganesan, Open Technology Group"]
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__doc__ = '''

Base module for STOQS loaders

@author: __author__
@status: __status__
@license: __license__
'''

import sys
import os.path, os
#
# The following are required to ensure that the GeoDjango models can be loaded up.
#
os.environ['DJANGO_SETTINGS_MODULE']='settings'
sys.path.insert(0, os.path.abspath('..'))
from django.conf import settings
from django.contrib.gis.geos import LineString
from django.contrib.gis.geos import Point
from django.db.utils import IntegrityError
from django.db import connection, transaction
from django.db.models import Max, Min
from stoqs import models as m
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
import time
import math, numpy
from coards import to_udunits, from_udunits
import csv
import urllib2
import logging
from utils.utils import percentile, median, mode, simplify_points
import pprint


# Set up logging
##logger = logging.getLogger('loaders')
logger = logging.getLogger('__main__')
logger.setLevel(logging.INFO)

# When settings.DEBUG is True Django will fill up a hash with stats on every insert done to the database.
# "Monkey patch" the CursorWrapper to prevent this.  Otherwise we can't load large amounts of data.
# See http://stackoverflow.com/questions/7768027/turn-off-sql-logging-while-keeping-settings-debug
from django.db.backends import BaseDatabaseWrapper
from django.db.backends.util import CursorWrapper

# Constant for ParameterGroup name - for utils/STOQSQmanager.py to use
MEASUREDINSITU = 'Measured in situ'

if settings.DEBUG:
    BaseDatabaseWrapper.make_debug_cursor = lambda self, cursor: CursorWrapper(cursor, self)

missing_value = 1e-34

class SkipRecord(Exception):
    pass


class ParameterNotFound(Exception):
    pass


class STOQS_Loader(object):
    '''
    The STOQSloaders class contains methods common across all loaders for creating and updating
    general STOQS model objects.  This is a base class that should be inherited by other
    classes customized to read and load various kinds of data from various sources.
    
    Mike McCann
    MBARI 26 May 2012
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

    def __init__(self, activityName, platformName, dbAlias='default', campaignName=None, 
                activitytypeName=None, platformColor=None, platformTypeName=None, stride=1):
        '''
        Intialize with settings that are common for any load of data into STOQS.
        
        @param activityName: A string describing this activity
        @param platformName: A string that is the name of the platform. If that name for a Platform exists in the DB, it will be used.
        @param platformColor: An RGB hex string represnting the color of the platform. 
        @param dbAlias: The name of the database alias as defined in settings.py
        @param campaignName: A string describing the Campaign in which this activity belongs, If that name for a Campaign exists in the DB, it will be used.
        @param activitytypeName: A string such as 'mooring deployment' or 'AUV mission' describing type of activity, If that name for a ActivityType exists in the DB, it will be used.
        @param platformTypeName: A string describing the type of platform, e.g.: 'mooring', 'auv'.  If that name for a PlatformType exists in the DB, it will be used.
        
        '''
        self.campaignName = campaignName
        self.activitytypeName = activitytypeName
        self.platformName = platformName
        self.platformColor = platformColor
        self.dbAlias = dbAlias
        self.platformTypeName = platformTypeName
        self.activityName = activityName
        self.stride = stride
        
        self.build_standard_names()

    
    def getPlatform(self, name, type):
        '''Given just a platform name get a platform object from the STOQS database.  If no such object is in the
        database then create a new one.  Makes use of the MBARI tracking database to keep the names and types
        consistent.  The intention of the logic here is to make platform settings dynamic, yet consistent in 
        reusing what is already in the database.  There might need to be some independent tests to ensure that
        we make no duplicates.  The aim is to be case insensitive on the lookup, but to preserve the case of
        what is in MBARItracking.'''

        ##paURL = 'http://odss-staging.shore.mbari.org/trackingdb/platformAssociations.csv'
        #-#paURL = 'http://odss.mbari.org/trackingdb/platformAssociations.csv'
        ##paURL = 'http://192.168.111.177/trackingdb/platformAssociations.csv'  # Private URL for host malibu
        # Returns lines like:
        # PlatformType,PlatformName
        # ship,Martin
        # ship,PT_LOBOS
        # ship,W_FLYER
        # ship,W_FLYER
        # ship,ZEPHYR
        # mooring,Bruce
        #-#logger.info("Opening %s to read platform names for matching to the MBARI tracking database" % paURL)
        #-#tpHandle = csv.DictReader(urllib2.urlopen(paURL))
        tpHandle = []
        platformName = ''
        for rec in tpHandle:
            ##print "rec = %s" % rec
            if rec['PlatformName'].lower() == name.lower():
                platformName = rec['PlatformName']
                platformTypeName = rec['PlatformType']
                break

        if not platformName:
            platformName = name
            platformTypeName = type
            logger.warn("Platform name %s not found in tracking database.  Creating new platform anyway.", platformName)

        # Create PlatformType
        logger.debug("calling db_manager('%s').get_or-create() on PlatformType for platformTypeName = %s", self.dbAlias, self.platformTypeName)
        (platformType, created) = m.PlatformType.objects.db_manager(self.dbAlias).get_or_create(name = self.platformTypeName)
        if created:
            logger.debug("Created platformType.name %s in database %s", platformType.name, self.dbAlias)
        else:
            logger.debug("Retrived platformType.name %s from database %s", platformType.name, self.dbAlias)


        # Create Platform 
        (platform, created) = m.Platform.objects.db_manager(self.dbAlias).get_or_create( name=platformName, 
                                                                                        color=self.platformColor, 
                                                                                        platformtype=platformType)
        if created:
            logger.info("Created platform %s in database %s", platformName, self.dbAlias)
        else:
            logger.info("Retrived platform %s from database %s", platformName, self.dbAlias)

        return platform

    def addParameters(self, parmDict):
      '''
      Wrapper so as to apply self.dbAlias in the decorator
      '''
      def innerAddParameters(self, parmDict):
        '''
        This method is a get_or_create() equivalent, but on steroids.  It first tries to find the
        parameter in a local cache (a python hash), first by standard_name, then by name.  Then it
        checks to see if it's in the database.  If it's not in the database it will then add it
        populating the fields from the attributes of the parameter dictionary that is passed.  The
        dictionary is patterned after the pydab.model.BaseType variable from the NetCDF file (OPeNDAP URL).
        '''

        # Go through the keys of the OPeNDAP URL for the dataset and add the parameters as needed to the database
        for key in parmDict.keys():
            logger.debug("key = %s", key)
            if (key in self.ignored_names) or (key not in self.include_names): # skip adding parameters that are ignored
                continue
            v = parmDict[key].attributes
            logger.debug("v = %s", v)
            try:
                self.getParameterByName(key)
            except ParameterNotFound as e:
                logger.debug("Parameter not found. Assigning parms from ds variable.")
                # Bug in pydap returns a gobbledegook list of things if the attribute value has not been
                # set.  Check for this on units and override what pydap returns.
                if type(v.get('units')) == list:
                    unitStr = ''
                else:
                    unitStr = v.get('units')
                
                parms = {'units': unitStr,
                    'standard_name': v.get('standard_name'),
                    'long_name': v.get('long_name'),
                    'type': v.get('type'),
                    'description': v.get('description'),
                    'origin': self.activityName,
                    'name': key}

                self.parameter_dict[key] = m.Parameter(**parms)
                try:
                    sid = transaction.savepoint(using=self.dbAlias)
                    self.parameter_dict[key].save(using=self.dbAlias)
                    self.ignored_names.remove(key)  # unignore, since a failed lookup will add it to the ignore list.
                except IntegrityError as e:
                    logger.warn('%s', e)
                    transaction.savepoint_rollback(sid)
                    if str(e).startswith('duplicate key value violates unique constraint "stoqs_parameter_pkey"'):
                        self.resetParameterAutoSequenceId()
                        try:
                            sid2 = transaction.savepoint(using=self.dbAlias)
                            self.parameter_dict[key].save(using=self.dbAlias)
                            self.ignored_names.remove(key)  # unignore, since a failed lookup will add it to the ignore list.
                        except Exception as e:
                            logger.error('%s', e)
                            transaction.savepoint_rollback(sid2,using=self.dbAlias)
                            raise Exception('''Failed reset auto sequence id on the stoqs_parameter table''')
                    else:
                        logger.error('Exception %s', e)
                        raise Exception('''Failed to add parameter for %s
                            %s\nEither add parameter manually, or add to ignored_names''' % (key,
                            '\n'.join(['%s=%s' % (k1,v1) for k1,v1 in parms.iteritems()])))
                    
                except Exception as e:
                    logger.error('%s', e)
                    transaction.savepoint_rollback(sid,using=self.dbAlias)
                    raise Exception('''Failed to add parameter for %s
                        %s\nEither add parameter manually, or add to ignored_names''' % (key,
                        '\n'.join(['%s=%s' % (k1,v1) for k1,v1 in parms.iteritems()])))
                logger.debug("Added parameter %s from data set to database %s", key, self.dbAlias)


      return innerAddParameters(self, parmDict)
 
    def createActivity(self):
        '''
        Use provided activity information to add the activity to the database.
        '''
        
        logger.info("Creating Activity with startDate = %s and endDate = %s", self.startDatetime, self.endDatetime)
        comment = 'Loaded on %s with these include_names: %s' % (datetime.now(), ' '.join(self.include_names))
        logger.info("comment = " + comment)

        # Create Platform 
        (self.activity, created) = m.Activity.objects.db_manager(self.dbAlias).get_or_create(    
                                        name = self.activityName, 
                                        ##comment = comment,
                                        platform = self.platform,
                                        startdate = self.startDatetime,
                                        enddate = self.endDatetime)

        if created:
            logger.info("Created activity %s in database %s", self.activityName, self.dbAlias)
        else:
            logger.info("Retrived activity %s from database %s", self.activityName, self.dbAlias)

        # Get or create activityType 
        if self.activitytypeName is not None:
            (activityType, created) = m.ActivityType.objects.db_manager(self.dbAlias).get_or_create(name = self.activitytypeName)
            self.activityType = activityType
    
            if self.activityType is not None:
                self.activity.activitytype = self.activityType
    
            self.activity.save(using=self.dbAlias)   # Resave with the activitytype
        
        # Get or create campaign
        if self.campaignName is not None:
            (campaign, created) = m.Campaign.objects.db_manager(self.dbAlias).get_or_create(name = self.campaignName)
            self.campaign = campaign
    
            if self.campaign is not None:
                self.activity.campaign = self.campaign
    
            self.activity.save(using=self.dbAlias)   # Resave with the campaign

    def addResources(self):
        '''Add Resources for this activity, namely the NC_GLOBAL attribute names and values.
        '''

        # The NC_GLOBAL attributes from the OPeNDAP URL.  Save them all.
        logger.debug("Getting or Creating ResourceType nc_global...")
        logger.debug("ds.attributes.keys() = %s", self.ds.attributes.keys() )
        if self.ds.attributes.has_key('NC_GLOBAL'):
            (resourceType, created) = m.ResourceType.objects.db_manager(self.dbAlias).get_or_create(name = 'nc_global')
            for rn in self.ds.attributes['NC_GLOBAL'].keys():
                value = self.ds.attributes['NC_GLOBAL'][rn]
                logger.debug("Getting or Creating Resource with name = %s, value = %s", rn, value )
                (resource, created) = m.Resource.objects.db_manager(self.dbAlias).get_or_create(
                            name=rn, value=value, resourcetype=resourceType)
                (ar, created) = m.ActivityResource.objects.db_manager(self.dbAlias).get_or_create(
                            activity=self.activity, resource=resource)
        else:
            logger.warn("No NC_GLOBAL attribute in %s", self.url)

        
    def getParameterByName(self, name):
        '''
        Locate a parameter's object from the database.  Cache objects after lookup.
        If a standard name is provided we'll look up using it instead, as it's more standard.
    
        @param name: Name of parameter object to lookup/locate 
        '''
        # First try to locate the parameter using the standard name (if we have one)
        if not self.parameter_dict.has_key(name):
            logger.debug("'%s' is not in self.parameter_dict", name)
            if self.standard_names.get(name) is not None:
                logger.debug("self.standard_names.get('%s') is not None", name)
                try:
                    logger.debug("For name = %s ", name)
                    logger.debug("standard_names = %s", self.standard_names[name])
                    logger.debug("retrieving from database %s", self.dbAlias)
                    self.parameter_dict[name] = m.Parameter.objects.db_manager(self.dbAlias).get(standard_name = self.standard_names[name][0])
                except ObjectDoesNotExist:
                    pass
                except IndexError:
                    pass
        # If we still haven't found the parameter using the standard_name, start looking using the name
        if not self.parameter_dict.has_key(name):
            logger.debug("Again '%s' is not in self.parameter_dict", name)
            try:
                logger.debug("trying to get '%s' from database %s...", name, self.dbAlias)
                ##(parameter, created) = m.Parameter.objects.get(name = name)
                self.parameter_dict[name] = m.Parameter.objects.db_manager(self.dbAlias).get(name = name)
                logger.debug("self.parameter_dict[name].name = %s", self.parameter_dict[name].name)
            except ObjectDoesNotExist:
                ##print >> sys.stderr, "Unable to locate parameter with name %s.  Adding to ignored_names list." % (name,)
                self.ignored_names.append(name)
                raise ParameterNotFound('Parameter %s not found in the cache nor the database' % (name,))
        # Finally, since we haven't had an error, we MUST have a parameter for this name.  Return it.

        logger.debug("Returning self.parameter_dict[name].units = %s", self.parameter_dict[name].units)
        try:
            self.parameter_dict[name].save(using=self.dbAlias)
        except Exception, e:
            print e
            print name
            pprint.pprint( self.parameter_dict[name])


        return self.parameter_dict[name]

    def createMeasurement(self, time, depth, lat, long):
        '''
        Create and return a measurement object in the database.  The measurement object
        is created by first creating an instance of stoqs.models.Instantpoint using the activity, 
        then by creating an instance of Measurement using the Instantpoint.  A reference to 
        an instance of a stoqs.models.Measurement object is then returned.
        @param time: A valid datetime instance of a datetime object used to create the Instantpoint
        @param depth: The depth for the measurement
        @param lat: The latitude (degrees, assumed WGS84) for the measurement
        @param long: The longitude (degrees, assumed WGS84) for the measurement
        @return: An instance of stoqs.models.Measurement
        '''

        if depth < -1000 or depth > 4000:
            raise SkipRecord('Bad depth')

        ip = m.InstantPoint(activity = self.activity,
                    timevalue = time)
        ip.save(using=self.dbAlias)
        point = 'POINT(%s %s)' % (repr(long), repr(lat))
        measurement = m.Measurement(instantpoint = ip,
                        depth = repr(depth),
                        geom = point)
        try:
            measurement.save(using=self.dbAlias)
        except Exception, e:
            logger.error('Exception %s', e)
            logger.error("Cannot save measurement time = %s, long = %s, lat = %s, depth = %s", time, repr(long), repr(lat), repr(depth))
            raise SkipRecord

        return measurement
    
    def preProcessParams(self, row):
        '''
        This method is designed to perform any final pre-processing, such as adding new
        parameters based on existing ones.  It's also possible to use this function to remove
        additional parameters (if necessary).  In particular, this is useful for derived
        columns such as chlorophyl count, etc.
        @param row: A dictionary representing a single "row" of parameter data to be added to the database. 
        '''
        logger.debug(row)
        try:
            if (row['longitude'] == missing_value or row['latitude'] == missing_value or
                float(row['longitude']) == 0.0 or float(row['latitude']) == 0.0 or
                math.isnan(row['longitude'] ) or math.isnan(row['latitude'])):
                raise SkipRecord('Invalid coordinate')
        except KeyError, e:
            raise SkipRecord('KeyError: ' + str(e))

        return row

    def checkForValidData(self):
        '''
        Do a pre- check on the OPeNDAP url for the include_names variables. If there are non-NaN data in
        any of the varibles return Ture, otherwise return False.
        '''

        allNaNFlag = {}
        anyValidData = False
        logger.info("Checking for valid data from %s", self.url)
        logger.debug("include_names = %s", self.include_names)
        for v in self.include_names:
            logger.debug("v = %s", v)
            try:
                vVals = self.ds[v][:]           # Case sensitive
                logger.debug(len(vVals))
                allNaNFlag[v] = numpy.isnan(vVals).all()
                if not allNaNFlag[v]:
                    anyValidData = True
            except KeyError:
                pass
            except ValueError:
                pass

        logger.debug("allNaNFlag = %s", allNaNFlag)
        for v in allNaNFlag.keys():
            if not allNaNFlag[v]:
                self.varsLoaded.append(v)
        logger.info("Variables that have data: self.varsLoaded = %s", self.varsLoaded)

        return anyValidData
    
   
    def build_standard_names(self):
        '''
        Create a dictionary that contains keys that are fields, and values that
        are the standard names of those fields.  Classes that inherit from this
        class should set any default standard names at the class level.
        '''
        try:
            # Assumes that we have a ds that came from an OPeNDAP call
            for var in self.ds.keys():
                if self.standard_names.has_key(var): continue # don't override pre-specified names
                if self.ds[var].attributes.has_key('standard_name'):
                    self.standard_names[var]=self.ds[var].attributes['standard_name']
                else:
                    self.standard_names[var]=None # Indicate those without a standard name
        except AttributeError, e:
            logger.warn(e)
            pass

    def updateActivityParameterStats(self, parameterCounts, sampledFlag=False):
        ''' 
        Examine the data for the Activity, compute and update some statistics on the measuredparameters
        for this activity.  Store the historgram in the associated table.
        '''                 
        if self.activity:
            a = self.activity
        else:
            raise Exception('Must have an activity defined in self.activity')

        for p in parameterCounts:
            if sampledFlag:
                data = m.SampledParameter.objects.using(self.dbAlias).filter(parameter=p, sample__instantpoint__activity=a)
            else:
                data = m.MeasuredParameter.objects.using(self.dbAlias).filter(parameter=p, measurement__instantpoint__activity=a)
            numpvar = numpy.array([float(v.datavalue) for v in data])
            numpvar.sort()              
            listvar = list(numpvar)
            ##logger.debug('%s: listvar = %s', p.name, listvar)
            if not listvar:
                logger.warn('No datavalues for p.name = %s in activity %s', p.name, a.name)
                continue

            logger.debug('parameter: %s, min = %f, max = %f, mean = %f, median = %f, mode = %f, p025 = %f, p975 = %f, shape = %s',
                            p, numpvar.min(), numpvar.max(), numpvar.mean(), median(listvar), mode(numpvar),
                            percentile(listvar, 0.025), percentile(listvar, 0.975), numpvar.shape)
            number = len(listvar)
                                        
            # Save statistics           
            try:                        
                ap, created = m.ActivityParameter.objects.using(self.dbAlias).get_or_create(activity = a, parameter = p)
                    
                if created: 
                    logger.info('Created ActivityParameter for parameter.name = %s', p.name)

                # Set attributes of this ap - if not created, an update will happen
                ap.number = number
                ap.min = numpvar.min()
                ap.max = numpvar.max()
                ap.mean = numpvar.mean()
                ap.median = median(listvar)
                ap.mode = mode(numpvar)
                ap.p025 = percentile(listvar, 0.025)
                ap.p975 = percentile(listvar, 0.975)
                ap.save(using=self.dbAlias)
                if created: 
                    logger.info('Saved ActivityParameter for parameter.name = %s', p.name)
                else:
                    logger.info('Updated ActivityParameter for parameter.name = %s', p.name)

            except IntegrityError, e:
                logger.warn('IntegrityError(%s): Cannot create ActivityParameter for parameter.name = %s.', e, p.name)

            ##raw_input('paused')

            # Compute and save histogram, use smaller number of bins for Sampled Parameters
            if sampledFlag:
                (counts, bins) = numpy.histogram(numpvar,10)
            else:
                (counts, bins) = numpy.histogram(numpvar,100)
            logger.debug(counts)
            logger.debug(bins)
            i = 0
            for count in counts:
                try:
                    logger.debug('Creating ActivityParameterHistogram...')
                    logger.debug('count = %d, binlo = %f, binhi = %f', count, bins[i], bins[i+1])
                    h, created = m.ActivityParameterHistogram.objects.using(self.dbAlias).get_or_create(
                                                    activityparameter=ap, bincount=count, binlo=bins[i], binhi=bins[i+1])
                    i = i + 1
                    if created:
                        logger.debug('Created ActivityParameterHistogram for parameter.name = %s, h = %s', p.name, h)
                except IntegrityError:
                    logger.warn('IntegrityError: Cannot create ActivityParameter for parameter.name = %s. Skipping.', p.name)

        logger.info('Updated statistics for activity.name = %s', a.name)

    def insertSimpleDepthTimeSeries(self, critSimpleDepthTime=10):
        '''
        Read the time series of depth values for this activity, simplify it and insert the values in the
        SimpleDepthTime table that is related to the Activity.

        @param critSimpleDepthTime: An integer for the simplification factor, 10 is course, .0001 is fine
        '''
        vlqs = m.Measurement.objects.using(self.dbAlias).filter( instantpoint__activity=self.activity,
                                                              ).values_list('instantpoint__timevalue', 'depth', 'instantpoint__pk')
        line = []
        pklookup = []
        for dt,dd,pk in vlqs:
            ems = 1000 * to_udunits(dt, 'seconds since 1970-01-01')
            d = float(dd)
            line.append((ems,d,))
            pklookup.append(pk)

        logger.debug('line = %s', line)
        logger.info('Number of points in original depth time series = %d', len(line))
        try:
            simple_line = simplify_points(line, critSimpleDepthTime)
        except IndexError:
            simple_line = []        # Likely "list index out of range" from a stride that's too big
        logger.info('Number of points in simplified depth time series = %d', len(simple_line))
        logger.debug('simple_line = %s', simple_line)

        for t,d,k in simple_line:
            try:
                ip = m.InstantPoint.objects.using(self.dbAlias).get(id = pklookup[k])
                m.SimpleDepthTime.objects.using(self.dbAlias).create(activity = self.activity, instantpoint = ip, depth = d, epochmilliseconds = t)
            except ObjectDoesNotExist:
                logger.warn('InstantPoint with id = %d does not exist; from point at index k = %d', pklookup[k], k)

        logger.info('Inserted %d values into SimpleDepthTime', len(simple_line))

    def updateCampaignStartEnd(self):
        '''
        Pull the min & max from InstantPoint and set the Campaign start and end from these
        '''
        try:
            if self.campaign:
                ip_qs = m.InstantPoint.objects.using(self.dbAlias).aggregate(Max('timevalue'), Min('timevalue'))
                m.Campaign.objects.using(self.dbAlias).update(
                                                       startdate = ip_qs['timevalue__min'],
                                                        enddate = ip_qs['timevalue__max'])
        except AttributeError, e:
            logger.warn(e)
            pass

    def assignParameterGroup(self, parameterCounts, groupName='Measured in situ'):
        ''' 
        For all the parameters in @parameterCounts create a many-to-many association with the Group named @groupName
        '''                 
        g, created = m.ParameterGroup.objects.using(self.dbAlias).get_or_create(name=groupName)
        for p in parameterCounts:
            pgps = m.ParameterGroupParameter.objects.using(self.dbAlias).filter(parameter=p, parametergroup=g)
            if not pgps:
                # Attempt saving relation only if it does not exist
                pgp = m.ParameterGroupParameter(parameter=p, parametergroup=g)
                try:
                    pgp.save(using=self.dbAlias)
                except Exception, e:
                    logger.warn('%s: Cannot create ParameterGroupParameter name = %s for parameter.name = %s. Skipping.', e, groupName, p.name)


if __name__ == '__main__':
    '''
    Simple test of methods in STOQS_loader()
    '''

    pass

