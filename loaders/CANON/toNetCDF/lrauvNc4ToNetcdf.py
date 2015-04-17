#!/usr/bin/env python
import matplotlib
import matplotlib.pyplot as plt
import sys
import os
import errno
# Add grandparent dir to pythonpath so that we can see the CANON and toNetCDF modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../") )
import pdb
import numpy as np
import pandas as pd
import time
import datetime as dt
from time import mktime
from CANON.toNetCDF import BaseWriter
from pupynere import netcdf_file
import pydap.client 
import DAPloaders
import logging
import socket

class InterpolatorWriter(BaseWriter):

 logger = []
 logger = logging.getLogger('lrauvNc4ToNetcdf')
 fh = logging.StreamHandler()
 f = logging.Formatter("%(levelname)s %(asctime)sZ %(filename)s %(funcName)s():%(lineno)d %(message)s")
 fh.setFormatter(f)
 logger.addHandler(fh)
 logger.setLevel(logging.DEBUG)

 def write_netcdf(self, outFile, inUrl):
    
        # Check parent directory and create if needed
        dirName = os.path.dirname(outFile)
        try:
               os.makedirs(dirName)
        except OSError, e:
               if e.errno != errno.EEXIST:
                      raise

        # Create the NetCDF file
        self.ncFile = netcdf_file(outFile, 'w')

        # If specified on command line override the default generic title with what is specified
        self.ncFile.title = 'LRAUV interpolated data'

        # Combine any summary text specified on commamd line with the generic summary stating the original source file
        self.ncFile.summary = 'Observational oceanographic data translated with modification from original data file %s' % inUrl
    
        # If specified on command line override the default generic license with what is specified
    
        # Trajectory dataset, time is the only netCDF dimension
        self.ncFile.createDimension('time', len(self.esec_list))
        self.time = self.ncFile.createVariable('time', 'float64', ('time',))
        self.time.standard_name = 'time'
        self.time.units = 'seconds since 1970-01-01'
        self.time[:] = self.esec_list

        # Record Variables - coordinates for trajectory - save in the instance and use for metadata generation
        self.latitude = self.ncFile.createVariable('latitude', 'float64', ('time',))
        self.latitude.long_name = 'LATITUDE'
        self.latitude.standard_name = 'latitude'
        self.latitude.units = 'degree_north'
        i = self.parms.index('latitude')
        self.latitude[:] = self.parm_sub_ts[i]

        self.longitude = self.ncFile.createVariable('longitude', 'float64', ('time',))
        self.longitude.long_name = 'LONGITUDE'
        self.longitude.standard_name = 'longitude'
        self.longitude.units = 'degree_east'
        i = self.parms.index('longitude')
        self.longitude[:] = self.parm_sub_ts[i]

        self.depth = self.ncFile.createVariable('depth', 'float64', ('time',))
        self.depth.long_name = 'DEPTH'
        self.depth.standard_name = 'depth'
        self.depth.units = 'm'
        i = self.parms.index('depth')
        self.depth[:] = self.parm_sub_ts[i]
       
        # add in parameters
        for i in range(len(self.parms)):
            ts = self.parm_sub_ts[i]
            # done record empty variables
            if not ts.empty:
                   parm = self.parms[i]
                   v = self.initRecordVariable(parm)
                   v[:] = self.parm_sub_ts[i]

        self.add_global_metadata()

        self.ncFile.close()

        # End write_pctd()


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

 def createSeriesPydap(self, name):
     v = self.df[name]
     v_t = self.df[name+'_time'] 
     data = np.asarray(v_t)
     data[data/1e10 < -1.] = 'NaN'
     data[data/1e10 > 1.] ='NaN'
     v_time_epoch = data
     v_time = pd.to_datetime(v_time_epoch[:],unit='s')
     v_time_series = pd.Series(v[:],index=v_time)
     return v_time_series
     # End createSeriesPydap

 def initRecordVariable(self, name, units=None):
     # Create record variable to store in nc file   
     v = self.df[name]
     rc = self.ncFile.createVariable(name, 'float64', ('time',))
     if 'long_name' in v.attributes:
        rc.long_name = v.attributes['long_name']
     if 'standard_name' in v.attributes:
        rc.standard_name = v.attributes['standard_name']

     rc.coordinates = 'time depth latitude longitude'
     if units is None:
            rc.unit = v.attributes['units']
     else:
            rc.units = units
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

 def processSingleParm(self, url, outFile, parm):
     self.esec_list = []
     self.df = []
     self.parm_sub_ts = []
     self.chl_ts = None
     self.parms =  ['latitude','longitude','depth'] + [parm]
     parm_ts = []

     try:
            self.df = pydap.client.open_url(url)
     except socket.error,e:
            self.logger.error('Failed in attempt to open_url(%s)', url)
            raise e
    
    # Create pandas time series for each parameter
     for i in range(len(self.parms)):
            parm = self.parms[i]
            try:
                   p_ts = self.createSeriesPydap(parm)
            except KeyError:
                   p_ts = pd.Series()
                   self.logger.info('Key error on ' + parm)

            parm_ts.append(p_ts)

     # Last time series is the independent parameter to store
     t = pd.Series(index = parm_ts[-1].index)

     # convert time to epoch seconds
     self.esec_list = t.index.values.astype(float)/1E9

     j = 0
     for p in parm_ts:
            if not p.empty :
                   # interpolate all time series onto independent parameter time scale
                   i = self.interpolate(p, t.index)
                   '''fig, axes = plt.subplots(2)
                   plt.legend(loc='best')
                   isub.plot(ax=axes[0],color='r')
                   p.plot(ax=axes[0])
                   isub.plot(ax=axes[1],color='g')
                   i.plot(ax=axes[1])
                   plt.show()'''
                   self.parm_sub_ts.append(i)
            else:
                   self.parm_sub_ts.append(pd.Series())
            j = j + 1

     # Write data to the file
     self.write_netcdf(outFile, url)
     self.logger.info('Wrote ' + outFile)

     # End processSingleParm

 def process(self, url, outFile, parms, interpFreq, resampleFreq):
     self.esec_list = []
     self.df = []
     self.parm_sub_ts = []
     self.chl_ts = None
     self.parms =  ['latitude','longitude','depth'] + parms
     parm_ts = []
     start_times = []
     end_times = []

     try:
            self.df = pydap.client.open_url(url)
     except socket.error,e:
            self.logger.error('Failed in attempt to open_url(%s)', url)
            raise e
    
    # Create pandas time series and get sampling metric for each
     for i in range(len(self.parms)):
            parm = self.parms[i]
            try:
                   p_ts = self.createSeriesPydap(parm)
            except KeyError, e:
                   p_ts = pd.Series()
                   self.logger.info('Key error on ' + parm)
                   raise e

            parm_ts.append(p_ts)
            try:
                   (start,end) = self.getValidTimeRange(p_ts)   
                   start_times.append(start)
                   end_times.append(end)
            except:
                   self.logger.info('Start/end ' + parm + ' time range invalid')   

     # the full range should span all the time series data to store
     start_time = min(start_times)
     end_time = max(end_times)
     full_range = pd.date_range(start_time,end_time,freq=interpFreq)
     t = pd.Series(index = full_range)
     ts = t.index.values

     # convert time to epoch seconds
     self.esec_list = t.resample(resampleFreq).index.values.astype(float)/1E9

     j = 0
     for p in parm_ts:
            if not p.empty :

                   # swap byte order and create a new series
                   values = p.values
                   newvalues = values.byteswap().newbyteorder()
                   pr = pd.Series(newvalues, index=p.index)

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
                       axes[0].set_title('raw ' + self.parms[j] + ' data') 
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
                   self.parm_sub_ts.append(isub)
            else:
                   self.parm_sub_ts.append(pd.Series())
            j = j + 1

     # Write data to the file
     self.write_netcdf(outFile, url)
     self.logger.info('Wrote ' + outFile)
            
     # End process

if __name__ == '__main__':

    pw = InterpolatorWriter()
    pw.process_command_line()
    url = 'http://elvis.shore.mbari.org/thredds/dodsC/LRAUV/daphne/realtime/hotspotlogs/20140412T004330/hotspot-Normal_201404120043_201404120147.nc4'
    #untested url = 'http://dods.mbari.org/opendap/hyrax/data/lrauv/daphne/realtime/hotspotlogs/20140313T233828/hotspot-Normal_201403140010_201403140044.nc4'
    outDir = '/tmp/'

    # Formulate new filename from the url. Should be the same name as the .nc4 specified in the url
    # with _i.nc appended to indicate it has interpolated data and is now in .nc format
    f = url.rsplit('/',1)[1]
    outFile = outDir + '.'.join(f.split('.')[:-1]) + '_i.nc'
    pw.process(url,outFile)

    print 'Done.'
