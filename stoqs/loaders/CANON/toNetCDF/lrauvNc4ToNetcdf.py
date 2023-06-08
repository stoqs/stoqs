#!/usr/bin/env python
__author__    = 'Danelle Cline'
__copyright__ = '2016'
__license__   = 'GPL v3'
__contact__   = 'dcline at mbari.org'

__doc__ = '''

Utility class to convert netCDF4 to netCDFs in a format compatible with STOQs loading.
This basically captures the independently sampled variables captured in the LRAUV and
(that have their own time base) and interpolates them onto a common lat/lon/depth/time
trajectory.

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''
import os
import tempfile
os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp()
import matplotlib as mpl
mpl.use('Agg')               # Force matplotlib to not use any Xwindows backend
import matplotlib.pyplot as plt
import sys
import errno
# Add grandparent dir to pythonpath so that we can see the CANON and toNetCDF modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../") )
from math import cos
import netCDF4
import numpy as np
import pandas as pd
import time
import datetime as dt
from time import mktime
from CANON.toNetCDF import BaseWriter
from contextlib import closing
from netCDF4 import Dataset
import pydap.client
import numpy
import DAPloaders
import logging
import socket
import json
import csv
import requests
import xarray as xr

# Map common LRAUV variable names to CF standard names: http://cfconventions.org/standard-names.html
sn_lookup = {
             'bin_mean_temperature': 'sea_water_temperature',
             'bin_median_sea_water_temperature': 'sea_water_temperature',
             'bin_mean_salinity': 'sea_water_salinity',
             'bin_median_sea_water_salinity': 'sea_water_salinity',
             'bin_mean_chlorophyll': 'mass_concentration_of_chlorophyll_in_sea_water', 
             'bin_median_mass_concentration_of_chlorophyll_in_sea_water': 'mass_concentration_of_chlorophyll_in_sea_water',
             'temperature': 'sea_water_temperature',
             'salinity': 'sea_water_salinity',
             'chlorophyll': 'mass_concentration_of_chlorophyll_in_sea_water', 
             'oxygen': 'mass_concentration_of_oxygen_in_sea_water',
            }


class MissingCoordinate(Exception):
    pass


class InterpolatorWriter(BaseWriter):
    logger = logging.getLogger(__name__)
    sh = logging.StreamHandler()
    f = logging.Formatter("%(levelname)s %(asctime)sZ %(filename)s %(funcName)s():%(lineno)d %(message)s")
    sh.setFormatter(f)
    logger.addHandler(sh)
    logger.setLevel(logging.DEBUG)

    df = []
    all_sub_ts = {}
    all_coord = {}
    all_attrib = {}
    nudged_file = {}
    tracking_file = {}

    def reset(self):
        self.df = []
        self.all_sub_ts = {}
        self.all_coord = {}
        self.all_attrib = {}
        self.nudged_file = {}
        self.tracking_file = {}

    def get_deployment_name(self, log_dir):
        '''Navigate to .dlist file in the parent directory and return the given Deployment Name
        '''
        file_name = os.path.basename(os.path.abspath(os.path.join(log_dir, os.pardir))) + '.dlist'
        dlist_path = os.path.abspath(os.path.join(log_dir, os.pardir, os.pardir, file_name))

        try:
            # This is how lrauv-tools/handle-lrauv-logs/*/scripts/dlist-tools.py parses the Name
            with open(dlist_path, 'r') as d:
                dlist_lines = [line.strip() for line in d]
        except FileNotFoundError:
            # Likely an sbd or cell log file with no associated .dlist file
            deployment_name = ''
            return deployment_name

        try:
            key, value = dlist_lines[0].split(': ', 1)
            deployment_name = value.strip()
        except ValueError:
            deployment_name = ''

        return deployment_name

    def get_esp_log_url(self, log_dir):
        '''Set esp_log_url attrubute to url of ESP Log file if it exists in log_dir
        '''
        url_path = log_dir.replace('/mbari/LRAUV', 'http://dods.mbari.org/opendap/data/lrauv')
        esp_log_url = os.path.join(url_path, 'ESP.log')
        if requests.head(esp_log_url).status_code == 200:
            return esp_log_url
        else:
            return None

    def write_netcdf(self, out_file, in_url, nudge_to_platform=None, nudge_interval=None, replace_with_platform=None):

        # Check parent directory and create if needed
        dirName = os.path.dirname(out_file)
        try:
            os.makedirs(dirName)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        # Create the NetCDF file - leave most of the netCDF4 calls in place, but don't write out the file
        self.logger.debug("Creating netCDF file %s", out_file + '.old')
        self.ncFile = Dataset(out_file + '.old', 'w')
        # Create xarray-driven NetCDF file as it is smarter about matching indexes and doesn't fail!
        self.logger.debug("Creating xarray Dataset to write to file %s", out_file)
        self.Dataset = xr.Dataset()

        # Lead the title with the Deployment Name form the .dlist file - if it exists
        # also save it in a 'deployment_name' global attribute
        deployment_name = self.get_deployment_name(dirName)
        self.esp_log_url = self.get_esp_log_url(dirName)
        if deployment_name:
            self.ncFile.title = deployment_name + ' - LRAUV interpolated data'
            self.ncFile.deployment_name = deployment_name
            self.Dataset.attrs["title"] = deployment_name + ' - LRAUV interpolated data'
            self.Dataset.attrs["deployment_name"] = deployment_name
        elif 'shore' in out_file:
            self.ncFile.title = 'LRAUV interpolated realtime data'
            self.Dataset.attrs["title"] = 'LRAUV interpolated realtime data'
        else:
            self.ncFile.title = 'LRAUV interpolated data'
            self.Dataset.attrs["title"] = 'LRAUV interpolated data'

        # Combine any summary text specified on command line with the generic summary stating the original source file
        self.ncFile.summary = 'Observational oceanographic data translated with modification from original data file %s' % in_url
        self.Dataset.attrs["summary"] = 'Observational oceanographic data translated with modification from original data file %s' % in_url

        # add in time dimensions first
        ts_key = []
        for key in list(self.all_sub_ts.keys()):
            if key.find('time') != -1:
                ts = self.all_sub_ts[key]

                if not ts.empty:
                    self.logger.debug("Adding in record variable %s", key)
                    v = self.initRecordVariable(key)
                    v[:] = self.all_sub_ts[key].values
            else:
                ts_key.append(key)

        # add in other remaining time series
        for key in ts_key:
            ts = self.all_sub_ts[key]

            if not ts.empty:
                # xarray is much smarter about matching different shapes to the same index
                self.logger.debug("Saving to xarray Dataset: %s", key)
                # Integerize time so that we don't have ns precision that coards.from_udunits() can't handle
                ts = ts.resample('2S').interpolate("linear")
                self.Dataset[key] =  xr.DataArray(
                    ts.values,
                    coords=[ts.index],
                    dims={"time"},
                    name=key,
                )
                try:
                    self.Dataset[key].attrs = self.all_attrib[key]
                except KeyError:
                    self.logger.debug(f"{key} has no attributes")
                if key in ("depth", "latitude", "longitude"):
                    self.Dataset[key].attrs["standard_name"] = key
                else:
                    self.Dataset[key].attrs["coordinates"] = "time depth latitude longitude"
                    if key in sn_lookup.keys():
                        self.Dataset[key].attrs["standard_name"] = sn_lookup[key]
            try:
                #self.logger.debug("Adding in record variable %s", key)
                # We no longer write out these variables, but initRecordVariable() likely has side effects that we still want
                v = self.initRecordVariable(key)
                v[:] = self.all_sub_ts[key].values
            except Exception as e:
                # Likely shape mismatch error as data from different instruments have different time bases
                # Getting around this error by using xarray to write the netCDF file
                self.logger.debug(e)
                continue

        # We let xarray write its own time coordinate then add standard_name as the STOQS loader needs it
        self.Dataset["time"].attrs["standard_name"] = "time"

        self.logger.debug("Adding in global metadata")
        self.add_global_metadata()
        self.add_xarray_global_metadata()
        if getattr(self, 'segment_count', None) and getattr(self, 'segment_minsum', None):
            if nudge_to_platform:
                self.ncFile.summary += f". {self.segment_count} underwater segments over {self.segment_minsum:.1f} minutes nudged toward {nudge_to_platform} fixes at {nudge_interval} minute intervals"
                self.Dataset.attrs["summary"] += f". {self.segment_count} underwater segments over {self.segment_minsum:.1f} minutes nudged toward {nudge_to_platform} fixes at {nudge_interval} minute intervals"
            else:
                self.ncFile.summary += f". {self.segment_count} underwater segments over {self.segment_minsum:.1f} minutes nudged toward GPS fixes"
                self.Dataset.attrs["summary"] += f". {self.segment_count} underwater segments over {self.segment_minsum:.1f} minutes nudged toward GPS fixes"
        if replace_with_platform:
            self.ncFile.summary += f". Entire mission's latitude and longitude replaced with positions from {replace_with_platform}"
            self.Dataset.attrs["summary"] += f". Entire mission's latitude and longitude replaced with positions from {replace_with_platform}"
        if getattr(self, 'trackingdb_values', None):
            self.ncFile.comment = f"latitude and longitude values interpolated from {self.trackingdb_values} values retrieved from {self.trackingdb_url}"
            self.ncFile.summary += f" {self.trackingdb_values} acoustic navigation fixes retrieved from tracking database with {self.trackingdb_url}"
            self.ncFile.title += " with acoustic navigation data retrieved from Tracking Database"
            self.Dataset.attrs["comment"] = f"latitude and longitude values interpolated from {self.trackingdb_values} values retrieved from {self.trackingdb_url}"
            self.Dataset.attrs["summary"] += f" {self.trackingdb_values} acoustic navigation fixes retrieved from tracking database with {self.trackingdb_url}"
            self.Dataset.attrs["title"] += " with acoustic navigation data retrieved from Tracking Database"
        if getattr(self, 'esp_log_url', None):
            self.ncFile.summary += f". Associated with ESP Log file {self.esp_log_url}"
            self.Dataset.attrs["summary"] += f". Associated with ESP Log file {self.esp_log_url}"

        self.ncFile.summary += "."
        self.Dataset.attrs["summary"] += "."

        # Commented out so the the .old file does not get written
        # self.ncFile.close()
        self.Dataset.to_netcdf(path=out_file, format="NETCDF4_CLASSIC")
        # End write_netcdf()


    def interpolate(self, data, times):
        x = np.asarray(times, dtype=np.float64)
        if np.any(np.diff(x) <= 0):
            x, counts = np.unique(x, return_counts=True)
            self.logger.warning(f"Removed repeated times values, counts = {counts}")

        xp = np.asarray(data.index,dtype=np.float64)
        fp = np.asarray(data)
        ts = pd.Series(index=times, dtype='float64')
        # interpolate to get data onto spacing of datetimes in times variable
        # this can be irregularly spaced
        ts[:] = np.interp(x,xp,fp)
        return ts
        # End interpolate

    def createSeriesPydap(self, name, tname):
        v = self.df[name]
        v_t = self.df[tname]
        data = np.asarray(v_t)
        data[data/1e10 < -1.] = np.nan
        data[data/1e10 > 1.] = np.nan
        v_time_epoch = data
        v_time = pd.to_datetime(v_time_epoch[:],unit='s')
        v_time_series = pd.Series(v[:],index=v_time)
        return v_time_series
        # End createSeriesPydap

    def _file_start_end(self):
        '''Return datetimes of the start and end of missionlogs in_file based on its name
        '''
        if 'missionlogs' in self.in_file:
            fstart = dt.datetime.strptime(os.path.basename(self.in_file).split('_')[0], '%Y%m%d%H%M')
            fend = dt.datetime.strptime(os.path.basename(self.in_file).split('_')[1].split('.nc4')[0], '%Y%m%d%H%M')
            return fstart, fend 
        else:
            return None, None

    def createSeries(self, subgroup, name, tname):
        if subgroup:
            v = subgroup[name]
            v_t = subgroup[tname]
        else:
            v = self.df[name]
            v_t = self.df[tname]

        # Discovered in /mbari/LRAUV/whoidhs/missionlogs/2019/20190610_20190613/20190611T165616/201906111656_201906111829.nc4
        # Also in http://dods.mbari.org/opendap/data/lrauv/makai/missionlogs/2019/20191001_20191010/20191007T152538/201910071525_201910080007.nc4.ascii?latitude[13618:1:13622]
        # Also http://dods.mbari.org/opendap/hyrax/data/lrauv/triton/missionlogs/2019/20191005_20191010/20191007T230214/201910072302_201910090436.nc4
        # raised the need to make a closer chop of the data based in file name start and end datetimes
        fstart, fend = self._file_start_end()
        if fstart and fend:
            out_of_file_time_values = np.where((v_t[:] < fstart.timestamp()) | (v_t[:] > fend.timestamp()))[0]
            if out_of_file_time_values.any():
                self.logger.info(f"{name:9s}: {len(out_of_file_time_values):4d} v_t values found before {fstart} and after {fend}")
                self.logger.debug(f"{name}: v_t values found before {fstart} and after {fend}: {out_of_file_time_values}")
                self.logger.debug(f"Their times:  {[time.ctime(ti) for ti in v_t[out_of_file_time_values]]}")
                self.logger.debug(f"Removing them: {v_t[out_of_file_time_values]} for variable {name}")
                v_t = np.delete(v_t, out_of_file_time_values)
                v = np.delete(v, out_of_file_time_values)

        v_time = pd.to_datetime(v_t[:], unit='s', errors = 'coerce')
        v_time_series = pd.Series(v[:], index=v_time)
        return v_time_series
        # End createSeries

    def initRecordVariable(self, key, units=None):
        # Create record variable to store in nc file
        v = self.all_sub_ts[key]

        if key.find('time') != -1:
            # convert time to epoch seconds
            esec_list = v.index.values.astype(dt.datetime)/1E9
            # trajectory dataset, time is the only netCDF dimension
            self.ncFile.createDimension(key, len(esec_list))
            rc = self.ncFile.createVariable(key, 'float64', (key,), fill_value=np.nan)
            rc.standard_name = 'time' 
            rc.units = 'seconds since 1970-01-01 00:00:00'
            # Used in global metadata
            if key == 'time':
                self.time = rc
            return rc

        elif key.find('latitude') != -1:
            # Record Variables - coordinates for trajectory - save in the instance and use for metadata generation
            c = self.all_coord[key]
            rc = self.ncFile.createVariable(key, 'float64', (c['time'],), fill_value=np.nan)
            rc.long_name = 'LATITUDE'
            rc.standard_name = 'latitude' 
            rc.units = 'degree_north'
            rc[:] = self.all_sub_ts[key].values
            # Used in global metadata
            if key == 'latitude':
                self.latitude = rc
            return rc

        elif key.find('longitude') != -1:
            c = self.all_coord[key]
            rc = self.ncFile.createVariable(key, 'float64', (c['time'],), fill_value=np.nan)
            rc.long_name = 'LONGITUDE'
            rc.standard_name = 'longitude'
            rc.units = 'degree_east'
            rc[:] = self.all_sub_ts[key].values
            # Used in global metadata
            if key == 'longitude':
                self.longitude = rc
            return rc

        elif key.find('depth') != -1:
            c = self.all_coord[key]
            rc = self.ncFile.createVariable(key, 'float64', (c['time'],), fill_value=np.nan)
            rc.long_name = 'DEPTH'
            rc.standard_name = 'depth' 
            rc.units = 'm'
            rc[:] = self.all_sub_ts[key].values
            # Used in global metadata
            if key == 'depth':
                self.depth = rc
            return rc

        else:
            a = self.all_attrib[key]
            c = self.all_coord[key]
            rc = self.ncFile.createVariable(key, 'float64', (c['time'],), fill_value=np.nan)

            if 'long_name' in a:
                rc.long_name = a['long_name']
            if 'standard_name' in a:
                rc.standard_name = a['standard_name']
            elif key in sn_lookup.keys():
                rc.standard_name = sn_lookup[key]

            rc.coordinates = ' '.join(list(c.values()))

            if units is None:
                if 'units' in a:
                    rc.units = a['units']
                else:
                    rc.units = ''
            else:
                rc.units = units

            if key.find('pitch') != -1 or key.find('roll') != -1 or key.find('yaw') != -1 or key.find('angle') != -1 or key.find('rate') != -1:
                if 'rad/s' in rc.units:
                    rc.units = 'degree/s'
                else:
                    rc.units = 'degree'

            return rc
        # End initRecordVariable

    def getValidTimeRange(self, ts):
        start = ts.index[0]
        end = ts.index[-1]

        if pd.isnull(start) or pd.isnull(end):
            self.logger.info('Invalid starting or ending time found. Searching for valid time range')
            selector = np.where(~pd.isnull(ts.index))

            if len(selector) > 2:
                start = ts[selector[0]]
                end = ts[selector[-1]]

            # If still can't find a valid time, then raise exception here
            if pd.isnull(start) or pd.isnull(end):
                raise Exception('Cannot find a valid time range')
            return (start, end)

        return(start, end)
        # End getValidTimeRange

    def process(self, url, out_file, parm, interp_key):
        self.df = []
        self.all_sub_ts = {}
        self.all_coord = {}
        self.all_attrib = {}
        coord =  ['latitude','longitude','depth']
        all_ts = {}
        parm_valid = []

        try:
            self.df = pydap.client.open_url(url)
        except socket.error as e:
            self.logger.error('Failed in attempt to open_url(%s)', url)
            raise e

        # Create pandas time series for each parameter and store attributes
        for key in parm:
            try:
                ts = self.createSeriesPydap(key, key + '_time')
                if ts.size == 0:
                    continue
                self.all_attrib[key] = self.df[key].attributes
                self.all_attrib[key + '_i'] = self.df[key].attributes
                self.all_coord[key] = {'time':'time','depth':'depth','latitude':'latitude','longitude':'longitude'}
                parm_valid.append(key)
                all_ts[key] = ts
                self.logger.info('Found parameter ' + key)
            except KeyError as e:
                self.logger.info('Key error on parameter ' + key)
                continue

        # Create another pandas time series for each coordinate
        for key in coord:
            try:
                ts = self.createSeriesPydap(key, key + '_time')
                all_ts[key] = ts
            except KeyError as e:
                self.logger.info('Key error on coordinate ' + key)
                raise e

        # create independent lat/lon/depth profiles for each parameter
        for key in parm_valid:
            # TODO: add try catch block on this
            # Get independent parameter to interpolate on
            t = pd.Series(index = all_ts[key].index)

            # Store the parameter as-is - this is the raw data
            self.all_sub_ts[key] = pd.Series(all_ts[key])
            self.all_coord[key] = { 'time': key+'_time', 'depth': key+'_depth', 'latitude': key+'_latitude', 'longitude':key+'_longitude'}

            # interpolate each coordinate to the time of the parameter
            # key looks like sea_water_temperature_depth, sea_water_temperature_lat, sea_water_temperature_lon, etc.
            for c in coord:

                # get coordinate
                ts = all_ts[c]

                # and interpolate using parameter time
                if not ts.empty:
                    i = self.interpolate(ts, t.index)
                    self.all_sub_ts[key + '_' + c] = i
                    self.all_coord[key + '_' + c] = { 'time': key+'_time', 'depth': key+' _depth', 'latitude': key+'_latitude', 'longitude':key+'_longitude'}

            # add in time coordinate separately
            v_time = all_ts[key].index
            esec_list = v_time.values.astype(dt.datetime)/1E9
            self.all_sub_ts[key + '_time'] = pd.Series(esec_list,index=v_time)

        # TODO: add try catch block on this
        # Get independent parameter to interpolate on
        t = pd.Series(index = all_ts[interp_key].index)

        # store time using interpolation parameter
        v_time = all_ts[interp_key].index
        esec_list = v_time.values.astype(dt.datetime)/1E9
        self.all_sub_ts['time'] = pd.Series(esec_list,index=v_time)

        # interpolate all parameters and coordinates
        for key in parm_valid:
            value = all_ts[key]
            if not value.empty :
               i = self.interpolate(value, t.index)
               self.all_sub_ts[key + '_i'] = i
            else:
               self.all_sub_ts[key + '_i'] = value

            self.all_coord[key + '_i'] = { 'time': 'time', 'depth': 'depth', 'latitude':'latitude', 'longitude':'longitude'}

        for key in coord:
            value = all_ts[key]
            self.all_sub_ts[key] = value
            if not value.empty :
               i = self.interpolate(value, t.index)
               self.all_sub_ts[key] = i
            else:
               self.all_sub_ts[key] = value

            self.all_coord[key] = { 'time': 'time', 'depth': 'depth', 'latitude':'latitude', 'longitude':'longitude'}


        self.logger.info("%s", list(self.all_sub_ts.keys()))

        # Write data to the file
        self.write_netcdf(out_file, url)
        self.logger.info('Wrote ' + out_file)

        # End processSingleParm

    def createNav(self, t_resample, resampleFreq):

        nav =  {
             'platform_pitch_angle': 'pitch',
             'platform_roll_angle': 'roll',
             'platform_orientation': 'yaw',
            }
        attr = {}
        create_nav_flag = False
        for v in self.df.variables:
            if any(v in s for s in nav):
                create_nav_flag = True

        if create_nav_flag:
            # Create pandas time series for each coordinate and store attributes
            for c, c_rename in nav.items():
                try:
                    ts = self.createSeries(self.df.variables, c, c+'_'+'time')

                    # don't store or try to interpolate empty time series
                    if ts.size == 0:
                        self.logger.info('Variable ' + c + ' empty so skipping')
                        continue

                    if c_rename.find('pitch') != -1 or c_rename.find('roll') != -1 or c_rename.find('yaw') != -1:
                        ts = ts * 180.0 / numpy.pi

                    # resample using the mean then interpolate on to the time dimension
                    self.logger.debug(f"calling ts.resample() for {c_rename}")
                    ts_resample = ts.resample(resampleFreq).mean()[:]
                    self.logger.debug(f"calling self.interpolate() for {c_rename}")
                    i = self.interpolate(ts_resample, t_resample.index)

                    for name in self.df[c].ncattrs():
                        attr[name] = getattr(self.df.variables[c],name)
                        if name == 'standard_name' and attr[name] == 'platform_orientation':
                            # Override original standard_name for yaw
                            attr[name] = 'platform_yaw_angle'

                    self.all_sub_ts[c_rename] = i
                    self.logger.info(f"{c} -> {c_rename}: {attr.copy()}")
                    self.all_attrib[c_rename] = attr.copy()
                    self.all_coord[c_rename] = { 'time':'time', 'depth':'depth', 'latitude':'latitude', 'longitude':'longitude'}
                except Exception as e:
                    self.logger.error(str(e))
                    continue
    # End createNav

    def createCoord(self, coord):

        all_ts = {}

        for v in self.df.variables:
            g = None

            if any(v in s for s in coord):
                # Create pandas time series for each coordinate and store attributes
                for c in coord:
                    try:
                        ##self.logger.debug(f'For variable {v:>20} creating coordinate {c:>20}')
                        ts = self.createSeries(self.df.variables, c, c+'_'+'time')
                        all_ts[c] = ts
                    except KeyError:
                        # Likely the variable c is not in the NetCDF file
                        self.logger.debug(f"Could not create coord {c}.  It's likely not in the file")
                    except ValueError as e:
                        self.logger.error('Could not create coord {}: {}'.format(c, str(e)))
                        continue

        return all_ts
    # End createCoord

    def trackingdb_lat_lon(self, in_file, sec_extend=3600, nudge_to_platform=None, nudge_interval=None, replace_with_platform=None):
        '''Query MBARI's Tracking Database and return Pandas time series
        of any acoustic fixes found.

        sec_extend: int
            Seconds beyond time range of in_file for query of tracking database
        nudge_to_platform: str
            If GPS fixes or <platform>_ac aren't available nudge to this platform's position from the Tracking database
            e.g. "wgTiny"
        nudge_interval: int
            How frequently (in minutes) to nudge back to nudge_to_platform's position
            e.g. 15
        '''
        self.logger.debug(f"Constructing trackingdb url to {sec_extend} seconds beyond time range of file")
        se = float(self.df['time'][0].data) - sec_extend
        ee = float(self.df['time'][-1].data) + sec_extend
        st = dt.datetime.utcfromtimestamp(se).strftime('%Y%m%dT%H%M%S')
        et = dt.datetime.utcfromtimestamp(ee).strftime('%Y%m%dT%H%M%S')
        vehicle = in_file.split('/')[3]
        if nudge_to_platform:
            url = f"http://odss.mbari.org/trackingdb/position/{nudge_to_platform}/between/{st}/{et}/data.csv"
        elif replace_with_platform:
            url = f"http://odss.mbari.org/trackingdb/position/{replace_with_platform}/between/{st}/{et}/data.csv"
        else:
            url = f"http://odss.mbari.org/trackingdb/position/{vehicle}_ac/between/{st}/{et}/data.csv"
        self.trackingdb_url = url
        self.logger.info(url)

        # Read positions from .csv response and collect into lists - expect less than 10^3 values
        ess = []
        lons = []
        lats = []
        with closing(requests.get(url, stream=True)) as resp:
            if resp.status_code != 200:
                self.logger.error('Cannot read %s, resp.status_code = %s', url, resp.status_code)
                return np.array(lons), np.array(lats)

            r_decoded = (line.decode('utf-8') for line in resp.iter_lines())
            lines = [line for line in csv.DictReader(r_decoded)]
            for r in reversed(lines):
                self.logger.debug(f"{float(r['epochSeconds'])}, {float(r['longitude'])}, {float(r['latitude'])}")
                ess.append(float(r['epochSeconds']))
                lons.append(float(r['longitude']))
                lats.append(float(r['latitude']))

        self.trackingdb_values = len(ess)
        self.logger.info(f"Found {self.trackingdb_values} position values from the Tracking database")
        v_time = pd.to_datetime(ess, unit='s',errors = 'coerce')
        if nudge_interval:
            nidx = pd.date_range(v_time.min(), v_time.max(), freq=f"{nudge_interval}min")
            lon_time_series = pd.Series(lons, index=v_time, dtype=np.float64).reindex(nidx, method='nearest', limit=1).interpolate()
            lat_time_series = pd.Series(lats, index=v_time, dtype=np.float64).reindex(nidx, method='nearest', limit=1).interpolate()
            self.logger.info(f"Sampled values at {nudge_interval} minute intervals reulting in {len(lon_time_series)} values")
        else:
            lon_time_series = pd.Series(lons, index=v_time, dtype=np.float64)
            lat_time_series = pd.Series(lats, index=v_time, dtype=np.float64)

        return lon_time_series, lat_time_series

    def outlier_mask(self, signal, name, threshold=4):
        # This method is relly only good for single point spikes as it relies on a difference between adjacent points
        # See: https://ocefpaf.github.io/python4oceanographers/blog/2015/03/16/outlier_detection/
        signal = signal.copy()
        difference = np.abs(signal - np.median(signal))
        median_difference = np.median(difference)
        if median_difference == 0:
            spike = 0
        else:
            spike = difference / float(median_difference)

        mask = spike > threshold
        if mask.any():
            self.logger.info(f"Found {name} outliers {signal[mask].values} at times {signal[mask].index.tolist()}, indexes: {np.where(mask == True)[0]}")
            self.logger.info(f"Median of {len(signal)} signal points: {np.median(signal)}")

        return mask

    def var_series(self, in_file, data_array, time_array, args, tmin=0, tmax=time.time(), angle=False):
        '''Return a Pandas series of the coordinate with invalid and out of range time values removed'''
        mt = np.ma.masked_invalid(time_array)
        mt = np.ma.masked_outside(mt, tmin, tmax)
        bad_times = [str(dt.datetime.utcfromtimestamp(es)) for es in time_array[:][mt.mask]]
        if bad_times:
            self.logger.info(f"Removing bad {data_array.name} times from {in_file} ([index], [values]): {np.where(mt.mask)[0]}, {bad_times}")
        v_time = pd.to_datetime(mt.compressed(), unit='s',errors = 'coerce')
        da = pd.Series(data_array[:][~mt.mask], index=v_time)

        # Remove 0 values
        if 'longitude' in data_array.name or 'latitude' in data_array.name:
            md = np.ma.masked_equal(data_array, 0)
            if md.mask is not np.ma.nomask:
                da = pd.Series(da[:][~md.mask], index=v_time)

        if args.remove_gps_outliers:
            # Remove gps fix outliers
            if ('longitude_fix' in data_array.name or 'latitude_fix' in data_array.name):
                # For /mbari/LRAUV/tethys/missionlogs/2018/20180829_20180830/20180829T225930/201808292259_201808300407.nc4 threshold=4 seems appropriate
                mask = self.outlier_mask(da, data_array.name, threshold=4)
                da = pd.Series(da[:][~mask], index=v_time)

        # Specific ad hoc QC fixes
        if ('daphne/missionlogs/2017/20171002_20171005/20171003T231731/201710032317_201710040517' in in_file or 
            'daphne/missionlogs/2017/20171002_20171005/20171004T170805/201710041708_201710042304' in in_file):
            if data_array.name == 'latitude':
                md = np.ma.masked_less(data_array, 0.6)     # < 30 deg latitude
                da = pd.Series(da[:][~md.mask], index=v_time)
            if data_array.name == 'longitude':
                md = np.ma.masked_less(data_array, -2.15)     # < -130 deg longitude
                da = pd.Series(da[:][~md.mask], index=v_time)
       
        if 'tethys/missionlogs/2016/20160923_20161003/20161001T150952/201610011510_201610031606' in in_file:
            if data_array.name == 'longitude':
                md = np.ma.masked_greater(data_array, -2.0)     # Remove points in Utah
                da = pd.Series(da[:][~md.mask], index=v_time)

        if angle:
            # Some universal positions are in degrees, some are in radians - make a guess based on mean values
            rad_to_deg = False
            if np.max(np.abs(da)) <= np.pi:
                rad_to_deg = True

            self.logger.debug(f"{data_array.name}: rad_to_deg = {rad_to_deg}")
            if rad_to_deg:
                da = da * 180.0 / np.pi

        return da

    def nudge_coords(self, in_file, args, max_sec_diff_at_end=10, nudge_to_platform=None, nudge_interval=15, replace_with_platform=None):
        '''Given a ds object to an LRAUV .nc4 file return adjusted longitude
        and latitude arrays that reconstruct the trajectory so that the dead
        reckoned positions are nudged so that they match the GPS fixes.

        max_sec_diff_at_end: int
            Number of seconds that need to agree at end to avoid a warning
        nudge_to_platform: str
            If GPS fixes or <platform>_ac aren't available nudge to this platform's position from the Tracking database
            e.g. "wgTiny"
        nudge_interval: int
            How frequently (in minutes) to nudge back to nudge_to_platform's position
            e.g. 15
        '''
        ds = self.df
        self.logger.info(f"{in_file}")    
       
        self.segment_count = None
        self.segment_minsum = None
 
        # Produce Pandas time series from the NetCDF variables
        lon = self.var_series(in_file, ds['longitude'], ds['longitude_time'], args, angle=True).dropna()
        lat = self.var_series(in_file, ds['latitude'], ds['latitude_time'], args, angle=True).dropna()
        self.logger.info(f"Using {len(lon)} vehicle dead reckoned longitude and latitude values")
        self.logger.debug(lon)
        try:
            if nudge_to_platform:
                lon_fix, lat_fix = self.trackingdb_lat_lon(in_file, 3600, nudge_to_platform, nudge_interval)
                self.logger.info(f"Using {len(lon_fix)} lon_fix and lat_fix values from {nudge_to_platform} at {nudge_interval} minute intervals")
                self.logger.debug(lon_fix)
            elif replace_with_platform:
                self.logger.info(f"replace_with_platform = {replace_with_platform} passed in meaning that GPS values are not trusted and need to be replaced")
                if len(ds['latitude_fix']) == 0:
                    self.logger.warning(f"No values in lat_fix. Returning from nudge_coords() with replaced position values")
                else:
                    self.logger.info(f"A sample of the {len(ds['latitude_fix'])} points in the _fix variables:")
                    self.logger.info(self.var_series(in_file, ds['longitude_fix'], ds['longitude_fix_time'], args, angle=True))
                    self.logger.info(self.var_series(in_file, ds['latitude_fix'], ds['latitude_fix_time'], args, angle=True))
                lon_fix, lat_fix = self.trackingdb_lat_lon(in_file, 3600, replace_with_platform=replace_with_platform)
                # See https://stackoverflow.com/a/47148740
                oidx=lon_fix.index
                nidx = lon.index
                lon_replaced = lon_fix.reindex(oidx.union(nidx)).interpolate('index').reindex(nidx)
                lat_replaced = lat_fix.reindex(oidx.union(nidx)).interpolate('index').reindex(nidx)
                self.logger.info(f"Replaced latitude longitude positions from {in_file} with reindexed values from {replace_with_platform}")
                return lon_replaced, lat_replaced
            else:
                lon_fix = self.var_series(in_file, ds['longitude_fix'], ds['longitude_fix_time'], args, angle=True)
                lat_fix = self.var_series(in_file, ds['latitude_fix'], ds['latitude_fix_time'], args, angle=True)
                self.logger.info(f"Using {len(lon_fix)} longitude_fix and latititude_fix values from {in_file}")
                self.logger.debug(lon_fix)
        except IndexError:
            # Encountered in http://dods.mbari.org/opendap/data/lrauv/tethys/missionlogs/2019/20190528_20190604/20190530T185218/201905301852_201905302040.nc4.html
            # just 1 longitude_fix
            self.logger.warning(f"Apparently only one GPS fix in this log: lons = {ds['longitude_fix'][:]}, lats = {ds['latitude_fix'][:]}")
            self.logger.info("Returning from nudge_coords() with original coords")
            return lon, lat

        if args.remove_gps_outliers:
            # Identify any bad GPS fixes 
            bad_lat_fix_index = np.where(lat_fix.isna())
            bad_lon_fix_index = np.where(lon_fix.isna())

        self.logger.info(f"{'seg#':4s}  {'end_sec_diff':12s} {'end_lon_diff':12s} {'end_lat_diff':12s} {'len(segi)':9s} {'seg_min':>9s} {'u_drift (cm/s)':14s} {'v_drift (cm/s)':14s} {'start datetime of segment':>29}")
        
        # Any dead reckoned points before first GPS fix - usually empty as GPS fix happens before dive
        lon_nudged = np.array([])
        lat_nudged = np.array([])
        dt_nudged = np.array([], dtype='datetime64[ns]')
        if lat_fix.any():
            segi = np.where(lat.index < lat_fix.index[0])[0]
            if lon[:][segi].any():
                lon_nudged = lon[segi]
                lat_nudged = lat[segi]
                dt_nudged = lon.index[segi]
                self.logger.debug(f"Filled _nudged arrays with {len(segi)} values starting at {lat.index[0]} which were before the first GPS fix at {lat_fix.index[0]}")
        else:
            self.logger.warning(f"No values in lat_fix. Returning from nudge_coords() with original coords")
            return lon, lat

        if segi.any():
            seg_min = (lat.index[segi][-1] - lat.index[segi][0]).total_seconds() / 60
        else:
            seg_min = 0
        self.logger.info(f"{' ':4}  {'-':>12} {'-':>12} {'-':>12} {len(segi):-9d} {seg_min:9.2f} {'-':>14} {'-':>14} {'-':>29}")
       
        seg_count = 0 
        seg_minsum = 0
        for i in range(len(lat_fix) - 1):
            # Segment of dead reckoned (under water) positions, each surrounded by GPS fixes
            segi = np.where(np.logical_and(lat.index > lat_fix.index[i], 
                                           lat.index < lat_fix.index[i+1]))[0]
            if args.remove_gps_outliers:
                if i in bad_lat_fix_index[0] or i in bad_lon_fix_index[0]:
                    self.logger.debug(f"Setting to NaN dead reckoned values found between bad GPS times of {lat_fix.index[i]} and {lat_fix.index[i+1]}")
                    lon[segi] = np.nan
                    lat[segi] = np.nan
                    continue

            if not segi.any():
                self.logger.debug(f"No dead reckoned values found between GPS times of {lat_fix.index[i]} and {lat_fix.index[i+1]}")
                continue

            end_sec_diff = (lat_fix.index[i+1] - lat.index[segi[-1]]).total_seconds()
            if end_sec_diff > max_sec_diff_at_end:
                self.logger.warning(f"end_sec_diff ({end_sec_diff}) > max_sec_diff_at_end ({max_sec_diff_at_end})")

            end_lon_diff = lon_fix[i+1] - lon[segi[-1]]
            end_lat_diff = lat_fix[i+1] - lat[segi[-1]]
            seg_min = (lat.index[segi][-1] - lat.index[segi][0]).total_seconds() / 60
            seg_minsum += seg_min
            
            # Compute approximate horizontal drift rate as a sanity check
            u_drift = (end_lat_diff * cos(lat_fix[i+1]) * 60 * 185300
                        / (lat.index[segi][-1] - lat.index[segi][0]).total_seconds())
            v_drift = (end_lat_diff * 60 * 185300 
                        / (lat.index[segi][-1] - lat.index[segi][0]).total_seconds())
            self.logger.info(f"{i:4d}: {end_sec_diff:12.3f} {end_lon_diff:12.7f} {end_lat_diff:12.7f} {len(segi):-9d} {seg_min:9.2f} {u_drift:14.2f} {v_drift:14.2f} {lat.index[segi][-1]}")

            # Start with zero adjustment at begining and linearly ramp up to the diff at the end
            lon_nudge = np.interp( lon.index[segi].astype(np.int64), 
                                  [lon.index[segi].astype(np.int64)[0], lon.index[segi].astype(np.int64)[-1]],
                                  [0, end_lon_diff] )
            lat_nudge = np.interp( lat.index[segi].astype(np.int64), 
                                  [lat.index[segi].astype(np.int64)[0], lat.index[segi].astype(np.int64)[-1]],
                                  [0, end_lat_diff] )

            # Sanity checks
            if np.max(np.abs(lon[segi] + lon_nudge)) > 180 or np.max(np.abs(lat[segi] + lon_nudge)) > 90:
                self.logger.warning(f"Nudged coordinate is way out of reasonable range - segment {seg_count}")
                self.logger.warning(f" max(abs(lon)) = {np.max(np.abs(lon[segi] + lon_nudge))}")
                self.logger.warning(f" max(abs(lat)) = {np.max(np.abs(lat[segi] + lat_nudge))}")

            lon_nudged = np.append(lon_nudged, lon[segi] + lon_nudge)
            lat_nudged = np.append(lat_nudged, lat[segi] + lat_nudge)
            dt_nudged = np.append(dt_nudged, lon.index[segi])
            seg_count += 1
        
        # Any dead reckoned points after first GPS fix - not possible to nudge, just copy in
        # Don't include last point, otherwise get a "positional indexers are out-of-bounds" exception
        segi = np.where(lat.index > lat_fix.index[-1])[0][:-1]
        seg_min = 0
        if segi.any():
            lon_nudged = np.append(lon_nudged, lon[segi])
            lat_nudged = np.append(lat_nudged, lat[segi])
            dt_nudged = np.append(dt_nudged, lon.index[segi])
            seg_min = (lat.index[segi][-1] - lat.index[segi][0]).total_seconds() / 60
       
        self.logger.info(f"{seg_count+1:4d}: {'-':>12} {'-':>12} {'-':>12} {len(segi):-9d} {seg_min:9.2f} {'-':>14} {'-':>14}")
        self.segment_count = seg_count
        self.segment_minsum = seg_minsum

        self.logger.info(f"Points in final series = {len(dt_nudged)}")

        return pd.Series(lon_nudged, index=dt_nudged), pd.Series(lat_nudged, index=dt_nudged)

    def _common_time_index(self):
        '''Create a union of all time indexes for all parameters to load and fillin values at
        fillin_freq. This ensures that all parameters can use a common set of coordinates 
        making the data more useful when loaded into STOQS.
        '''
        # Use member variables assigned in processNc4FileDecimated()
        min_time = pd.Timestamp.max
        max_time = pd.Timestamp.min
        common_times = pd.DatetimeIndex([], dtype='datetime64[ns]')
        for group in self.df.groups:
            if group in self.group_parms.keys():
                self.logger.debug("Examining group %s from %s", group, self.in_file)
                for parameter in self.group_parms[group]:
                    self.logger.debug("parameter: %s", parameter)
                    for variable in self.df.groups[group].variables:
                        self.logger.debug("variable: %s", variable)
                        if parameter['name'] == variable:
                            self.logger.debug("Variable %s marked for loading", variable)
                            oidx = self.createSeries(self.df.groups[group].variables, variable, variable+'_'+'time').index
                            min_time = oidx.min() if oidx.min() < min_time else min_time
                            max_time = oidx.max() if oidx.max() > max_time else max_time
                            self.logger.info("Unionifying %d time index values from %s", len(oidx), variable)
                            common_times = common_times.union(oidx)

        common_times = common_times.drop_duplicates()
        self.logger.info("Final count of unioned times is %d between %s and %s", len(common_times), min_time, max_time) 
        return common_times, min_time, max_time

    def processNc4FileDecimated(self, url, in_file, out_file, parms, fillin_freq, group_parms, interp_key):
        self.reset()
        self.group_parms = group_parms
        parm_valid = []
        coord =  ['latitude', 'longitude', 'depth']

        self.df = netCDF4.Dataset(in_file, mode='r')
        self.in_file = in_file
        coord_ts = self.createCoord(coord)

        # Scan all netCDF variables to assemble a common time axis for all varaibles
        common_times, min_time, max_time = self._common_time_index()
        nidx = pd.date_range(min_time, max_time, freq=fillin_freq)

        # Create pandas time series for each parameter and store attributes - root group from .nc4 file
        for key in parms:
            try:
                ts = self.createSeries({}, key, key + '_time')
            except IndexError:
                ##self.logger.debug("Parameter %s not in root group of %s", key, in_file)
                continue
            ts = ts[~ts.index.duplicated(keep='first')]
            self.logger.info("Upsampling %s's %d values to '%s'", key, len(ts), fillin_freq)
            common_interp = common_times.union(nidx).drop_duplicates()
            ts = ts.reindex(common_interp).interpolate('index').reindex(nidx)
            self.logger.info("Number of upsampled values now in %s: %d", key, len(ts))
            try:
                ts = self.interpolate(ts, ts.index)
            except ValueError:
                self.logger.warning("Cannot interpolate %s", key)

            if ts.size == 0:
                self.logger.info('Variable ' + key + ' empty so skipping')
                continue

            attr = {}
            for name in self.df[key].ncattrs(): 
                self.logger.debug(f"Variable {key} has attribute {name}")
                attr[name]=getattr(self.df[key],name)
            self.all_attrib[key] = attr
            self.all_coord[key] = {'time': 'time', 'depth': 'depth', 'latitude': 'latitude', 'longitude': 'longitude'}
            parm_valid.append(key)
            self.all_sub_ts[key] = ts
            self.logger.debug('Found parameter ' + key)

        # Create pandas time series for each parameter in each group and store attributes
        for group in self.df.groups:
            g = None
            variables = None

            if group in group_parms.keys():
                g = group
            else:
                continue

            times = []
            subgroup = None
            pkeys = None

            try:
                subgroup = self.df.groups[g]
                pkeys = group_parms[g]

            except Exception as e:
                self.logger.error(e)
                continue

            # Create pandas time series for each parameter and store attributes
            if subgroup is not None and pkeys is not None:
                for p in pkeys:
                    try:
                        key = p["rename"]
                        var = p["name"]
                        ts = self.createSeries(subgroup.variables, var, var+'_'+'time')
                        ts = ts[~ts.index.duplicated(keep='first')]
                        self.logger.info("Upsampling %s's %d values to '%s'", var, len(ts), fillin_freq)
                        common_interp = common_times.union(nidx).drop_duplicates()
                        ts = ts.reindex(common_interp).interpolate('index').reindex(nidx)
                        self.logger.info("Number of upsampled values now in %s: %d", p, len(ts))
                        ts = self.interpolate(ts, ts.index)
                        attr = {}

                        # don't store or try to interpolate empty time series
                        if ts.size == 0:
                            self.logger.info('Variable ' + var + ' empty so skipping')
                            continue

                        for name in subgroup.variables[var].ncattrs():
                            attr[name] = getattr(subgroup.variables[var],name)

                        # Potential override of attributes from json data
                        for name in ('units', 'standard_name'):
                            try:
                                attr[name] = p[name]
                            except KeyError:
                                continue

                        self.all_attrib[key] = attr

                        if key.find('pitch') != -1 or key.find('roll') != -1 or key.find('yaw') != -1 or key.find('angle') != -1 or key.find('rate') != -1:
                            ts = ts * 180.0 / numpy.pi

                        # store for later processing into the netCDF
                        self.all_sub_ts[key] = ts
                        self.all_coord[key] = { 'time':'time', 'depth':'depth', 'latitude':'latitude', 'longitude':'longitude'}

                        self.logger.debug('Found in group ' + group + ' parameter ' + var + ' renaming to ' + key)
                        parm_valid.append(key)
                    except KeyError as e:
                        self.logger.debug(e)
                        continue
                    except Exception as e:
                        self.logger.error(e)
                        continue

        # create aligned lat/lon/depth coordinates for each parameter
        for key in parm_valid:
            # Get independent parameter to interpolate on - remove NaNs first
            self.all_sub_ts[key] = self.all_sub_ts[key].dropna()
            t = pd.Series(index = self.all_sub_ts[key].index, dtype='float64')
            self.all_coord[key] = { 'time': 'time', 'depth': 'depth', 'latitude': 'latitude', 'longitude': 'longitude'}

            # interpolate each coordinate to the time of the parameter
            for c in coord:
                try:
                    # get coordinate
                    ts = coord_ts[c]
                except KeyError as e:
                    msg = f"Required coordinate {c} missing from {url}"
                    self.logger.warning(msg)
                    raise MissingCoordinate(msg)

                # and interpolate using parameter time
                if not ts.empty:

                    self.logger.info("Variable %s, interpolating coordinate %s", key, c)
                    i = self.interpolate(ts, t.index)
                    self.all_sub_ts[c] = i
                    self.all_coord[c] = { 'time': 'time', 'depth': 'depth', 'latitude': 'latitude', 'longitude': 'longitude'}

            # add in time coordinate separately
            v_time = self.all_sub_ts[key].index
            esec_list = v_time.values.astype(dt.datetime)/1E9
            self.all_sub_ts['time'] = pd.Series(esec_list,index=v_time)

        # Get independent parameter to interpolate on
        t = pd.Series(index = self.all_sub_ts[interp_key].index, dtype='float64')

        # store time using interpolation parameter
        v_time = self.all_sub_ts[interp_key].index
        esec_list = v_time.values.astype(dt.datetime)/1E9
        self.all_sub_ts['time'] = pd.Series(esec_list,index=v_time)

        for key in coord:
            value = coord_ts[key]
            self.all_sub_ts[key] = value
            if not value.empty:
                self.logger.info("Interpolating coordinate %s", key)
                i = self.interpolate(value, t.index)
                self.all_sub_ts[key] = i
            else:
                self.all_sub_ts[key] = value

            self.all_coord[key] = { 'time': 'time', 'depth': 'depth', 'latitude':'latitude', 'longitude':'longitude'}

        self.logger.info(f"Collected data from {url}")
        shape_count = 0
        for parm in self.all_sub_ts.keys():
            if parm in parms:
                self.logger.info(f"{parm:11s} shape: {self.all_sub_ts[parm].shape}")
            else:
                self.logger.info(f"coordinate {parm:11s} shape: {self.all_sub_ts[parm].shape}")
            shape_count += self.all_sub_ts[parm].shape[0]

        self.logger.debug("shape_count = %s", shape_count)
        if shape_count > 0:
            # Write data to the file
            self.write_netcdf(out_file, url)
            self.logger.info('Wrote ' + out_file)

        # End processSingleParm

    def processNc4File(self, in_file, out_file, parm, resampleFreq):
        self.reset()
        all_ts = {}
        start_times = []
        end_times = []
        coord = ["latitude", "longitude", "depth", "time"]

        self.df = netCDF4.Dataset(in_file, mode='r')
        self.in_file = in_file

        all_ts = self.createCoord(coord)

        for group in self.df.groups:
            g = None
            variables = None

            if any(group in s for s in list(parm.keys())):
                g = group
            else:
                continue

            times = []
            subgroup = None
            pkeys = None

            # either a subgroup or a list of variables
            try:
                for key in subgroup:
                    subgroup = self.df.groups[g].group[key]
                    pkeys = list(parm[g][key].keys())
                    break

            except Exception as e:
                self.logger.error(e)
                self.logger.warning('falling back to main group %s' % group)
                subgroup = self.df.groups[g]
                pkeys = parm[g]

            if subgroup is not None and pkeys is not None:
                # Create pandas time series for each parameter and store attributes
                for v in pkeys:
                    try:
                        key = group + '_' + v # prepend the group name to the variable name to make it unique
                        ts = self.createSeries(subgroup.variables, v, v+'_'+'time')

                        # don't store or try to interpolate empty time series
                        if ts.size == 0:
                            self.logger.info('Variable ' + v + ' empty so skipping')
                            continue

                        attr = {}
                        for name in subgroup.variables[v].ncattrs():
                            attr[name]=getattr(subgroup.variables[v],name)

                        self.all_attrib[key] = attr

                        # resample using the mean
                        ts_resample = ts.resample(resampleFreq).mean()[:]
                        self.all_sub_ts[key] = ts_resample
                        self.all_coord[key] = { 'time': key+'_time', 'depth': key+' _depth', 'latitude': key+'_latitude', 'longitude':key+'_longitude'}

                        # create independent lat/lon/depth profiles for each parameter
                        # interpolate each coordinate to the time of the param
                        # key looks like sea_water_temperature_depth, sea_water_temperature_lat, sea_water_temperature_lon, etc.
                        for c in coord:
                            i = self.interpolate(ts, ts_resample.index)
                            self.all_sub_ts[key + '_' + c] = i
                            self.all_coord[key + '_' + c] = { 'time': key+'_time', 'depth': key+' _depth', 'latitude': key+
                                                              '_latitude', 'longitude':key+'_longitude'}

                        self.logger.info('Found parameter ' + key)
                    except KeyError as e:
                        self.logger.error(e)
                        continue
                    except Exception as e:
                        self.logger.error(e)
                        continue

        # Get time parameter and align other coordinates to this
        t = pd.Series(index = all_ts['time'].index)

        # resample
        t_resample = t.resample(resampleFreq)[:]

        # add in coordinates
        for key in coord:
            value = all_ts[key]
            i = self.interpolate(value, t_resample.index)
            self.all_sub_ts[key] = i
            self.all_coord[key] = { 'time': 'time', 'depth': 'depth', 'latitude':'latitude', 'longitude':'longitude'}

        self.logger.info("%s", list(self.all_sub_ts.keys()))

        # Write data to the file
        self.write_netcdf(out_file, in_file)
        self.logger.info('Wrote ' + out_file)

        # End processNc4


    def processResampleNc4File(self, in_file, out_file, parm, resampleFreq, rad_to_deg, args):
        self.reset()
        coord_ts = {}
        start_times = []
        end_times = []

        coord = ["latitude", "longitude", "depth", "time"]


        log_file = out_file.replace('.nc', '.log')
        fh = logging.FileHandler(log_file, 'w+')
        frm = logging.Formatter("%(levelname)s %(asctime)sZ %(filename)s %(funcName)s():%(lineno)d %(message)s")
        fh.setFormatter(frm)
        self.logger.addHandler(fh)

        self.in_file = in_file
        base_name = os.path.basename(in_file)
        os.system(f"/bin/cp {in_file} /tmp/{base_name}")
        self.logger.info('Reading %s file...' % in_file)
        self.logger.info(f"After copying to /tmp/{base_name}")
        self.df = netCDF4.Dataset(f"/tmp/{base_name}", mode='r')
        self.logger.info(f'Read file {in_file}')

        coord_ts = self.createCoord(coord)

        # Remove repeated or decreasing values from each coordinate - accumulate maxiumum to catch multiple decreased values
        # See: https://stackoverflow.com/questions/28563711/make-a-numpy-array-monotonic-without-a-python-loop
        for crd in coord:
            repeated_values = np.where(np.diff(np.maximum.accumulate(coord_ts[crd].index.astype('int'))) <= 0)[0]
            if len(repeated_values) > 0:
                self.logger.warning(f"Dropping from {crd} repeated/decreasing values at indices: {repeated_values}")
                coord_ts[crd].drop(coord_ts[crd].index[repeated_values], inplace=True)

        # Get time parameter and align everything to this
        self.logger.info(f'Creating t variable of the time indexes')
        t = pd.Series(index = coord_ts['time'].index, dtype=np.float64)

        # resample
        t_resample = t.resample(resampleFreq).asfreq()[:]

        nudge_to_platform=None
        nudge_interval=None
        replace_with_platform=None
        for group in self.df.groups:
            g = None
            variables = None

            if group in list(parm.keys()):
                g = group
            else:
                continue

            times = []
            subgroup = None
            pkeys = None

            try:
                subgroup = self.df.groups[g]
                pkeys = parm[g]

            except Exception as e:
                self.logger.error(e)
                raise e

            if subgroup is not None and pkeys is not None:
                # Create pandas time series for each parameter and store attributes
                for p in pkeys:
                    try:
                        key = p["rename"]
                        var = p["name"]
                        ts = self.createSeries(subgroup.variables, var, var+'_'+'time')
                        attr = {}

                        # don't store or try to interpolate empty time series
                        if ts.size == 0:
                            self.logger.info('Variable ' + var + ' empty so skipping')
                            continue

                        for name in subgroup.variables[var].ncattrs():
                            attr[name] = getattr(subgroup.variables[var],name)

                        # Potential override of attributes from json data
                        for name in ('units', 'standard_name'):
                            try:
                                attr[name] = p[name]
                            except KeyError:
                                continue

                        self.all_attrib[key] = attr

                        # resample using the mean then interpolate on to the time dimension
                        ts_resample = ts.resample(resampleFreq).mean()[:]
                        i = self.interpolate(ts_resample, t_resample.index)

                        if key.find('pitch') != -1 or key.find('roll') != -1 or key.find('yaw') != -1 or key.find('angle') != -1 or key.find('rate') != -1:
                            i = i * 180.0 / numpy.pi

                        # store for later processing into the netCDF
                        self.all_sub_ts[key] = i
                        self.all_coord[key] = { 'time':'time', 'depth':'depth', 'latitude':'latitude', 'longitude':'longitude'}

                        # plotting for debugging
                        '''fig, axes = plt.subplots(3)
                        plt.legend(loc='best')
                        axes[0].set_title('raw ' + var + ' data')
                        ts.plot(ax=axes[0],color='r')
                        axes[1].set_title('resampled')
                        ts_resample.plot(ax=axes[1],color='g')
                        axes[2].set_title('interpolated')
                        i.plot(ax=axes[2],color='b')
                        plt.show()'''

                        self.logger.info('Found in group ' + group + ' parameter ' + var + ' renaming to ' + key)
                    except KeyError as e:
                        self.logger.debug(f"{e} not in {in_file}")
                        continue
                    except Exception as e:
                        self.logger.error(e)
                        continue

        # add in navigation
        self.createNav(t_resample, resampleFreq)

        # add in coordinates
        for key in coord:
            try:
                value = coord_ts[key]
                if rad_to_deg:
                    if key.find('latitude') != -1 or key.find('longitude') != -1:
                        value = value * 180.0 / numpy.pi
                        # Navigation corrections, favor acoustic fixes over original nudged positions
                        if args.nudge:
                            if not self.nudged_file.get(in_file):
                                # Log files that have no GPS _fix variables can be found with:
                                # grep "No values in lat_fix" /mbari/LRAUV/brizo/missionlogs/2023/2023051*/*/*scieng.log

                                # But all ESP Cartridges were sampled under wgTiny in stoqs_canon_may2023, those missoins are found with:
                                # grep "Selecting Cart" /mbari/LRAUV/brizo/missionlogs/2023/202305*/*/syslog | cut -d/ -f1-8 | sort | uniq | xargs find | grep "nc4"
                                # Whose output are the values in this list:
                                bad_gps_files = [
                                    "/mbari/LRAUV/brizo/missionlogs/2023/20230518_20230525/20230519T145926/202305191459_202305191937.nc4",
                                    "/mbari/LRAUV/brizo/missionlogs/2023/20230518_20230525/20230519T193838/202305191938_202305200021.nc4",
                                    "/mbari/LRAUV/brizo/missionlogs/2023/20230518_20230525/20230520T002111/202305200021_202305210151.nc4",
                                    "/mbari/LRAUV/brizo/missionlogs/2023/20230518_20230525/20230521T015109/202305210151_202305220151.nc4",
                                    "/mbari/LRAUV/brizo/missionlogs/2023/20230518_20230525/20230522T015111/202305220151_202305221752.nc4",
                                    "/mbari/LRAUV/brizo/missionlogs/2023/20230518_20230525/20230522T175201/202305221752_202305232031.nc4",
                                    "/mbari/LRAUV/brizo/missionlogs/2023/20230518_20230525/20230523T203113/202305232031_202305241858.nc4",
                                ]
                                if in_file in bad_gps_files:
                                    replace_with_platform="wgTiny"
                                    # nudge_to_platform='wgTiny' doesn't seem to work well -- all dead reckoned postions drift egregiously to the west
                                    #nudge_to_platform="wgTiny"
                                    #nudge_interval=15
                                    #self.logger.info(f'Special handling of brizo during CANON May 2023: nudging underwater positions to {nudge_to_platform} every {nudge_interval} minutes')
                                    #self.nudged_lons, self.nudged_lats = self.nudge_coords(in_file, args, 10, nudge_to_platform, nudge_interval, replace_with_platform)
                                    self.logger.info(f'Special handling of brizo during CANON May 2023: replacing underwater positions with {replace_with_platform} values')
                                    self.nudged_lons, self.nudged_lats = self.nudge_coords(in_file, args, 10, replace_with_platform=replace_with_platform)
                                else:
                                    self.nudged_lons, self.nudged_lats = self.nudge_coords(in_file, args)
                                self.nudged_file[in_file] = True
                            if key.find('longitude') != -1 and self.nudged_lons.any():
                                value = self.nudged_lons
                            if key.find('latitude') != -1 and self.nudged_lats.any():
                                value = self.nudged_lats
                        if args.trackingdb:
                            if not self.tracking_file.get(in_file):
                                self.ac_lons, self.ac_lats = self.trackingdb_lat_lon(in_file)
                                self.tracking_file[in_file] = True
                            if key.find('longitude') != -1 and self.ac_lons.any():
                                value = self.ac_lons
                            if key.find('latitude') != -1 and self.ac_lats.any():
                                value = self.ac_lats

                if key == 'depth':
                    # Ad hoc QC for special cases
                    if 'brizo/missionlogs/2023/20230512_20230517/20230517T035153/202305170352_202305171120' in in_file:
                        value = value.mask(value > 1000, np.nan)  # Remove the 5 depth values greater than 1000 m

                i = self.interpolate(value, t_resample.index)
                if key == 'time':
                    repeated_values = np.where(np.diff(i.values) <= 0.1)[0]
                    if len(repeated_values) > 0:
                        self.logger.warning(f"Interpolated 'time' variable has {len(repeated_values)} repeated values at indices {repeated_values}")
                        self.logger.info(f"Overwriting interpolated repeated values with time's index values")
                        # Useful debugging code for verifying proper interpolation, e.g. no wild outliers in time
                        ##for counter, (rv, indxv) in enumerate(zip(i[repeated_values], i[repeated_values].index.astype(np.int64)/1E9)):
                        ##    print(f"{str(dt.datetime.fromtimestamp(rv))} <= {str(dt.datetime.fromtimestamp(indxv))}")
                        ##    if not counter % 10000:
                        ##        import pdb; pdb.set_trace()
                        i[repeated_values] = i[repeated_values].index.astype(np.int64)/1E9

                self.all_sub_ts[key] = i
                self.all_coord[key] = { 'time': 'time', 'depth': 'depth', 'latitude':'latitude', 'longitude':'longitude'}
            except (IndexError, ValueError) as e:
                self.logger.error(e)
                self.logger.error(f"Not creating {out_file}")
                return

        self.logger.info("%s", list(self.all_sub_ts.keys()))

        self.write_netcdf(out_file, in_file, nudge_to_platform, nudge_interval, replace_with_platform)
        self.logger.info('Wrote ' + out_file)
        self.logger.removeHandler(fh)

        self.logger.info(f"Removing /tmp/{base_name}")
        os.system(f"/bin/rm -f /tmp/{base_name}")

        # End processResampleNc4File

    def processResample(self, url, out_file, parm, interpFreq, resampleFreq):
        self.reset()
        esec_list = []
        self.parm =  ['latitude','longitude','depth'] + parm
        all_ts = {}
        start_times = []
        end_times = []

        try:
            self.df = pydap.client.open_url(url)
        except socket.error as e:
            self.logger.error('Failed in attempt to open_url(%s)', url)
            raise e
        except ValueError as e:
            self.logger.error('Value error when opening open_url(%s)', url)
            raise e

        # Create pandas time series and get sampling metric for each
        for key, value in list(parm.items()):
            try:
                p_ts = self.createSeriesPydap(key)
            except KeyError as e:
                p_ts = pd.Series()
                self.logger.info('Key error on ' + key)
                raise e

            all_ts[key] = p_ts
            try:
                (start,end) = self.getValidTimeRange(p_ts)
                start_times.append(start)
                end_times.append(end)
            except Exception:
                self.logger.info('Start/end ' + parm + ' time range invalid')

        # the full range should span all the time series data to store
        start_time = min(start_times)
        end_time = max(end_times)
        full_range = pd.date_range(start_time,end_time,freq=interpFreq)
        t = pd.Series(index = full_range)
        ts = t.index.values

        # convert time to epoch seconds
        esec_list = t.resample(resampleFreq).index.values.astype(dt.datetime)/1E9

        for key, value in list(all_ts.items()):
            if not value.empty :

                # swap byte order and create a new series
                values = value
                newvalues = values.byteswap().newbyteorder()
                pr = pd.Series(newvalues, index=value.index)

                # reindex to the full range that covers all data
                # forward fill
                pr.reindex(index = full_range, method='ffill')

                # interpolate onto regular time scale
                i = self.interpolate(pr, ts)
                try:
                    isub = i.resample(resampleFreq)[:]

                    # plotting for debugging
                    '''fig, axes = plt.subplots(4)
                    plt.legend(loc='best')
                    axes[0].set_title('raw ' + self.parm[j] + ' data')
                    p.plot(ax=axes[0],color='r')
                    axes[1].set_title('reindexed')
                    pr.plot(ax=axes[1],color='g')
                    axes[2].set_title('interpolated')
                    i.plot(ax=axes[2],color='b')
                    axes[3].set_title('resampled')
                    isub.plot(ax=axes[3],color='y')
                    plt.show()'''
                except IndexError as e:
                    self.logger.error(e)
                    raise e
                self.all_sub_ts[key] = isub
            else:
                self.all_sub_ts[key] = pd.Series()

        # Write data to the file
        self.write_netcdf(out_file, url)
        self.logger.info('Wrote ' + out_file)

        # End processResample

if __name__ == '__main__':

    pw = InterpolatorWriter()
    args = pw.process_command_line()
    nc4_file='/home/vagrant/LRAUV/daphne/missionlogs/2015/20150930_20151008/20151006T201728/201510062017_201510062027.nc4'
    nc4_file='/mbari/LRAUV/opah/missionlogs/2017/20170502_20170508/20170508T185643/201705081856_201705090002.nc4'
    nc4_file='/mbari/LRAUV/makai/missionlogs/2018/20180802_20180806/20180805T004113/201808050041_201808051748.nc4'
    nc4_file='/mbari/LRAUV/makai/realtime/sbdlogs/2019/201908/20190820T055043/shore.nc4'
    url_src='http://dods.mbari.org/opendap/data/lrauv/makai/realtime/sbdlogs/2019/201908/20190820T055043/shore.nc4'
    outDir = '/tmp/'
    resample_freq='10S'
    rad_to_deg = True
    parms = ['chlorophyll', 'temperature', 'oxygen', ]
    groupparms = '{' \
           '"CTD_NeilBrown": [ ' \
           '{ "name":"sea_water_salinity" , "rename":"salinity" }, ' \
           '{ "name":"sea_water_temperature" , "rename":"temperature" } ' \
           '],' \
           '"WetLabsBB2FL": [ ' \
           '{ "name":"mass_concentration_of_chlorophyll_in_sea_water", "rename":"chlorophyll" }, ' \
           '{ "name":"Output470", "rename":"bbp470" }, ' \
           '{ "name":"Output650", "rename":"bbp650" } ' \
           '],' \
           '"PAR_Licor": [ ' \
           '{ "name":"downwelling_photosynthetic_photon_flux_in_sea_water", "rename":"PAR" } ' \
           '],' \
           '"ISUS" : [ ' \
           '{ "name":"mole_concentration_of_nitrate_in_sea_water", "rename":"nitrate" } ' \
           '],' \
           '"Aanderaa_O2": [ ' \
           '{ "name":"mass_concentration_of_oxygen_in_sea_water", "rename":"oxygen" } ' \
           '] }'


    # Formulate new filename from the url. Should be the same name as the .nc4 specified in the url
    # with resample appended to indicate it has resampled data and is now in .nc format
    f = nc4_file.rsplit('/',1)[1]
    out_file = outDir + '.'.join(f.split('.')[:-1]) + '_' + resample_freq + '.nc'
    ##pw.processResampleNc4File(nc4_file, out_file, json.loads(parms),resample_freq, rad_to_deg, args)
    pw.logger.debug(f"Testing processNc4FileDecimated() to create {out_file}...")
    pw.processNc4FileDecimated(url_src, nc4_file, out_file, parms, '2S', json.loads(groupparms), 'depth')

    print('Done.')
