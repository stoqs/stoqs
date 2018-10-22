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

import matplotlib as mpl
mpl.use('Agg')               # Force matplotlib to not use any Xwindows backend
import matplotlib.pyplot as plt
import sys
import os
import errno
# Add grandparent dir to pythonpath so that we can see the CANON and toNetCDF modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../") )
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

# Map common LRAUV variable names to CF standard names: http://cfconventions.org/standard-names.html
sn_lookup = {
             'bin_mean_temperature': 'sea_water_temperature',
             'bin_mean_salinity': 'sea_water_salinity',
             'bin_mean_chlorophyll': 'mass_concentration_of_chlorophyll_in_sea_water', 
            }


class InterpolatorWriter(BaseWriter):

    logger = logging.getLogger('lrauvNc4ToNetcdf')
    fh = logging.StreamHandler()
    f = logging.Formatter("%(levelname)s %(asctime)sZ %(filename)s %(funcName)s():%(lineno)d %(message)s")
    fh.setFormatter(f)
    logger.addHandler(fh)
    logger.setLevel(logging.DEBUG)
    df = []
    all_sub_ts = {}
    all_coord = {}
    all_attrib = {}

    def reset(self):
        self.df = []
        self.all_sub_ts = {}
        self.all_coord = {}
        self.all_attrib = {}

    def write_netcdf(self, out_file, in_url):

        # Check parent directory and create if needed
        dirName = os.path.dirname(out_file)
        try:
            os.makedirs(dirName)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        # Create the NetCDF file
        self.logger.debug("Creating netCDF file %s", out_file)
        self.ncFile = Dataset(out_file, 'w')

        # If specified on command line override the default generic title with what is specified
        self.ncFile.title = 'LRAUV interpolated data'

        # Combine any summary text specified on command line with the generic summary stating the original source file
        self.ncFile.summary = 'Observational oceanographic data translated with modification from original data file %s' % in_url

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
                try:
                    logging.debug("Adding in record variable %s", key)
                    v = self.initRecordVariable(key)
                    v[:] = self.all_sub_ts[key].values
                except Exception as e:
                    self.logger.error(e)
                    continue

        self.logger.debug("Adding in global metadata")
        self.add_global_metadata()
        if getattr(self, 'trackingdb_values'):
            self.ncFile.comment(f"latitude and longitude values interpolated from {self.trackingdb_values} values retrieved from {self.trackingdb_url}")

        self.ncFile.close()
        # End write_netcdf()


    def interpolate(self, data, times):
        x = np.asarray(times,dtype=np.float64)
        xp = np.asarray(data.index,dtype=np.float64)
        fp = np.asarray(data)
        ts = pd.Series(index=times)
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

    def createSeries(self, subgroup, name, tname):
        v = subgroup[name]
        v_t = subgroup[tname]
        v_time_epoch = v_t
        v_time = pd.to_datetime(v_time_epoch[:],unit='s',errors = 'coerce')
        v_time_series = pd.Series(v[:],index=v_time)
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

                rc.standard_name = key

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
        for v in self.df.variables:
            if any(v in s for s in nav):
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
                        ts_resample = ts.resample(resampleFreq).mean()[:]
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
                        self.logger.error(e)
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
                        print('Creating {}'.format(c))
                        ts = self.createSeries(self.df.variables, c, c+'_'+'time')
                        all_ts[c] = ts
                    except Exception as e:
                        self.logger.error('Error in creating coord {} {}'.format(c, e))
                        continue

        return all_ts
    # End createCoord

    def trackingdb_lat_lon(self, args, sec_extend=3600):
        '''Query MBARI's Tracking Database and return Pandas time series
        of any acoustic fixes found.
        '''
        self.logger.debug(f"Constructing trackingdb url to {sec_extend} seconds beyond time range of file")
        se = float(self.df['time'][0].data) - sec_extend
        ee = float(self.df['time'][-1].data) + sec_extend
        st = dt.datetime.utcfromtimestamp(se).strftime('%Y%m%dT%H%M%S')
        et = dt.datetime.utcfromtimestamp(ee).strftime('%Y%m%dT%H%M%S')
        vehicle = args.inDir.split('/')[3]
        url = f"http://odss.mbari.org/trackingdb/position/{vehicle}_ac/between/{st}/{et}/data.csv"
        self.trackingdb_url = url
        self.logger.debug(url)

        # Read positions from .csv response and collect into lists - expect less than 10^3 values
        ess = []
        lons = []
        lats = []
        with closing(requests.get(url, stream=True)) as resp:
            if resp.status_code != 200:
                logger.error('Cannot read %s, resp.status_code = %s', url, resp.status_code)
                return

            r_decoded = (line.decode('utf-8') for line in resp.iter_lines())
            lines = [line for line in csv.DictReader(r_decoded)]
            for r in reversed(lines):
                self.logger.debug(f"{float(r['epochSeconds'])}, {float(r['longitude'])}, {float(r['latitude'])}")
                ess.append(float(r['epochSeconds']))
                lons.append(float(r['longitude']))
                lats.append(float(r['latitude']))

        self.trackingdb_values = len(ess)
        v_time = pd.to_datetime(ess, unit='s',errors = 'coerce')
        lon_time_series = pd.Series(lons, index=v_time)
        lat_time_series = pd.Series(lats, index=v_time)

        return lon_time_series, lat_time_series

    def processNc4FileDecimated(self, url, in_file, out_file, parms, group_parms, interp_key):
        self.reset()
        parm_valid = []
        coord =  ['latitude','longitude','depth']

        self.df = netCDF4.Dataset(in_file, mode='r')
        coord_ts = self.createCoord(coord)

        # Create pandas time series for each parameter and store attributes
        for key in parms:
          try:
            ts = self.createSeriesPydap(key, key + '_time')
            if ts.size == 0:
                self.logger.info('Variable ' + key + ' empty so skipping')
                continue

            attr = {}
            for name in self.df[key].ncattrs(): 
                attr[name]=getattr(self.df[key],name)
            self.all_attrib[key] = attr
            self.all_coord[key] = {'time': 'time', 'depth': 'depth', 'latitude': 'latitude', 'longitude': 'longitude'}
            parm_valid.append(key)
            self.all_sub_ts[key] = ts
            self.logger.info('Found parameter ' + key)
          except Exception as e:
            self.logger.error(e)
            continue

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

                        self.logger.info('Found in group ' + group + ' parameter ' + var + ' renaming to ' + key)
                        parm_valid.append(key)
                    except KeyError as e:
                        self.logger.error(e)
                        continue
                    except Exception as e:
                        self.logger.error(e)
                        continue

        # create independent lat/lon/depth profiles for each parameter
        for key in parm_valid:
            # Get independent parameter to interpolate on
            t = pd.Series(index = self.all_sub_ts[key].index)
            self.all_coord[key] = { 'time': key+'_time', 'depth': key+'_depth', 'latitude': key+'_latitude', 'longitude':key+'_longitude'}

            # interpolate each coordinate to the time of the parameter
            # key looks like sea_water_temperature_depth, sea_water_temperature_lat, sea_water_temperature_lon, etc.
            for c in coord:

                # get coordinate
                ts = coord_ts[c]

                # and interpolate using parameter time
                if not ts.empty:

                    i = self.interpolate(ts, t.index)
                    self.all_sub_ts[key + '_' + c] = i
                    self.all_coord[key + '_' + c] = { 'time': key+'_time', 'depth': key+' _depth', 'latitude': key+'_latitude', 'longitude':key+'_longitude'}

            # add in time coordinate separately
            v_time = self.all_sub_ts[key].index
            esec_list = v_time.values.astype(dt.datetime)/1E9
            self.all_sub_ts[key + '_time'] = pd.Series(esec_list,index=v_time)

        # Get independent parameter to interpolate on
        t = pd.Series(index = self.all_sub_ts[interp_key].index)

        # store time using interpolation parameter
        v_time = self.all_sub_ts[interp_key].index
        esec_list = v_time.values.astype(dt.datetime)/1E9
        self.all_sub_ts['time'] = pd.Series(esec_list,index=v_time)

        for key in coord:
            value = coord_ts[key]
            self.all_sub_ts[key] = value
            if not value.empty :
               i = self.interpolate(value, t.index)
               self.all_sub_ts[key] = i
            else:
               self.all_sub_ts[key] = value

            self.all_coord[key] = { 'time': 'time', 'depth': 'depth', 'latitude':'latitude', 'longitude':'longitude'}

        self.logger.info("%s", self.all_sub_ts.keys())

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
                self.logger.warn('falling back to main group %s' % group)
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

        self.logger.info('Reading %s file...' % in_file)
        self.df = netCDF4.Dataset(in_file, mode='r')

        coord_ts = self.createCoord(coord)

        # Get time parameter and align everything to this
        t = pd.Series(index = coord_ts['time'].index)

        # resample
        t_resample = t.resample(resampleFreq).asfreq()[:]

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
                        self.logger.error(e)
                        continue
                    except Exception as e:
                        self.logger.error(e)
                        continue

        # add in navigation
        if resampleFreq == '2S':
            # Add roll, pitch, and yaw to only the 2S_eng.nc file
            self.createNav(t_resample, resampleFreq)

        # add in coordinates
        for key in coord:
            try:
                value = coord_ts[key]
                if rad_to_deg:
                    if key.find('latitude') != -1 or key.find('longitude') != -1:
                        value = value * 180.0/ numpy.pi
                        if args.trackingdb:
                            lons, lats = self.trackingdb_lat_lon(args)
                            if key.find('longitude') != -1 and lons.any():
                                value = lons
                            if key.find('latitude') != -1 and lats.any():
                                value = lats

                i = self.interpolate(value, t_resample.index)
                self.all_sub_ts[key] = i
                self.all_coord[key] = { 'time': 'time', 'depth': 'depth', 'latitude':'latitude', 'longitude':'longitude'}
            except Exception as e:
                self.logger.error(e)
                raise e

        self.logger.info("%s", list(self.all_sub_ts.keys()))

        self.write_netcdf(out_file, in_file)
        self.logger.info('Wrote ' + out_file)

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
    outDir = '/tmp/'
    resample_freq='10S'
    rad_to_deg = True
    parm = '{' \
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
    pw.processResampleNc4File(nc4_file, out_file, json.loads(parm),resample_freq, rad_to_deg, args)

    print('Done.')
