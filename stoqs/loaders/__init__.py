'''
Base module for STOQS loaders

@author: __author__
@status: __status__
@license: __license__
'''

import os
import sys

app_dir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, app_dir)
os.environ['DJANGO_SETTINGS_MODULE']='config.settings.local'
import django
django.setup()

from django.conf import settings
from django.contrib.gis.geos import Polygon
from django.db.utils import IntegrityError
from django.db import transaction, DatabaseError
from django.db.models import Max, Min
from stoqs import models as m
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
import time
import re
import subprocess
import math
import numpy as np
from coards import to_udunits
import seawater.eos80 as sw
import csv
import urllib2
import logging
from utils.utils import percentile, median, mode, simplify_points, spiciness
from tempfile import NamedTemporaryFile
import pprint
from netCDF4 import Dataset
import httplib


# When settings.DEBUG is True Django will fill up a hash with stats on every insert done to the database.
# "Monkey patch" the CursorWrapper to prevent this.  Otherwise we can't load large amounts of data.
# See http://stackoverflow.com/questions/7768027/turn-off-sql-logging-while-keeping-settings-debug
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.utils import CursorWrapper

# Constant for ParameterGroup name - for utils/STOQSQmanager.py to use
MEASUREDINSITU = 'Measured in situ'

# Constants for a Resource and ResourceType names - to be also used in utils/Viz
X3D_MODEL = 'X3D_MODEL'
X3D_MODEL_NOMINALDEPTH = 'X3D_MODEL_nominaldepth'
X3D_MODEL_SCALEFACTOR = 'X3D_MODEL_scalefactor'
X3DPLATFORMMODEL = 'x3dplatformmodel'

if settings.DEBUG:
    BaseDatabaseWrapper.make_debug_cursor = lambda self, cursor: CursorWrapper(cursor, self)

missing_value = 1e-34

def cmd_exists(cmd):
    return subprocess.call("type " + cmd, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0
    

class SkipRecord(Exception):
    pass


class HasMeasurement(Exception):
    pass


class ParameterNotFound(Exception):
    pass


class FileNotFound(Exception):
    pass


class LoadScript(object):
    '''
    Base class for load script to inherit from for reusing common utility methods such
    as process_command_line()
    ''' 

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    def __init__(self, base_dbAlias, base_campaignName, description=None, stride=1, x3dTerrains=None, grdTerrain=None):
        self.base_dbAlias = base_dbAlias
        self.base_campaignName = base_campaignName
        self.campaignDescription = description
        self.stride = stride
        self.x3dTerrains = x3dTerrains
        self.grdTerrain = grdTerrain

    def process_command_line(self):
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS. 
        Process command line arguments to support these kind of database loads:
            - Optimal stride
            - Test version
            - Uniform stride

        Load scripts should have execution code that looks like:

            # Execute the load
            cl.process_command_line()
        
            if cl.args.test:
                ##cl.loadDorado(stride=100)
                cl.loadM1ts(stride=10)
                cl.loadM1met(stride=10)
            
            elif cl.args.optimal_stride:
                cl.loadDorado(stride=2)
                cl.loadM1ts(stride=1)
                cl.loadM1met(stride=1)
        
            else:
                cl.stride = cl.args.stride
                cl.loadDorado()
                cl.loadM1ts()
                cl.loadM1met()

        Optional arguments for associating X3D Terrains and Viewpoints with this Campaign: 
            - x3dTerrains: Dict of absolute URL hashes to X3D GeoElevationGrids with hashes of 
                           viewpoint position, orientation, and centerOfRotation

        '''

        import argparse
        from argparse import RawTextHelpFormatter

        exampleString = ''
        for dbType in ('', '_t', '_o', '_s10'):
            if dbType == '':
                exampleString = exampleString + '  %s       \t# Load full resolution data into %s\n' % (
                                    sys.argv[0], self.base_dbAlias)
            elif dbType == '_s10':
                exampleString = exampleString + '  %s -%s 10\t# Load data into %s\n' % (
                                    sys.argv[0], dbType[1], self.base_dbAlias + dbType)
            else:
                exampleString = exampleString + '  %s -%s    \t# Load data into %s\n' % (
                                    sys.argv[0], dbType[1], self.base_dbAlias + dbType)

        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='STOQS load script for "%s"' % self.base_campaignName,
                                         epilog='Examples:' + '\n\n' + exampleString + '\n' +
                                            '(Databases must be created, synced and defined in privateSettings - see INSTALL instructions)')
        parser.add_argument('--dbAlias', action='store',
                            help='Database alias (default = %s)' % self.base_dbAlias)
        parser.add_argument('--campaignName', action='store',
                            help='Campaign Name (default = "%s")' % self.base_campaignName)
        parser.add_argument('-o', '--optimal_stride', action='store_true',
                            help='Run load for optimal stride configuration as defined in \n"if cl.args.optimal_stride:" section of load script')
        parser.add_argument('-t', '--test', action='store_true',
                            help='Run load for test configuration as defined in \n"if cl.args.test:" section of load script')
        parser.add_argument('-s', '--stride', action='store', type=int, default=1,
                            help='Stride value (default=1)')
        parser.add_argument('-a', '--append', action='store_true', 
                            help='Append data to existing activity - for use in repetative runs')
        parser.add_argument('-v', '--verbose', action='store_true', 
                            help='Turn on DEBUG level logging output')

        self.args = parser.parse_args()

        # Modify base dbAlias with conventional suffix if dbAlias not specified on command line
        if not self.args.dbAlias:
            if self.args.optimal_stride:
                self.dbAlias = self.base_dbAlias + '_o'
            elif self.args.test:
                self.dbAlias = self.base_dbAlias + '_t'
            elif self.args.stride:
                if self.args.stride == 1:
                    self.dbAlias = self.base_dbAlias
                else:
                    self.dbAlias = self.base_dbAlias + '_s%d' % self.args.stride
        else:
            self.dbAlias = self.args.dbAlias

        # Modify base campaignName with conventional suffix if campaignName not specified on command line
        if not self.args.campaignName:
            if self.args.optimal_stride:
                self.campaignName = self.base_campaignName + ' with optimal strides'
            elif self.args.test:
                self.campaignName = self.base_campaignName + ' for testing'
            elif self.args.stride:
                if self.args.stride == 1:
                    self.campaignName = self.base_campaignName
                else:
                    self.campaignName = self.base_campaignName + ' with uniform stride of %d' % self.args.stride
        else:
            self.campaignName = self.args.campaignName

        if self.args.verbose:
            self.logger.setLevel(logging.DEBUG)

        self.commandline = ' '.join(sys.argv)
        self.logger.info('Executing command: %s', self.commandline)

    def addTerrainResources(self):
        '''
        If X3D Terrain information is specified then add as Resources to Campaign.  To be called after process_command_line().
        '''
        if not self.x3dTerrains:
            return

        # Enable use of this method without calling process_command_line() - as is done in ROVCTDloader.py
        if not hasattr(self, 'dbAlias'):
            self.dbAlias = self.base_dbAlias
        if not hasattr(self, 'campaignName'):
            self.campaignName = self.base_campaignName
        
        resourceType, _ = m.ResourceType.objects.using(self.dbAlias).get_or_create(
                          name='x3dterrain', description='X3D Terrain information for Spatial 3D visualization')
            
        self.logger.info('Adding to ResourceType: %s', resourceType)
        self.logger.debug('Looking in database %s for Campaign name = %s', self.dbAlias, self.campaignName)
        campaign = m.Campaign.objects.using(self.dbAlias).get(name=self.campaignName)
        
        for url, viewpoint in self.x3dTerrains.iteritems():
            self.logger.debug('url = %s, viewpoint = %s', url, viewpoint)
            for name, value in viewpoint.iteritems():
                resource, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                              uristring=url, name=name, value=value, resourcetype=resourceType)
                m.CampaignResource.objects.using(self.dbAlias).get_or_create(
                              campaign=campaign, resource=resource)
                self.logger.info('Resource uristring=%s, name=%s, value=%s', url, name, value)


    def addPlaybackResources(self, x3dmodelurl, aName):
        '''
        If X3D scene graph and DOM control information is specified then add as Resources to Activity.  
        To be called with each file (Activity) load.
        '''

        resourceType, _ = m.ResourceType.objects.using(self.dbAlias).get_or_create(
                          name='x3dplayback', description='X3D scene graph for Activity playback')
        ##resourceType, created = m.ResourceType.objects.using(self.dbAlias).get_or_create(
        ##                        name='x3dplaybackhtml', description='X3D DOM control HTML stubs for Activity playback')

        self.logger.info('Adding to ResourceType: %s', resourceType)
        self.logger.debug('Looking in database %s for Activity name = %s', self.dbAlias, aName)
        activity = m.Activity.objects.using(self.dbAlias).get(name=aName)
        
        resource, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                      uristring=x3dmodelurl, name=X3D_MODEL, value=
                      'Output from bed2x3d.py - uristring to be included in GeoLocation node',
                      resourcetype=resourceType)
        m.ActivityResource.objects.using(self.dbAlias).get_or_create(
                      activity=activity, resource=resource)
        self.logger.info('Resource uristring=%s', x3dmodelurl)

    def addPlatformResources(self, x3dmodelurl, pName, value='X3D model', nominaldepth=0.0, scalefactor=1.0):
        '''Add Resources to Platform.  Used initially for adding X3D model of a platform.
        Can put additional descriptive information in value option, e.g.: "X3D model 
        derived from SolidWorks model of ESP and processed through aopt"
        '''

        resourceType, _ = m.ResourceType.objects.using(self.dbAlias).get_or_create(
                name=X3DPLATFORMMODEL, description='X3D scene for model of a platform')

        self.logger.info('Adding to ResourceType: %s', resourceType)
        self.logger.debug('Looking in database %s for Platform name = %s', self.dbAlias, pName)
        try:
            platform = m.Platform.objects.using(self.dbAlias).get(name=pName)
        except ObjectDoesNotExist:
            self.logger.warn("Platform {} not found. Can't add Resources.".format(pName))
            return
        
        r, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                uristring=x3dmodelurl, name=X3D_MODEL, value=value, resourcetype=resourceType)
        m.PlatformResource.objects.using(self.dbAlias).get_or_create(
                platform=platform, resource=r)

        r, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                uristring=x3dmodelurl, 
                name=X3D_MODEL_NOMINALDEPTH, value=nominaldepth, resourcetype=resourceType)
        m.PlatformResource.objects.using(self.dbAlias).get_or_create(
                platform=platform, resource=r)

        r, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                uristring=x3dmodelurl, 
                name=X3D_MODEL_SCALEFACTOR, value=scalefactor, resourcetype=resourceType)
        m.PlatformResource.objects.using(self.dbAlias).get_or_create(
                platform=platform, resource=r)

        self.logger.info('Resource uristring=%s', x3dmodelurl)


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
    global_ignored_names = ('longitude','latitude', 'time', 'Time',
                'LONGITUDE','LATITUDE','TIME', 'NominalDepth', 'esecs', 'Longitude', 'Latitude',
                'DEPTH','depth') # A list (tuple) of parameters that should not be imported as parameters
    global_dbAlias = ''

    logger = logging.getLogger('__main__')
    logger.setLevel(logging.INFO)

    def __init__(self, activityName, platformName, dbAlias='default', campaignName=None, 
                 campaignDescription=None, activitytypeName=None, platformColor=None, 
                 platformTypeName=None, stride=1):
        '''
        Intialize with settings that are common for any load of data into STOQS.
        
        @param activityName: A string describing this activity
        @param platformName: A string that is the name of the platform. If that name 
                             for a Platform exists in the DB, it will be used.
        @param platformColor: An RGB hex string represnting the color of the platform. 
        @param dbAlias: The name of the database alias as defined in settings.py
        @param campaignName: A string describing the Campaign in which this activity belongs, 
                             If that name for a Campaign exists in the DB, it will be used.
        @param campaignDescription: A string expanding on the campaignName. It should be a 
                                    short phrase expressing the where and why of a campaign.
        @param activitytypeName: A string such as 'mooring deployment' or 'AUV mission' 
                                 describing type of activity, If that name for a ActivityType 
                                 exists in the DB, it will be used.
        @param platformTypeName: A string describing the type of platform, e.g.: 'mooring', 
                                 'auv'.  If that name for a PlatformType exists in the DB, 
                                 it will be used.
        
        '''
        self.campaignName = campaignName
        self.campaignDescription = campaignDescription
        self.activitytypeName = activitytypeName
        self.platformName = platformName
        self.platformColor = platformColor
        self.dbAlias = dbAlias
        self.platformTypeName = platformTypeName
        self.activityName = activityName
        self.stride = stride
        
        self.build_standard_names()

    
    def getPlatform(self, name, type_name):
        '''
        Given just a platform name get a platform object from the STOQS database.  If no such object is in the
        database then create a new one.  Makes use of the MBARI tracking database to keep the names and types
        consistent.  The intention of the logic here is to make platform settings dynamic, yet consistent in 
        reusing what is already in the database.  There might need to be some independent tests to ensure that
        we make no duplicates.  The aim is to be case insensitive on the lookup, but to preserve the case of
        what is in MBARItracking.

        Platform names mut be composed of [a-zA-Z0-9_], containing no special characters or spaces.
        '''

        ##paURL = 'http://odss-staging.shore.mbari.org/trackingdb/platformAssociations.csv'
        paURL = 'http://odss.mbari.org/trackingdb/platformAssociations.csv'
        ##paURL = 'http://192.168.111.177/trackingdb/platformAssociations.csv'  # Private URL for host malibu
        # Returns lines like:
        # PlatformType,PlatformName
        # ship,Martin
        # ship,PT_LOBOS
        # ship,W_FLYER
        # ship,W_FLYER
        # ship,ZEPHYR
        # mooring,Bruce

        if re.search('[^a-zA-Z0-9_-]', name):
            raise Exception('Platform name = "%s" is not allowed.  Name can contain only letters, numbers, "_", and "-"' % name)

        self.logger.debug("Opening %s to read platform names for matching to the MBARI tracking database", paURL)
        try:
            tpHandle = csv.DictReader(urllib2.urlopen(paURL))
        except urllib2.URLError as e:
            self.logger.warn('Could not open %s', paURL)
            self.logger.warn(e)

        platformName = ''
        try:
            for rec in tpHandle:
                ##print "rec = %s" % rec
                if rec['PlatformName'].lower() == name.lower():
                    platformName = rec['PlatformName']
                    tdb_platformTypeName = rec['PlatformType']
                    break
        except httplib.IncompleteRead as e:
            self.logger.warn(e)

        if not platformName:
            platformName = name
            self.logger.debug("Platform name %s not found in tracking database.  Creating new platform anyway.", platformName)

        # Preference: 1. __init__(), 2. this function arg, 3. tracking DB
        if not self.platformTypeName:
            if type_name:
                self.platformTypeName = type_name
            elif tdb_platformTypeName:
                self.platformTypeName = tdb_platformTypeName
            else:
                self.logger.warn('self.platformTypeName has not been assigned')

        # Create PlatformType
        self.logger.debug("calling using('%s').get_or-create() on PlatformType for platformTypeName = %s", self.dbAlias, self.platformTypeName)
        platformType, created = m.PlatformType.objects.using(self.dbAlias).get_or_create(name = self.platformTypeName)
        if created:
            self.logger.debug("Created platformType.name %s in database %s", platformType.name, self.dbAlias)
        else:
            self.logger.debug("Retrieved platformType.name %s from database %s", platformType.name, self.dbAlias)


        # Create Platform, allowing color to be updated by later load, eliminating potential duplicate names
        platform, created = m.Platform.objects.using(self.dbAlias).get_or_create(name=platformName, 
                                                                                 platformtype=platformType)
        if created:
            self.logger.info("Created platform %s in database %s", platformName, self.dbAlias)
        else:
            self.logger.info("Retrieved platform %s from database %s", platformName, self.dbAlias)

        platform.color = self.platformColor
        platform.save(using=self.dbAlias)

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
            dictionary is patterned after the pydap.model.BaseType variable from the NetCDF file (OPeNDAP URL).
            '''

            # Go through the keys of the OPeNDAP URL for the dataset and add the parameters as needed to the database
            for key in parmDict.keys():
                self.logger.debug("key = %s", key)
                if (key in self.ignored_names) or (key not in self.include_names): # skip adding parameters that are ignored
                    continue
                v = parmDict[key].attributes
                self.logger.debug("v = %s", v)
                try:
                    self.getParameterByName(key)
                except ParameterNotFound as e:
                    self.logger.debug("Parameter not found. Assigning parms from ds variable.")
                    # Bug in pydap returns a gobbledegook list of things if the attribute value has not been
                    # set.  Check for this on units and override what pydap returns.
                    if isinstance(v.get('units'), list):
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
                        self.logger.warn('%s', e)
                        transaction.savepoint_rollback(sid)
                        if str(e).startswith('duplicate key value violates unique constraint "stoqs_parameter_pkey"'):
                            self.resetParameterAutoSequenceId()
                            try:
                                sid2 = transaction.savepoint(using=self.dbAlias)
                                self.parameter_dict[key].save(using=self.dbAlias)
                                self.ignored_names.remove(key)  # unignore, since a failed lookup will add it to the ignore list.
                            except Exception as e:
                                self.logger.error('%s', e)
                                transaction.savepoint_rollback(sid2,using=self.dbAlias)
                                raise Exception('''Failed reset auto sequence id on the stoqs_parameter table''')
                        else:
                            self.logger.error('Exception %s', e)
                            raise Exception('''Failed to add parameter for %s
                                %s\nEither add parameter manually, or add to ignored_names''' % (key,
                                '\n'.join(['%s=%s' % (k1,v1) for k1,v1 in parms.iteritems()])))
                        
                    except Exception as e:
                        self.logger.error('%s', e)
                        transaction.savepoint_rollback(sid,using=self.dbAlias)
                        raise Exception('''Failed to add parameter for %s
                            %s\nEither add parameter manually, or add to ignored_names''' % (key,
                            '\n'.join(['%s=%s' % (k1,v1) for k1,v1 in parms.iteritems()])))
                    self.logger.debug("Added parameter %s from data set to database %s", key, self.dbAlias)

        return innerAddParameters(self, parmDict)

    def createCampaign(self):
        '''Create Campaign in the database ensuring that there is only one Campaign
        in the database. If supplied Campaign name exists in database then that
        campaign is used and supplied Campaign description is ignored.
        '''

        try:
            self.campaign = m.Campaign.objects.using(self.dbAlias).get(id=1)
            self.logger.info('Retrieved Campaign = %s', self.campaign)
            if self.campaign.name != self.campaignName:
                self.logger.warn('Supplied Campaign name of %s does not match name = %s '
                    'in database %s', self.campaignName, self.campaign.name, self.dbAlias)
                self.logger.warn('Using Campaign already existing in the database')
        except ObjectDoesNotExist:
            self.campaign = m.Campaign(name = self.campaignName,
                                       description = self.campaignDescription)
            self.campaign.save(using=self.dbAlias)
            self.logger.info('Created campaign = %s', self.campaign)
 
    def createActivity(self):
        '''
        Use provided activity information to add the activity to the database.
        '''
        
        self.logger.info("Creating Activity with startDate = %s and endDate = %s", 
                self.startDatetime, self.endDatetime)
        comment = 'Loaded on %s with these include_names: %s' % (datetime.now(), 
                ' '.join(self.include_names))
        self.logger.info("comment = " + comment)

        # Need to create Campaign and ActivityType before creating Activity
        self.createCampaign()
        if self.activitytypeName is not None:
            self.activityType, created = m.ActivityType.objects.using(self.dbAlias
                                        ).get_or_create(name = self.activitytypeName)

        # Get or create Activity based on unique identifiers
        self.activity, created = m.Activity.objects.using(self.dbAlias).get_or_create(    
                                        name__contains = self.activityName,
                                        platform = self.platform,
                                        campaign = self.campaign,
                                        activitytype = self.activityType,
                                        startdate = self.startDatetime)

        if created:
            self.logger.info("Created activity %s in database %s with startDate=%s, endDate = %s",
                    self.activityName, self.dbAlias, self.startDatetime, self.endDatetime)
        else:
            self.logger.info("Retrieved activity %s from database %s", self.activityName, self.dbAlias)

        # Update Activity with attributes that may change, e.g.  with --append option
        m.Activity.objects.using(self.dbAlias).filter(
                    id=self.activity.id).update(enddate = self.endDatetime)
    
    def addResources(self):
        '''
        Add Resources for this activity, namely the NC_GLOBAL attribute names and values,
        and all the attributes for each variable in include_names.
        '''
        # The source of the data - this OPeNDAP URL
        resourceType, _ = m.ResourceType.objects.using(self.dbAlias).get_or_create(name = 'opendap_url')
        self.logger.debug("Getting or Creating Resource with name = %s, value = %s", 'opendap_url', self.url )
        resource, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                            name='opendap_url', value=self.url, uristring=self.url, resourcetype=resourceType)
        ar, _ = m.ActivityResource.objects.using(self.dbAlias).get_or_create(
                    activity=self.activity, resource=resource)

        # The NC_GLOBAL attributes from the OPeNDAP URL.  Save them all.
        self.logger.debug("Getting or Creating ResourceType nc_global...")
        self.logger.debug("ds.attributes.keys() = %s", self.ds.attributes.keys() )
        if 'NC_GLOBAL' in self.ds.attributes:
            resourceType, _ = m.ResourceType.objects.using(self.dbAlias).get_or_create(name = 'nc_global')
            for rn, value in self.ds.attributes['NC_GLOBAL'].iteritems():
                self.logger.debug("Getting or Creating Resource with name = %s, value = %s", rn, value )
                resource, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                            name=rn, value=value, resourcetype=resourceType)
                ar, _ = m.ActivityResource.objects.using(self.dbAlias).get_or_create(
                            activity=self.activity, resource=resource)

            # Use potentially monkey-patched self.getFeatureType() method to write a correct value - as the UI depends on it
            mp_resource, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                        name='featureType', value=self.getFeatureType(), resourcetype=resourceType)
            ars = m.ActivityResource.objects.using(self.dbAlias).filter(activity=self.activity,
                            resource__resourcetype=resourceType, resource__name='featureType').select_related('resource')

            if not ars:
                # There was no featureType NC_GLOBAL in the dataset - associate to the one from self.getFeatureType()
                ar, _ = m.ActivityResource.objects.using(self.dbAlias).get_or_create(
                            activity=self.activity, resource=mp_resource)
            for ar in ars:
                if ar.resource.value != mp_resource.value:
                    # Update (override NC_GLOBAL's) with monkey-patched self.getFeatureType()'s value
                    ars = m.ActivityResource.objects.using(self.dbAlias).filter(activity=self.activity,
                            resource__resourcetype=resourceType, resource__name='featureType').update(resource=mp_resource)
                    self.logger.warn('Over-riding featureType from NC_GLOBAL (%s) with monkey-patched value = %s', 
                            ar.resource.value, mp_resource.value)
        else:
            self.logger.warn("No NC_GLOBAL attribute in %s", self.url)

        self.logger.info('Adding attributes of all the variables from the original NetCDF file')
        for v in self.include_names + ['altitude']:
            self.logger.info('v = %s', v)
            try:
                for rn, value in self.ds[v].attributes.iteritems():
                    self.logger.debug("Getting or Creating Resource with name = %s, value = %s", rn, value )
                    resource, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                                          name=rn, value=value, resourcetype=resourceType)
                    m.ParameterResource.objects.using(self.dbAlias).get_or_create(
                                    parameter=self.getParameterByName(v), resource=resource)
                    m.ActivityResource.objects.using(self.dbAlias).get_or_create(
                                    activity=self.activity, resource=resource)
                    
            except KeyError as e:
                # Just skip derived parameters that may have been added for a sub-classed Loader
                if v != 'altitude':
                    self.logger.warn('include_name %s is not in %s - skipping', v, self.url)
            except AttributeError as e:
                # Just skip over loaders that don't have the plotTimeSeriesDepth attribute
                self.logger.warn('%s for include_name %s in %s. Skipping', e, v, self.url)
            except ParameterNotFound as e:
                self.logger.warn('Could not get Parameter for v = %s: %s', v, e)

        self.logger.info('Adding plotTimeSeriesDepth Resource for Parameters we want plotted in Parameter tab')
        for v in self.include_names + ['altitude']:
            if hasattr(self, 'plotTimeSeriesDepth'):
                if self.plotTimeSeriesDepth.get(v, None) is not None:
                    self.logger.info('v = %s', v)
                    try:
                        uiResType, _ = m.ResourceType.objects.using(self.dbAlias).get_or_create(name='ui_instruction')
                        resource, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                                              name='plotTimeSeriesDepth', value=self.plotTimeSeriesDepth[v], resourcetype=uiResType)
                    except ParameterNotFound as e:
                        self.logger.warn('Could not get_or_create uiResType or resource for v = %s: %s', v, e)
                    try:
                        m.ParameterResource.objects.using(self.dbAlias).get_or_create(
                                        parameter=self.getParameterByName(v), resource=resource)
                    except ParameterNotFound as e:
                        self.logger.warn('Could not add plotTimeSeriesDepth ParameterResource for v = %s: %s', v, e)
                    try:
                        m.ActivityResource.objects.using(self.dbAlias).get_or_create(
                                        activity=self.activity, resource=resource)
                    except ParameterNotFound as e:
                        self.logger.warn('Could not add plotTimeSeriesDepth PlatformResource for v = %s: %s', v, e)
        
    def getParameterByName(self, name):
        '''
        Locate a parameter's object from the database.  Cache objects after lookup.
        If a standard name is provided we'll look up using it instead, as it's more standard.
    
        @param name: Name of parameter object to lookup/locate 
        '''
        # First try to locate the parameter using the standard name (if we have one)
        if name not in self.parameter_dict:
            self.logger.debug("'%s' is not in self.parameter_dict", name)
            if self.standard_names.get(name) is not None:
                self.logger.debug("self.standard_names.get('%s') is not None", name)
                try:
                    self.logger.debug("For name = %s ", name)
                    self.logger.debug("standard_names = %s", self.standard_names[name])
                    self.logger.debug("retrieving from database %s", self.dbAlias)
                    self.parameter_dict[name] = m.Parameter.objects.using(self.dbAlias).get(standard_name = self.standard_names[name][0])
                except ObjectDoesNotExist:
                    pass
                except IndexError:
                    pass
        # If we still haven't found the parameter using the standard_name, start looking using the name
        if name not in self.parameter_dict:
            self.logger.debug("Again '%s' is not in self.parameter_dict", name)
            try:
                self.logger.debug("trying to get '%s' from database %s...", name, self.dbAlias)
                ##(parameter, created) = m.Parameter.objects.get(name = name)
                self.parameter_dict[name] = m.Parameter.objects.using(self.dbAlias).get(name = name)
                self.logger.debug("self.parameter_dict[name].name = %s", self.parameter_dict[name].name)
            except ObjectDoesNotExist:
                ##print >> sys.stderr, "Unable to locate parameter with name %s.  Adding to ignored_names list." % (name,)
                self.ignored_names.append(name)
                raise ParameterNotFound('Parameter %s not found in the cache nor the database' % (name,))
        # Finally, since we haven't had an error, we MUST have a parameter for this name.  Return it.

        self.logger.debug("Returning self.parameter_dict[name].units = %s", self.parameter_dict[name].units)
        try:
            self.parameter_dict[name].save(using=self.dbAlias)
        except Exception as e:
            print e
            print name
            pprint.pprint( self.parameter_dict[name])

        return self.parameter_dict[name]

    def createMeasurement(self, mtime, depth, lat, lon, nomDepth=None, nomLat=None, nomLong=None):
        '''
        Create and return a measurement object in the database.  The measurement object
        is created by first creating an instance of stoqs.models.Instantpoint using the activity, 
        then by creating an instance of Measurement using the Instantpoint.  A reference to 
        an instance of a stoqs.models.Measurement object is then returned.
        @param mtime: A valid datetime instance of a datetime object used to create the Instantpoint
        @param depth: The depth for the measurement
        @param lat: The latitude (degrees, assumed WGS84) for the measurement
        @param lon: The longitude (degrees, assumed WGS84) for the measurement
        @param nomDepth: The nominal depth (e.g. for a timeSeriesProfile featureType) measurement
        @param nomLat: The nominal latitude (e.g. for a timeSeriesProfile featureType) measurement
        @param nomLong: The nominal longitude (e.g. for a timeSeriesProfile featureType) measurement
        @return: An instance of stoqs.models.Measurement
        '''
        # Brute force QC check on depth to remove egregous outliers
        minDepth = -1000
        maxDepth = 5000
        if depth < minDepth or depth > maxDepth:
            raise SkipRecord('Bad depth: %s (depth must be between %s and %s)' % (depth, minDepth, maxDepth))

        # Brute force QC check on latitude and longitude to remove egregous outliers
        if lat < -90 or lat > 90:
            raise SkipRecord('Bad lat: %s (latitude must be between %s and %s)' % (lat, -90, 90))
        if lon < -720 or lon > 720:
            raise SkipRecord('Bad lon: %s (longitude must be between %s and %s)' % (long, -720, 720))

        ip, _ = m.InstantPoint.objects.using(self.dbAlias).get_or_create(activity=self.activity, timevalue=mtime)

        nl = None
        point = 'POINT(%s %s)' % (repr(lon), repr(lat))
        if not (nomDepth is None and nomLat is None and nomLong is None):
            self.logger.debug('nomDepth = %s nomLat = %s nomLong = %s', nomDepth, nomLat, nomLong)
            nom_point = 'POINT(%s %s)' % (repr(nomLong), repr(nomLat))
            nl, _ = m.NominalLocation.objects.using(self.dbAlias).get_or_create(depth=repr(nomDepth), 
                                    geom=nom_point, activity=self.activity)

        try:
            measurement, _ = m.Measurement.objects.using(self.dbAlias).get_or_create(instantpoint=ip, 
                                    nominallocation=nl, depth=repr(depth), geom=point)
        except DatabaseError:
            self.logger.exception('''DatabaseError:
                It is likely that you need https://code.djangoproject.com/attachment/ticket/16778/postgis-adapter.patch.
                Check the STOQS INSTALL file for instructions on Django patch #16778.

                It's also likely that creating a nominallocation was attempted on a database that does not have that relation.
                Several schema changes were checked into the STOQS repository in June 2013.  It's suggested that you
                drop the database, recreate it, resync, and reload. 
                ''')
            sys.exit(-1)
        except Exception as e:
            self.logger.error('Exception %s', e)
            self.logger.error("Cannot save measurement mtime = %s, long = %s, lat = %s,"
                              " depth = %s", mtime, repr(long), repr(lat), repr(depth))
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
        self.logger.debug(row)
        if 'measurement' in row:
            # Special for things like LOPC data 
            raise HasMeasurement()
               
        try:
            if (row['longitude'] == missing_value or row['latitude'] == missing_value or
                    #float(row['longitude']) == 0.0 or float(row['latitude']) == 0.0 or
                    math.isnan(row['longitude'] ) or math.isnan(row['latitude'])):
                raise SkipRecord('Invalid latitude or longitude coordinate')
        except KeyError as e:
            raise SkipRecord('KeyError: ' + str(e))

        # Additional sanity check on latitude and longitude
        if row['latitude'] > 90 or row['latitude'] < -90:
            raise SkipRecord('Invalid latitude = %s' % row['latitude'])
        if row['longitude'] > 720 or row['longitude'] < -720:
            raise SkipRecord('Invalid longitude = %s' % row['longitude'])

        return row

    def checkForValidData(self):
        '''
        Do a pre- check on the OPeNDAP url for the include_names variables. If there are non-NaN data in
        any of the variables return True, otherwise return False.
        '''
        allNaNFlag = {}
        anyValidData = False
        self.logger.info("Checking for valid data from %s", self.url)
        self.logger.debug("include_names = %s", self.include_names)
        for v in self.include_names:
            self.logger.debug("v = %s", v)
            try:
                try:
                    allNaNFlag[v] = np.isnan(self.ds[v][:]).all()
                except TypeError:
                    allNaNFlag[v] = np.isnan(self.ds[v].array).all()
                if not allNaNFlag[v]:
                    anyValidData = True
            except KeyError:
                self.logger.debug('Parameter %s not in %s. Skipping.', v, self.ds.keys())
                if v.find('.') != -1:
                    raise Exception('Parameter names must not contain periods - cannot load data. Paramater %s violates CF conventions.' % v)
            except ValueError:
                pass

        self.logger.debug("allNaNFlag = %s", allNaNFlag)
        for v in allNaNFlag.keys():
            if not allNaNFlag[v]:
                self.varsLoaded.append(v)
        self.logger.info("Variables that have data: self.varsLoaded = %s", self.varsLoaded)

        return anyValidData
    
   
    def build_standard_names(self):
        '''
        Create a dictionary that contains keys that are fields, and values that
        are the standard names of those fields.  Classes that inherit from this
        class should set any default standard names at the class level.
        '''
        if not hasattr(self, 'ds'):
            # Loaders (such as those in SampleLoaders.py) may inherit this method and not use OPeNDAP
            return
        try:
            for var in self.ds.keys():
                if var in self.standard_names: 
                    continue # don't override pre-specified names
                if 'standard_name' in self.ds[var].attributes:
                    self.standard_names[var]=self.ds[var].attributes['standard_name']
                else:
                    self.standard_names[var]=None # Indicate those without a standard name
        except AttributeError as e:
            self.logger.warn(e)

    @staticmethod
    def update_ap_stats(dbAlias, activity, parameters, sampledFlag=False):
        '''Update the database with descriptive statistics for parameters
        belonging to the activity.
        '''
        for p in parameters:
            ap, _ = m.ActivityParameter.objects.using(dbAlias).get_or_create(
                            parameter=p, activity=activity)

            if sampledFlag:
                data = m.SampledParameter.objects.using(dbAlias).filter(
                                parameter=p, sample__instantpoint__activity=activity
                                ).values_list('datavalue', flat=True)
            else:
                data = m.MeasuredParameter.objects.using(dbAlias).filter(
                                parameter=p, measurement__instantpoint__activity=activity
                                ).values_list('datavalue', flat=True)

            np_data = np.array([float(d) for d in data])
            np_data.sort()
            ap.number = len(np_data)
            ap.min = np_data.min()
            ap.max = np_data.max()
            ap.mean = np_data.mean()
            ap.median = median(list(np_data))
            ap.mode = mode(np_data)
            ap.p025 = percentile(list(np_data), 0.025)
            ap.p975 = percentile(list(np_data), 0.975)
            ap.p010 = percentile(list(np_data), 0.010)
            ap.p990 = percentile(list(np_data), 0.990)
            ap.save(using=dbAlias)

            # Compute and save histogram, use smaller number of bins 
            # for Sampled Parameters
            if sampledFlag:
                (counts, bins) = np.histogram(np_data,10)
            else:
                (counts, bins) = np.histogram(np_data,100)
            for i,count in enumerate(counts):
                m.ActivityParameterHistogram.objects.using(dbAlias).get_or_create(
                        activityparameter=ap, bincount=count, 
                        binlo=bins[i], binhi=bins[i+1])

    @classmethod
    def update_activityparameter_stats(cls, dbAlias, activity, parameters, sampledFlag=False):
        '''Class method for update_ap_stats() so that subclasses can call it via
        updateActivityParameterStats()
        '''
        cls.update_ap_stats(dbAlias, activity, parameters, sampledFlag)

    def updateActivityParameterStats(self, parameterCounts, sampledFlag=False):
        ''' 
        Examine the data for the Activity, compute and update some statistics on the measuredparameters
        for this activity.  Store the histogram in the associated table.
        '''                 
        if self.activity:
            act = self.activity
        else:
            raise Exception('Must have an activity defined in self.activity')

        try:
            self.update_activityparameter_stats(self.dbAlias, act, parameterCounts, sampledFlag)
        except ValueError as e:
            self.logger.warn('%s. Likely a dataarray as from LOPC data', e)
        except IntegrityError as e:
            self.logger.warn('IntegrityError(%s): Cannot create ActivityParameter and '
                             'updated statistics for Activity %s.', (e, act))

        self.logger.info('Updated statistics for activity.name = %s', act.name)

    def insertSimpleDepthTimeSeries(self, critSimpleDepthTime=10):
        '''
        Read the time series of depth values for this activity, simplify it and insert the values in the
        SimpleDepthTime table that is related to the Activity.  This procedure is suitable for only
        trajectory data; timeSeriesProfile type data uses another method to produce a collection of
        simple depth time series for display in flot.
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

        self.logger.debug('line = %s', line)
        self.logger.info('Number of points in original depth time series = %d', len(line))
        try:
            # Original simplify_points code modified: the index from the original line is added as 3rd item in the return
            simple_line = simplify_points(line, critSimpleDepthTime)
        except IndexError:
            simple_line = []        # Likely "list index out of range" from a stride that's too big
        self.logger.info('Number of points in simplified depth time series = %d', len(simple_line))
        self.logger.debug('simple_line = %s', simple_line)

        for t,d,k in simple_line:
            try:
                ip = m.InstantPoint.objects.using(self.dbAlias).get(id = pklookup[k])
                m.SimpleDepthTime.objects.using(self.dbAlias).create(activity = self.activity, instantpoint = ip, depth = d, epochmilliseconds = t)
            except ObjectDoesNotExist:
                self.logger.warn('InstantPoint with id = %d does not exist; from point at index k = %d', pklookup[k], k)

        self.logger.info('Inserted %d values into SimpleDepthTime', len(simple_line))

    def saveBottomDepth(self):
        @transaction.atomic(using=self.dbAlias)
        def _innerSaveBottomDepth(self):
            '''
            Read the time series of Parameter altitude and add to depth values to compute BottomDepth
            and add it to the Measurement so that our Matplotlib plots can also ieasily include the depth profile.  
            This procedure is suitable for only trajectory data.
            '''
            mpQS = m.MeasuredParameter.objects.using(self.dbAlias).select_related('measurement'
                                          ).filter( datavalue__isnull=False,
                                                    measurement__instantpoint__activity=self.activity, 
                                                    parameter__standard_name='height_above_sea_floor')
            count =  mpQS.count()
            self.logger.info('mpQS.count() = %s', count)

            counter = 0
            for mp in mpQS:
                counter += 1
                try:
                    mp.measurement.bottomdepth = mp.measurement.depth + mp.datavalue
                    mp.measurement.save(using=self.dbAlias)
                except DatabaseError as e:
                    self.logger.warn(e)

                if counter % 10000 == 0:
                    self.logger.info('%d of %d mp.measurement.bottomdepth records saved', counter, count)

            return _innerSaveBottomDepth(self)

    def insertSimpleBottomDepthTimeSeries(self, critSimpleBottomDepthTime=10):
        @transaction.atomic(using=self.dbAlias)
        def _innerInsertSimpleBottomDepthTimeSeries(self, critSimpleBottomDepthTime=10):
            '''
            Read the bottomdepth from Measurement for the Activity, simplify it 
            and insert the values in the SimpleBottomDepthTime table that is related to the Activity.  
            This procedure is suitable for only trajectory data.
            @param critSimpleBottomDepthTime: An integer for the simplification factor, 10 is course, .0001 is fine
            '''
            tbdQS = m.MeasuredParameter.objects.using(self.dbAlias).filter(measurement__instantpoint__activity=self.activity
                                          ).values('measurement__instantpoint__timevalue', 'measurement__bottomdepth',
                                          'measurement__instantpoint__id')
            count =  tbdQS.count()

            # simplify_points() has a limit of how many points it can handle
            maxRecords = .1e6
            stride = 1
            if count > maxRecords:
                stride = int((count + maxRecords / 2)/ maxRecords)
                self.logger.info('Striding tbdQS by %d to be kind to simplify_points()', stride)

            # Now, get time and bottomdepth that we just saved for building the SimpleBottomDepth time series
            line = []
            pklookup = []
            i = 0
            counter = 0
            for tbd in tbdQS:
                i += 1
                if i % stride == 0:
                    counter += 1
                    ems = 1000 * to_udunits(tbd['measurement__instantpoint__timevalue'], 'seconds since 1970-01-01')
                    if tbd['measurement__bottomdepth']:
                        line.append( (ems, tbd['measurement__bottomdepth']) )
                        pklookup.append(tbd['measurement__instantpoint__id'])
                        if counter % 10000 == 0:
                            self.logger.info('%d of %d points read', counter, int(count / stride))

            if line:
                try:
                    # Original simplify_points code modified: the index from the original line is added as 3rd item in the return
                    self.logger.info('Calling simplify_points with len(line) = %d', len(line))
                    simple_line = simplify_points(line, critSimpleBottomDepthTime)
                except IndexError:
                    simple_line = []        # Likely "list index out of range" from a stride that's too big
            else:
                simple_line = []

            self.logger.info('Number of points in simplified depth time series = %d', len(simple_line))
            self.logger.debug('simple_line = %s', simple_line)

            for t,d,k in simple_line:
                try:
                    ip = m.InstantPoint.objects.using(self.dbAlias).get(id = pklookup[k])
                    m.SimpleBottomDepthTime.objects.using(self.dbAlias).create(
                            activity=self.activity, instantpoint=ip, bottomdepth=d, epochmilliseconds=t)
                except ObjectDoesNotExist:
                    self.logger.warn('InstantPoint with id = %d does not exist; from point at index k = %d', pklookup[k], k)

            self.logger.info('Inserted %d values into SimpleBottomDepthTime', len(simple_line))

        return _innerInsertSimpleBottomDepthTimeSeries(self, critSimpleBottomDepthTime)

    def insertSimpleDepthTimeSeriesByNominalDepth(self, critSimpleDepthTime=10, trajectoryProfileDepths=None):
        '''
        Read the time series of depth values for each nominal depth of this activity, simplify them 
        and insert the values in the SimpleDepthTime table that is related via the NominalLocations
        to the Activity.  This procedure is suitable for timeSeries and timeSeriesProfile data
        @param critSimpleDepthTime: An integer for the simplification factor, 10 is course, .0001 is fine
        '''
        for i,nl in enumerate(m.NominalLocation.objects.using(self.dbAlias).filter(activity=self.activity)):
            nomDepth = nl.depth
            self.logger.debug('nomDepth = %s', nomDepth)
            # Collect depth time series into a timeseries by activity and nominal depth hash
            ndlqs = m.Measurement.objects.using(self.dbAlias).filter( instantpoint__activity=self.activity, nominallocation__depth=nomDepth
                                        ).values_list('instantpoint__timevalue', 'depth', 'instantpoint__pk').order_by('instantpoint__timevalue')
            line = []
            pklookup = []
            if trajectoryProfileDepths:
                self.logger.info('Loading time varying depths in SimpleDepthTime for nomDepth=%s', nomDepth)
                for (dt,dd,pk), depths in zip(ndlqs, trajectoryProfileDepths):
                    ems = 1000 * to_udunits(dt, 'seconds since 1970-01-01')
                    d = depths[i]
                    line.append((ems,d,))
                    pklookup.append(pk)
            else:
                for dt,dd,pk in ndlqs:
                    ems = 1000 * to_udunits(dt, 'seconds since 1970-01-01')
                    d = float(dd)
                    line.append((ems,d,))
                    pklookup.append(pk)

            self.logger.debug('line = %s', line)
            self.logger.debug('Number of points in original depth time series = %d', len(line))
            try:
                # Original simplify_points code modified: the index from the original line is added as 3rd item in the return
                simple_line = simplify_points(line, critSimpleDepthTime)
            except IndexError:
                simple_line = []        # Likely "list index out of range" from a stride that's too big
            self.logger.debug('Number of points in simplified depth time series = %d', len(simple_line))
            self.logger.debug('simple_line = %s', simple_line)
            if len(simple_line) != 2:
                self.logger.warn('len(simple_line) != 2. If appending data, then all points will be added to SimpleDepthTime')

            if self.dataStartDatetime and len(simple_line) == 2:
                # Assume that we are appending data. Make sure first time point exists
                t0,d0,k0 = simple_line[0]
                self.logger.debug('First point t0,d0,k0 = %s, %s, %s', t0,d0,k0)
                try:
                    ip = m.InstantPoint.objects.using(self.dbAlias).get(id = pklookup[k0])
                    self.logger.debug('ip = %s', ip)
                    m.SimpleDepthTime.objects.using(self.dbAlias).get_or_create(activity=self.activity, nominallocation=nl,
                                                                                instantpoint=ip, depth=d0, epochmilliseconds=t0)
                except ObjectDoesNotExist:
                    self.logger.warn('InstantPoint with id = %d does not exist; from point at index k = %d', pklookup[k0], k0)
                except MultipleObjectsReturned as e:
                    self.logger.warn(e)
                    firstPoints = m.SimpleDepthTime.objects.using(self.dbAlias).filter(activity=self.activity, nominallocation=nl,
                                                                                       instantpoint=ip, depth=d0, epochmilliseconds=t0)
                    self.logger.info('Deleting multiple points and creating just one.')
                    for fp in firstPoints:
                        fp.delete(using=self.dbAlias)
                    m.SimpleDepthTime.objects.using(self.dbAlias).create(activity=self.activity, nominallocation=nl,
                                                                         instantpoint=ip, depth=d0, epochmilliseconds=t0)

                # Update last point's time value by first deleting all times at depth for the activity > first time point
                t1,d1,k1 = simple_line[1]
                self.logger.debug('Last point t1,d1,k1 = %s, %s, %s', t1,d1,k1)
                lastPoints = m.SimpleDepthTime.objects.using(self.dbAlias).filter(
                        activity=self.activity, nominallocation=nl, depth=d1, epochmilliseconds__gt=t0)
                for lp in lastPoints:
                    self.logger.debug('Deleting SimpleDepthTime point with epochmilliseconds=%s', lp.epochmilliseconds)
                    lp.delete(using=self.dbAlias)
                try:
                    ip = m.InstantPoint.objects.using(self.dbAlias).get(id = pklookup[k1])
                    self.logger.debug('ip = %s', ip)
                    m.SimpleDepthTime.objects.using(self.dbAlias).create(activity=self.activity, nominallocation=nl,
                                                                         instantpoint=ip, depth=d1, epochmilliseconds=t1)
                except ObjectDoesNotExist:
                    self.logger.warn('InstantPoint with id = %d does not exist; from point at index k = %d', pklookup[k1], k1)
                
            else:
                for t,d,k in simple_line:
                    self.logger.debug('t,d,k = %s, %s, %s', t,d,k)
                    try:
                        ip = m.InstantPoint.objects.using(self.dbAlias).get(id = pklookup[k])
                        self.logger.debug('ip = %s', ip)
                        m.SimpleDepthTime.objects.using(self.dbAlias).create(activity=self.activity, nominallocation=nl,
                                                                         instantpoint=ip, depth=d, epochmilliseconds=t)
                    except ObjectDoesNotExist:
                        self.logger.warn('InstantPoint with id = %d does not exist; from point at index k = %d', pklookup[k], k)

            self.logger.info('Inserted %d values into SimpleDepthTime for nomDepth = %f', len(simple_line), nomDepth)

    def updateActivityMinMaxDepth(self):
        '''
        Pull the min & max depth from Measurement and set the Activity mindepth and maxdepth
        '''
        m_qs = (m.Measurement.objects.using(self.dbAlias)
                        .filter(instantpoint__activity__id=self.activity.id)
                        .aggregate(Max('depth'), Min('depth')))
        m.Activity.objects.using(self.dbAlias).filter(id=self.activity.id).update(
                                                        mindepth = m_qs['depth__min'],
                                                        maxdepth = m_qs['depth__max'])
    def updateCampaignStartEnd(self):
        '''
        Pull the min & max from InstantPoint and set the Campaign start and end from these
        '''
        try:
            if self.campaign:
                ip_qs = m.InstantPoint.objects.using(self.dbAlias).aggregate(Max('timevalue'), Min('timevalue'))
                m.Campaign.objects.using(self.dbAlias).filter(id=self.campaign.id).update(
                                                                                startdate = ip_qs['timevalue__min'],
                                                                                enddate = ip_qs['timevalue__max'])
        except AttributeError as e:
            self.logger.warn(e)

    def assignParameterGroup(self, parameterCounts, groupName=MEASUREDINSITU):
        ''' 
        For all the parameters in @parameterCounts create a many-to-many association with the Group named @groupName
        '''                 
        g, _ = m.ParameterGroup.objects.using(self.dbAlias).get_or_create(name=groupName)
        for p in parameterCounts:
            pgps = m.ParameterGroupParameter.objects.using(self.dbAlias).filter(parameter=p, parametergroup=g)
            if not pgps:
                # Attempt saving relation only if it does not exist
                pgp = m.ParameterGroupParameter(parameter=p, parametergroup=g)
                try:
                    pgp.save(using=self.dbAlias)
                except Exception as e:
                    self.logger.warn('%s: Cannot create ParameterGroupParameter name = %s for parameter.name = %s. Skipping.', e, groupName, p.name)

    def addSigmaTandSpice(self, parameterCounts, activity=None):
        ''' 
        For all measurements that have standard_name parameters of (sea_water_salinity or sea_water_practical_salinity) and sea_water_temperature 
        compute sigma-t and add it as a parameter
        '''                 
        def _innerAddSigmaTandSpice(self, parameterCounts, activity):
            # Find all measurements with 'sea_water_temperature' and ('sea_water_salinity' or 'sea_water_practical_salinity')
            ms = m.Measurement.objects.using(self.dbAlias)
            if activity:
                ms = ms.filter(instantpoint__activity=activity)

            ms = ms.filter(measuredparameter__parameter__standard_name='sea_water_temperature')

            # Test whether our measurements use 'sea_water_salinity' or 'sea_water_practical_salinity'
            salinity_standard_name = 'sea_water_salinity'
            if ms.filter(measuredparameter__parameter__standard_name='sea_water_practical_salinity'):
                salinity_standard_name = 'sea_water_practical_salinity'
            elif ms.filter(measuredparameter__parameter__standard_name='sea_water_salinity'):
                salinity_standard_name = 'sea_water_salinity'

            ms = ms.filter(measuredparameter__parameter__standard_name=salinity_standard_name)

            if not ms:
                self.logger.info("No sea_water_temperature and sea_water_salinity; can't add SigmaT and Spice.")
                return parameterCounts

            if self.dataStartDatetime:
                ms = ms.filter(instantpoint__timevalue__gt=self.dataStartDatetime)

            # Create our new Parameters
            p_sigmat, _ = m.Parameter.objects.using(self.dbAlias).get_or_create(
                    standard_name='sea_water_sigma_t',
                    long_name='Sigma-T',
                    units='kg m-3',
                    name='sigmat',
            )
            if 'spice' in self.include_names:
                p_spice, _ = m.Parameter.objects.using(self.dbAlias).get_or_create( 
                        name='stoqs_spice',
                        defaults={'long_name': 'Spiciness'}
                )
            else:
                p_spice, _ = m.Parameter.objects.using(self.dbAlias).get_or_create( 
                        name='spice',
                        defaults={'long_name': 'Spiciness'}
                )
            # Update with descriptions, being kind to legacy databases
            p_sigmat.description = ("Calculated in STOQS loader from Measured Parameters having standard_names"
                                    " sea_water_temperature and sea_water_salinity, and pressure converted from depth"
                                    " using seawater.eos80 module: sw.pden(s, t, sw.pres(me.depth, me.geom.y)) - 1000.0.")
            p_sigmat.save(using=self.dbAlias)
            p_spice.description = ("Calculated in STOQS loader from Measured Parameters having standard_names"
                                   " sea_water_temperature and sea_water_salinity using algorithm from Flament (2002):"
                                   " http://www.satlab.hawaii.edu/spice.")
            p_spice.save(using=self.dbAlias)

            parameterCounts[p_sigmat] = ms.count()
            parameterCounts[p_spice] = ms.count()
            self.assignParameterGroup({p_sigmat: ms.count()}, groupName=MEASUREDINSITU)
            self.assignParameterGroup({p_spice: ms.count()}, groupName=MEASUREDINSITU)

            # Loop through all Measurements, compute Sigma-T & Spice, and add to the Measurement
            for me in ms.distinct():
                try:
                    with transaction.atomic():
                        t = m.MeasuredParameter.objects.using(self.dbAlias).filter(measurement=me, 
                                parameter__standard_name='sea_water_temperature').values_list('datavalue')[0][0]
                        s = m.MeasuredParameter.objects.using(self.dbAlias).filter(measurement=me, 
                                parameter__standard_name=salinity_standard_name).values_list('datavalue')[0][0]
                except IntegrityError as e:
                    self.logger.warn(e)

                sigmat = sw.pden(s, t, sw.pres(me.depth, me.geom.y)) - 1000.0
                spice = spiciness(t, s)

                mp_sigmat = m.MeasuredParameter(datavalue=sigmat, measurement=me, parameter=p_sigmat)
                mp_spice = m.MeasuredParameter(datavalue=spice, measurement=me, parameter=p_spice)
                try:
                    with transaction.atomic():
                        mp_sigmat.save(using=self.dbAlias)
                        mp_spice.save(using=self.dbAlias)
                except IntegrityError as e:
                    self.logger.warn(e)

            return parameterCounts

        return _innerAddSigmaTandSpice(self, parameterCounts, activity)

    def addAltitude(self, parameterCounts, activity=None):
        ''' 
        For all measurements lookup the water depth from a GMT grd file using grdtrack(1), 
        subtract the depth and add altitude as a new Parameter to the Measurement
        To be called from load script after process_command_line().
        '''
        @transaction.atomic(using=self.dbAlias)
        def _innerAddAltitude(self, parameterCounts, activity=None):
            # Read the bounding box of the terrain file. The grdtrack command quietly does not write any lines for points outside of the grid.
            if self.grdTerrain:
                try:
                    fh = Dataset(self.grdTerrain)
                    # Old GMT format
                    xmin, xmax = fh.variables['x_range'][:]
                    ymin, ymax = fh.variables['y_range'][:]
                except IOError as e:
                    self.logger.error('Cannot add altitude. Make sure file %s is present.', self.grdTerrain)
                except KeyError as e:
                    try:
                        # New GMT format
                        xmin, xmax = fh.variables['lon'].actual_range
                        ymin, ymax = fh.variables['lat'].actual_range
                    except Exception as e:
                        try:
                            # Yet another format (seen in SanPedroBasin50.grd)
                            xmin, xmax = fh.variables['x'].actual_range
                            ymin, ymax = fh.variables['y'].actual_range
                        except Exception as e:
                            self.logger.error('Cannot read range metadata from %s. Not able to load'
                                              ' altitude, bottomdepth or simplebottomdepthtime', self.grdTerrain)
                            return parameterCounts
                except Exception as e:
                    self.logger.exception(e)
                    return parameterCounts
                finally:
                    fh.close()

                bbox = Polygon.from_bbox( (xmin, ymin, xmax, ymax) )

            # Build file of Measurement lon & lat for grdtrack to process
            xyFileName = NamedTemporaryFile(dir='/dev/shm', prefix='STOQS_LatLon_', suffix='.txt').name
            xyFH = open(xyFileName, 'w')
            ms = m.Measurement.objects.using(self.dbAlias).filter(geom__within=bbox)
            if activity:
                ms = ms.filter(instantpoint__activity=activity)
            ms = ms.order_by('instantpoint__activity__id', 'instantpoint__timevalue').values('id', 'geom', 'depth').distinct()
            mList = []
            depthList = []
            for me in ms:
                mList.append(me['id'])
                depthList.append(me['depth'])
                xyFH.write("%f %f\n" % (me['geom'].x, me['geom'].y))

            xyFH.close()
            inputFileCount = len(mList)
            self.logger.debug('Wrote file %s with %d records', xyFileName, inputFileCount)

            # Requires GMT (yum install GMT)
            bdepthFileName = NamedTemporaryFile(dir='/dev/shm', prefix='STOQS_BDepth', suffix='.txt').name
            if cmd_exists('grdtrack'):
                cmd = "grdtrack %s -V -G%s > %s" % (xyFileName, self.grdTerrain, bdepthFileName)
            else:
                # Assume we have GMT Version 5 installed
                cmd = "gmt grdtrack %s -V -G%s > %s" % (xyFileName, self.grdTerrain, bdepthFileName)

            self.logger.info('Executing %s' % cmd)
            os.system(cmd)
            if self.totalRecords > 1e6:
                self.logger.info('Sleeping 60 seconds to give time for system call to finish writing to %s', bdepthFileName)
                time.sleep(60)
            if self.totalRecords > 1e7:
                self.logger.info('Sleeping another 300 seconds to give time for system call to'
                                 ' finish writing to %s for more than 10 million records', bdepthFileName)
                time.sleep(300)

            # Create our new Parameter
            self.logger.info('Getting or creating new altitude Parameter')
            try:
                p_alt, _ = m.Parameter.objects.using(self.dbAlias).get_or_create(
                        standard_name='height_above_sea_floor',
                        long_name='Altitude',
                        description=("Calculated in STOQS loader by using GMT's grdtrack(1) program on the Platform's"
                                     " latitude, longitude values and differencing the Platform's depth with the"
                                     " bottom depth data in file %s." % self.grdTerrain.split('/')[-1]),
                        units='m',
                        name='altitude',
                        origin='https://github.com/stoqs/stoqs/blob/45f53d134d336fdbdb38f73959a2ce3be4148227/stoqs/loaders/__init__.py#L1216-L1322'
                )
            except IntegrityError:
                # A bit of a mystery why sometimes this Exception happens (simply get p_alt if it happens):
                # IntegrityError: duplicate key value violates unique constraint "stoqs_parameter_name_key"
                p_alt = m.Parameter.objects.using(self.dbAlias).get(name='altitude')

            parameterCounts[p_alt] = ms.count()
            self.assignParameterGroup({p_alt: ms.count()}, groupName=MEASUREDINSITU)

            # Read values from the grid sampling (bottom depths) and add datavalues to the altitude parameter using the save Measurements
            count = 0
            with open(bdepthFileName) as altFH:
                for line in altFH:
                    bdepth = line.split()[2]
                    alt = -float(bdepth)-depthList.pop(0)
                    try:
                        meas = m.Measurement.objects.using(self.dbAlias).get(id=mList.pop(0))
                        mp_alt = m.MeasuredParameter(datavalue=alt, measurement=meas, parameter=p_alt)
                        mp_alt.save(using=self.dbAlias)
                    except IntegrityError as e:
                        self.logger.warn(e)
                    except DatabaseError as e:
                        self.logger.warn(e)
                    count += 1

            # Cleanup and sanity check
            os.remove(xyFileName)
            os.remove(bdepthFileName)
            if inputFileCount != count:
                self.logger.warn('Counts are not equal! inputFileCount = %s, count from grdtrack output = %s', inputFileCount, count)

            return parameterCounts

        return _innerAddAltitude(self, parameterCounts, activity)

