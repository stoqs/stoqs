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
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE']='config.settings.local'
import django
django.setup()

from collections import defaultdict
from django.conf import settings
from django.contrib.gis.geos import Polygon, Point
from django.db.utils import IntegrityError
from django.db import transaction, DatabaseError, connections
from django.db.models import Max, Min
from stoqs import models as m
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
import time
import re
import subprocess
import math
import numpy as np
from coards import to_udunits
import seawater.eos80 as sw
import csv
import requests
from contextlib import closing
import logging
from utils.utils import percentile, median, mode, simplify_points, spiciness
from tempfile import NamedTemporaryFile
import pprint
from netCDF4 import Dataset
from argparse import ArgumentParser, RawTextHelpFormatter


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

# Parameter names created by STOQS Loads, shared with at least DAPloaders
SIGMAT = 'sigmat'
SPICE = 'spice'
SPICINESS = 'Spiciness'
ALTITUDE = 'altitude'

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

    def __init__(self, base_dbAlias, base_campaignName, description=None, stride=1, x3dTerrains=None, grdTerrain=None):
        self.base_dbAlias = base_dbAlias
        self.base_campaignName = base_campaignName
        self.campaignDescription = description
        self.stride = stride
        self.x3dTerrains = x3dTerrains
        self.grdTerrain = grdTerrain

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
        self.parser = ArgumentParser(formatter_class=RawTextHelpFormatter,
                                     description='STOQS load script for "%s"' % self.base_campaignName,
                                     epilog='Examples:' + '\n\n' + exampleString + '\n' +
                                            '(Databases must be created first, usually by execuing stoqs/loaders/load.py)')

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


        self.parser.add_argument('--dbAlias', action='store',
                            help='Database alias (default = %s)' % self.base_dbAlias)
        self.parser.add_argument('--campaignName', action='store',
                            help='Campaign Name (default = "%s")' % self.base_campaignName)
        self.parser.add_argument('-o', '--optimal_stride', action='store_true',
                            help='Run load for optimal stride configuration as defined in \n"if cl.args.optimal_stride:" section of load script')
        self.parser.add_argument('-t', '--test', action='store_true',
                            help='Run load for test configuration as defined in \n"if cl.args.test:" section of load script')
        self.parser.add_argument('-s', '--stride', action='store', type=int, default=1,
                            help='Stride value (default=1)')
        self.parser.add_argument('-a', '--append', action='store_true', 
                            help='Append data to existing activity - for use in repetative runs')
        self.parser.add_argument('--startdate', action='store', 
                            help='For loaders that use it set startdate, in format YYYYMMDD')
        self.parser.add_argument('--enddate', action='store', 
                            help='For loaders that use it set enddate, in format YYYYMMDD')
        self.parser.add_argument('--previous_month', action='store_true', 
                            help='For loaders that use startdate and enddate, load data from the previoius month')
        self.parser.add_argument('--current_month', action='store_true', 
                            help='For loaders that use startdate and enddate, load data from the current month')
        self.parser.add_argument('--remove_appended_activities', action='store_true',
                            help='First remove activities loaded after load_date_gmt')
        self.parser.add_argument('-v', '--verbose', action='store_true', 
                            help='Turn on DEBUG level logging output')

        self.args = self.parser.parse_args()

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
        else:
            self.logger.setLevel(logging.INFO)

        if self.args.previous_month:
            prev_mon = datetime.today() - relativedelta(months=1)
            prev_mon_st_dt = datetime(prev_mon.year, prev_mon.month, 1)
            prev_mon_en_dt = prev_mon_st_dt + relativedelta(months=1)
            self.args.startdate = prev_mon_st_dt.strftime('%Y%m%d')
            self.args.enddate = prev_mon_en_dt.strftime('%Y%m%d')

        if self.args.current_month:
            curr_mon = datetime.today()
            curr_mon_st_dt= datetime(curr_mon.year, curr_mon.month, 1)
            curr_mon_en_dt = curr_mon_st_dt + relativedelta(months=1)
            self.args.startdate = curr_mon_st_dt.strftime('%Y%m%d')
            self.args.enddate = curr_mon_en_dt.strftime('%Y%m%d')

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
        try:
            campaign = m.Campaign.objects.using(self.dbAlias).get(name=self.campaignName)
        except m.Campaign.DoesNotExist:
            self.logger.error(f"Could not find Campaign record in {self.dbAlias} at end of load. Perhaps no data was loaded?")
            sys.exit(-1)
        
        for url, viewpoint in list(self.x3dTerrains.items()):
            self.logger.debug('url = %s, viewpoint = %s', url, viewpoint)
            for name, value in list(viewpoint.items()):
                resource, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                              uristring=url, name=name, value=value, resourcetype=resourceType)
                m.CampaignResource.objects.using(self.dbAlias).get_or_create(
                              campaign=campaign, resource=resource)
                self.logger.info('Resource uristring=%s, name=%s, value=%s', url, name, value)

        # Add default clipping planes to avoid z-buffer problems with curtainx3d terrain intersections 
        for url, viewpoint in list(self.x3dTerrains.items()):
            self.logger.debug('url = %s, viewpoint = %s', url, viewpoint)
            self.logger.debug('url = %s, viewpoint.keys() = %s', url, viewpoint.keys())
            if 'zNear' not in viewpoint.keys() and 'zFar' not in viewpoint.keys():
                self.logger.info('Adding default clipping plane zNear, zFar values: 100.0, 300000.0')
                resource, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                              uristring=url, name='zNear', value=100.0, resourcetype=resourceType)
                m.CampaignResource.objects.using(self.dbAlias).get_or_create(
                              campaign=campaign, resource=resource)
                resource, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                              uristring=url, name='zFar', value=300000.0, resourcetype=resourceType)
                m.CampaignResource.objects.using(self.dbAlias).get_or_create(
                              campaign=campaign, resource=resource)

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
            self.logger.debug(f"Platform {pName} not found in database {self.dbAlias}. Can't add Resources.")
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

    standard_names = {} # should be defined for each child class
    include_names=[] # names to include, if set it is used in conjunction with ignored_names
    # Note: if a name is both in include_names and ignored_names it is ignored.
    ignored_names=[]  # Should be defined for each child class
    global_ignored_names = ('longitude','latitude', 'time', 'Time',
                'LONGITUDE','LATITUDE','TIME', 'NominalDepth', 'esecs', 'Longitude', 'Latitude',
                'DEPTH','depth') # A list (tuple) of parameters that should not be imported as parameters
    global_dbAlias = ''

    logger = logging.getLogger(__name__)

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

        platformName = ''
        try:
            with closing(requests.get(paURL, stream=True)) as r:
                if r.status_code == 200:
                    r_decoded = (line.decode('utf-8') for line in r.iter_lines())
                    tpHandle = csv.DictReader(r_decoded)
                    for rec in tpHandle:
                        ##self.logger.info("rec = %s" % rec)
                        if rec['PlatformName'].lower() == name.lower():
                            platformName = rec['PlatformName']
                            tdb_platformTypeName = rec['PlatformType']
                            break
        except requests.exceptions.ConnectionError as e:
            self.logger.warn(f'{e}')
            self.logger.warn(f'Unable to read platform names from the MBARI tracking database: {paURL}')

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

    def parameter_name(self, variable):
        if variable not in self.ds:
            raise ParameterNotFound(f"variable {variable} not in self.ds")
        parameter_units = self.ds[variable].attributes.get('units')
        if parameter_units:
            parameter_name = f"{variable} ({parameter_units})"
        else:
            parameter_name = f"{variable}"
   
        return parameter_name, parameter_units

    def add_parameters(self, ds):
        '''
        Rely on Django's get_or_create() to add unique Parameters to the database.
        '''
        # Initialize cache for each url/ds/activity
        self.parameter_dict = {} 

        # Go through the keys of the OPeNDAP URL for the dataset and add the parameters as needed to the database
        for variable in (set(self.include_names) & set(self.ds.keys())):
            if (variable in self.ignored_names):
                self.logger.debug(f"variable {variable} is in ignored_names")
                continue

            parameter_name, parameter_units = self.parameter_name(variable)

            self.logger.info(f"variable: {variable}, parameter_name: {parameter_name}")
            try:
                parm = self.getParameterByName(parameter_name)
            except ParameterNotFound as e:
                self.logger.debug("Parameter not found in local cache. Getting from database.")
                vattr = ds[variable].attributes
                self.parameter_dict[parameter_name], created = (m.Parameter.objects
                             .using(self.dbAlias).get_or_create(
                                        name = parameter_name,
                                        units = parameter_units,
                                        standard_name = vattr.get('standard_name'),
                                        long_name = vattr.get('long_name'),
                                        type = vattr.get('type'),
                                        description =  vattr.get('description') or vattr.get('comment', '')[:512],
                                        origin = self.activityName 
                                    )) 
                parm = self.parameter_dict[parameter_name]
                if created:
                    self.logger.debug(f"Added parameter {parameter_name} from {self.url} to database {self.dbAlias}")

            if not parm.standard_name and ds[variable].attributes.get('standard_name'):
                # Add standard_name if found in a later Activity (dataset)
                parm.standard_name = ds[variable].attributes.get('standard_name')
                parm.save(using=self.dbAlias)

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
 
    def remove_appended_activities(self):
        loaded_date = None
        for dt_str in m.Resource.objects.using(self.dbAlias).filter(name='load_date_gmt').values_list('value', flat=True):
            # 2022-01-26 10:28:53.535769 - simply use the last one if there are multiples
            loaded_date = datetime.fromisoformat(dt_str)

        if not loaded_date:
            self.logger.info("--remove_appended_activities requested, but loaded_date not found in %s.  Perhaps another load is in process.", self.dbAlias)
            return

        for act in m.Activity.objects.using(self.dbAlias).filter(enddate__gt=loaded_date):
            self.logger.info("Removing Activity %s before appending", act)
            act.delete(using=self.dbAlias)

    def createActivity(self):
        '''
        Use provided activity information to add the activity to the database.
        '''
        
        self.logger.debug("Creating Activity with startDate = %s and endDate = %s", 
                self.startDatetime, self.endDatetime)
        comment = 'Loaded on %s with these include_names: %s' % (datetime.now(), 
                ' '.join(self.include_names))
        self.logger.info("comment = " + comment)

        # Need to create Campaign and ActivityType before creating Activity
        self.createCampaign()
        if self.activitytypeName is not None:
            self.activityType, created = m.ActivityType.objects.using(self.dbAlias
                                        ).get_or_create(name = self.activitytypeName)

        if hasattr(self, 'getActivityName'):
            self.activityName = self.getActivityName()

        # Get or create Activity based on unique identifiers - respect initial startdate
        created = False
        try:
            self.activity = m.Activity.objects.using(self.dbAlias).get(    
                                            name__contains = self.activityName,
                                            platform = self.platform,
                                            campaign = self.campaign,
                                            activitytype = self.activityType)
        except m.Activity.DoesNotExist:
            self.activity, created = m.Activity.objects.using(self.dbAlias).get_or_create(    
                                                name__contains = self.activityName,
                                                platform = self.platform,
                                                campaign = self.campaign,
                                                activitytype = self.activityType,
                                                startdate = self.startDatetime)

        if created:
            self.activity.name = self.activityName
            self.activity.startdate = self.startDatetime
            self.activity.save(using=self.dbAlias)
            self.logger.info("Created activity %s in database %s with startDate=%s, endDate = %s",
                    self.activity.name, self.dbAlias, self.activity.startdate, self.activity.enddate)
        else:
            self.logger.info("Retrieved activity %s from database %s", self.activityName, self.dbAlias)

        # Update Activity with attributes that may change, e.g.  with --append option
        m.Activity.objects.using(self.dbAlias).filter(
                    id=self.activity.id).update(enddate = self.endDatetime)

    def _add_nc_global_attrs(self, all_names):
        # The source of the data - this OPeNDAP URL
        resourceType, _ = m.ResourceType.objects.using(self.dbAlias).get_or_create(name = 'opendap_url')
        self.logger.debug("Getting or Creating Resource with name = %s, value = %s", 'opendap_url', self.url )
        resource, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                            name='opendap_url', value=self.url, uristring=self.url, resourcetype=resourceType)
        ar, _ = m.ActivityResource.objects.using(self.dbAlias).get_or_create(
                    activity=self.activity, resource=resource)

        self.logger.debug("Getting or Creating ResourceType nc_global...")
        self.logger.debug("ds.attributes.keys() = %s", list(self.ds.attributes.keys()) )
        resourceType, _ = m.ResourceType.objects.using(self.dbAlias).get_or_create(name = 'nc_global')
        for rn, value in list(self.ds.attributes['NC_GLOBAL'].items()):
            self.logger.debug("Getting or Creating Resource with name = %s, value = %s", f"nc_global.{rn}", value )
            resource, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                        name=f"nc_global.{rn}", value=value, resourcetype=resourceType)
            ar, _ = m.ActivityResource.objects.using(self.dbAlias).get_or_create(
                        activity=self.activity, resource=resource)

        # Use potentially monkey-patched self.getFeatureType() method to write a correct value - as the UI depends on it
        mp_ft_res, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                    name='featureType', value=self.getFeatureType(), resourcetype=resourceType)
        ars = m.ActivityResource.objects.using(self.dbAlias).filter(activity=self.activity,
                        resource__resourcetype=resourceType, resource__name='featureType').select_related('resource')

        if not ars:
            # There was no featureType NC_GLOBAL in the dataset - associate to the one from self.getFeatureType()
            ar, _ = m.ActivityResource.objects.using(self.dbAlias).get_or_create(
                        activity=self.activity, resource=mp_ft_res)
        for ar in ars:
            if ar.resource.value != mp_ft_res.value:
                # Update (override NC_GLOBAL's) with monkey-patched self.getFeatureType()'s value
                ars = m.ActivityResource.objects.using(self.dbAlias).filter(activity=self.activity,
                        resource__resourcetype=resourceType, resource__name='featureType').update(resource=mp_ft_res)
                self.logger.warn('Over-riding featureType from NC_GLOBAL (%s) with monkey-patched value = %s', 
                        ar.resource.value, mp_ft_res.value)

        self.logger.info('Adding attributes of all the variables from the original NetCDF file')
        for v in all_names:
            self.logger.debug('v = %s', v)
            try:
                for rn, value in list(self.ds[v].attributes.items()):
                    self.logger.debug("Getting or Creating Resource with name = %s, value = %s", f"{v}.{rn}", value )
                    resource, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                                          name=f"{v}.{rn}", value=value, resourcetype=resourceType)
                    pn, _ = self.parameter_name(v)
                    m.ParameterResource.objects.using(self.dbAlias).get_or_create(
                                    parameter=self.getParameterByName(pn), resource=resource)
                    m.ActivityResource.objects.using(self.dbAlias).get_or_create(
                                    activity=self.activity, resource=resource)
                    
            except KeyError as e:
                # Just skip derived parameters that may have been added for a sub-classed Loader
                if v != ALTITUDE:
                    self.logger.debug('include_name %s is not in %s - skipping', v, self.url)
            except AttributeError as e:
                # Just skip over loaders that don't have the plotTimeSeriesDepth attribute
                self.logger.warn('%s for include_name %s in %s. Skipping', e, v, self.url)
            except ParameterNotFound as e:
                self.logger.warn('Could not get Parameter for v = %s: %s', v, e)

    def _add_plot_timeseries_depth_resources(self, all_names):
        self.logger.info('Adding plotTimeSeriesDepth Resource for Parameters we want plotted in Parameter tab')
        for v in all_names:
            if hasattr(self, 'plotTimeSeriesDepth'):
                if self.plotTimeSeriesDepth.get(v, None) is not None:
                    self.logger.debug('v = %s', v)
                    try:
                        uiResType, _ = m.ResourceType.objects.using(self.dbAlias).get_or_create(name='ui_instruction')
                        resource, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                                              name='plotTimeSeriesDepth', value=self.plotTimeSeriesDepth[v], resourcetype=uiResType)
                    except ParameterNotFound as e:
                        self.logger.warn('Could not get_or_create uiResType or resource for v = %s: %s', v, e)
                    try:
                        pn, _ = self.parameter_name(v)
                        m.ParameterResource.objects.using(self.dbAlias).get_or_create(
                                        parameter=self.getParameterByName(pn), resource=resource)
                    except ParameterNotFound as e:
                        self.logger.debug('Could not add plotTimeSeriesDepth ParameterResource for v = %s: %s', v, e)
                    try:
                        m.ActivityResource.objects.using(self.dbAlias).get_or_create(
                                        activity=self.activity, resource=resource)
                    except ParameterNotFound as e:
                        self.logger.warn('Could not add plotTimeSeriesDepth PlatformResource for v = %s: %s', v, e)

    def addResources(self):
        '''
        Add Resources for this activity, namely the NC_GLOBAL attribute names and values,
        and all the attributes for each variable in include_names.
        '''
        # Make sure Activity has a featureType Resource - as in ROVCTD data loads, where there is no self.ds
        # Use potentially monkey-patched self.getFeatureType() method to write a correct value - as the UI depends on it
        resourceType, _ = m.ResourceType.objects.using(self.dbAlias).get_or_create(name = 'nc_global')
        mp_ft_res, _ = m.Resource.objects.using(self.dbAlias).get_or_create(
                        name='featureType', value=self.getFeatureType(), resourcetype=resourceType)
        m.ActivityResource.objects.using(self.dbAlias).get_or_create(activity=self.activity, resource=mp_ft_res)

        # Add stoqs calculated Parameters to the names we add resources to - crude test for presence of SIGMAT in database
        all_names = self.include_names + [ALTITUDE]
        if m.Parameter.objects.using(self.dbAlias).filter(name=SIGMAT):
            all_names = all_names + [SIGMAT, SPICE]

        self._add_plot_timeseries_depth_resources(all_names)

        # Save the NC_GLOBAL attributes from the OPeNDAP URL - But only if the Activity name is in the url
        if hasattr(self, 'add_to_activity'):
            if self.add_to_activity.name.split(' (')[0] not in self.url:
                self.logger.info(f"Not adding NC_GLOBAL attributes from {self.url} as we are adding to Activity {self.add_to_activity.name}")
                return
        if hasattr(self, 'associatedActivityName'):
            if self.associatedActivityName.split(' (')[0] not in self.url:
                self.logger.info(f"Not adding NC_GLOBAL attributes from {self.url} as we are associated with Activity {self.associatedActivityName}")
                return
        if hasattr(self, 'ds'):
            if 'NC_GLOBAL' in self.ds.attributes:
                self._add_nc_global_attrs(all_names)
            else:
                self.logger.warn("No NC_GLOBAL attribute in %s", self.url)
        
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
                self.parameter_dict[name] = m.Parameter.objects.using(self.dbAlias).get(name=name)
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
            self.logger.warn('name = %s: %s', name, str(e))
            pprint.pprint(self.parameter_dict[name])

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

        Note: createMeasurement() is mostly deprecated following implementation of bulk_create in 2018.
        It is still used for loading small numbers of Measurements in stoqs/loaders/SampleLoaders.py.
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
            raise SkipRecord('Bad lon: %s (longitude must be between %s and %s)' % (lon, -720, 720))

        ip, _ = m.InstantPoint.objects.using(self.dbAlias).get_or_create(activity=self.activity, timevalue=mtime)

        nl = None
        point = Point(lon, lat)
        if not (nomDepth is None and nomLat is None and nomLong is None):
            self.logger.debug('nomDepth = %s nomLat = %s nomLong = %s', nomDepth, nomLat, nomLong)
            nom_point = Point(nomLong, nomLat)
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
            self.logger.error("Cannot save measurement mtime = %s, lon = %s, lat = %s,"
                              " depth = %s", mtime, repr(lon), repr(lat), repr(depth))
            raise SkipRecord

        return measurement
   
    def is_coordinate_bad(self, key, mtime, depth, lat=None, lon=None, min_depth=-1000, max_depth=5000,
                                         min_lat=-90, max_lat=90, min_lon=-720, max_lon=720):
        '''Return True if coordinate is missing or fill_value, or falls outside of reasonable bounds
        '''
        # None depth rejections - Ideally a Trajectory file won't have any None-valued depths, but realtime LRAUV data do
        if depth is None:
            return True

        # Missing value rejections
        ac = self.coord_dicts[key]
        if 'depth' in ac:   # Tolerate EPIC 'sensor_depth' type data
            try:
                if self.mv_by_key[ac['depth']]:
                    if depth == 0.0:
                        pass
                    elif np.isclose(depth, self.mv_by_key[ac['depth']]):
                        return True
            except KeyError:
                # Tolerate ac[DEPTH] == 0.0, or other value given in auxCoords
                pass

        if lat:
            if self.mv_by_key[ac['latitude']]:
                if np.isclose(lat, self.mv_by_key[ac['latitude']]):
                    return True

        if lon:
            if self.mv_by_key[ac['longitude']]:
                if np.isclose(lon, self.mv_by_key[ac['longitude']]):
                    return True

        # fill_value rejections
        if 'depth' in ac:   # Tolerate EPIC 'sensor_depth' type data
            try:
                if depth == 0.0:
                    pass
                elif self.fv_by_key[ac['depth']]:
                    if np.isclose(depth, self.fv_by_key[ac['depth']]):
                        return True
            except KeyError:
                # Tolerate ac[DEPTH] == 0.0, or other value given in auxCoords
                pass

        if lat:
            if self.fv_by_key[ac['latitude']]:
                if np.isclose(lat, self.fv_by_key[ac['latitude']]):
                    return True

        if lon:
            if self.fv_by_key[ac['longitude']]:
                if np.isclose(lon, self.fv_by_key[ac['longitude']]):
                    return True

        # Brute force QC check on depth to remove egregous outliers
        if depth < min_depth or depth > max_depth:
            return True

        if lat and lon:
            # Brute force QC check on latitude and longitude to remove egregous outliers
            if lat < min_lat or lat > max_lat:
                return True
            if lon < min_lon or lon > max_lon:
                return True

        # NaN value rejections - Ideally a Trajectory file won't have any NaN-valued coordinates, but sometimes people write them
        try:
            if np.isnan(lat) or np.isnan(lon):
                return True
        except TypeError:
            # Likely TypeError: ufunc 'isnan' not supported for the input types, and the inputs could not be safely coerced to any supported types
            pass

        return False

    def is_value_bad(self, key, value):
        if self.mv_by_key[key]:
            if np.isclose(value, self.mv_by_key[key]):
                return True

        if self.fv_by_key[key]:
            if np.isclose(value, self.fv_by_key[key]):
                return True

        if value == 'null' or np.isnan(value):
            return True

        return False

    def good_coords(self, pnames, mtimes, depths, latitudes, longitudes, coords_equal=np.array([])):
        '''Use attributes to determine if coordinate values are good.  Yield None
        values for all coordinates if any are bad (e.g. _FillValue, time decreasing).
        Appropriate for trajectory data where there is one-to-one match of coordinates.
        '''
        # Checking for duplicate or decreasing times is time consuming, do it for only known
        # problematic sources of data
        known_dup_or_decr_time_sources = ('pctd', 'Daphne_ECOHAB_March2013')

        known_dup_or_decr_time_problem = False
        for string in known_dup_or_decr_time_sources:
            if string in self.url:
                self.logger.info(f'Setting known_dup_or_decr_time_problem for known_dup_or_decr_time_source: {string}')
                known_dup_or_decr_time_problem = True

        # Coordinates (mtimes, depths, latitudes, longitudes) are generators read from the DAP URL as
        # identified in CF metadata as associated with all variables in pnames - use just the first one 
        # for .is_coordinate_bad() check
        previous_times = []
        for i, (mt, de, la, lo) in enumerate(zip(mtimes, depths, latitudes, longitudes)):
            # Useful for LRAUV data load debugging, e.g. from bad interpolation by lrauvNc4ToNetcdf.py
            ##self.logger.info(f"{i}: {mt}, {de}, {la}, {lo}")
            ##if not i % 100:
            ##    import pdb; pdb.set_trace()
            if self.is_coordinate_bad(pnames[0], mt, de, la, lo):
                self.logger.debug(f"Marked coordinate bad: i = {i}, mt = {mt}, de = {de}, la = {la}, lo = {lo}")
                mt = None
                de = None
                la = None
                lo = None
            if coords_equal.any():
                if coords_equal[i]:
                    mt = None
                    de = None
                    la = None
                    lo = None

            bad_time = False
            if known_dup_or_decr_time_problem:
                dup_time = False
                decr_time = False
                if mt in previous_times:
                    self.logger.warn(f'Will not load data from duplicate time coordinate: {mt} at index {i}')
                    dup_time = True
                elif mt and i > 0 and previous_times:
                    if mt <= previous_times[-1]:
                        self.logger.warn(f'Will not load data from decreasing time coordinate: {mt} at index {i}')
                        decr_time = True
               
                bad_time = dup_time or not mt or decr_time
                self.logger.debug(f'{mt} at index {i}: bad_time = {bad_time}')

                if not bad_time: 
                    # Save only not None, non-duplicate, and non-decreasing times
                    previous_times.append(mt)

            yield mt, de, la, lo, bad_time

    def preProcessParams(self, row):
        '''
        This method is designed to perform any final pre-processing, such as adding new
        parameters based on existing ones.  It's also possible to use this function to remove
        additional parameters (if necessary).  In particular, this is useful for derived
        columns such as chlorophyl count, etc.
        @param row: A dictionary representing a single "row" of parameter data to be added to the database. 
        '''
        # First seen in April 2017 Nemesis data
        if row['depth'] == self.get_FillValue('depth'):
            raise SkipRecord('depth == _FillValue (%s)' % row['depth'])

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
            allNaNFlag[v] = True
            self.logger.debug("include_name: %s", v)
            try:
                if len(self.ds[v].shape) == 1:
                    anyValidData = not np.isnan(np.array(self.ds[v].data[:])).all()
                elif len(self.ds[v].shape) == 2:
                    # Likely lopc data - look at just first bin values [time][bin]
                    anyValidData = not np.isnan(np.array(self.ds[v].data[:][0])).all()
                elif len(self.ds[v].shape) == 3:
                    # Likely USGS EPIC ADCP variables with missing depth coordinate, but having nominal sensor depth metadata
                    anyValidData = not np.isnan(np.array(self.ds[v].data[:][0][0])).all()
                elif len(self.ds[v].shape) == 4:
                    # Likely mooring data with fully specified coords: [time][depth][lat][lon]
                    anyValidData = not np.isnan(np.array(self.ds[v].data[:][:][0][0])).all()
                else:
                    self.logger.error('Parameter %s shape length of %s not handled', v, len(self.ds[v].shape))
                    raise Exception(f"Parameter {v} with shape {len(self.ds[v].shape)} length of not handled")
            except KeyError:
                self.logger.debug('Parameter %s not in %s. Skipping.', v, list(self.ds.keys()))
                if v.find('.') != -1:
                    raise Exception('Parameter names must not contain periods - cannot load data. Paramater %s violates CF conventions.' % v)
            except ValueError:
                pass

            if anyValidData:
                allNaNFlag[v] = False

        self.logger.debug("allNaNFlag = %s", allNaNFlag)
        for v in list(allNaNFlag.keys()):
            if not allNaNFlag[v]:
                self.varsLoaded.append(v)
        self.logger.info(f"Variables that have data: {self.varsLoaded}")
        anyValidData = not all(allNaNFlag.values())

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
            for var in list(self.ds.keys()):
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
        for p in list(parameters.keys()):
            if sampledFlag:
                data = m.SampledParameter.objects.using(dbAlias).filter(
                                parameter=p, sample__instantpoint__activity=activity
                                ).values_list('datavalue', flat=True)
            else:
                data = m.MeasuredParameter.objects.using(dbAlias).filter(
                                parameter=p, measurement__instantpoint__activity=activity
                                ).values_list('datavalue', flat=True)

            # Just don't create an ActivityParameter for data that don't exist
            if len(data) == 0:
                # Assume data is like LOPC - get dataarray values
                data_array = m.MeasuredParameter.objects.using(dbAlias).filter(parameter=p, 
                                measurement__instantpoint__activity__name=activity
                                ).values_list('dataarray', flat=True)
                try:
                    data = [item for sublist in data_array for item in sublist]
                except TypeError:
                    # Likely 'NoneType' object is not iterable because p is altitude of LOPC data
                    data = []

            np_data = np.array([float(d) for d in data if d is not None])
            if not len(np_data):
                # Quietly skip over 'no valid data' - can't log because of @static method
                continue

            ap, _ = m.ActivityParameter.objects.using(dbAlias).get_or_create(
                            parameter=p, activity=activity)
            np_data.sort()
            ap.number = len(np_data)
            try:
                ap.min = np_data.min()
                ap.max = np_data.max()
            except ValueError as err:
                # At least update ap with number, likely 0
                ap.save(using=dbAlias)
                if not err.args:
                    err.args=('',)

                err.args += (f'Parameter: {p}',)
                raise

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
                try:
                    (counts, bins) = np.histogram(np_data,100)
                except (IndexError, ValueError):
                    # Likely something like 'index -9223372036854775808 is out of bounds for axis 1 with size 101' 
                    # from numpy/lib/function_base.py.  Encoutered in really wild LRAUV data, e.g.:
                    # http://dods.mbari.org/opendap/data/lrauv/tethys/missionlogs/2015/20150824_20150825/20150825T055243/201508250552_201508250553_2S_eng.nc.ascii?control_inputs_mass_position[0:1:13]
                    # These kind of messages will appear in the log:
                    # /vagrant/dev/stoqsgit/venv-stoqs/lib64/python3.6/site-packages/numpy/lib/function_base.py:766: RuntimeWarning: overflow encountered in double_scalars
                    #  norm = n_equal_bins / (last_edge - first_edge)
                    #/vagrant/dev/stoqsgit/venv-stoqs/lib64/python3.6/site-packages/numpy/lib/function_base.py:788: RuntimeWarning: invalid value encountered in multiply
                    # tmp_a *= norm
                    # ValueError: autodetected range of [-inf, inf] is not finite encountered in:
                    # http://dods.mbari.org/opendap/data/lrauv/tethys/missionlogs/2016/20160801_20160809/20160807T120403/201608071204_201608091210_2S_scieng.nc
                    # Contunue silently (as this is a static method), with the above errors given as a warning.
                    continue

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

    def updateActivityParameterStats(self, act_to_update=None, sampledFlag=False):
        ''' 
        Examine the data for the Activity, compute and update some statistics on the measuredparameters
        for this activity.  Store the histogram in the associated table.
        '''
        if not act_to_update:
            act_to_update = self.activity
        try:
            self.update_activityparameter_stats(self.dbAlias, act_to_update, self.parameter_counts, sampledFlag)
        except ValueError as e:
            self.logger.warn(f"{e}")
            raise
        except IntegrityError as e:
            self.logger.warn('IntegrityError(%s): Cannot create ActivityParameter and '
                             'updated statistics for Activity %s.', (e, act_to_update))

        self.logger.info('Updated statistics for act_to_update.name = %s', act_to_update.name)

    def insertSimpleDepthTimeSeries(self, critSimpleDepthTime=10):
        '''
        Read the time series of depth values for this activity, simplify it and insert the values in the
        SimpleDepthTime table that is related to the Activity.  This procedure is suitable for only
        trajectory data; timeSeriesProfile type data uses another method to produce a collection of
        simple depth time series for display in flot.
        @param critSimpleDepthTime: An integer for the simplification factor, 10 is course, .0001 is fine
        '''
        vlqs = (m.Measurement.objects.using(self.dbAlias)
                        .filter(instantpoint__activity=self.activity)
                        .values_list('instantpoint__timevalue', 'depth', 'instantpoint__pk'))
        line = []
        pklookup = []
        for dt,dd,pk in vlqs:
            ems = 1000 * to_udunits(dt, 'seconds since 1970-01-01')
            d = float(dd)
            line.append((ems,d,))
            pklookup.append(pk)

        self.logger.info('Number of points in original depth time series = %d', len(line))
        ##self.logger.debug('line = %s', line)
        try:
            # Original simplify_points code modified: the index from the original line is added as 3rd item in the return
            simple_line = simplify_points(line, critSimpleDepthTime)
        except IndexError:
            simple_line = []        # Likely "list index out of range" from a stride that's too big
        self.logger.info('Number of points in simplified depth time series = %d', len(simple_line))
        self.logger.debug('simple_line = %s', simple_line)

        for t,d,k in simple_line:
            try:
                ip = m.InstantPoint.objects.using(self.dbAlias).get(id=pklookup[k])
                m.SimpleDepthTime.objects.using(self.dbAlias).create(
                                            activity=self.activity, 
                                            instantpoint=ip,
                                            depth=d, 
                                            epochmilliseconds=t)
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
            ndlqs = m.Measurement.objects.using(self.dbAlias).filter( instantpoint__activity=self.activity, nominallocation=nl
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
                self.logger.debug('Loading depths in SimpleDepthTime for nomDepth=%s', nomDepth)
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

            self.logger.debug('Inserted %d values into SimpleDepthTime for nomDepth = %f', len(simple_line), nomDepth)

    def updateActivityMinMaxDepth(self, act_to_update):
        '''
        Pull the min & max depth from Measurement and set the Activity mindepth and maxdepth
        '''
        m_qs = (m.Measurement.objects.using(self.dbAlias)
                        .filter(instantpoint__activity__id=act_to_update.id)
                        .aggregate(Max('depth'), Min('depth')))
        m.Activity.objects.using(self.dbAlias).filter(id=act_to_update.id).update(
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

    def assignParameterGroup(self, groupName=MEASUREDINSITU):
        ''' 
        For all the parameters in self.parameter_counts create a many-to-many association with the Group named @groupName
        '''                 
        g, _ = m.ParameterGroup.objects.using(self.dbAlias).get_or_create(name=groupName)
        for p in self.parameter_counts:
            pgps = m.ParameterGroupParameter.objects.using(self.dbAlias).filter(parameter=p, parametergroup=g)
            if not pgps:
                # Attempt saving relation only if it does not exist
                pgp = m.ParameterGroupParameter(parameter=p, parametergroup=g)
                try:
                    pgp.save(using=self.dbAlias)
                except Exception as e:
                    self.logger.warn('%s: Cannot create ParameterGroupParameter name = %s for parameter.name = %s. Skipping.', e, groupName, p.name)

    def _best_ts_parameter_names(self, ms, salinity_standard_name):
        '''Find the best sea_water_temperature and seawater_salinity Parameter names
        to use for sigmat and spice calculations
        '''
        temp_pn = ''
        sal_pn = ''
        # Pick Parameter names that have sea_water_temperature and sea_water_salinity standard_names
        temp_mp = (m.MeasuredParameter.objects.using(self.dbAlias)
                    .filter(measurement__in=ms, parameter__standard_name='sea_water_temperature')
                    .values_list('parameter__name', flat=True).order_by('parameter__name').distinct())
        sal_mp = (m.MeasuredParameter.objects.using(self.dbAlias)
                    .filter(measurement__in=ms, parameter__standard_name=salinity_standard_name)
                    .values_list('parameter__name', flat=True).order_by('parameter__name').distinct())

        # See if we have "Best CTD is ..." in our netCDF metadata and set parameter - expect either 'ctd1' or 'ctd2'
        best_ctd_is_re = re.compile("Best CTD is (ctd1|ctd2)", re.IGNORECASE)
        if "NC_GLOBAL" in self.ds.attributes:
            if "comment" in self.ds.attributes["NC_GLOBAL"]:
                self.logger.info(f'netCDF comment = {self.ds.attributes["NC_GLOBAL"]["comment"]}')
                if best_ctd := best_ctd_is_re.search(self.ds.attributes["NC_GLOBAL"]["comment"]):
                    self.logger.info(f"Looking for Best CTD in temp_mp list: {temp_mp}")
                    self.logger.info(f"Looking for Best CTD in sal_mp list: {sal_mp}")
                    for tn, sn in zip(temp_mp, sal_mp):
                        if best_ctd.group(1).lower() in tn:
                            temp_pn = tn
                        if best_ctd.group(1).lower() in sn:
                            sal_pn = sn
                    self.logger.info(f"temp_pn = {temp_pn}, sal_pn = {sal_pn}")
        if not temp_pn:
            # Choose the first one
            temp_pn = temp_mp[0]
        if not sal_pn:
            # Choose the first one
            sal_pn = sal_mp[0]
        self.logger.info("Using Parameters '%s' and '%s' to compute sigmat and spice", temp_pn, sal_pn)
        return temp_pn, sal_pn

    def _combined_temp_sal(self, temp_pn, sal_pn, ms):
        '''Use Parameter-Parameter like query to get paired T & S values.
        We need to do this in case we have missing/bad values for one and not the other.
        '''
        temps = []
        salts = []
        mids = []
        depths = []
        lats = []
        with connections[self.dbAlias].cursor() as cursor:
            sql = f"""
            SELECT DISTINCT mp_x.datavalue AS temp,
                            mp_y.datavalue AS sal,
                            stoqs_measurement.id AS mid,
                            stoqs_measurement.depth AS depth,
                            ST_Y(stoqs_measurement.geom) AS lat,
                            stoqs_instantpoint.timevalue as time
            FROM stoqs_measuredparameter
            INNER JOIN stoqs_measurement ON (stoqs_measuredparameter.measurement_id = stoqs_measurement.id)
            INNER JOIN stoqs_instantpoint ON (stoqs_measurement.instantpoint_id = stoqs_instantpoint.id)
            INNER JOIN stoqs_activity ON (stoqs_instantpoint.activity_id = stoqs_activity.id)
            INNER JOIN stoqs_platform ON (stoqs_activity.platform_id = stoqs_platform.id)
            INNER JOIN stoqs_measurement m_x ON m_x.instantpoint_id = stoqs_instantpoint.id
            INNER JOIN stoqs_measuredparameter mp_x ON mp_x.measurement_id = m_x.id
            INNER JOIN stoqs_parameter p_x ON mp_x.parameter_id = p_x.id
            INNER JOIN stoqs_measurement m_y ON m_y.instantpoint_id = stoqs_instantpoint.id
            INNER JOIN stoqs_measuredparameter mp_y ON mp_y.measurement_id = m_y.id
            INNER JOIN stoqs_parameter p_y ON mp_y.parameter_id = p_y.id
            WHERE (p_x.name = '{temp_pn}')
              AND (p_y.name = '{sal_pn}')
              AND (stoqs_measurement.id IN ({','.join([str(meas.id) for meas in ms])}))
            ORDER BY stoqs_instantpoint.timevalue;
            """
            cursor.execute(sql)
            for row in cursor.fetchall():
                temps.append(row[0])
                salts.append(row[1])
                mids.append(row[2])
                depths.append(row[3])
                lats.append(row[4])
        return temps, salts, mids, depths, lats

    def _calculate_sigmat_mps(self, temps, salts, mids, depths, lats, p_sigmat, salinity_standard_name):
        '''Return calculated sigmat list of MeasuredParameters
        '''
        meass = m.Measurement.objects.using(self.dbAlias).filter(id__in=mids).order_by('instantpoint__timevalue')
        sigmats = sw.pden(salts, temps, sw.pres(depths, lats)) - 1000.0
        sigmat_mps = []
        for meas, sigmat in zip(meass, sigmats):
            sigmat_mp = m.MeasuredParameter(measurement=meas, parameter=p_sigmat, datavalue=sigmat)
            sigmat_mps.append(sigmat_mp)
        return sigmat_mps

    def _calculate_spice_mps(self, temps, salts, mids, p_spice, salinity_standard_name):
        '''Return calculated spice list of MeasuredParameters
        '''
        meass = m.Measurement.objects.using(self.dbAlias).filter(id__in=mids).order_by('instantpoint__timevalue')
        spices = spiciness(temps, salts)
        spice_mps = []
        for meas, spice in zip(meass, spices):
            spice_mp = m.MeasuredParameter(measurement=meas, parameter=p_spice, datavalue=spice)
            spice_mps.append(spice_mp)
        return spice_mps

    def _get_sea_water_parameters(self):
        '''Check for more than one set of sea_water_temperature nand sea_water_salinity standard names as in
        http://odss.mbari.org/thredds/dodsC/CANON/2016_Sep/Platforms/ROMS/roms_spray_0313.nc.html.
        Return tuple of single Paremeters for sea_water_temperature and sea_water_salinity, and standard_name
        used for sea_water_salinity - either sea_water_salinity or sea_water_practical_salinity
        '''
        sea_water_temperature_parms = [p for p in self.parameter_dict.values() if p.standard_name=='sea_water_temperature']
        try:
            sea_water_temperature_parm = sea_water_temperature_parms[0]
        except IndexError:
            raise NameError('No Parameter with standard_name of sea_water_temperature')
        if len(sea_water_temperature_parms) > 1:
            self.logger.info(f"Found more than one Parameter in {self.url} with standard_name == 'sea_water_temperature'")
            self.logger.info(f'{sea_water_temperature_parms}')
        
            # Default is first in list, to be overridden by 
            # a more simply-named Parameter as determined by no ammendments to the name, such as 'roms_'
            for p in sea_water_temperature_parms:
                if '_' not in p.name:
                    sea_water_temperature_parm = p
                    break
            self.logger.info(f"Using {sea_water_temperature_parm} for sea_water_temperature")


        # Test whether our measurements use 'sea_water_salinity' or 'sea_water_practical_salinity'
        salinity_standard_name = 'sea_water_salinity'
        sea_water_salinity_parms = [p for p in self.parameter_dict.values() if p.standard_name==salinity_standard_name]
        if not sea_water_salinity_parms:
            salinity_standard_name = 'sea_water_practical_salinity'
            sea_water_salinity_parms = [p for p in self.parameter_dict.values() if p.standard_name==salinity_standard_name]

        try:
            sea_water_salinity_parm = sea_water_salinity_parms[0]
        except IndexError:
            raise NameError('No Parameter with standard_name of sea_water_temperature')
        if len(sea_water_salinity_parms) > 1:
            self.logger.info(f"Found more than one Parameter in {self.url} with standard_name == 'sea_water_salinity'")
            self.logger.info(f'{sea_water_salinity_parms}')
        
            # Default is first in list, to be overridden by 
            # a more simply-named Parameter as determined by no ammendments to the name, such as 'roms_'
            for p in sea_water_salinity_parms:
                if '_' not in p.name:
                    sea_water_salinity_parm = p
                    break
            self.logger.info(f"Using {sea_water_salinity_parm} for sea_water_salinity")

        return sea_water_temperature_parm, sea_water_salinity_parm, salinity_standard_name

    def addSigmaTandSpice(self, activity=None):
        ''' 
        For all measurements that have standard_name parameters of (sea_water_salinity or sea_water_practical_salinity) and sea_water_temperature 
        compute sigma-t and add it as a parameter
        '''                 
        # Find all measurements with 'sea_water_temperature' and ('sea_water_salinity' or 'sea_water_practical_salinity')
        ms = m.Measurement.objects.using(self.dbAlias)
        if activity:
            self.logger.info(f'activity = {activity}')
            ms = ms.filter(instantpoint__activity=activity)

        try:
            sea_water_temperature_parm, sea_water_salinity_parm, salinity_standard_name = self._get_sea_water_parameters()
        except NameError as e:
            self.logger.info(f'{e}')
            self.logger.info("No sea_water_temperature and sea_water_salinity Parameters. Not adding SigmaT and Spice.")
            return

        ms = ms.filter(measuredparameter__parameter=sea_water_temperature_parm)
        ms = ms.filter(measuredparameter__parameter=sea_water_salinity_parm)

        if not ms:
            self.logger.info("No sea_water_temperature and sea_water_salinity measurements. Not adding SigmaT and Spice.")
            return

        if self.dataStartDatetime:
            ms = ms.filter(instantpoint__timevalue__gt=self.dataStartDatetime)

        # Create our new Parameters
        p_sigmat, _ = m.Parameter.objects.using(self.dbAlias).get_or_create(
                standard_name='sea_water_sigma_t',
                long_name='Sigma-T',
                units='kg m-3',
                name=SIGMAT,
        )
        if 'spice' in self.include_names:
            p_spice, _ = m.Parameter.objects.using(self.dbAlias).get_or_create( 
                    name='stoqs_spice',
                    defaults={'long_name': SPICINESS}
            )
        else:
            p_spice, _ = m.Parameter.objects.using(self.dbAlias).get_or_create( 
                    name=SPICE,
                    defaults={'long_name': SPICINESS}
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

        self.parameter_counts[p_sigmat] = ms.count()
        self.parameter_counts[p_spice] = ms.count()
        self.assignParameterGroup(groupName=MEASUREDINSITU)
        self.assignParameterGroup(groupName=MEASUREDINSITU)

        self.logger.info(f'Calculating {self.parameter_counts[p_sigmat]} sigmat & spice MeasuredParameters')
        temp_pn, sal_pn = self._best_ts_parameter_names(ms, salinity_standard_name)
        temps, salts, mids, depths, lats = self._combined_temp_sal(temp_pn, sal_pn, ms)
        sigmat_mps = self._calculate_sigmat_mps(temps, salts, mids, depths, lats, p_sigmat, salinity_standard_name)
        spice_mps = self._calculate_spice_mps(temps, salts, mids, p_spice, salinity_standard_name)

        self.logger.info(f'Bulk loading {self.parameter_counts[p_sigmat]} sigmat MeasuredParameters')
        m.MeasuredParameter.objects.using(self.dbAlias).bulk_create(sigmat_mps)
        self.logger.info(f'Bulk loading {self.parameter_counts[p_spice]} spice MeasuredParameters')
        m.MeasuredParameter.objects.using(self.dbAlias).bulk_create(spice_mps)

    def addAltitude(self, activity=None):
        ''' 
        For all measurements lookup the water depth from a GMT grd file using grdtrack(1), 
        subtract the depth and add altitude as a new Parameter to the Measurement
        To be called from load script after process_command_line().
        '''
        # Read the bounding box of the terrain file. The grdtrack command quietly does not write any lines for points outside of the grid.
        if self.grdTerrain:
            try:
                fh = Dataset(self.grdTerrain)
                # Old GMT format
                xmin, xmax = fh.variables['x_range'][:]
                ymin, ymax = fh.variables['y_range'][:]
            except IOError as e:
                self.logger.error(f'Cannot add {ALTITUDE}. Make sure file {os.path.abspath(self.grdTerrain)} is present.')
                self.logger.error(f'cd stoqs/loaders && wget https://stoqs.mbari.org/terrain/{os.path.basename(self.grdTerrain)}')
                self.logger.error('Exiting with error')
                sys.exit(-1)
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
                        self.logger.error(f'Cannot read range metadata from {self.grdTerrain}. Not able to load'
                                          ' {ALTITUDE}, bottomdepth or simplebottomdepthtime')
                        return
            except Exception as e:
                self.logger.exception(e)
                return

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
            self.logger.info('This is lame... Sleeping 5 seconds to give time for system call to finish writing to %s', bdepthFileName)
            time.sleep(5)
        if self.totalRecords > 1e7:
            self.logger.info('Sleeping another 300 seconds to give time for system call to'
                             ' finish writing to %s for more than 10 million records', bdepthFileName)
            time.sleep(300)

        # Create our new Parameter
        self.logger.debug('Getting or creating new altitude Parameter')
        try:
            p_alt, _ = m.Parameter.objects.using(self.dbAlias).get_or_create(
                    standard_name='height_above_sea_floor',
                    long_name='Altitude',
                    description=("Calculated in STOQS loader by using GMT's grdtrack(1) program on the Platform's"
                                 " latitude, longitude values and differencing the Platform's depth with the"
                                 " bottom depth data in file %s." % self.grdTerrain.split('/')[-1]),
                    units='m',
                    name=ALTITUDE,
                    origin='https://github.com/stoqs/stoqs/blob/45f53d134d336fdbdb38f73959a2ce3be4148227/stoqs/loaders/__init__.py#L1216-L1322'
            )
        except IntegrityError:
            # A bit of a mystery why sometimes this Exception happens (simply get p_alt if it happens):
            # IntegrityError: duplicate key value violates unique constraint "stoqs_parameter_name_key"
            p_alt = m.Parameter.objects.using(self.dbAlias).get(name=ALTITUDE)

        self.parameter_counts[p_alt] = ms.count()
        self.assignParameterGroup(groupName=MEASUREDINSITU)

        # Read values from the grid sampling (bottom depths) and add datavalues to the altitude parameter using the save Measurements
        self.logger.info("Saving altitude MeasuredParameters")
        meass = m.Measurement.objects.using(self.dbAlias).filter(id__in=mList).order_by('instantpoint__activity__id', 'instantpoint__timevalue')
        count = 0
        alt_mps = []
        with open(bdepthFileName) as altFH:
            try:
                with transaction.atomic():
                    for line, meas in zip(altFH, meass):
                        try:
                            bdepth = line.split()[2]
                        except IndexError:
                            # Likely list index out of range
                            continue
                        alt = -float(bdepth)-depthList.pop(0)
                        mp_alt = m.MeasuredParameter(datavalue=alt, measurement=meas, parameter=p_alt)
                        alt_mps.append(mp_alt)
                        count += 1
            except IntegrityError as e:
                self.logger.warn(e)
            except DatabaseError as e:
                self.logger.warn(e)
            self.logger.info(f'Bulk loading {count} altitude MeasuredParameters')
            try:
                m.MeasuredParameter.objects.using(self.dbAlias).bulk_create(alt_mps)
            except IntegrityError as e:
                self.logger.warning("Cannot load altitudes: %s", e)
        self.logger.info("Done saving altitude MeasuredParameters")

        # Cleanup and sanity check
        os.remove(xyFileName)
        os.remove(bdepthFileName)
        if inputFileCount != count:
            self.logger.warn('Counts are not equal! inputFileCount = %s, count from grdtrack output = %s', inputFileCount, count)

        return
