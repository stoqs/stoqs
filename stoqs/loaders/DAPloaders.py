#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2011, MBARI"
__credits__ = ["Chander Ganesan, Open Technology Group"]
__license__ = "GPL"
__version__ = "$Revision: 1.1 $".split()[1]
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
'''
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
import re
import sys
from argparse import Namespace
from django.contrib.gis.geos import LineString, Point
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # config is one dir up
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
from django.conf import settings

from django.db.models import Max
from django.db.utils import IntegrityError, DatabaseError
from django.db import transaction
from jdcal import gcal2jd, jd2gcal
from stoqs.models import (Activity, InstantPoint, Measurement, MeasuredParameter,
                          NominalLocation, Resource, ResourceType, ActivityResource,
                          Parameter)
from datetime import datetime, timedelta
from psycopg2.errors import UniqueViolation
import pytz
from pydap.client import open_url
import pydap.model
import math
from coards import to_udunits, from_udunits, ParserError
import logging
import socket
import seawater.eos80 as sw
from utils.utils import mode, simplify_points
from loaders import (STOQS_Loader, SkipRecord, HasMeasurement, MEASUREDINSITU, FileNotFound,
                     SIGMAT, SPICE, SPICINESS, ALTITUDE)
from loaders.SampleLoaders import get_closest_instantpoint, ClosestTimeNotFoundException
import numpy as np
import psycopg2
from collections import defaultdict


# Set up logging
logger = logging.getLogger(__name__)
# Logging level set in stoqs/config/common.py or via command line from LoadScript(), but may override here
logger.setLevel(logging.DEBUG)

# When settings.DEBUG is True Django will fill up a hash with stats on every insert done to the database.
# "Monkey patch" the CursorWrapper to prevent this.  Otherwise we can't load large amounts of data.
# See http://stackoverflow.com/questions/7768027/turn-off-sql-logging-while-keeping-settings-debug
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.utils import CursorWrapper

TRAJECTORY = 'trajectory'
TIMESERIES = 'timeseries'
TIMESERIESPROFILE = 'timeseriesprofile'
TRAJECTORYPROFILE = 'trajectoryprofile'

TIME = 'time'
DEPTH = 'depth'
LATITUDE = 'latitude'
LONGITUDE = 'longitude'

# Set batch_size such that we avoid swapping with bulk_create() on a 3 GB RAM system, a value = 10000 is good
# Significant swap disk is used (12%) and loads of DEIMOS data take 20% longer with BATCH_SIZE=100000
# Some loads (e.g. stoqs_canon_october2020) will crash postgresql unless BATCH_SIZE is reduced to 1000
# Update on 6 March 2020:
#   A more raw version of the DEIMOS data with 2619 depths in each profile runs out of memory unless it's
#   run on a VM with more than 10 GB of RAM.  Reducing BATCH_SIZE to 4 helps some with the memory requirement
#   but will still crash (be killed) on a 3 GB VM and takes will take twice the time on a bigger VM.
#   TODO: Load these data as trajectoryProfile with point simplification (removal of redundant data points).
BATCH_SIZE=10000

if settings.DEBUG:
    BaseDatabaseWrapper.make_debug_cursor = lambda self, cursor: CursorWrapper(cursor, self)


class ParameterNotFound(Exception): 
    pass


class NoValidData(Exception): 
    pass


class AuxCoordMissingStandardName(Exception):
    pass


class VariableMissingCoordinatesAttribute(Exception):
    pass


class VariableHasBadCoordinatesAttribute(Exception):
    pass


class InvalidSliceRequest(Exception):
    pass


class OpendapError(Exception):
    pass


class DuplicateData(Exception):
    pass


class CoordNotEqual(Exception):
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
       campaign specific database
    2. By setting startDatetime and endDatetime to None, in which case the start and end
       times are defined by the start and end of the data in the specified url

    A third time parameter (dataStartDatetime) can be specified.  This is used for when
    data is to be appended to an existing activity, such as for the realtime tethys loads
    as done by the monitorLrauv.py script in the realtime folder.  This
    use has not been fully tested.
    '''
    def __init__(self, activityName, platformName, url, dbAlias='default', campaignName=None, campaignDescription=None,
                activitytypeName=None, platformColor=None, platformTypeName=None, 
                startDatetime=None, endDatetime=None, dataStartDatetime=None, auxCoords=None, stride=1,
                grdTerrain=None, command_line_args=None):
        '''
        Given a URL open the url and store the dataset as an attribute of the object,
        then build a set of standard names using the dataset.
        The activity is saved, as all the data loaded will be a set of instantpoints
        that use the specified activity.
        stride is used to speed up loads by skipping data.
        
        @param activityName: A string describing this activity
        @param platformName: A string that is the name of the platform. 
                             If that name for a Platform exists in the DB, it will be used.
        @param platformColor: An RGB hex string represnting the color of the platform. 
        @param url: The OPeNDAP URL for the data source
        @param dbAlias: The name of the database alias as defined in settings.py
        @param campaignName: A string describing the Campaign in which this activity belongs. 
                             If that name for a Campaign exists in the DB, it will be used.
        @param campaignDescription: A string expanding on the campaignName. 
                                    It should be a short phrase expressing the where and why of a campaign.
        @param activitytypeName: A string such as 'mooring deployment' or 'AUV mission' describing type of 
                                 activity, If that name for a ActivityType exists in the DB, it will be used.
        @param platformTypeName: A string describing the type of platform, e.g.: 'mooring', 'auv'.  
                                 If that name for a PlatformType exists in the DB, it will be used.
        @param startDatetime: A Python datetime.dateime object specifying the start date time of data to load
        @param endDatetime: A Python datetime.dateime object specifying the end date time of data to load
        @param dataStartDatetime: A Python datetime.dateime object specifying the start date time of data 
                                  to append to an existing Activity
        @param command_line_args.append: If true then a dataStartDatetime value will be set by looking up the last
                           timevalue in the database for the Activity returned by getActivityName().
                           A True value will override the passed parameter dataStartDatetime.
        @param auxCoords: a dictionary of coordinate standard_names (time, latitude, longitude, depth) 
                          pointing to exact names of those coordinates. Used for variables missing the 
                          coordinates attribute.
        @param stride: The stride/step size used to retrieve data from the url.
        '''
        self.campaignName = campaignName
        self.campaignDescription = campaignDescription
        self.activitytypeName = activitytypeName
        self.platformName = platformName
        self.platformColor = platformColor
        self.dbAlias = dbAlias
        self.platformTypeName = platformTypeName
        self.activityName = activityName
        self.requested_startDatetime = startDatetime
        self.startDatetime = startDatetime
        self.requested_endDatetime = endDatetime
        self.endDatetime = endDatetime
        self.dataStartDatetime = dataStartDatetime  # For when we append data to an existing Activity
        self.auxCoords = auxCoords
        self.stride = stride
        self.grdTerrain = grdTerrain
        self.command_line_args = command_line_args
        self.coord_dicts = {}

        self.url = url
        self.varsLoaded = []
        try:
            self.ds = open_url(url)
        except (socket.error, pydap.exceptions.ServerError, pydap.exceptions.ClientError):
            message = 'Failed in attempt to open_url("%s")' % url
            self.logger.warn(message)
            # Give calling routing option of catching and ignoring
            raise OpendapError(message)
        except Exception as e:
            # Prevent multiline WARNINGs in the output log files
            message = str(e).split('\n')[0]
            self.logger.warn(f"Failed in attempt to open_url('{url}'): {message}")
            raise

        self.ignored_names = list(self.global_ignored_names)    # Start with copy of list of global ignored names
        self.build_standard_names()

    def _getStartAndEndTimeFromDS(self):
        '''
        Examine all possible time coordinates for include_names and set the overall min and max time for the dataset.
        To be used for setting Activity startDatetime and endDatetime.
        '''
        # TODO: Refactor to simplify. McCabe MC0001 pylint complexity warning issued.
        # TODO: Parse EPIC time and time2 variables
        minDT = {}
        maxDT = {}
        for v in self.include_names:
            try:
                ac = self.coord_dicts[v]
            except KeyError as e:
                self.logger.debug(str(e))
                continue

            if self.getFeatureType() == TRAJECTORY or self.getFeatureType() == TRAJECTORYPROFILE: 
                self.logger.debug('Getting trajectory min and max times for v = %s', v)
                self.logger.debug("self.ds[ac['time']][0] = %s", self.ds[ac['time']][0])
                try:
                    minDT[v] = from_udunits(self.ds[ac['time']].data[0][0], self.ds[ac['time']].attributes['units'])
                    maxDT[v] = from_udunits(self.ds[ac['time']].data[-1][0], self.ds[ac['time']].attributes['units'])
                except ParserError as e:
                    self.logger.warn("%s. Trying to fix up time units", e)
                    # Tolerate units like 1970-01-01T00:00:00Z - which is found on the IOOS Glider DAC
                    if self.ds[ac['time']].attributes['units'] == 'seconds since 1970-01-01T00:00:00Z':
                        minDT[v] = from_udunits(self.ds[ac['time']].data[0][0], 'seconds since 1970-01-01 00:00:00')
                        maxDT[v] = from_udunits(self.ds[ac['time']].data[-1][0], 'seconds since 1970-01-01 00:00:00')
                except ValueError as e:
                    self.logger.warn(f'Skipping load of {self.url}: {e}')
                    raise NoValidData(f'Could not get min and max time from {self.url}')
                    
            elif self.getFeatureType() == TIMESERIES or self.getFeatureType() == TIMESERIESPROFILE: # pragma: no cover
                self.logger.debug('Getting timeseries start time for v = %s', v)
                time_units = self.ds[list(self.ds[v].maps.keys())[0]].units.lower()
                if time_units == 'true julian day':
                    self.logger.debug('Converting EPIC times to epoch seconds')
                    tindx = self.getTimeBegEndIndices(self.ds[list(self.ds[v].keys())[1]])
                    times = self.ds[list(self.ds[v].maps.keys())[0]].data[tindx[0]:tindx[-1]:self.stride]
                    times, time_units = self._convert_EPIC_times(times, tindx)
                    minDT[v] = from_udunits(times[0], time_units)
                    maxDT[v] = from_udunits(times[-1], time_units)
                else:
                    minDT[v] = from_udunits(self.ds[v][ac['time']].data[0][0], self.ds[ac['time']].attributes['units'])
                    maxDT[v] = from_udunits(self.ds[v][ac['time']].data[-1][0], self.ds[ac['time']].attributes['units'])
            else:
                # Perhaps a strange file like LOPC size class data along a trajectory
                minDT[v] = from_udunits(self.ds[ac['time']].data[0][0], self.ds[ac['time']].attributes['units'])
                maxDT[v] = from_udunits(self.ds[ac['time']].data[-1][0], self.ds[ac['time']].attributes['units'])

        self.logger.debug('minDT = %s', minDT)
        self.logger.debug('maxDT = %s', maxDT)

        # STOQS does not deal with data in the future and in B.C.
        startDatetime = datetime.utcnow()
        endDatetime = datetime(1,1,1)

        for v, dt in list(minDT.items()):
            try:
                if dt < startDatetime:
                    startDatetime = dt
            except NameError:
                startDatetime = dt
                
        for v, dt in list(maxDT.items()):
            try:
                if dt > endDatetime:
                    endDatetime = dt
            except NameError:
                endDatetime = dt

        if not maxDT or not minDT:
            raise NoValidData('No valid dates')

        self.logger.info('Activity from %s: startDatetime = %s, endDatetime = %s', self.url, startDatetime, endDatetime)
        return startDatetime, endDatetime

    def initDB(self):
        '''
        Do the intial Database activities that are required before the data are processed: getPlatorm and createActivity.
        Can be overridden by sub class.  An overriding method can do such things as setting startDatetime and endDatetime.
        '''
        if hasattr(self, 'command_line_args'):
            if hasattr(self.command_line_args, 'append') and hasattr(self.command_line_args, 'remove_appended_activities'):
                if self.command_line_args.append and self.command_line_args.remove_appended_activities:
                    self.remove_appended_activities()
        if self.checkForValidData():
            self.platform = self.getPlatform(self.platformName, self.platformTypeName)
            self.add_parameters(self.ds)

            if hasattr(self, 'add_to_activity'):
                # Allow use of existing Activity for loading additional data, e.g. Dorado plankton_proxies
                self.logger.info(f"Will add these data to Activity (likely plankton_proxies) {self.add_to_activity}")
            elif hasattr(self, 'associatedActivityName'):
                self.logger.info(f"Will associate these data (likely lopc) to Activity {self.associatedActivityName}")
            else:
                # Ensure that startDatetime and startDatetime are defined as they are required fields of Activity
                if not self.startDatetime or not self.endDatetime:
                    self.startDatetime, self.endDatetime = self._getStartAndEndTimeFromDS()
                self.createActivity()
        else:
            raise NoValidData('No valid data in url %s' % (self.url))

    def getmissing_value(self, var):
        '''
        Return the missing_value attribute for netCDF variable var
        '''
        mv = None
        try:
            mv = float(self.ds[var].attributes['missing_value'])
        except KeyError:
            if 'nemesis' in self.url and var in ('u', 'v'):
                self.logger.debug('Special fix for nemesis data, return a standard missing_value of -1.e34')
                mv = -1.0e34
            else:
                self.logger.debug('Cannot get attribute missing_value for variable %s from url %s', var, self.url)
        except AttributeError as e:
            self.logger.debug(str(e))
        
        return mv

    def get_FillValue(self, var):
        '''
        Return the _FillValue attribute for netCDF variable var
        '''
        fv = None
        try:
            fv = float(self.ds[var].attributes['_FillValue'])
        except KeyError:
            self.logger.debug('Cannot get attribute _FillValue for variable %s from url %s', var, self.url)
            try:
                # Fred's L_662 and other glider data files have the 'FillValue' attribute, not '_FillValue'
                fv = float(self.ds[var].attributes['FillValue'])
            except KeyError:
                try:
                    # http://odss.mbari.org/thredds/dodsC/CANON/2013_Sep/Platforms/AUVs/Daphne/NetCDF/Daphne_CANON_Fall2013.nc.html has 'fill_value'
                    fv = float(self.ds[var].attributes['fill_value'])
                except Exception as e:
                    self.logger.debug('Cannot get FillValue for variable %s from url %s: %s', var, self.url, str(e))
        except ValueError as e:
            self.logger.warn('%s for variable %s from url %s', str(e), var, self.url)
        except AttributeError as e:
            self.logger.debug(str(e))

        return fv

    def get_shape_length(self, pname):
        '''Works for both pydap 3.1.1 and 3.2.0
        '''
        try:
            shape_length = len(self.ds[pname].shape)
        except AttributeError:
            # Likely using pydap 3.2+
            shape_length = len(self.ds[pname].array.shape)

        return shape_length

    def getActivityName(self):
        '''Return actual Activity name that will be in the database accounting
        for permutations of startDatetime and stride values per NetCDF file name.
        '''
        # Modify Activity name if temporal subset extracted from NetCDF file
        newName = self.activityName
        if not ' starting at ' in newName:
            if hasattr(self, 'requested_startDatetime') and hasattr(self, 'requested_endDatetime'):
                if self.requested_startDatetime and self.requested_endDatetime:
                    if '(stride' in self.activityName:
                        first_part = self.activityName[:self.activityName.find('(stride')]
                        last_part = self.activityName[self.activityName.find('(stride'):]
                    else:
                        first_part = self.activityName
                        last_part = ''
                    newName = '{} starting at {} {}'.format(first_part.strip(), self.requested_startDatetime, last_part)

        return newName

    def getFeatureType(self):
        '''
        Return string of featureType from table at http://cf-pcmdi.llnl.gov/documents/cf-conventions/1.6/ch09.html.
        Accomodate previous concepts of this attribute and convert to the new discrete sampling geometry conventions in CF-1.6.
        Possible return values: TRAJECTORY, TIMESERIES, TIMESERIESPROFILE, lowercase versions.
        '''
        conventions = ''
        if hasattr(self, 'ds'):
            try:
                nc_global_keys = self.ds.attributes['NC_GLOBAL']
            except KeyError:
                self.logger.warn('Dataset does not have an NC_GLOBAL attribute! Setting featureType to "trajectory" assuming that this is an old Tethys file')
                return TRAJECTORY
        else:
            self.logger.warn('Loader has no ds attribute. Setting featureType to "trajectory" assuming that this is an ROVCTD Loader.')
            return TRAJECTORY

        if 'Conventions' in nc_global_keys:
            conventions = self.ds.attributes['NC_GLOBAL']['Conventions'].lower()
        elif 'Convention' in nc_global_keys:
            conventions = self.ds.attributes['NC_GLOBAL']['Convention'].lower()
        elif 'conventions' in nc_global_keys: # pragma: no cover
            conventions = self.ds.attributes['NC_GLOBAL']['conventions'].lower()
        else:
            conventions = ''

        if 'cf-1.6' in conventions.lower():
            try:
                featureType = self.ds.attributes['NC_GLOBAL']['featureType']
            except KeyError:
                # For https://dods.ndbc.noaa.gov/thredds/dodsC/oceansites/DATA/MBARI/OS_MBARI-M1_20160829_R_TS.nc.das
                featureType = self.ds.attributes['NC_GLOBAL']['cdm_data_type']
        else:
            # Accept earlier versions of the concept of this attribute that may be in legacy data sets
            if 'cdm_data_type' in nc_global_keys:
                featureType = self.ds.attributes['NC_GLOBAL']['cdm_data_type']
            elif 'thredds_data_type' in nc_global_keys:
                featureType = self.ds.attributes['NC_GLOBAL']['thredds_data_type'] 
            elif 'CF%3afeatureType' in nc_global_keys:
                featureType = self.ds.attributes['NC_GLOBAL']['CF%3afeatureType']
            elif 'CF_featureType' in nc_global_keys:
                featureType = self.ds.attributes['NC_GLOBAL']['CF_featureType']
            elif 'CF:featureType' in nc_global_keys:    # Seen in lrauv/*/realtime/sbdlogs files
                featureType = self.ds.attributes['NC_GLOBAL']['CF:featureType']
            elif 'featureType' in nc_global_keys:       # Seen in roms.nc file from JPL
                featureType = self.ds.attributes['NC_GLOBAL']['featureType']
            else:
                featureType = ''

        if featureType.lower() == 'station':
            # Used in elvis' TDS mooring data aggregation, it's really 'timeseriesprofile'
            featureType = TIMESERIESPROFILE

        if featureType.lower() == 'trajectory':
            featureType = TRAJECTORY

        # Put the CF-1.6 proper featureType into NC_GLOBAL so that addResources will put it into the database
        self.ds.attributes['NC_GLOBAL']['featureType'] = featureType

        return featureType.lower()

    def _getCoordinates(self, from_variables):
        '''Return tuple of (Dictionary of geospatial/temporal standard_names keyed by variable name,
        Dictionary of variable names keyed by geospatial/temporal standard_names).
        '''
        coordSN = {}
        snCoord = {}
        for k in from_variables:
            try:
                if 'standard_name' in self.ds[k].attributes:
                    if self.ds[k].attributes['standard_name'] in ('time', 'latitude', 'longitude', 'depth'):
                        coordSN[k] = self.ds[k].attributes['standard_name']
                        snCoord[self.ds[k].attributes['standard_name']] = k
            except KeyError:
                self.logger.error(f"Could not find variable {k} in the file. Perhaps there's a problem with the coordinates attribute?")
                raise

        return coordSN, snCoord

    def getAuxCoordinates(self, variable):
        '''
        Return a dictionary of a variable's auxilary coordinates mapped to the standard_names of 'time', 'latitude',
        'longitude', and 'depth'.  Accommodate previous ways of associating these variables and convert to the new
        CF-1.6 conventions as outlined in Chapter 5 of the document.  If an auxCoord dictionary is passed to the
        Loader then that dictionary will be returned for variables that do not have a valid coordinates attribute;
        this is handy for datasets that are not yet compliant.

        Requirements for compliance: variables have a coordinates attribute listing the 4 geospatial/temporal 
        coordinates, the coordinate variables have standard_names of 'time', 'latitude', 'longitude', 'depth'.
        Example return value: {'time': 'esecs', 'depth': 'DEPTH', 'latitude': 'lat', 'longitude': 'lon'}
        '''
        # Match items in coordinate attribute, via coordinate standard_name to coordinate name
        if variable not in self.ds:
            raise ParameterNotFound('Variable %s is not in dataset %s' % (variable, self.url))

        coord_dict = {}
        if 'coordinates' in self.ds[variable].attributes:
            coords = self.ds[variable].attributes['coordinates'].split()
            try:
                coordSN, snCoord = self._getCoordinates(coords)
            except KeyError as e:
                self.logger.error(f"Could not get coordinates for {variable}. Check its coordinates attribute.")
                raise VariableHasBadCoordinatesAttribute(e)
            for coord in coords:
                self.logger.debug(coord)
                try:
                    self.logger.debug(snCoord)
                    coord_dict[coordSN[coord]] = coord
                except KeyError as e:
                    if coord == 'trajectory':
                        self.logger.info(f"Found 'trajectory' in coordinates attribute. Likely a Saildrone or GliderDAC trajectory file.")
                    else:
                        raise AuxCoordMissingStandardName(e)
        else:
            self.logger.debug('Variable %s is missing coordinates attribute, checking if loader has specified it in auxCoords', variable)
            if variable in self.auxCoords:
                # Try getting it from overridden values provided
                for coordSN, coord in list(self.auxCoords[variable].items()):
                    try:
                        coord_dict[coordSN] = coord
                    except KeyError as e:
                        raise AuxCoordMissingStandardName(e)
            else:
                self.logger.warn('%s not in auxCoords' % variable)

        # Check for all 4 coordinates needed for spatial-temporal location - if any are missing raise exception with suggestion
        reqCoords = set(('time', 'latitude', 'longitude', 'depth'))
        self.logger.debug('coord_dict = %s', coord_dict)
        if set(coord_dict.keys()) != reqCoords:
            self.logger.debug('Required coordinate(s) %s missing in NetCDF file.',
                        list(reqCoords - set(coord_dict.keys())))
            if not self.auxCoords:
                raise VariableMissingCoordinatesAttribute('%s: %s missing coordinates attribute' % (self.url, variable,))

        self.logger.debug('coord_dict = %s', coord_dict)

        if not coord_dict or set(coord_dict.keys()) != reqCoords: # pragma: no cover
            if self.auxCoords:
                if variable in self.auxCoords:
                    # Simply return self.auxCoords if specified in the constructor
                    self.logger.debug('Returning auxCoords for variable %s that were specified in the constructor: %s', variable, self.auxCoords[variable])
                    return self.auxCoords[variable]
                else:
                    raise ParameterNotFound('auxCoords is specified, but variable requested (%s) is not in %s' % (variable, self.auxCoords))
        else:
            return coord_dict

    def getNominalLocation(self):
        '''
        For timeSeries and timeSeriesProfile data return nominal location as a tuple of (depth, latitude, longitude) as
        expressed in the coordinate variables of the mooring or station. For timeSeries features depth will be a scalar, 
        for timeSeriesProfile depth will be an array of depths.  For timeSeries and timeSeriesProfile variables with precise
        longitudes and latitudes ignore them here - this method returns just the single nominal horizontal position.
        '''
        depths = {}
        lats = {}
        lons = {}
        for v in self.include_names:
            self.logger.debug('v = %s', v)
            try:
                ac = self.coord_dicts[v]
            except KeyError as e:
                self.logger.debug('Skipping include_name = %s: %s', v, e)
                continue
     
            # depth may be single-valued or an array 
            if self.getFeatureType() == TIMESERIES: 
                self.logger.debug('Initializing depths list for timeseries, ac = %s', ac)
                try:
                    if 'depth' in ac:
                        depths[v] = self.ds[v][ac['depth']].data[:][0]
                except KeyError:
                    self.logger.warn('No depth coordinate found for %s.  Assuming EPIC scalar and assigning depth from first element', v)
                    depths[v] = self.ds[ac['depth']].data[0]
            elif self.getFeatureType() == TIMESERIESPROFILE:
                self.logger.debug('Initializing depths list for timeseriesprofile, ac = %s', ac) 
                try:
                    depths[v] = self.ds[v][ac['depth']].data[:]
                except KeyError:
                    # Likely a TIMESERIES variable in a TIMESERIESPROFILE file (e.g. heading in ADCP file)
                    # look elsewhere for a nominal depth
                    if 'nominal_sensor_depth' in self.ds.attributes['NC_GLOBAL']:
                        # Hard-coded CCE EPIC nominal depth
                        depths[v] = [float(self.ds.attributes['NC_GLOBAL']['nominal_sensor_depth'])]
                    else:
                        self.logger.warning(f"Could not find {ac['depth']} for variable {v} in {self.url}, attempting to hard-code the depth with 'ADCP_DEPTH'")
                        if v == 'SW_FLUX_HR':
                            self.logger.info(f"Attempting to hard-code the depth with the first value from 'HR_DEPTH_0'")
                            depths[v] = [self.ds['HR_DEPTH_0'].data[:][0]]
                        else:
                            self.logger.info(f"Attempting to hard-code the depth with the first value from 'ADCP_DEPTH'")
                            depths[v] = [self.ds['ADCP_DEPTH'].data[:][0]]
            elif self.getFeatureType() == TRAJECTORYPROFILE:
                self.logger.debug('Initializing depths list for trajectoryprofile, ac = %s', ac)
                depths[v] = self.ds[v][ac['depth']].data[:]

            try:
                lons[v] = self.ds[v][ac['longitude']].data[:][0]
            except KeyError:
                if len(self.ds[ac['longitude']].data[:]) == 1:
                    lons[v] = self.ds[ac['longitude']].data[:][0]
                elif len(self.ds[ac['longitude']].data[:]) == 2:
                    # OASIS ADCP data has GPS_LONGITUDE and GPS_LATITUDE time series in auxillary coordinate
                    self.logger.debug(f"Auxillary longitude coordinate {ac['longitude']} is a variable with"
                                      f" {len(self.ds[ac['longitude']][ac['longitude']].data[:])} points")
                    self.logger.info(f"Using COARDS coordinate for {v}'s longitude")
                    try:
                        lons[v] = self.ds[list(self.ds[v].maps.keys())[3]].data[:][0]
                    except IndexError:
                        self.logger.warn(f'Cannot get nominal longitude coordinate using COARDS rules: self.ds[v].keys() = {self.ds[v].keys()}')
                else:
                    self.logger.warn('Variable %s has longitude auxillary coordinate of length %d, expecting it to be 1.',
                                v, len(self.ds[ac['longitude']].data[:]))

            try:
                lats[v] = self.ds[v][ac['latitude']].data[:][0]
            except KeyError:
                if len(self.ds[ac['latitude']].data[:]) == 1:
                    lats[v] = self.ds[ac['latitude']].data[:][0]
                elif len(self.ds[ac['latitude']].data[:]) == 2:
                    # OASIS ADCP data has GPS_LONGITUDE and GPS_LATITUDE time series in auxillary coordinate
                    self.logger.debug(f"Auxillary latitude coordinate {ac['latitude']} is a variable with"
                                      f" {len(self.ds[ac['latitude']][ac['latitude']].data[:])} points")
                    self.logger.info(f"Using COARDS coordinate for {v}'s latitude")
                    try:
                        lats[v] = self.ds[list(self.ds[v].maps.keys())[2]].data[:][0]
                    except IndexError:
                        self.logger.warn(f'Cannot get nominal latitude coordinate using COARDS rules: self.ds[v].keys() = {self.ds[v].keys()}')
                else:
                    self.logger.warn('Variable %s has latitude auxillary coordidate of length %d, expecting it to be 1.', 
                                v, len(self.ds[ac['latitude']].data[:]))

        # All variables must have the same nominal location 
        if len(set(lats.values())) != 1 or len(set(lons.values())) != 1:
            raise Exception('Invalid file coordinates structure.  All variables must have'
                            ' identical nominal lat & lon, lats = %s, lons = %s' % lats, lons)

        return depths, lats, lons

    def getTimeBegEndIndices(self, timeAxis):
        '''
        Return beginning and ending indices for the corresponding time axis indices
        '''
        if not getattr(self, 'startDatetime', None) and not getattr(self, 'endDatetime', None):
            s = 0
            e = timeAxis.shape[0]
            return s, e

        isEPIC = False
        try:
            isEPIC = 'EPIC' in self.ds.attributes['NC_GLOBAL']['Conventions'].upper()
        except KeyError:
            # No 'Conventions' key on 'NC_GLOBAL', check another way, e.g.
            # http://dods.mbari.org/opendap/data/CCE_Archive/MS1/20151006/CTOBSTrans9m/MBCCE_MS1_CTOBSTrans9m_20151006.nc
            # does not have a Conventions global attribute, so also check for time, time2 and the units
            isEPIC = 'time' in self.ds.keys() and 'time2' in self.ds.keys() and self.ds['time'].attributes['units'] == 'True Julian Day'
            if isEPIC:
                self.logger.warn("%s does not have 'Conventions', yet appears to be EPIC from its time/time2 variables", self.url)

        if isEPIC:
            # True Julian dates are at noon, so take int() to match EPIC's time axis values and to satisfy:
            #   datum: Time (UTC) in True Julian Days: 2440000 = 0000 h on May 23, 1968
            #   NOTE: Decimal Julian day [days] = time [days] + ( time2 [msec] / 86400000 [msec/day] )
            jbd = int(sum(gcal2jd(self.startDatetime.year, self.startDatetime.month, self.startDatetime.day)) + 0.5)
            jed = int(sum(gcal2jd(self.endDatetime.year, self.endDatetime.month, self.endDatetime.day)) + 0.5)

            t_indx = np.where((jbd <= timeAxis) & (timeAxis <= jed))[0]
            if not t_indx.any():
                raise NoValidData('No data from %s for time values between %s and %s.  Skipping.' % (self.url, 
                                  self.startDatetime, self.endDatetime))

            # Refine indicies with fractional portion of the day (ms since midnight) as represented in the time2 variable
            bms = 0
            if self.startDatetime.hour or self.startDatetime.minute or self.startDatetime.second:
                bms = self.startDatetime.hour * 3600000 + self.startDatetime.minute * 60000 + self.startDatetime.second * 1000
            ems = 86400000
            if self.endDatetime.hour or self.endDatetime.minute or self.endDatetime.second:
                ems = self.endDatetime.hour * 3600000 + self.endDatetime.minute * 60000 + self.endDatetime.second * 1000

            # Tolerate datasets that begin or end inside the limits of self.startDatetime and self.endDatetime
            beg_day_indices = np.where(jbd == timeAxis)[0]
            t2_indx_beg = 0
            if beg_day_indices.any():
                time2_axis_beg = self.ds['time2']['time2'][beg_day_indices[0]:beg_day_indices[-1]]
                try:
                    t2_indx_beg = np.where(bms <= time2_axis_beg)[0][0]
                except IndexError:
                    # Likely no bms <= time2_axis_beg, leave t2_indx_beg = 0
                    pass

            end_day_indices = np.where(jed == timeAxis)[0]
            t2_indx_end = 0
            if end_day_indices.any():
                if end_day_indices[0] > 0 and (end_day_indices[0] == end_day_indices[-1]):
                    time2_axis_end = self.ds['time2']['time2'][int(end_day_indices[0]) - 1:int(end_day_indices[-1])]
                else:
                    time2_axis_end = self.ds['time2']['time2'][int(end_day_indices[0]):int(end_day_indices[-1])]
                try:
                    t2_indx_end = len(time2_axis_end) - np.where(ems >= time2_axis_end)[0][-1]
                except IndexError:
                    # Likely ems ls less than the sampling interval, resulting in an empty np.where(ems >= time2_axis_end)
                    t2_indx_end = len(time2_axis_end)

            indices = t_indx[0] + t2_indx_beg, t_indx[-1] - t2_indx_end
            return indices


        timeAxisUnits =  timeAxis.units.lower()
        timeAxisUnits = timeAxisUnits.replace('utc', 'UTC')        # coards requires UTC to be upper case 
        if timeAxis.units == 'seconds since 1970-01-01T00:00:00Z'or timeAxis.units == 'seconds since 1970/01/01 00:00:00Z':
            timeAxisUnits = 'seconds since 1970-01-01 00:00:00'    # coards doesn't like ISO format
        if self.startDatetime: 
            self.logger.debug('self.startDatetime, timeAxis.units = %s, %s', self.startDatetime, timeAxis.units)
            s = to_udunits(self.startDatetime, timeAxisUnits)
            self.logger.debug("For startDatetime = %s, the udnits value is %f", self.startDatetime, s)

        if self.dataStartDatetime: 
            # Override s if self.dataStartDatetime is specified
            self.logger.debug('self.dataStartDatetime, timeAxis.units = %s, %s', self.dataStartDatetime, timeAxis.units)
            s = to_udunits(self.dataStartDatetime, timeAxisUnits)
            self.logger.debug("For dataStartDatetime = %s, the udnits value is %f", self.dataStartDatetime, s)

        if self.requested_endDatetime:
            # endDatetime may be None, in which case just read until the end
            e = to_udunits(self.endDatetime, timeAxisUnits)
            self.logger.debug("For endDatetime = %s, the udnits value is %f", self.endDatetime, e)
        else:
            e = timeAxis[-1]
            self.logger.debug("requested_endDatetime not given, using the last value of timeAxis = %f", e.data[0])

        tf = np.array([])
        if getattr(self, 'command_line_args', False):
            if self.command_line_args.append:
                # Exclusive of s, as that is the max timevalue in the database for the Activity
                self.logger.info(f"--append specified. Finding start index where time > {s}")
                tf = (s < timeAxis) & (timeAxis <= e)
        if not tf.any():
            # Inclusive of the specified start time
            tf = (s <= timeAxis) & (timeAxis <= e)

        # Numpy Array tf has True values at indices corresponding to the data we need to load
        tIndx = np.nonzero(tf == True)[0]
        if tIndx.size == 0:
            raise NoValidData(f'No time values from {self.url} between time values {s} and {e}')
        elif tIndx.size == 1:
            # Loading a single value
            tIndx = np.array([tIndx[0], tIndx[0]])

        try:
            indices = (tIndx[0], tIndx[-1] + 1)
        except IndexError:
            raise NoValidData('Could not get first and last indexes from tIndex = %s. Skipping.' % (tIndx))
        self.logger.info('Start and end indices are: %s', indices)

        if indices[1] <= indices[0]:
            raise InvalidSliceRequest('Cannot issue DAP temporal constraint expression of non-positive slice: indices = {indices}')

        return indices

    def getTotalRecords(self):
        '''
        For the url count all the records that are to be loaded from all the include_names and return it.
        Computes the sum of the product of the time slice and the rest of the elements of the shape.
        '''
        pcount = 0
        count = 0
        numDerived = 0
        trajSingleParameterCount = 0
        for name in self.include_names:
            try:
                tIndx = self.getTimeBegEndIndices(self.ds[self.coord_dicts[name]['time']])
            except KeyError:
                self.logger.debug('Ignoring parameter: %s', name)
            except InvalidSliceRequest:
                self.logger.warn('No valid data for parameter: %s', name)
                continue
            except KeyError as e:
                self.logger.warn("%s: Skipping", e)
                continue
            try:
                if self.getFeatureType() == TRAJECTORY:
                    try:
                        trajSingleParameterCount = np.prod(self.ds[name].shape[1:] + (np.diff(tIndx)[0],))
                    except AttributeError:
                        # Likely using pydap 3.2+
                        trajSingleParameterCount = np.prod(self.ds[name].array.shape[1:] + (np.diff(tIndx)[0],))
                try:
                    pcount = (np.prod(self.ds[name].shape[1:] + (np.diff(tIndx)[0],)) / self.stride)
                    count += pcount
                except AttributeError:
                    # Likely using pydap 3.2+
                    pcount = (np.prod(self.ds[name].array.shape[1:] + (np.diff(tIndx)[0],)) / self.stride)
                    count += pcount
            except KeyError as e:
                if self.getFeatureType() == TRAJECTORY:
                    # Assume that it's a derived variable and add same count as 
                    self.logger.debug("%s: Assuming it's a derived parameter", e)
                    numDerived += 1
            self.logger.info(f'Count of parameter {name:20}: {int(pcount):7d}')
                    
        self.logger.debug('Adding %d derived parameters of length %d to the count', numDerived, trajSingleParameterCount / self.stride)
        if trajSingleParameterCount:
            count += (numDerived * trajSingleParameterCount / self.stride)

        return count 

    def _equal_coords(self, load_groups, coor_groups):
        '''Peek at the data in the axes and mark with True values those elements that match.
        This is a special fix for realtime LRAUV data from shore_i.nc files.
        Tested with:
        1. Initial short mission
        http://dods.mbari.org/opendap/data/lrauv/whoidhs/realtime/sbdlogs/2019/201906/20190609T194744/shore_i.nc
        2. Unequal array lengths
        http://dods.mbari.org/opendap/data/lrauv/whoidhs/realtime/sbdlogs/2019/201906/20190609T202208/shore_i.nc
        3. Very unequal lengths, pad with 41 zeros; fails with duplicate key value
        http://dods.mbari.org/opendap/data/lrauv/whoidhs/realtime/sbdlogs/2019/201906/20190612T024430/shore_i.nc
        4. Horrendously bad result with coordinates and data represented badly in STOQS UI section plots.
        (Implemented temporary fix by not loading salinity; problem occurs with loading both temperature & salinity)
        http://dods.mbari.org/opendap/data/lrauv/makai/realtime/sbdlogs/2020/202010/20201008T014813/shore_i.nc
    
        The role of this method is to identify truly equal coordinates of variables to be loaded for the 
        calling routine to determine whether a bulk_create() may be done or whether the variables need to be
        loaded the old fashioned (slower) way - one element at a time, reusing previously loaded coordinates.

        N.B.: In Janurary 2022 stoqs/loaders/CANON/toNetCDF/lrauvNc4ToNetcdf.py was modified to re-interpolate
        the decimated data to '2S' frequency and use common coordinate axes for all variables - so this finction
        isn't really needed for those new shore_i.nc files.
        '''
        coord_equals = {}
        if len(coor_groups) == 1:
            self.logger.info(f"Single set of coordinates as would be found in a modern shore_i.nc file")
            return coord_equals
        for count, (axes, ac) in enumerate(coor_groups.items()):
            self.logger.info(f"Initializing coord_equals to all False for axes {axes}")
            self.logger.info(f"Number of {ac[TIME]} values: {len(self.ds[ac[TIME]])}")
            coord_equals[axes] = np.full(len(self.ds[ac[TIME]]), False)

            variable = load_groups[axes][0]
            if count > 0:
                if len(last_times) < len(self.ds[ac[TIME]]):
                    self.logger.info(f"len(last_times) ({len(last_times)}) < len(self.ds[ac[TIME]]) ({len(self.ds[ac[TIME]])})")
                    num_pad = len(self.ds[ac[TIME]]) - len(last_times)
                    self.logger.info(f"Padding last_ coordinate arrays with {num_pad} zero(s) to match (taking a chance) the self.ds coordinate arrays")
                    last_times = np.pad(last_times, [(0, num_pad)], mode='constant', constant_values=0)
                    last_depths = np.pad(last_depths, [(0, num_pad)], mode='constant', constant_values=0)
                    last_latitudes = np.pad(last_latitudes, [(0, num_pad)], mode='constant', constant_values=0)
                    last_longitudes = np.pad(last_longitudes, [(0, num_pad)], mode='constant', constant_values=0)

                if len(last_times) > len(self.ds[ac[TIME]]):
                    self.logger.warn(f"len(last_times) ({len(last_times)}) > len(self.ds[ac[TIME]]) ({len(self.ds[ac[TIME]])})")
                    self.logger.warn(f"Not Padding self.ds arrays - not able to attempt a fix")
                    continue

                self.logger.debug(f"Comparing coords with those from {last_variables}")
                times_equal = np.equal(last_times, self.ds[ac[TIME]])
                self.logger.debug(f"  {variable} times: {times_equal}")
                self.logger.debug(f"    {list(last_times[:])}")
                self.logger.debug(f"    {list(self.ds[ac[TIME]])}")
                depths_equal = np.equal(last_depths, self.ds[ac[DEPTH]][ac[DEPTH]])
                self.logger.debug(f"  {variable} depths: {depths_equal}")
                self.logger.debug(f"    {list(last_depths[:])}")
                self.logger.debug(f"    {list(self.ds[ac[DEPTH]][ac[DEPTH]])}")
                latitudes_equal = np.equal(last_latitudes, self.ds[ac[LATITUDE]][ac[LATITUDE]])
                self.logger.debug(f"  {variable} latitudes: {latitudes_equal}")
                self.logger.debug(f"    {list(last_latitudes[:])}")
                self.logger.debug(f"    {list(self.ds[ac[LATITUDE]][ac[LATITUDE]])}")
                longitudes_equal = np.equal(last_longitudes, self.ds[ac[LONGITUDE]][ac[LONGITUDE]])
                self.logger.debug(f"  {variable} longitudes: {longitudes_equal}")
                self.logger.debug(f"    {list(last_longitudes[:])}")
                self.logger.debug(f"    {list(self.ds[ac[LONGITUDE]][ac[LONGITUDE]])}")
                coord_equals[axes] = np.logical_and(np.logical_and(times_equal, 
                                                                   depths_equal), 
                                                    np.logical_and(latitudes_equal, 
                                                                   longitudes_equal))
                self.logger.debug(f"  {variable} .logical_and(): {coord_equals[axes]}")
        
            last_times = self.ds[ac[TIME]]
            last_depths = self.ds[ac[DEPTH]][ac[DEPTH]]
            last_latitudes = self.ds[ac[LATITUDE]][ac[LATITUDE]]
            last_longitudes = self.ds[ac[LONGITUDE]][ac[LONGITUDE]]
            last_variables = load_groups[axes]

        return coord_equals

    def get_load_structure(self):
        '''Return data structure organized by Parameters with common coordinates.
        This supports the use of bulk_create() to speed the loading of data.
        '''
        ac = {}
        load_groups = defaultdict(list)
        coor_groups = {}
        for pname in self.include_names:
            if pname not in list(self.ds.keys()):
                self.logger.debug('include_name %s not in dataset %s', pname, self.url)
                continue
            ac[pname] = self.coord_dicts[pname]
            try:
                load_groups[''.join(sorted(list(ac[pname].values())))].append(pname)
                coor_groups[''.join(sorted(list(ac[pname].values())))] = ac[pname]
            except TypeError:
                # Likely "TypeError: '<' not supported between instances of 'float' and 'str'" because depth = 0.0 in auxCoords
                self.logger.debug(f'Number likely in auxCoords rather than a coordinate name, convert to string for group_name')
                group_name = ''
                for v in ac[pname].values():
                    group_name += str(v)

                self.logger.debug(f'group_name = {group_name}')
                load_groups[group_name].append(pname)
                coor_groups[group_name] = ac[pname]

        return load_groups, coor_groups

    def _ips(self, mtimes):
        for i, mt in enumerate(mtimes):
            if mt:
                yield InstantPoint(activity=self.activity, timevalue=mt)
            else:
                self.logger.debug(f"Bad timevalue from {self.url} at index {i}")
                yield None

    def _meass(self, depths, longitudes, latitudes):
        for i, (de, lo, la) in enumerate(zip(depths, longitudes, latitudes)):
            # Accept depths that are 0.0, but not latitudes and longitudes that are zero
            if de is not None and lo and la:
                yield Measurement(depth=repr(de), geom=Point(float(lo), float(la)))
            else:
                self.logger.debug(f"Bad coordinate from {self.url} at index {i}")
                yield None

    def _find_dup_coords(self, ips, meass, coords_equal):
        for index, (ip, meas) in enumerate(zip(ips, meass)):
            if meas:
                try:
                    measurement = Measurement.objects.using(self.dbAlias).filter(depth=meas.depth,
                                                                                 geom=meas.geom,
                                                                                 instantpoint=ip)
                    self.logger.info(f"Adding index {index} to coords_equal for meas = {meas}")
                    coords_equal[index] = True
                except Measurement.DoesNotExist:
                    continue

        return coords_equal

    def _all_coords_equal(self, tindx, ac, pnames, axes, coords_equal=np.array([])):
        '''If duplicate coordinant found in database then this is for testing whether
        all the coordinates in the data to be loaded are identical with an Activity
        already in the database.  Initially implemented to add plankton_proxy data
        to an existing Dorado Activity.
        '''

    def _read_coords_from_ds(self, tindx, ac, multidim_trajectory=False):
        '''Initial implementations assume a single trajectory in each netCDF file.
        With adoption of CF-1.7 " It is strongly recommended that there always be a 
        trajectory variable (of any data type) with the attribute cf_role=”trajectory_id” 
        attribute, whose values uniquely identify the trajectories." 
        http://cfconventions.org/Data/cf-conventions/cf-conventions-1.7/cf-conventions.html#trajectory-data
        The multidim_trajectory flag is for indicating a netCDF file that has a
        Multidimensional array representation of trajectories.
        '''
        if multidim_trajectory:
            # TODO: Deal with (as yet unseen) case where multiple trajectories exist in a netCDF file
            times = self.ds[ac[TIME]][0][0][tindx[0]:tindx[-1]:self.stride]
        else:
            times = self.ds[ac[TIME]][tindx[0]:tindx[-1]:self.stride]
        time_units = self.ds[ac[TIME]].units.lower().replace('utc', 'UTC')
        if self.ds[ac[TIME]].units == 'seconds since 1970-01-01T00:00:00Z':
            time_units = 'seconds since 1970-01-01 00:00:00'          # coards doesn't like ISO format
        try:
            if times.shape[0] > 0:
                mtimes = (from_udunits(mt, time_units) for mt in times)
        except IndexError:
            # Trap case where times.shape = () giving opportunity to turn a single value into a list
            mtimes = [from_udunits(float(times.data), time_units)]

        try:
            if isinstance(self.ds[ac[DEPTH]], pydap.model.GridType):
                depths = self.ds[ac[DEPTH]][ac[DEPTH]][tindx[0]:tindx[-1]:self.stride]
            else:
                depths = self.ds[ac[DEPTH]][tindx[0]:tindx[-1]:self.stride]
        except KeyError:
            # Allow for variables with no depth coordinate to be loaded at the depth specified in auxCoords
            if ac[DEPTH] in self.ds:
                if isinstance(ac[DEPTH], (int, float)):
                    depths = ac[DEPTH] * np.ones(len(times))
            else:
                self.logger.warn(f'No depth coordinate {ac[DEPTH]} in {self.ds}')
                if isinstance(ac[DEPTH], (int, float)):
                    if multidim_trajectory:
                        self.logger.info('Overridden in auxCoords: ac[DEPTH] = {ac[DEPTH]}, setting depths to [{ac[DEPTH]}] * len(times)')
                        depths = [ac[DEPTH]] * len(times)
                    else:
                        self.logger.info('Overridden in auxCoords: ac[DEPTH] = {ac[DEPTH]}, setting depths to [{ac[DEPTH]}]')
                        depths = [ac[DEPTH]]

        if isinstance(self.ds[ac[LATITUDE]], pydap.model.GridType):
            latitudes = self.ds[ac[LATITUDE]][ac[LATITUDE]][tindx[0]:tindx[-1]:self.stride]
        elif multidim_trajectory:
            # TODO: Deal with (as yet unseen) case where multiple trajectories exist in a netCDF file
            latitudes = self.ds[ac[LATITUDE]][0][0][tindx[0]:tindx[-1]:self.stride]
        else:
            latitudes = self.ds[ac[LATITUDE]][tindx[0]:tindx[-1]:self.stride]
        try:
            if latitudes.shape[0] > 0:
                pass
        except IndexError:
            # Trap case where latitudes.shape = () giving opportunity to turn a single value into a list
            latitudes = [float(latitudes.data)]

        if isinstance(self.ds[ac[LONGITUDE]], pydap.model.GridType):
            longitudes = self.ds[ac[LONGITUDE]][ac[LONGITUDE]][tindx[0]:tindx[-1]:self.stride]
        elif multidim_trajectory:
            # TODO: Deal with (as yet unseen) case where multiple trajectories exist in a netCDF file
            longitudes = self.ds[ac[LONGITUDE]][0][0][tindx[0]:tindx[-1]:self.stride]
        else:
            longitudes = self.ds[ac[LONGITUDE]][tindx[0]:tindx[-1]:self.stride]
        try:
            if longitudes.shape[0] > 0:
                pass
        except IndexError:
            # Trap case where longitudes.shape = () giving opportunity to turn a single value into a list
            longitudes = [float(longitudes.data)]

        return mtimes, depths, latitudes, longitudes

    def _load_coords_from_dsg_ds(self, tindx, ac, pnames, axes, coords_equal=np.array([]), multidim_trajectory=False):
        '''Pull coordinates from Discrete Sampling Geometry NetCDF dataset,
        (with accomodations made so that it works as well for EPIC conventions)
        and bulk create in the database. Retain None values for bad coordinates.
        '''
        mtimes, depths, latitudes, longitudes = self._read_coords_from_ds(tindx, ac, multidim_trajectory=multidim_trajectory)
        self.logger.debug(f'Getting good_coords for {pnames}...')
        mtimes, depths, latitudes, longitudes, dup_times = zip(*self.good_coords(
                                        pnames, mtimes, depths, latitudes, longitudes, coords_equal))

        # Reassign meass with Measurement objects that have their id set
        try:
            meass, mask = self._bulk_load_coordinates(self._ips(mtimes), self._meass(
                                                      depths, longitudes, latitudes), 
                                                      dup_times, ac, axes)
        except (UniqueViolation, IntegrityError) as e:
            # Likely a realtime LRAUV load with a coord already loaded - add the dup to coords_equal
            self.logger.info(f"{e}: Trying _bulk_load_coordinates() again after _find_dup_coords()")
            coords_equal = self._find_dup_coords(self._ips(mtimes), self._meass(
                                                 depths, longitudes, latitudes), 
                                                 coords_equal)
            mtimes, depths, latitudes, longitudes, dup_times = zip(*self.good_coords(
                                        pnames, mtimes, depths, latitudes, longitudes, coords_equal))
            meass, mask = self._bulk_load_coordinates(self._ips(mtimes), self._meass(
                                                      depths, longitudes, latitudes), 
                                                      dup_times, ac, axes)

        return meass, dup_times, mask

    def _load_coords_from_instr_ds(self, tindx, ac):
        '''Pull time coordinate from Instrument (time-coordinate-only) NetCDF dataset (e.g. LOPC),
        lookup matching Measurment (containing depth, latitude, and longitude) and bulk create 
        Instantpoints and Measurements in the database.
        '''
        meass_nodups = []
        try:
            times = self.ds[ac[TIME]][tindx[0]:tindx[-1]:self.stride]
        except ValueError:
            self.logger.warn(f'Stride of {self.stride} likely greater than range of data: {tindx[0]}:{tindx[-1]}')
            self.logger.warn(f'Skipping load of {self.url}')
            return meass_nodups
    
        time_units = self.ds[ac[TIME]].units.lower().replace('utc', 'UTC')
        if self.ds[ac[TIME]].units == 'seconds since 1970-01-01T00:00:00Z':
            timeUnits = 'seconds since 1970-01-01 00:00:00'          # coards doesn't like ISO format
        mtimes = (from_udunits(mt, time_units) for mt in times)

        warn_secs_diff = 2
        noload_secs_diff = 70
        ips = []
        meass = []
        warn_count = 0
        noload_count = 0
        for mt in mtimes:
            try:
                ip, secs_diff = get_closest_instantpoint(self.associatedActivityName, mt, self.dbAlias)
            except ClosestTimeNotFoundException as e:
                self.logger.error('Could not find corresponding measurment for LOPC data measured at %s', mt)
            else:
                if secs_diff > noload_secs_diff:
                    noload_count += 1
                    self.logger.debug(f"{noload_count:3d}. LOPC data at {mt.strftime('%Y-%m-%d %H:%M:%S')} not loaded - more than "
                                      f"{noload_secs_diff} secs away from existing measurement: {secs_diff}")
                    continue
                if secs_diff > warn_secs_diff:
                    warn_count += 1
                    self.logger.debug(f"{warn_count:3d}. LOPC data at {mt.strftime('%Y-%m-%d %H:%M:%S')} more than "
                                     f"{warn_secs_diff} secs away from existing measurement: {secs_diff}")

                meass.append(Measurement.objects.using(self.dbAlias).get(instantpoint=ip))

        self.logger.warn(f"{noload_count} of {len(times)} original LOPC measurements not loaded because they "
                         f"were more than {noload_secs_diff} seconds away from an existing measurement")
        self.logger.warn(f"{warn_count} of {len(meass)} collected LOPC measurements were more than "
                         f"{noload_secs_diff} seconds away from an existing measurement")

        if not meass:
            return meass_nodups

        # Remove duplicates leaving the meass_nodups ordered in time
        duplicates_removed = -1
        meass_nodups.append(meass[0])
        last_meas = meass[0]
        for meas in meass:
            if meas.instantpoint.timevalue > last_meas.instantpoint.timevalue:
                meass_nodups.append(meas)
            else:
                duplicates_removed += 1
            last_meas = meas

        self.logger.info(f'{duplicates_removed} duplicate Measurements removed')

        return meass_nodups

    def _good_value_generator(self, pname, values):
        '''Generate good data values where bad values and nans are replaced consistently with None
        '''
        for value in values:
            if self.is_value_bad(pname, value):
                value = None

            yield value

    def _mask_data(self, vd, vm):
        # Yield only good values (not masked)
        good_count = 0
        for i, (v, m) in enumerate(zip(vd, vm)):
            if not m:
                yield v
                good_count += 1
            else:
                self.logger.debug(f"Removing bad data value at index {i}")
        if good_count == 0:
            self.logger.warning(f"No good data yielded. Coordinate values in {self.url} are likely bad.")

    def _meass_from_activity(self, add_to_activity, tindx, ac):
        '''Retreive Measurements from existing Activity and confirm that the coordinates
        are identical to what's in the netCDF we are loading from.  Initially developed
        for Dorado plankton_proxies data.
        '''
        meass = (Measurement.objects.using(self.dbAlias).filter(instantpoint__activity=add_to_activity)
                                                        .order_by('instantpoint__timevalue'))
        dup_times = [False] * meass.count()
        mask = [False] * meass.count()

        unequal_ti = unequal_de = unequal_la = unequal_lo = 0
        for count, (meas, mt, de, la, lo) in enumerate(zip(meass, *self._read_coords_from_ds(tindx, ac))):
            if meas.instantpoint.timevalue != mt:
                ti_msg = f"Existing timevalue ({meas.instantpoint.timevalue}) != mt ({mt}) at index {count}"
                self.logger.debug(ti_msg)
                unequal_ti += 1
                if unequal_ti == 1:
                    first_ti_msg = ti_msg
            if not np.isclose(meas.depth, de):
                de_msg = f"Existing depth ({meas.depth}) != de ({de}) at index {count}"
                self.logger.debug(de_msg)
                unequal_de += 1
            if not np.isclose(meas.geom.y, la):
                la_msg = f"Existing latitude ({meas.geom.y}) != la ({la}) at index {count}"
                self.logger.debug(la_msg)
                unequal_la += 1
            if not np.isclose(meas.geom.x, lo):
                lo_msg = f"Existing longitude ({meas.geom.x}) != lo ({lo}) at index {count}"
                self.logger.debug(lo_msg)
                unequal_lo += 1

        if unequal_ti:
            self.logger.error(f"Encountered {unequal_ti} unequal_ti when adding data from {self.url} to Activity {add_to_activity}")
            self.logger.error(f"First time mismatch: {first_ti_msg}")
            self.logger.error(f"Last time mismatch: {ti_msg}")

        return meass, dup_times, mask

    def load_trajectory(self, add_to_activity=None):
        '''Stream trajectory data directly from pydap proxies to generators fed to bulk_create() calls
        '''
        multidim_trajectory = False
        load_groups, coor_groups = self.get_load_structure()
        coords_equal_hash = {}
        if 'shore_i.nc' in self.url:
            try:
                # Variables from same NetCDF4 group in realtime LRAUV data have different axis names,
                # but same coord values. Find them to not load duplicate measurements.
                coords_equal_hash = self._equal_coords(load_groups, coor_groups)
            except ValueError as e:
                self.logger.warning(f"Skipping {self.url}: {e}")

        total_loaded = 0
        mask = []
        for axis_count, (k, pnames) in enumerate(load_groups.items()):
            ac = coor_groups[k]
            try:
                if len(self.ds[ac[TIME]].shape) == 2:
                    multidim_trajectory = True
                    # TODO: Deal with (as yet unseen) case where multiple trajectories exist in a netCDF file
                    tindx = self.getTimeBegEndIndices(self.ds[ac[TIME]][0][0])
                else:
                    tindx = self.getTimeBegEndIndices(self.ds[ac[TIME]])
            except (InvalidSliceRequest, NoValidData) as e:
                self.logger.warn(f"{e}")
                self.logger.warn(f'Failed to getTimeBegEndIndices() for axes {k} from {self.url}')
                continue

            for i, pname in enumerate(pnames):
                self.logger.debug(f'{i}, {pname}')
                if i == 0:
                    # First time through, bulk load the coordinates: instant_points and measurements
                    if DEPTH not in ac:
                        self.logger.warn(f'{self.param_by_key[pname]} does not have {DEPTH} in {ac}. Skipping.')
                        continue
                    if ac[DEPTH] not in self.ds and isinstance(ac[DEPTH], (int, float)):
                        # Likely u and v parameters from nemesis glider data where there is no depth_uv coordinate in the NetCDF
                        self.logger.info(f'{self.param_by_key[pname]} does not have {DEPTH} in {self.url}.')
                        self.logger.info(f'ac[DEPTH] = {ac[DEPTH]}. Assume that this depth coordinate was provided in auxCoords')
                        self.logger.info(f'Loading coordinates for axes {k}')
                        meass, dup_times, mask = self._load_coords_from_dsg_ds(tindx, ac, pnames, k, multidim_trajectory=multidim_trajectory)
                    elif ac[DEPTH] in self.ds and ac[LATITUDE] in self.ds and ac[LONGITUDE] in self.ds:
                        try:
                            # Expect CF Discrete Sampling Geometry or EPIC dataset
                            self.logger.info(f'Loading coordinates for axes {k}')
                            if coords_equal_hash == {}:
                                if add_to_activity:
                                    meass, dup_times, mask = self._meass_from_activity(add_to_activity, tindx, ac)
                                else:
                                    meass, dup_times, mask = self._load_coords_from_dsg_ds(tindx, ac, pnames, k)
                            else:
                                meass, dup_times, mask = self._load_coords_from_dsg_ds(tindx, ac, pnames, k, coords_equal_hash[k])
                        except CoordNotEqual as e:
                            self.logger.exception(e)
                            sys.exit(-1)
                        except ValueError as e:
                            # Likely ValueError: not enough values to unpack (expected 5, got 0) from good_coords()
                            self.logger.debug(str(e))
                            self.logger.warn(f'No good coordinates for {pname} - skipping it')
                            continue
                        except OverflowError as e:
                            # Likely unable to convert a udunit to a value as in time from:
                            # http://legacy.cencoos.org:8080/thredds/dodsC/gliders/Line66/Nemesis/nemesis_201705/nemesis_20170518T203246_rt0.nc.ascii?time[149:1:149]
                            # = -4.31865376e+107  (should be a value like 1.495143822559231E9)
                            self.logger.debug(str(e))
                            self.logger.warn(f'OverflowError when converting coordinates for {pname} - skipping it')
                            return total_loaded
                    else:
                        # Expect instrument (time-coordinate-only) dataset
                        self.logger.warn(f'{pname} has no {ac[DEPTH]} coordinate - processing as time-coordinate-only, e.g. LOPC')
                        meass = self._load_coords_from_instr_ds(tindx, ac)
                else:
                    # Parameters after the first one
                    if k in coords_equal_hash:
                        if coords_equal_hash[k].all():
                            # For follow-on Parameters using same axes, pass in equal coordinates boolean array
                            meass, dup_times, mask = self._load_coords_from_dsg_ds(tindx, ac, pnames, k, coords_equal_hash[k])
                        else:
                            # Load Parameter one element at a time - the old fashioned (slower) way
                            self.logger.warning(f"Parameter {pname} does not share the same coordinates of previously loaded Parameters, skipping for now.")
                            self.logger.debug(f"coords_equal_hash[{k}] = {coords_equal_hash[k]}")
                            continue
                            # TODO: Implement one element at a time loader method
                try:
                    if isinstance(self.ds[pname], pydap.model.GridType):
                        constraint_string = f"(GridType) using python slice: ds['{pname}']['{pname}'][{tindx[0]}:{tindx[-1]}:{self.stride}]"
                        values = self.ds[pname][pname].data[tindx[0]:tindx[-1]:self.stride]
                    elif multidim_trajectory:
                        self.logger.info(f"(multidim) loading {pname} from multidimensional trajectory file")
                        constraint_string = f"using python slice: ds['{pname}'][0][0][{tindx[0]}:{tindx[-1]}:{self.stride}]"
                        # TODO: Deal with (as yet unseen) case where multiple trajectories exist in a netCDF file
                        values = self.ds[pname].data[0][0][tindx[0]:tindx[-1]:self.stride]
                    else:
                        constraint_string = f"(default) using python slice: ds['{pname}'][{tindx[0]}:{tindx[-1]}:{self.stride}]"
                        values = self.ds[pname].data[tindx[0]:tindx[-1]:self.stride]
                except ValueError:
                    self.logger.warn(f'Stride of {self.stride} likely greater than range of data: {tindx[0]}:{tindx[-1]}')
                    self.logger.warn(f'Skipping load of {self.url}')
                    return total_loaded

                # Test whether we need to make values iterable
                try:
                    self.logger.debug(f"len(values) = {len(values)}")
                except TypeError:
                    # Likely values is a single valued array, e.g. nemesis u, v data
                    values = [float(values)]

                if mask:
                    # Mask the values and dup_times where coordinates are bad
                    # Need values as a list() because of LOPC test below
                    values = list(self._mask_data(values, mask))
                    if not values:
                        self.logger.warning(f'Coordinates likely bad - check them here:')
                        self.logger.warning(f"Depth data: {self.url}.ascii?{ac[DEPTH]}[{tindx[0]}:{self.stride}:{tindx[-1] - 1}]")
                        self.logger.warning(f"Latitude data: {self.url}.ascii?{ac[LATITUDE]}[{tindx[0]}:{self.stride}:{tindx[-1] - 1}]")
                        self.logger.warning(f"Longitude data: {self.url}.ascii?{ac[LONGITUDE]}[{tindx[0]}:{self.stride}:{tindx[-1] - 1}]")
                        return total_loaded

                self.logger.info(f"Time data: {self.url}.ascii?{ac[TIME]}[{tindx[0]}:{self.stride}:{tindx[-1] - 1}]")
                if hasattr(values[0], '__iter__'):
                    # For data like LOPC data - expect all values to be non-nan, load array and the sum of it
                    self.param_by_key[pname].description = 'Sum of counts saved in datavalue, spectrum of counts saved in dataarray'
                    self.param_by_key[pname].save(using=self.dbAlias)
                    mps = (MeasuredParameter(measurement=me, parameter=self.param_by_key[pname], 
                                                dataarray=list(va), datavalue=sum(va)) 
                                                for me, va in zip(meass, values))
                else:
                    # Need to bulk_create() all values, set bad ones to None and remove them after insert
                    values = self._good_value_generator(pname, values)
                    mps = (MeasuredParameter(measurement=me, parameter=self.param_by_key[pname], 
                                                datavalue=va) for me, va, dt in zip(
                                                meass, values, dup_times) if not dt)

                # All items but meass are generators, so we can call len() on it
                self.logger.info(f'Bulk loading {len(meass)} {self.param_by_key[pname]} datavalues into MeasuredParameter {constraint_string} with batch_size = {BATCH_SIZE}')
                mps = self._measuredparameter_with_measurement(meass, mps)
                mps = MeasuredParameter.objects.using(self.dbAlias).bulk_create(mps, batch_size=BATCH_SIZE)
                self.parameter_counts[self.param_by_key[pname]] = len(mps)
                total_loaded += len(mps)

        return total_loaded

    def _convert_EPIC_times(self, times, tindx):
        # Create COARDS time from EPIC data
        time2s = self.ds['time2']['time2'].data[tindx[0]:tindx[-1]:self.stride]
        time_units = 'seconds since 1970-01-01 00:00:00'
        epoch_seconds = []
        for jd, ms in zip(times, time2s):
            gcal = jd2gcal(jd - 0.5, ms / 86400000.0)
            try:
                gcal_datetime = datetime(*gcal[:3]) + timedelta(days=gcal[3])
            except ValueError as e:
                # Encountered this error after removing start & end times for the load on this dataset:
                # http://dods.mbari.org/opendap/data/CCE_Archive/MS3/20151005/Aquadopp2000/MBCCE_MS3_Aquadopp2000_20151005.nc.ascii?time[93900:1:94100]
                self.logger.debug(f"{e} in {self.url}")

            epoch_seconds.append(to_udunits(gcal_datetime, time_units))

        return epoch_seconds, time_units

    def load_timeseriesprofile(self):
        '''Stream timeseriesprofile data directly from pydap proxies to generators fed to bulk_create() calls.
        Used also for timeseries data.
        '''
        time_axes_loaded = set()
        depth_axes_loaded = set()
        load_groups, coor_groups = self.get_load_structure()
        for k, pnames in load_groups.items():
            ac = coor_groups[k]
            total_loaded = 0   
            for i, pname in enumerate(pnames):
                if i == 0:
                    # First time through, bulk load the coordinates: instant_points and measurements
                    # As all pnames share the same coordinates we can use pnames[0] to access them
                    firstp = pnames[0]

                    if ac[TIME] != list(self.ds[firstp].keys())[1]:
                        # Gratuitous check 
                        self.logger.warn("Auxillary time coordinate '{ac[TIME]}' != first COARDS"
                                         "coordnate '{list(self.ds[firstp].keys())[1]}'")

                    # CF (nee COARDS) has tzyx coordinate ordering, time is at index [1] and depth is at [2]
                    # - times: Assume CF/COARDS, override if EPIC data detected
                    tindx = self.getTimeBegEndIndices(self.ds[list(self.ds[firstp].keys())[1]])
                    try:
                        times = self.ds[list(self.ds[firstp].maps.keys())[0]].data[tindx[0]:tindx[-1]:self.stride]
                    except ValueError as e:
                        # Likely 'not enough values to unpack' because of self.stride exceeding range
                        self.logger.warn(f"{e}. Stride value of {self.stride} is likely too high.")
                        self.logger.warn(f"Skipping all parameters in coor_group {ac}")
                        continue
                    time_units = self.ds[list(self.ds[firstp].maps.keys())[0]].units.lower()

                    if time_units == 'true julian day': # pragma: no cover
                        times, time_units = self._convert_EPIC_times(times, tindx)

                    time_units = time_units.replace('utc', 'UTC')           # coards requires UTC in uppercase
                    if self.ds[list(self.ds[firstp].maps.keys())[0]].units == 'seconds since 1970-01-01T00:00:00Z':
                        time_units = 'seconds since 1970-01-01 00:00:00'    # coards 1.0.4 and earlier doesn't like ISO format

                    mtimes = [from_udunits(mt, time_units) for mt in times]

                    # 1. - depths: first by CF/COARDS coordinate rules, then by EPIC conventions
                    nomDepths = None
                    nomLat = None
                    nomLon = None
                    try:
                        depths = self.ds[list(self.ds[firstp].maps.keys())[1]].data[:]   # TODO lookup more precise depth from conversion from pressure
                    except IndexError:
                        self.logger.warn(f'Variable {firstp} has less than 2 coordinates: {self.ds[pname].keys()}')
                        depths = np.array([])

                    # If data aren't COARDS then index 2 will not be depths, but could be latitude, detect by testing length & auxCoords
                    if len(depths) == 1 and 'depth' not in ac:
                        try:
                            self.logger.info('Attempting to set nominal depth from EPIC Convention sensor_depth variable attribute')
                            depths = np.array([self.ds[firstp].attributes['sensor_depth']])
                        except KeyError:
                            self.logger.info('Variable %s does not have a sensor_depth attribute', firstp)
                    elif not depths.any():
                        self.logger.warn('Depth coordinate not found at index [2]. Looking for nominal position from EPIC Convention global attributes.')
                        try:
                            depths = np.array([float(self.ds.attributes['NC_GLOBAL']['nominal_instrument_depth'])])
                            nomLat = self.ds.attributes['NC_GLOBAL']['latitude']
                            nomLon = self.ds.attributes['NC_GLOBAL']['longitude']
                        except KeyError:
                            self.logger.warn('EPIC nominal position not found in global attributes. Assigning from variables (and maybe variable attribute).')
                            if 'depth' in self.ds:
                                if not hasattr(self.ds['depth'].data[0], '__iter__'):
                                    depths = np.array([self.ds['depth'].data[0]])
                            if 'nominal_instrument_depth' in self.ds[firstp].attributes:
                                nomDepths = self.ds[firstp].attributes['nominal_instrument_depth']
                            if 'lat' in self.ds:
                                nomLat = self.ds['lat'].data[0][0]
                            if 'lon' in self.ds:
                                nomLon = self.ds['lon'].data[0][0]

                    if nomDepths and nomLat and nomLon:
                        pass
                    elif depths.any() and nomLat and nomLon:
                        self.logger.info('Nominal position assigned from EPIC Convention global attributes')
                        nomDepths = depths
                    elif depths.any():
                        self.logger.info('Nominal depth assigned from EPIC Convention variable attributes')
                        nomDepths = depths
                        nom_loc = self.getNominalLocation()
                        nomLat, nomLon = nom_loc[1][firstp], nom_loc[2][firstp]
                    else:
                        # Possible to have both precise and nominal locations with this approach
                        nom_loc = self.getNominalLocation()
                        nomDepths, nomLat, nomLon = nom_loc[0][firstp], nom_loc[1][firstp], nom_loc[2][firstp]

                    # Ensure that nomDepths is a numpy array
                    if not hasattr(nomDepths, '__iter__'):
                        nomDepths = np.array([nomDepths])
                    try:
                        _ = nomDepths.any()
                    except AttributeError:
                        nomDepths = np.array(nomDepths)

                    # 2 & 3. - latitudes & longitudes: first by CF/COARDS coordinate rules, then by EPIC conventions
                    shape_length = self.get_shape_length(firstp)
                    if shape_length == 4:
                        self.logger.info('%s has shape of 4, assume that singleton dimensions are used for nominal latitude and longitude', firstp)
                        # Would like all data set to have COARDS coordinate ordering, but they don't
                        # - http://dods.mbari.org/opendap/data/CCE_Archive/MS1/20151006/TU65m/MBCCE_MS1_TU65m_20151006.nc.html - has COARDS ordering
                        # - http://dods.mbari.org/opendap/data/CCE_Archive/MS2/20151005/ADCP300/MBCCE_MS2_ADCP300_20151005.nc - does not have COARDS ordering!
                        if ac['latitude'] in self.ds[ac['latitude']]:
                            # Precise GPS latitude positions
                            latitudes = self.ds[ac['latitude']][ac['latitude']].data[:]
                        else:
                            latitudes = float(self.ds[list(self.ds[firstp].maps.keys())[2]].data[0])

                        if ac['longitude'] in self.ds[ac['longitude']]:
                            # Precise GPS longitude positions
                            longitudes = self.ds[ac['longitude']][ac['longitude']].data[:]
                        else:
                            longitudes = float(self.ds[list(self.ds[firstp].maps.keys())[3]].data[0])

                    elif shape_length == 3 and 'EPIC' in self.ds.attributes['NC_GLOBAL']['Conventions'].upper(): # pragma: no cover
                        # Special fix for USGS EPIC ADCP variables missing depth coordinate, but having nominal sensor depth metadata
                        # - http://dods.mbari.org/opendap/data/CCE_Archive/MS1/20151006/ADCP300/MBCCE_MS1_ADCP300_20151006.nc - does not have COARDS ordering!
                        latitudes = float(self.ds[list(self.ds[firstp].maps.keys())[1]].data[0])      # TODO lookup more precise gps lat via coordinates pointing to a vector
                        longitudes = float(self.ds[list(self.ds[firstp].maps.keys())[2]].data[0])     # TODO lookup more precise gps lon via coordinates pointing to a vector
                        depths = nomDepths
                    elif shape_length == 2:
                        self.logger.info('%s has shape of 2, assuming no latitude and longitude singletime'
                                    ' dimensions. Using nominal location read from auxillary coordinates', firstp)
                        longitudes = nomLon
                        latitudes = nomLat
                    elif shape_length == 1:
                        self.logger.info('%s has shape of 1, assuming no latitude, longitude, and'
                                    ' depth singletime dimensions. Using nominal location read'
                                    ' from auxially coordinates', firstp)
                        longitudes = nomLon
                        latitudes = nomLat
                        depths = nomDepths
                    else:
                        raise Exception('{} has shape of {}. Can handle only shapes of 2, and 4'.format(firstp, shape_length))

                    if hasattr(latitudes, '__iter__') and hasattr(longitudes, '__iter__'):
                        # We have precise gps positions, a location for each time value
                        points = []
                        for i, (lo, la) in enumerate(zip(longitudes, latitudes)):
                            if (lo == self.ds[ac['longitude']].attributes['_FillValue'] or
                                lo == self.ds[ac['longitude']].attributes['missing_value'] or
                                la == self.ds[ac['latitude']].attributes['_FillValue'] or
                                la == self.ds[ac['latitude']].attributes['missing_value']):
                                self.logger.debug(f"Not using missing or fill value at index {i}: lo, la = {lo}, {la}")
                            else:
                                points.append(Point(lo, la))
                    else:
                        if abs(latitudes) > 90:
                            # Brute-force fix for non-COARDS ordering, swap the coordinates
                            self.logger.info('%s appears to not have COARDS ordering of coordinate dimensions, swapping them', firstp)
                            tmp_var = latitudes
                            latitudes = longitudes
                            longitudes = tmp_var

                        self.logger.debug(f"Making points list from {(longitudes, latitudes)} for each {len(list(mtimes))} mtimes")
                        points = [Point(float(longitudes), float(latitudes)) for i in range(len(list(mtimes)))]

                    # Need a set of points for all the timeseriesprofile depths
                    points = points * len(list(depths))

                    ips = (InstantPoint(activity=self.activity, timevalue=mt) for mt in mtimes)
                    try:
                        self.logger.info(f'Calling bulk_create() for InstantPoints in ips generator for firstp = {firstp} with batch_size = {BATCH_SIZE}')
                        ips = InstantPoint.objects.using(self.dbAlias).bulk_create(ips, batch_size=BATCH_SIZE)
                    except (IntegrityError, psycopg2.IntegrityError) as e:
                        self.logger.info(f"Time axis '{ac[TIME]}' likely has timevalues already loaded from an axis in {time_axes_loaded}")
                        self.logger.info(f'Getting matching InstantPoints from the database, creating new ones not yet there.')
                        ips_new = []
                        num_created = 0
                        for ip in (InstantPoint(activity=self.activity, timevalue=mt) for mt in mtimes):
                            ip_db, created = InstantPoint.objects.using(self.dbAlias).get_or_create(
                                            activity=self.activity, timevalue=ip.timevalue)
                            if created:
                                num_created += 1

                            ips_new.append(ip_db) 

                        ips = ips_new 
                        self.logger.info(f'Got {len(ips) - num_created} InstantPoints from the database, created {num_created} new ones')
                       
                        if not ips: 
                            self.logger.error(f'Unable to load load InstantPoints for axis {ac[TIME]}. Exiting.')
                            self.logger.exception(f"Maybe you should delete Activity '{self.activity.name}' first?")
                            sys.exit(-1)

                    # TIME axes are commonly shared amongst variables on different grids in timeseriesprofile data
                    # Keep track of axis names for use in logger info messages
                    time_axes_loaded.add(ac[TIME])

                    if nomLon and nomLat:
                        nom_point = Point(float(nomLon), float(nomLat))

                    # Expect that nomDepths is a numpy array, even it is single-valued
                    if nomDepths.any() and nom_point:
                        nls = []
                        for nd in nomDepths:
                            nl, _ = NominalLocation.objects.using(self.dbAlias).get_or_create(
                                        depth=repr(nd), geom=nom_point, activity=self.activity)
                            nls.append(nl)
                    else:
                        nls = [None] * len(list(depths))

                    meass = []
                    for ip in ips:
                        for de, po, nl in zip(depths, points, nls):
                            if self.is_coordinate_bad(firstp, ip.timevalue, de):
                                self.logger.warn(f'Bad coordinate: {ip}, {de}')
                            meass.append(Measurement(depth=repr(de), geom=po, instantpoint=ip, nominallocation=nl))

                    try:
                        self.logger.info(f'Calling bulk_create() for {len(meass)} Measurements with batch_size = {BATCH_SIZE}')
                        meass = Measurement.objects.using(self.dbAlias).bulk_create(meass, batch_size=BATCH_SIZE)
                    except (IntegrityError, psycopg2.IntegrityError) as e:
                        self.logger.info(f"Depth axis '{ac[DEPTH]}' likely has depths already loaded from an axis in {depth_axes_loaded}")
                        self.logger.info(f'Getting matching Measurements from the database, creating new ones not yet there.')
                        meass_new = []
                        num_created = 0
                        for meas in meass:
                            meas_db, created = Measurement.objects.using(self.dbAlias).get_or_create(
                                            instantpoint=meas.instantpoint, depth=meas.depth, 
                                            geom=meas.geom, nominallocation=meas.nominallocation) 
                            if created:
                                num_created += 1

                            meass_new.append(meas_db) 

                        meass = meass_new
                        self.logger.info(f'Got {len(meass) - num_created} Measurements from the database, created {num_created} new ones')

                        if not meass:
                            self.logger.error(f'Unable to load load Measurements for axis {ac[DEPTH]}. Exiting.')
                            self.logger.exception(f"Maybe you should delete Activity '{self.activity.name}' first?")
                            sys.exit(-1)

                    # DEPTH axes are commonly shared amongst variables on different grids in timeseriesprofile data
                    # Keep track of axis names for use in logger info messages
                    if DEPTH in ac:
                        depth_axes_loaded.add(ac[DEPTH])

                # End if i == 0 (loading coords for list of pnames)
 
                constraint_string = f"using python slice: ds['{pname}']['{pname}'][{tindx[0]}:{tindx[-1]}:{self.stride}]"
                try:
                    values = self.ds[pname][pname].data[tindx[0]:tindx[-1]:self.stride]
                except ValueError as e:
                    # Likely 'not enough values to unpack' because of self.stride exceeding range
                    self.logger.warn(f"{e}. Stride value of {self.stride} is likely too high.")
                    self.logger.warn(f"Skipping all parameters in coor_group {ac}")
                    continue
                if len(values.shape) == 1:
                    self.logger.info("len(values.shape) = 1; likely EPIC timeseries data - reshaping to add a 'depth' dimension")
                    values = values.reshape(values.shape[0], 1)

                # Need to bulk_create() all values, set bad ones to None and remove them after insert
                values = self._good_value_generator(pname, values.flatten())
                mps = (MeasuredParameter(measurement=me, parameter=self.param_by_key[pname], 
                                                datavalue=va) for me, va in zip(meass, values))

                # All items but mess are generators, so we can call len() on it
                self.logger.info(f'Bulk loading {len(meass)} {self.param_by_key[pname]} datavalues into MeasuredParameter {constraint_string} with batch_size = {BATCH_SIZE}')
                self.logger.info(f"Time data: {self.url}.ascii?{ac[TIME]}[{tindx[0]}:{self.stride}:{tindx[-1] - 1}]")
                mps = MeasuredParameter.objects.using(self.dbAlias).bulk_create(mps, batch_size=BATCH_SIZE)
                total_loaded += len(mps)

        return total_loaded

    def _measurement_with_instantpoint(self, ips, meass):
        for ip, meas in zip(ips, meass):
            meas.instantpoint = ip
            yield meas
       
    def _bulk_load_coordinates(self, ips, meass, dup_times, ac, axes):

        self.logger.info(f'Calling bulk_create() for InstantPoints in ips generator')
        # Create mask array in case any coordinate is None, so that we can know which MPs to bulk_create()
        mask = []
        ips_to_load = []
        meas_to_load = []
        for ip, meas, dt in zip(ips, meass, dup_times):
            if not ip or not meas or dt:
                mask.append(True)
            else:
                mask.append(False)
                ips_to_load.append(ip)
                meas_to_load.append(meas)
       
        try:
            self.ips = InstantPoint.objects.using(self.dbAlias).bulk_create(ips_to_load, batch_size=BATCH_SIZE)
        except IntegrityError as e:
            # Some data sets (e.g. Waveglider) share time coordinates with different depths
            # Report the reuse of previous self.ips values
            if hasattr(self, 'ips'):
                self.logger.info(f"Duplicate time values for axes {axes}. Reusing previously loaded time values for {ac['time']}")
            else:
                self.logger.error(f"{e}")
                self.logger.error(f"It's likely that the {ac['time']} variable in {self.url} has a duplicate value")
                raise DuplicateData(f"Duplicate data from {self.url} in {self.dbAlias}")

        meass = self._measurement_with_instantpoint(self.ips, meas_to_load)

        self.logger.info(f'Calling bulk_create() for Measurements in meass generator with batch_size = {BATCH_SIZE}')
        meass = Measurement.objects.using(self.dbAlias).bulk_create(meass, batch_size=BATCH_SIZE)

        return meass, mask

    def _measuredparameter_with_measurement(self, meass, mps):
        for meas, mp in zip(meass, mps):
            mp.measurement = meas
            yield mp

    def _delete_bad_datavalues(self, pname):
        num, _ = (MeasuredParameter.objects.using(self.dbAlias)
                    .filter(parameter__name=pname, datavalue=np.nan).delete())
        if num:
            self.logger.info(f'Deleted {num} nan {pname} MeasuredParameters')
        num, _ = (MeasuredParameter.objects.using(self.dbAlias)
                    .filter(parameter__name=pname, datavalue=np.inf).delete())
        if num:
            self.logger.info(f'Deleted {num} inf {pname} MeasuredParameters')

    def _post_process_updates(self, mps_loaded, featureType='', add_to_activity=None):

        #
        # Query database to a path for trajectory or stationPoint for timeSeriesProfile and timeSeries
        #
        stationPoint = None
        path = None
        if add_to_activity:
            self.activity = add_to_activity
        if not hasattr(self, 'activity') and hasattr(self, 'associatedActivityName'):
            self.activity = Activity.objects.using(self.dbAlias).get(name=self.associatedActivityName)

        linestringPoints = Measurement.objects.using(self.dbAlias).filter(instantpoint__activity=self.activity
                                                       ).order_by('instantpoint__timevalue').values_list('geom')
        try:
            path = LineString([p[0] for p in linestringPoints]).simplify(tolerance=.001)
        except (TypeError, ValueError) as e:
            # Likely "LineString requires at least 2 points, got 1."
            self.logger.warn('%s', e)
            self.logger.info('Leaving path set to None')
        else:
            if len(path) == 2:
                self.logger.info("Length of path = 2: path = %s", path)
                if path[0][0] == path[1][0] and path[0][1] == path[1][1]:
                    self.logger.info("And the 2 points are identical. Saving the first point of this"
                                " path as a point as the featureType is also %s.", featureType)
                    stationPoint = Point(path[0][0], path[0][1])
                    path = None
            else:
                # Use NominalLocation - for cases when we have precise GPS locations
                lon = set([p.x for p in NominalLocation.objects.using(self.dbAlias)
                                        .filter(activity=self.activity)
                                        .values_list('geom', flat=True)])
                lat = set([p.y for p in NominalLocation.objects.using(self.dbAlias)
                                        .filter(activity=self.activity)
                                        .values_list('geom', flat=True)])
                if lon and lat:
                    if len(lon) != 1 or len(lat) != 1:
                        self.logger.error(f"For activity={self.activity} length of nominal latitudes and longitudes != 1")
                    else:
                        stationPoint = Point(lon.pop(), lat.pop())

        # Add additional Parameters for all appropriate Measurements
        self.logger.info("Adding SigmaT and Spiciness to the Measurements...")
        self.addSigmaTandSpice(self.activity)

        if self.grdTerrain and 'netcdf_proxies' not in self.url:
            self.logger.info("Adding altitude to the Measurements...")
            try:
                self.addAltitude(self.activity)
            except FileNotFound as e:
                self.logger.warn(str(e))

        # Bulk loading of stoqs calculated values may introduce NaNs, remove them
        for pname in (SIGMAT, SPICE, ALTITUDE):
            self._delete_bad_datavalues(pname)

        # Update the Activity with information we now have following the load
        try:
            varList = ', '.join(set(list(self.ds.keys())) & set(self.varsLoaded))
        except AttributeError:
            # ROVCTDloader creates self.vSeen dictionary with counts of each parameter
            varList = ', '.join(list(self.vSeen.keys()))

        # Construct a meaningful comment that looks good in the UI Metadata->NetCDF area
        if hasattr(self, 'add_to_activity'):
            act_to_update = Activity.objects.using(self.dbAlias).get(id=self.add_to_activity.id)
            load_comment = f"{act_to_update.comment} - Loaded variables {varList} from {self.url}"
            load_comment += f" (added to Activity {self.add_to_activity.name})"
        elif hasattr(self, 'associatedActivityName'):
            act_to_update = Activity.objects.using(self.dbAlias).get(name=self.associatedActivityName)
            load_comment = f"{act_to_update.comment} - Loaded variables {varList} from {self.url}"
            load_comment += f" (added to Activity {self.associatedActivityName})"
        else:
            act_to_update = Activity.objects.using(self.dbAlias).get(id=self.activity.id)
            load_comment = f"Loaded variables {varList} from {self.url}"

        if hasattr(self, 'requested_startDatetime') and hasattr(self, 'requested_endDatetime'):
            if self.requested_startDatetime and self.requested_endDatetime:
                load_comment += f" between {self.requested_startDatetime} and {self.requested_endDatetime}"
        load_comment += f" with a stride of {self.stride} on {str(datetime.utcnow()).split('.')[0]}Z "

        self.logger.debug("Updating its comment with load_comment = %s", load_comment)
        if hasattr(self, 'add_to_activity') or hasattr(self, 'associatedActivityName'):
            num_updated = Activity.objects.using(self.dbAlias).filter(id=act_to_update.id).update(
                            comment=load_comment,
                            num_measuredparameters=mps_loaded + act_to_update.num_measuredparameters)
        else:
            num_updated = Activity.objects.using(self.dbAlias).filter(id=act_to_update.id).update(
                            name=self.getActivityName(),
                            comment=load_comment,
                            maptrack=path,
                            mappoint=stationPoint,
                            num_measuredparameters=mps_loaded,
                            loaded_date=datetime.utcnow())
        self.logger.debug("%d activitie(s) updated with new attributes.", num_updated)

        #
        # Add resources after loading data to capture additional metadata that may be added
        #
        try:
            self.addResources()
        except IntegrityError as e:
            self.logger.error('Failed to properly addResources: %s', e)

        # 
        # Update the stats and store simple line values
        #
        self.updateActivityMinMaxDepth(act_to_update)
        self.updateActivityParameterStats(act_to_update)
        self.updateCampaignStartEnd()
        self.assignParameterGroup(groupName=MEASUREDINSITU)
        if featureType == TRAJECTORY:
            if hasattr(self, 'critSimpleDepthTime'):
                # Loader may have this attribute set, e.g. for BED that need less simplification
                self.insertSimpleDepthTimeSeries(critSimpleDepthTime=self.critSimpleDepthTime)
            else: 
                self.insertSimpleDepthTimeSeries()
            self.saveBottomDepth()
            self.insertSimpleBottomDepthTimeSeries()
        elif featureType == TIMESERIES or featureType == TIMESERIESPROFILE:
            self.insertSimpleDepthTimeSeriesByNominalDepth()
        elif featureType == TRAJECTORYPROFILE:
            self.insertSimpleDepthTimeSeriesByNominalDepth(trajectoryProfileDepths=self.timeDepthProfiles)
        self.logger.info("Data load complete, %d records loaded.", mps_loaded)

        return path


    def process_trajectory_values_from_generator(self, data_generator): 
        '''Use original method to load a MeasuredParameter datavalue a value
        at a time into the database. Works only for featureType='trajectory'.
        '''

        self.initDB()

        path = None
        last_key = None
        self.param_by_key = {}
        self.parameter_counts = defaultdict(lambda: 0)
        featureType='trajectory'
        mps_loaded = 0
        for row in data_generator():
            row = self.preProcessParams(row)
            (longitude, latitude, mtime, depth) = (
                            row.pop('longitude'),
                            row.pop('latitude'),
                            from_udunits(row.pop('time'), row.pop('timeUnits')),
                            row.pop('depth'))


            key, value = list(row.items()).pop()
            value = float(value)
            if key != last_key:
                logger.info(f'Loading values for Parameter {key}')
            last_key = key

            point = Point(longitude, latitude)

            self.param_by_key[key] = self.getParameterByName(key)
            self.parameter_counts[self.param_by_key[key]] += 1

            ip,_ = InstantPoint.objects.using(self.dbAlias).get_or_create(
                                        activity=self.activity, timevalue=mtime)
            meas,_ = Measurement.objects.using(self.dbAlias).get_or_create(
                                        instantpoint=ip, geom=point, depth=depth)
            mp = MeasuredParameter(measurement=meas, 
                                        parameter=self.param_by_key[key], datavalue=value)

            mp.save(using=self.dbAlias)
            mps_loaded += 1

        self.totalRecords = self.getTotalRecords()
        path = self._post_process_updates(mps_loaded, featureType)

        return mps_loaded, path, self.parameter_counts

    def process_data(self, featureType='', add_to_activity=None): 
        '''Bulk copy measurement data into database
        '''

        self.coord_dicts = {}
        for v in self.include_names:
            try:
                self.coord_dicts[v] = self.getAuxCoordinates(v)
            except ParameterNotFound as e:
                self.logger.debug(str(e))
            except VariableHasBadCoordinatesAttribute as e:
                self.logger.error(str(e))

        self.initDB()

        path = None
        parmCount = {}
        self.parameter_counts = {}
        for key in self.include_names:
            parmCount[key] = 0

        if getattr(self, 'command_line_args', False):
            if self.command_line_args.append:
                self.dataStartDatetime = (InstantPoint.objects.using(self.dbAlias)
                                            .filter(activity__name=self.getActivityName())
                                            .aggregate(Max('timevalue'))['timevalue__max'])

        self.param_by_key = {}
        self.mv_by_key = {}
        self.fv_by_key = {}

        for key in (set(self.include_names) & set(self.ds.keys())):
            parameter_name, _ = self.parameter_name(key)
            self.param_by_key[key] = self.getParameterByName(parameter_name)
            self.parameter_counts[self.param_by_key[key]] = 0

        for key in self.ds.keys():
            self.mv_by_key[key] = self.getmissing_value(key)
            self.fv_by_key[key] = self.get_FillValue(key)

        self.logger.info("From: %s", self.url)
        if featureType:
            featureType = featureType.lower()
        else:
            featureType = self.getFeatureType()

        mps_loaded = 0
        try:
            if featureType== TRAJECTORY:
                mps_loaded = self.load_trajectory(add_to_activity=add_to_activity)
            elif featureType == TIMESERIES:
                mps_loaded = self.load_timeseriesprofile()
            elif featureType == TIMESERIESPROFILE:
                mps_loaded = self.load_timeseriesprofile()
            elif featureType == TRAJECTORYPROFILE:
                self.logger.warn(f"Loader for featureType {featureType} has not yet been implemented")
            else:
                raise Exception(f"Global attribute 'featureType' is not one of '{TRAJECTORY}',"
                        " '{TIMESERIES}', or '{TIMESERIESPROFILE}' - see:"
                        " http://cf-pcmdi.llnl.gov/documents/cf-conventions/1.6/ch09.html")
            self.totalRecords = mps_loaded
        except (IntegrityError, DuplicateData) as e:
            # Likely duplicate key value violates unique constraint "stoqs_measuredparameter_measurement_id_parameter_1328c3fb_uniq"
            # Can't append data from source with bulk_create(), give appropriate warning
            self.logger.exception(str(e))
            self.logger.error(f'Failed to bulk_create() data from URL: {self.url}')
            self.logger.error(f'If you need to load data that has been appended to the URL then delete its Activity before loading.')

            return mps_loaded, path, parmCount
        except KeyError as e:
            # Likely an include_name variable has a bad coordinates attribute, give a better error message than just KeyError
            self.logger.exception(str(e))
            self.logger.error(f'Failed to bulk_create() data from URL: {self.url}')

            return mps_loaded, path, parmCount

        if mps_loaded:
            # Bulk loading may introduce None values, remove them
            MeasuredParameter.objects.using(self.dbAlias).filter(datavalue=None, dataarray=None).delete()

            # Removing Nones above may leave a Parameter without any MeasuredParameters, remove them
            for parameter in self.parameter_counts.copy().keys():
                mp_count = MeasuredParameter.objects.using(self.dbAlias).filter(parameter=parameter).count()
                self.logger.info(f"{parameter.name:40} count: {mp_count:6}")
                if mp_count == 0:
                    self.logger.info(f"Deleting Parameter because it has no valid data: {parameter}")
                    try:
                        del parmCount[parameter.name.split(' ')[0]]
                        del self.parameter_counts[parameter]
                        del self.parameter_dict[parameter.name]
                    except KeyError as e:
                        self.logger.warning(f"{e} not from Activity {self.activity}")
                    parameter.delete(using=self.dbAlias)
                else:
                    parmCount[parameter.name.split(' ')[0]] = mp_count
            path = self._post_process_updates(mps_loaded, featureType, add_to_activity=add_to_activity)

        return mps_loaded, path, parmCount


class Trajectory_Loader(Base_Loader):
    '''
    Generic loader for trajectory data.  May be subclassed if special data or metadata processing 
    is needed for a particular kind of trajectory data.
    '''
    include_names = ['temperature', 'conductivity']

    def preProcessParams(self, row):
        '''
        Compute on-the-fly any additional parameters for loading into the database
        '''
        # Compute salinity if it's not in the record and we have temperature, conductivity, and pressure
        ##if row.has_key('temperature') and row.has_key('pressure') and row.has_key('latitude'):
        ##  conductivity_ratio = row['conductivity'] / 
        ##  row['salinity'] = sw.salt(conductivity_ratio, sw.T90conv(row['temperature']), row['pressure'])

        # TODO: Compute sigma-t if we have standard_names of sea_water_salinity, sea_water_temperature and sea_water_pressure

        # TODO: Lookup bottom depth here and create new bottom depth and altitude parameters...

        return super(Trajectory_Loader, self).preProcessParams(row)


class Dorado_Loader(Trajectory_Loader):
    '''
    MBARI Dorado data as read from the production archive.  This class includes overriden methods
    to load quick-look plot and other Resources into the STOQS database.
    '''
    def addResources(self):
        '''
        In addition to the NC_GLOBAL attributes that are added in the base class also add the quick-look plots that are on the dods server.
        '''
        if not self.url.endswith('_decim.nc'):
            return super(Dorado_Loader, self).addResources()

        baseUrl = 'http://dods.mbari.org/data/auvctd/surveys'
        survey = self.url.split('/')[-1].split('.nc')[0].split('_decim')[0] # Works for both .nc and _decim.nc files
        yyyy = int(survey.split('_')[1])
        # Quick-look plots
        self.logger.debug("Getting or Creating ResourceType quick_look...")
        resourceType, _ = ResourceType.objects.db_manager(self.dbAlias).get_or_create(
                        name='quick_look', description='Quick Look plot of data from this AUV survey')
        for ql in ['2column', 'biolume', 'hist_stats', 'lopc', 'nav_adjust', 'prof_stats']:
            url = '%s/%4d/images/%s_%s.png' % (baseUrl, yyyy, survey, ql)
            self.logger.debug("Getting or Creating Resource with name = %s, url = %s", ql, url )
            resource, _ = Resource.objects.db_manager(self.dbAlias).get_or_create(
                        name=ql, uristring=url, resourcetype=resourceType)
            ActivityResource.objects.db_manager(self.dbAlias).get_or_create(
                        activity=self.activity,
                        resource=resource)

        # kml, odv, mat
        kmlResourceType, _ = ResourceType.objects.db_manager(self.dbAlias).get_or_create(
                        name = 'kml', description='Keyhole Markup Language file of data from this AUV survey')
        odvResourceType, _ = ResourceType.objects.db_manager(self.dbAlias).get_or_create(
                        name = 'odv', description='Ocean Data View spreadsheet text file')
        matResourceType, _ = ResourceType.objects.db_manager(self.dbAlias).get_or_create(
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
                self.logger.warn('No handler for res = %s', res)

            self.logger.debug("Getting or Creating Resource with name = %s, url = %s", res, url )
            resource, _ = Resource.objects.db_manager(self.dbAlias).get_or_create(
                        name=res, uristring=url, resourcetype=rt)
            ActivityResource.objects.db_manager(self.dbAlias).get_or_create(
                        activity=self.activity, resource=resource)

        return super(Dorado_Loader, self).addResources()


class Lrauv_Loader(Trajectory_Loader):
    '''
    MBARI Long Range AUV data loader.
    '''
    include_names = [
            'mass_concentration_of_oxygen_in_sea_water',
            'mole_concentration_of_nitrate_in_sea_water',
            'mass_concentration_of_chlorophyll_in_sea_water',
            'sea_water_salinity',
            'sea_water_temperature',
    ]

    def __init__(self, contourUrl, timezone, critSimpleDepthTime, *args, **kwargs):
        self.contourUrl = contourUrl
        self.timezone = timezone 
        self.critSimpleDepthTime = critSimpleDepthTime
        super(Lrauv_Loader, self).__init__(*args, **kwargs)

    def addResources(self):
        '''
        In addition to the NC_GLOBAL attributes that are added in the base class also add the quick-look plots that are on the dods server.
        '''

        if self.contourUrl and self.timezone: # pragma: no cover
            # Replace netCDF file with png extension
            outurl = re.sub('\.nc$','.png', self.url)

            # Contour plots
            self.logger.debug("Getting or Creating ResourceType quick_look...")
            resourceType, _ = ResourceType.objects.db_manager(self.dbAlias).get_or_create(
                            name = 'quick_look', description='Quick Look plot of data from this AUV survey')

            self.logger.debug("Getting or Creating Resource with name = log, url = %s", outurl)
            resource, _ = Resource.objects.db_manager(self.dbAlias).get_or_create(
                        name='log', uristring=outurl, resourcetype=resourceType)
            ActivityResource.objects.db_manager(self.dbAlias).get_or_create(
                        activity=self.activity,
                        resource=resource)

            startDateTimeUTC = pytz.utc.localize(self.startDatetime)
            startDateTimeLocal = startDateTimeUTC.astimezone(pytz.timezone(self.timezone))
            startDateTimeLocal = startDateTimeLocal.replace(hour=0,minute=0,second=0,microsecond=0)
            startDateTimeUTC = startDateTimeLocal.astimezone(pytz.utc)

            endDateTimeUTC = pytz.utc.localize(self.startDatetime)
            endDateTimeLocal = endDateTimeUTC.astimezone(pytz.timezone(self.timezone))
            endDateTimeLocal = endDateTimeLocal.replace(hour=23,minute=59,second=0,microsecond=0)
            endDateTimeUTC = endDateTimeLocal.astimezone(pytz.utc)

            outurl = self.contourUrl + self.platformName  + '_log_' + startDateTimeUTC.strftime(
                    '%Y%m%dT%H%M%S') + '_' + endDateTimeUTC.strftime('%Y%m%dT%H%M%S') + '.png'
            self.logger.debug("Getting or Creating Resource with name = 24hr, url = %s", outurl)
            resource, _ = Resource.objects.db_manager(self.dbAlias).get_or_create(
                    name='24hr', uristring=outurl, resourcetype=resourceType)
            ActivityResource.objects.db_manager(self.dbAlias).get_or_create(
                    activity=self.activity,
                    resource=resource)

        return super(Lrauv_Loader, self).addResources()


class Glider_Loader(Trajectory_Loader):
    '''
    CenCOOS Line 66 Spray glider data loader
    '''
    include_names=['TEMP', 'PSAL', 'OPBS', 'FLU2']

    def preProcessParams(self, row):
        '''
        Placeholder for any special preprocessing for Glider data
        '''
        return super(Glider_Loader,self).preProcessParams(row)


class TimeSeries_Loader(Base_Loader):
    '''
    Generic loader for station (non-trajectory) data.  Expects CF-1.6 timeSeries discrete sampling geometry featureType.
    '''
    # Subclasses or calling function must specify include_names
    include_names=[]

    def preProcessParams(self, row):
        '''
        Placeholder for any special preprocessing, for example adding sigma-t or other derived parameters
        '''
        return super(TimeSeries_Loader,self).preProcessParams(row)


class Mooring_Loader(TimeSeries_Loader):
    '''
    OceanSITES formatted Mooring data loader.  Expects CF-1.6 timeSeriesProfile discrete sampling geometry type.
    '''
    include_names=['Temperature', 'Salinity', 'TEMP', 'PSAL', 'ATMP', 'AIRT', 'WDIR', 'WSDP']

    def preProcessParams(self, row):
        '''
        Placeholder for any special preprocessing for Mooring data
        '''
        return super(Mooring_Loader,self).preProcessParams(row)


class BED_TS_Loader(TimeSeries_Loader):
    '''
    Benthic Event Detector timeSeries data.  Expects CF-1.6 timeSeries discrete sampling geometry type.
    '''
    include_names = ['XA', 'YA', 'ZA', 'XR', 'YR', 'ZR', 'PRESS', 'BED_DEPTH']

    def preProcessParams(self, row):
        '''
        Placeholder for any special preprocessing for Mooring data
        '''
        return super(BED_TS_Loader, self).preProcessParams(row)


class BED_Trajectory_Loader(Trajectory_Loader):
    '''
    Benthic Event Detector trajectory data.  Expects CF-1.6 timeSeries discrete sampling geometry type.
    '''
    include_names = ['XA', 'YA', 'ZA', 'A', 'XR', 'YR', 'ZR', 'ROTRATE', 'ROTCOUNT', 'P', 'P_ADJUSTED', 'DEPTH']

    def __init__(self, framegrab, critSimpleDepthTime, *args, **kwargs):
        self.framegrab = framegrab
        self.critSimpleDepthTime = critSimpleDepthTime
        super(BED_Trajectory_Loader, self).__init__(*args, **kwargs)

    def addResources(self): # pragma: no cover
        '''
        In addition to the NC_GLOBAL attributes that are added in the base class also add the frame grab URL
        '''
        self.logger.debug("Getting or Creating ResourceType framegrab...")
        resourceType, _ = ResourceType.objects.using(self.dbAlias).get_or_create(
                        name='quick_look', description='Video framegrab of BED located on sea floor')

        self.logger.debug("Getting or Creating Resource with framegrab = self.framegrab")
        link_text = 'framegrab'
        if self.framegrab.endswith('.m4v') or self.framegrab.endswith('.mov'):
            link_text = 'video'
        resource, _ = Resource.objects.using(self.dbAlias).get_or_create(
                    name=link_text, uristring=self.framegrab, resourcetype=resourceType)
        ActivityResource.objects.using(self.dbAlias).get_or_create(
                    activity=self.activity, resource=resource)

        return super(BED_Trajectory_Loader, self).addResources()


#
# Helper methods that expose a common interface for executing the loaders for specific platforms
#
def runTrajectoryLoader(url, cName, cDesc, aName, pName, pColor, pTypeName, aTypeName, parmList, dbAlias, 
                        stride, plotTimeSeriesDepth=None, grdTerrain=None, command_line_args=None):
    '''
    Run the DAPloader for Generic AUVCTD trajectory data and update the Activity with 
    attributes resulting from the load into dbAlias. Designed to be called from script
    that loads the data.  Following the load important updates are made to the database.
    If a number vaue is given to plotTimeSeriesDepth then that Resource is added for each
    Parameter loaded; this gives instruction to the STOQS UI to also plot timeSries data
    in the Parameter tab.
    '''
    loader = Trajectory_Loader(
            url = url,
            campaignName = cName,
            campaignDescription = cDesc,
            dbAlias = dbAlias,
            activityName = aName,
            activitytypeName = aTypeName,
            platformName = pName,
            platformColor = pColor,
            platformTypeName = pTypeName,
            stride = stride,
            grdTerrain = grdTerrain,
            command_line_args = command_line_args)

    loader.include_names = parmList

    # Fix up legacy data files
    if loader.auxCoords is None:
        loader.auxCoords = {}
        if aName.find('_jhmudas_v1') != -1:
            for p in loader.include_names:
                loader.auxCoords[p] = {'time': 'time', 'latitude': 'latitude', 'longitude': 'longitude', 'depth': 'depth'}

    if plotTimeSeriesDepth is not None:
        # Used first for BEDS where we want both trajectory and timeSeries plots
        loader.plotTimeSeriesDepth = dict.fromkeys(parmList + [ALTITUDE, SIGMAT, SPICE], plotTimeSeriesDepth)

    loader.process_data()
    loader.logger.debug("Loaded Activity with name = %s", aName)

def runBEDTrajectoryLoader(url, cName, cDesc, aName, pName, pColor, pTypeName, aTypeName,
                           parmList, dbAlias, stride, plotTimeSeriesDepth=None,
                           grdTerrain=None, framegrab=None, critSimpleDepthTime=1): # pragma: no cover
    '''
    Run the DAPloader for Benthic Event Detector trajectory data and update the Activity with 
    attributes resulting from the load into dbAlias. Designed to be called from script
    that loads the data.  Following the load important updates are made to the database.
    If a number vaue is given to plotTimeSeriesDepth then that Resource is added for each
    Parameter loaded; this gives instruction to the STOQS UI to also plot timeSries data
    in the Parameter tab.
    '''
    loader = BED_Trajectory_Loader(
            url = url,
            campaignName = cName,
            campaignDescription = cDesc,
            dbAlias = dbAlias,
            activityName = aName,
            activitytypeName = aTypeName,
            platformName = pName,
            platformColor = pColor,
            platformTypeName = pTypeName,
            stride = stride,
            grdTerrain = grdTerrain,
            framegrab = framegrab,
            critSimpleDepthTime = critSimpleDepthTime)

    loader.include_names = parmList

    if plotTimeSeriesDepth:
        # Used first for BEDS where we want both trajectory and timeSeries plots - assumes starting depth of BED
        loader.plotTimeSeriesDepth = dict.fromkeys(parmList + ['altitude'], plotTimeSeriesDepth)

    loader.process_data()
    loader.logger.debug("Loaded Activity with name = %s", aName)

def _loadLOPC(url, stride, loader, cName, cDesc, dbAlias, aTypeName, pName, 
              pColor, pTypeName, grdTerrain, plotTimeSeriesDepth):
    # Construct LOPC data url that looks like:
    # http://dods.mbari.org/opendap/data/ssdsdata/ssds/generated/netcdf/files/ssds.shore.mbari.org/auvctd/missionlogs/2010/2010300/2010.300.00/lopc.nc
    # from url that looks like: http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/Dorado389_2010_300_00_300_00_decim.nc
    #                  or like: http://odss.mbari.org/thredds/dodsC/CANON_march2013/dorado/Dorado389_2013_074_02_074_02_decim.nc
    # or from auv-python generated netCDFs:
    #                           http://dods.mbari.org/thredds/dodsC/auv/dorado/2022/netcdf/dorado_2022.054.01_1S.nc.html
    #                           http://dods.mbari.org/opendap/data/auvctd/surveys/2022/netcdf/dorado_2022.054.01_1S.nc.html
    # TODO: Handle multiple missions that compose a survey
    if 'Dorado389' in url:
        survey = url[url.find('Dorado389'):]
        yr = survey.split('_')[1]
        yd = survey.split('_')[2]
        mn = survey.split('_')[3]
    elif 'dorado_' in url:
        survey = url[url.find('dorado_'):]
        yr = survey.split('_')[1].split('.')[0]
        yd = survey.split('_')[1].split('.')[1]
        mn = survey.split('_')[1].split('.')[2]
    else:
        self.logger.warning("Could not parse yr, td, mn from url = %s", url)
        return
    lopc_url = ('http://dods.mbari.org/opendap/data/ssdsdata/ssds/generated/netcdf/'
                  'files/ssds.shore.mbari.org/auvctd/missionlogs/{}/{}/{}.{}.{}/'
                  'lopc.nc').format(yr, yr + yd, yr, yd, mn)

    lopc_aName = '{} (stride={})'.format(lopc_url, stride)

    loader.logger.debug("Instantiating Dorado_Loader for url = %s", lopc_url)
    try:
        # As we use the Measurements from the original Activity, associate the LOPC 
        # MeasuredParameters with it as well so that we can compare them in the UI
        lopc_loader = Dorado_Loader(url = lopc_url, campaignName = cName,
                                    campaignDescription = cDesc, dbAlias = dbAlias,
                                    activityName = loader.activity.name, 
                                    activitytypeName = loader.activity.activitytype.name,
                                    platformName = pName, platformColor = pColor,
                                    platformTypeName = pTypeName, stride = stride,
                                    grdTerrain = grdTerrain)
    except Exception as e:
        # Fail somewhat silently
        loader.logger.debug(str(e))
        loader.logger.warn('No LOPC data to load at %s', lopc_url)
        return

    lopc_loader.include_names = ['sepCountList', 'mepCountList']
    if plotTimeSeriesDepth is not None:
        lopc_loader.plotTimeSeriesDepth = dict.fromkeys(lopc_loader.include_names, plotTimeSeriesDepth)

    # These get added to ignored_names on previous .process_data(), remove them
    if 'sepCountList' in lopc_loader.ignored_names:
        lopc_loader.ignored_names.remove('sepCountList')
    if 'mepCountList' in lopc_loader.ignored_names:
        lopc_loader.ignored_names.remove('mepCountList')

    lopc_loader.associatedActivityName = loader.activityName

    # Auxillary coordinates are the same for all include_names
    lopc_loader.auxCoords = {}
    for v in lopc_loader.include_names:
        lopc_loader.auxCoords[v] = {'time': 'time', 'latitude': 'latitude', 'longitude': 'longitude', 'depth': 'depth'}

    Dorado_Loader.getFeatureType = lambda self: TRAJECTORY

    try:
        # Specify featureType so that non-CF LOPC data can be loaded
        lopc_loader.process_data(featureType=TRAJECTORY)
    except VariableMissingCoordinatesAttribute as e:
        loader.logger.exception(str(e))
    except NoValidData as e:
        loader.logger.warn(str(e))
    except KeyError as e:
        loader.logger.warn(str(e))
    else:
        loader.logger.debug("Loaded Activity with name = %s", lopc_loader.activityName)

def _load_plankton_proxies(url, stride, loader, cName, cDesc, dbAlias, aTypeName, pName, 
                           pColor, pTypeName, grdTerrain, plotTimeSeriesDepth):
    if 'Dorado389' in url:
        survey = url[url.find('Dorado389'):]
        yr = survey.split('_')[1]
        yd = survey.split('_')[2]
        mn = survey.split('_')[3]
    elif 'dorado_' in url:
        survey = url[url.find('dorado_'):]
        yr = survey.split('_')[1].split('.')[0]
        yd = survey.split('_')[1].split('.')[1]
        mn = survey.split('_')[1].split('.')[2]
    else:
        self.logger.warning("Could not parse yr, td, mn from url = %s", url)
        return

    # http://odss.mbari.org/thredds/dodsC/Other/routine/Products/Dorado/netcdf_proxies/2003/Dorado_2003_340_02_proxies.nc
    pp_url = ('http://odss.mbari.org/thredds/dodsC/Other/routine/Products/Dorado/'
              'netcdf_proxies/{}/Dorado_{}_{}_{}_proxies.nc').format(yr, yr, yd, mn)

    pp_aName = '{} (stride={})'.format(pp_url, stride)

    loader.logger.debug("Instantiating Trajectory_Loader for url = %s", pp_url)
    try:
        pp_loader = Trajectory_Loader(url = pp_url, campaignName = cName,
                                    campaignDescription = cDesc, dbAlias = dbAlias,
                                    activityName = pp_aName, activitytypeName = aTypeName,
                                    platformName = pName, platformColor = pColor,
                                    platformTypeName = pTypeName, stride = stride,
                                    grdTerrain = grdTerrain)
    except Exception:
        loader.logger.warn('No plankton proxy data to load at %s', pp_url)
        return

    pp_loader.include_names = ['adinos', 'bg_biolum', 'diatoms', 'fluo', 'hdinos', 'intflash', 'nbflash_high', 'nbflash_low', 'profile']
    if plotTimeSeriesDepth is not None:
        pp_loader.plotTimeSeriesDepth = dict.fromkeys(pp_loader.include_names, plotTimeSeriesDepth)

    # Auxillary coordinates are the same for all include_names
    pp_loader.auxCoords = {}
    for v in pp_loader.include_names:
        pp_loader.auxCoords[v] = {'time': 'time', 'latitude': 'latitude', 'longitude': 'longitude', 'depth': 'depth'}

    Trajectory_Loader.getFeatureType = lambda self: TRAJECTORY
    try:
        # Specify featureType so that non-CF LOPC data can be loaded
        pp_loader.add_to_activity=loader.activity
        pp_loader.process_data(featureType=TRAJECTORY, add_to_activity=loader.activity)
    except VariableMissingCoordinatesAttribute as e:
        loader.logger.exception(str(e))
    except NoValidData as e:
        loader.logger.warn(str(e))
    except KeyError as e:
        loader.logger.warn(str(e))
    else:
        loader.logger.debug("Loaded Activity with name = %s", pp_loader.activityName)

def runDoradoLoader(url, cName, cDesc, aName, pName, pColor, pTypeName, aTypeName, parmList, 
                    dbAlias, stride, grdTerrain=None, plotTimeSeriesDepth=None, plankton_proxies=False):
    '''
    Run the DAPloader for Dorado AUVCTD trajectory data and update the Activity with 
    attributes resulting from the load into dbAlias. Designed to be called from script
    that loads the data.  Following the load important updates are made to the database.
    '''
    loader = Dorado_Loader(
            url = url,
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
        loader.include_names = parmList

    # Auxillary coordinates are the same for all include_names
    loader.auxCoords = {}
    for v in loader.include_names:
        loader.auxCoords[v] = {'time': 'time', 'latitude': 'latitude', 'longitude': 'longitude', 'depth': 'depth'}

    if plotTimeSeriesDepth is not None:
        # Useful in some situations to have simple time series display of Dorado data
        loader.plotTimeSeriesDepth = dict.fromkeys(parmList + [ALTITUDE, SIGMAT, SPICE], plotTimeSeriesDepth)

    try:
        mps_loaded, _, _ = loader.process_data()
    except VariableMissingCoordinatesAttribute as e:
        loader.logger.exception(str(e))

    loader.logger.info(f"Loaded Activity {aName} with {mps_loaded} MeasuredParameters")

    if mps_loaded:
        if 'Dorado389' in url and ('sepCountList' in loader.include_names or 'mepCountList' in loader.include_names):
            # Load these only for legacy Matlab processed data, e.g. netCDF files named 'Dorado389...'
            _loadLOPC(url, stride, loader, cName, cDesc, dbAlias, aTypeName, pName, pColor, pTypeName, grdTerrain, plotTimeSeriesDepth)

        if plankton_proxies:
            _load_plankton_proxies(url, stride, loader, cName, cDesc, dbAlias, aTypeName, pName, pColor, pTypeName, grdTerrain, plotTimeSeriesDepth)
    else:
        loader.logger.warn(f"Did not load any MeasuredParameters from {loader.url}")
    return mps_loaded


def runLrauvLoader(url, cName, cDesc, aName, pName, pColor, pTypeName, aTypeName, parmList, dbAlias, 
                   stride=1, startDatetime=None, endDatetime=None, grdTerrain=None,
                   dataStartDatetime=None, contourUrl=None, auxCoords=None, timezone='America/Los_Angeles',
                   command_line_args=None, plotTimeSeriesDepth=None, critSimpleDepthTime=10): # pragma: no cover
    '''
    Run the DAPloader for Long Range AUVCTD trajectory data and update the Activity with 
    attributes resulting from the load into dbAlias. Designed to be called from script
    that loads the data.  Following the load important updates are made to the database.
    '''
    loader = Lrauv_Loader(
            url = url,
            campaignName = cName,
            campaignDescription = cDesc,
            dbAlias = dbAlias,
            activityName = aName,
            activitytypeName = aTypeName,
            platformName = pName,
            platformColor = pColor,
            platformTypeName = pTypeName,
            stride = stride,
            startDatetime = startDatetime,
            endDatetime = endDatetime,
            dataStartDatetime = dataStartDatetime,
            grdTerrain = grdTerrain,
            contourUrl = contourUrl,
            auxCoords = auxCoords,
            timezone = timezone,
            command_line_args = command_line_args,
            critSimpleDepthTime = critSimpleDepthTime)

    if parmList:
        loader.include_names = []
        for p in parmList:
            if p.find('.') == -1:
                loader.include_names.append(p)
            else:
                loader.logger.warn('Parameter %s not included. CANNOT HAVE PARAMETER NAMES WITH PERIODS. Period.', p)

    # Auxiliary coordinates are generally the same for all include_names
    if auxCoords is None:
        loader.auxCoords = {}
        if url.endswith('shore.nc'):
            for p in loader.include_names:
                loader.auxCoords[p] = {'time': 'Time', 'latitude': 'latitude', 'longitude': 'longitude', 'depth': 'depth'}
        else:
            for p in loader.include_names:
                loader.auxCoords[p] = {'time': 'time', 'latitude': 'latitude', 'longitude': 'longitude', 'depth': 'depth'}

    if plotTimeSeriesDepth is not None:
        # Useful to plot as time series engineering data for LRAUVs
        loader.plotTimeSeriesDepth = dict.fromkeys(parmList + [ALTITUDE, SIGMAT, SPICE], plotTimeSeriesDepth)

    try:
        loader.process_data()
    except NoValidData as e:
        loader.logger.warn(str(e))
        raise
    else:    
        loader.logger.debug("Loaded Activity with name = %s", aName)


def runGliderLoader(url, cName, cDesc, aName, pName, pColor, pTypeName, aTypeName, parmList, 
                    dbAlias, stride, startDatetime=None, endDatetime=None, grdTerrain=None, 
                    dataStartDatetime=None, plotTimeSeriesDepth=None, command_line_args=None): # pragma: no cover
    '''
    Run the DAPloader for Spray Glider trajectory data and update the Activity with 
    attributes resulting from the load into dbAlias. Designed to be called from script
    that loads the data.  Following the load important updates are made to the database.
    '''
    loader = Glider_Loader(
            url = url,
            campaignName = cName,
            campaignDescription = cDesc,
            dbAlias = dbAlias,
            activityName = aName,
            activitytypeName = aTypeName,
            platformName = pName,
            platformColor = pColor,
            platformTypeName = pTypeName,
            stride = stride,
            startDatetime = startDatetime,
            endDatetime = endDatetime,
            dataStartDatetime = dataStartDatetime,
            grdTerrain = grdTerrain,
            command_line_args = command_line_args)

    if parmList:
        loader.logger.debug("Setting include_names to %s", parmList)
        loader.include_names = parmList

    # Auxillary coordinates are the same for all include_names
    # NOTE: Presence of coordinates variable attribute will override these assignments
    loader.auxCoords = {}
    if pTypeName == 'waveglider':
        # for v in loader.include_names:
        #     loader.auxCoords[v] = {'time': 'TIME', 'latitude': 'latitude', 'longitude': 'longitude', 'depth': 'depth'}
        pass
    elif pName.startswith('Slocum'):
        # Set depth to 0.0 for u and v as no depth coord is in the dataset's metadata 
        # - leave it up to the user not the data creator to decide this. :-(.  Must also specify all other auxCoords.
        loader.auxCoords['u'] = {'time': 'time_uv', 'latitude': 'lat_uv', 'longitude': 'lon_uv', 'depth': 0.0}
        loader.auxCoords['v'] = {'time': 'time_uv', 'latitude': 'lat_uv', 'longitude': 'lon_uv', 'depth': 0.0}
        loader.auxCoords['temperature'] = {'time': 'time', 'latitude': 'lat', 'longitude': 'lon', 'depth': 'depth'}
        loader.auxCoords['salinity'] = {'time': 'time', 'latitude': 'lat', 'longitude': 'lon', 'depth': 'depth'}
        loader.auxCoords['density'] = {'time': 'time', 'latitude': 'lat', 'longitude': 'lon', 'depth': 'depth'}
        loader.auxCoords['fluorescence'] = {'time': 'time', 'latitude': 'lat', 'longitude': 'lon', 'depth': 'depth'}
        loader.auxCoords['phycoerythrin'] = {'time': 'time', 'latitude': 'lat', 'longitude': 'lon', 'depth': 'depth'}
        loader.auxCoords['cdom'] = {'time': 'time', 'latitude': 'lat', 'longitude': 'lon', 'depth': 'depth'}
        loader.auxCoords['oxygen'] = {'time': 'time', 'latitude': 'lat', 'longitude': 'lon', 'depth': 'depth'}
        loader.auxCoords['optical_backscatter470nm'] = {'time': 'time', 'latitude': 'lat', 'longitude': 'lon', 'depth': 'depth'}
        loader.auxCoords['optical_backscatter532nm'] = {'time': 'time', 'latitude': 'lat', 'longitude': 'lon', 'depth': 'depth'}
        loader.auxCoords['optical_backscatter660nm'] = {'time': 'time', 'latitude': 'lat', 'longitude': 'lon', 'depth': 'depth'}
        loader.auxCoords['optical_backscatter700nm'] = {'time': 'time', 'latitude': 'lat', 'longitude': 'lon', 'depth': 'depth'}

    elif pName.startswith('SPRAY'):
        for p in loader.include_names:
            loader.auxCoords[p] = {'time': 'TIME', 'latitude': 'LATITUDE', 'longitude': 'LONGITUDE', 'depth': 'DEPTH'}

    elif pName.upper().startswith('NPS'):
        for p in loader.include_names:
            loader.auxCoords[p] = {'time': 'TIME', 'latitude': 'LATITUDE', 'longitude': 'LONGITUDE', 'depth': 'DEPTH'}

    elif url.find('waveglider_gpctd_WG') != -1:
        for p in loader.include_names:
            loader.auxCoords[p] = {'time': 'TIME', 'latitude': 'latitude', 'longitude': 'longitude', 'depth': 'depth'}

    elif url.find('waveglider_pco2_WG') != -1:
        for p in loader.include_names:
            loader.auxCoords[p] = {'time': 'TIME', 'latitude': 'LATITUDE', 'longitude': 'LONGITUDE', 'depth': 'DEPTH'}

    # Fred is now writing according to CF-1.6 and we can expect compliance with auxillary coordinate attribute specifications for future files

    if plotTimeSeriesDepth is not None:
        # WaveGliders essentially stay at the surface it's handy to have the Parameter tab for their data
        loader.plotTimeSeriesDepth = dict.fromkeys(parmList + ['altitude'], plotTimeSeriesDepth)

    try:
        loader.process_data()
    except VariableMissingCoordinatesAttribute as e:
        loader.logger.exception(str(e))
    else:    
        loader.logger.debug("Loaded Activity with name = %s", aName)


def runTimeSeriesLoader(url, cName, cDesc, aName, pName, pColor, pTypeName, aTypeName, parmList, dbAlias, 
                        stride, startDatetime=None, endDatetime=None, command_line_args=None):
    '''
    Run the DAPloader for Generic CF Metadata timeSeries featureType data. 
    Following the load important updates are made to the database.
    '''
    loader = TimeSeries_Loader(
            url = url,
            campaignName = cName,
            campaignDescription = cDesc,
            dbAlias = dbAlias,
            activityName = aName,
            activitytypeName = aTypeName,
            platformName = pName,
            platformColor = pColor,
            platformTypeName = pTypeName,
            stride = stride,
            startDatetime = startDatetime,
            endDatetime = endDatetime,
            command_line_args = command_line_args)

    if parmList:
        loader.logger.debug("Setting include_names to %s", parmList)
        loader.include_names = parmList

    loader.process_data()
    loader.logger.debug("Loaded Activity with name = %s", aName)


def runMooringLoader(url, cName, cDesc, aName, pName, pColor, pTypeName, aTypeName, parmList, 
                     dbAlias, stride, startDatetime=None, endDatetime=None, dataStartDatetime=None,
                     command_line_args=None):
    '''
    Run the DAPloader for OceanSites formatted Mooring Station data and update the Activity with 
    attributes resulting from the load into dbAlias. Designed to be called from script
    that loads the data.  Following the load important updates are made to the database.
    '''
    loader = Mooring_Loader(
            url = url,
            campaignName = cName,
            campaignDescription = cDesc,
            dbAlias = dbAlias,
            activityName = aName,
            activitytypeName = aTypeName,
            platformName = pName,
            platformColor = pColor,
            platformTypeName = pTypeName,
            stride = stride,
            startDatetime = startDatetime,
            dataStartDatetime = dataStartDatetime,
            endDatetime = endDatetime,
            command_line_args = command_line_args,
            )

    if parmList:
        loader.logger.debug("Setting include_names to %s", parmList)
        loader.include_names = parmList

    loader.auxCoords = {} 

    if url.endswith('_CMSTV.nc'):
        # Special for combined file which has different coordinates for different variables
        for v in loader.include_names:
            if v in ['eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR']:
                loader.auxCoords[v] = {'time': 'hr_time_adcp', 'latitude': 'latitude', 'longitude': 'longitude', 'depth': 'HR_DEPTH_adcp'}
            elif v in ['SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR']:
                loader.auxCoords[v] = {'time': 'hr_time_ts', 'latitude': 'LATITUDE', 'longitude': 'LONGITUDE', 'depth': 'DEPTH'}
            elif v in ['SW_FLUX_HR', 'AIR_TEMPERATURE_HR', 'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR']:
                loader.auxCoords[v] = {'time': 'hr_time_met', 'latitude': 'Latitude', 'longitude': 'Longitude', 'depth': 'HR_DEPTH_met'}
            else:
                loader.logger.warn('Do not have an auxCoords assignment for variable %s in url %s', v, url)
    elif url.find('_hs2_') != -1:
        # Special for fluorometer on M1 - the HS2
        for v in loader.include_names:
            if v in ['bb470', 'bb676', 'fl676']:
                loader.auxCoords[v] = {'time': 'esecs', 'latitude': 'Latitude', 'longitude': 'Longitude', 'depth': 'NominalDepth'}
    elif url.find('OA') != -1: # pragma: no cover
        # Special for OA moorings: only 'time' is lower case
        for v in loader.include_names:
            loader.auxCoords[v] = {'time': 'time', 'latitude': 'LATITUDE', 'longitude': 'LONGITUDE', 'depth': 'DEPTH'}
    elif url.find('ccebin') != -1: # pragma: no cover
        # Special for CCEBIN mooring
        if 'adcp' in url:
            for v in loader.include_names:
                loader.auxCoords[v] = {'time': 'time', 'latitude': 'latitude', 'longitude': 'longitude', 'depth': 'depth'}
        else:
            for v in loader.include_names:
                loader.auxCoords[v] = {'time': 'esecs', 'latitude': 'Latitude', 'longitude': 'Longitude', 'depth': 'NominalDepth'}
    elif url.find('CCE_BIN') != -1: # pragma: no cover
        # CCE_BIN file variables have coordinate attributes, no need to override
        loader.auxCoords = []
    else:
        # Auxillary coordinates are the same for all include_names for _TS and _M files
        for v in loader.include_names:
            loader.auxCoords[v] = {'time': 'TIME', 'latitude': 'LATITUDE', 'longitude': 'LONGITUDE', 'depth': 'DEPTH'}

    try:
        loader.process_data()
        loader.logger.debug("Loaded Activity with name = %s", aName)
    except NoValidData as e:
        loader.logger.warning(str(e))


if __name__ == '__main__':
    # A nice test data load for a northern Monterey Bay survey  
    # See loaders/CANON/__init__.py for more examples of how these loaders are used
    baseUrl = 'http://odss.mbari.org/thredds/dodsC/dorado/'
    auv_file = 'Dorado389_2010_300_00_300_00_decim.nc'
    parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
              'fl700_uncorr', 'salinity', 'biolume', 'roll', 'pitch', 'yaw',
              'sepCountList', 'mepCountList'
    ]
    stride = 1000       # Make large for quicker runs, smaller for denser data
    dbAlias = 'default'

    runDoradoLoader(baseUrl + auv_file, 'Campaign Name', 'Campaign Description',
                    'Activity Name', 'Platform Name - Dorado', 'ffeda0', 'auv', 
                    'AUV Mission', parms, dbAlias, stride)


