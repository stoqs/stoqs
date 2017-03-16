#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__doc__ = '''

Script to read data from CSV formatted data that Monique makes from the ESP Drifter
platform and write them to netCDF files.  

    1. CTD 
    2. ISUS

Use the conventions for Trajectory feature type and write as much metadata as possible.

This script is meant to preserve the data identically as it is reported in the
.csv files.  Use ESP positions from the MBARI Tracking database and interpolate 
those as necessary to match the measurement data.

Mike McCann
MBARI 15 September 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@license: __license__
'''

import os
import sys
import csv
import time
import coards
import urllib.request, urllib.error, urllib.parse
import datetime
import numpy as np
from pupynere import netcdf_file

# Add grandparent dir to pythonpath so that we can see the CANON and toNetCDF modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../") )

from CANON.toNetCDF import BaseWriter

class ParserWriter(BaseWriter):
    '''
    Handle all information needed to parse LR Waveglider CSV files and produce 
    NetCDF for each of them
    '''

    #
    # Object-level dictionaries of interpolated lat lon for easy lookup by 5-sec measurement data
    #
    gps_lat = {}
    gps_lon = {}

    def __init__(self, parentDir):
        self.parentDir = parentDir
        # For reading from malibu on the Western Flyer
        ##self.read_gps(url='http://192.168.111.177/trackingdb/position/ESP/between/20120910T000000/20120920T000000/data.csv')
        self.read_gps()
       
    def read_gps(self, url='http://odss.mbari.org/trackingdb/position/ESP/between/20120910T000000/20120920T000000/data.csv'):
        '''
        Read the GPS positions from the .csv response and save in an array for easy lookup for the measurement data
        '''

        es = []
        la = []
        lo = []
        # Careful - trackingdb returns the records in reverse time order
        for r in csv.DictReader(urllib.request.urlopen(url)):
            es.append(int(round(float(r['epochSeconds']))))
            la.append(float(r['latitude']))
            lo.append(float(r['longitude']))

        print(("Read in %d ESP GPS records" % len(es)))

        # Create lookup to get lat & lon given any epoch second, accurate to integer seconds
        # Reverse the order for the numpy lat & lon arrays
        esArray = np.arange(es[-1], es[0], 1, dtype='int32')    # Reversed
        laArray = np.interp(esArray, np.array(es)[::-1], np.array(la)[::-1])
        loArray = np.interp(esArray, np.array(es)[::-1], np.array(lo)[::-1])

        for esecs, lat, lon in zip(esArray, laArray, loArray):
            #print esecs, lat, lon
            self.gps_lat[esecs] = lat
            self.gps_lon[esecs] = lon

        ##te = int(es[5])        # Test epoch seconds
        ##print 'te = ', te
        ##d = dict(e = te, lat = self.gps_lat[te], lon = self.gps_lon[te])
        ##print '{e}: self.gps_lat[{e}] = {lat}, self.gps_lon[{e}] = {lon}'.format(**d)
            
    def write_ctd(self, inFile='ESP_ctd.csv', outFile='ESP_ctd.nc'):
        '''
        Read in records from one of the ESP drifter and write out as NetCDF.  The records look like (time is local):

        year,month,day,hour,minute,second,temp,sal,chl (calibrated),chl (ini)
        2012,   9,  11,  15,  32,  38,15.24,33.34,0.68,2.54
        2012,   9,  11,  15,  37,  39,15.29,33.25,0.66,2.44
        '''

        # Initialize lists for the data to be parsed and written
        esec_list = []
        lat_list = []
        lon_list = []
        dep_list = []
        tem_list = []
        sal_list = []
        chl_cal_list = []
        chl_ini_list = []

        # Read data in from the input file
        reader = csv.DictReader(open(os.path.join(self.parentDir, inFile)))
        for r in reader:
            localDT = datetime.datetime(int(r['year']), int(r['month']), int(r['day']), 
                                        int(r['hour']), int(r['minute']), int(r['second']))
            ##print str(localDT)
            es = time.mktime(localDT.timetuple())

            esec_list.append(es)
            lat_list.append(self.gps_lat[es])
            lon_list.append(self.gps_lon[es])
            dep_list.append(10.0)               # For September 2012 ESP deployment the nominal depth is 10m
        
            tem_list.append(r['temp'])
            sal_list.append(r['sal'])
            chl_cal_list.append(r['chl (calibrated)'])
            chl_ini_list.append(r['chl (ini)'])

        # Create the NetCDF file
        self.ncFile = netcdf_file(outFile, 'w')
        self.outFile = outFile

        # Trajectory dataset, time is the only netCDF dimension
        self.ncFile.createDimension('time', len(esec_list))
        self.time = self.ncFile.createVariable('time', 'float64', ('time',))
        self.time.standard_name = 'time'
        self.time.units = 'seconds since 1970-01-01'
        self.time[:] = esec_list

        # Record Variables - coordinates for trajectory - save in the instance and use for metadata generation
        self.latitude = self.ncFile.createVariable('latitude', 'float64', ('time',))
        self.latitude.long_name = 'LATITUDE'
        self.latitude.standard_name = 'latitude'
        self.latitude.units = 'degree_north'
        self.latitude[:] = lat_list

        self.longitude = self.ncFile.createVariable('longitude', 'float64', ('time',))
        self.longitude.long_name = 'LONGITUDE'
        self.longitude.standard_name = 'longitude'
        self.longitude.units = 'degree_east'
        self.longitude[:] = lon_list

        self.depth = self.ncFile.createVariable('depth', 'float64', ('time',))
        self.depth.long_name = 'DEPTH'
        self.depth.standard_name = 'depth'
        self.depth.units = 'm'
        self.depth[:] = dep_list

        # Record Variables - CTD Data
        temp = self.ncFile.createVariable('TEMP', 'float64', ('time',))
        temp.long_name = 'Sea Water Temperature in-situ ITS-90 or IPTS-68 scale'
        temp.standard_name = 'sea_water_temperature'
        temp.coordinates = 'time depth latitude longitude'
        temp.units = 'Celsius'
        temp[:] = tem_list

        sal = self.ncFile.createVariable('PSAL', 'float64', ('time',))
        sal.long_name = 'Sea Water Salinity in-situ PSS 1978 scale'
        sal.standard_name = 'sea_water_salinity'
        sal.coordinates = 'time depth latitude longitude'
        sal[:] = sal_list

        chlcal = self.ncFile.createVariable('chl', 'float64', ('time',))
        chlcal.long_name = 'Chlorophyll'
        chlcal.coordinates = 'time depth latitude longitude'
        chlcal.units = '?'
        chlcal[:] = chl_cal_list

        chlini = self.ncFile.createVariable('chl_ini', 'float64', ('time',))
        chlini.long_name = 'Raw Chlorophyll'
        chlini.coordinates = 'time depth latitude longitude'
        chlini.units = '?'
        chlini[:] = chl_ini_list

        self.add_global_metadata()

        self.ncFile.close()

        # End write_gpctd()

    def write_isus(self, inFile='ESP_isus.csv', outFile='ESP_isus.nc'):
        '''
        Read in records from .csv file and write out as NetCDF.  Merge with GPS data from MBARI Tracking.
        This method builds the NetCDF variables dynamically using the Python 'exec' method.
        '''

        esec_list = []
        lat_list = []
        lon_list = []
        dep_list = []

        isus_vars = [   'no3' 
                    ]

        lastEs = 0
        reader = csv.DictReader(open(os.path.join(self.parentDir, inFile)))
        for r in reader:
            localDT = datetime.datetime(int(r['year']), int(r['month']), int(r['day']), 
                                        int(r['hour']), int(r['minute']), int(r['second']))
            ##print str(localDT)
            es = time.mktime(localDT.timetuple())
        
            if es <= lastEs:
                continue                        # Must have monotonically increasing time

            esec_list.append(es)
            lat_list.append(self.gps_lat[es])
            lon_list.append(self.gps_lon[es])
            dep_list.append(10.0)               # For September 2012 ESP deployment the nominal depth is 10m
        
            # This is kind of ridiculous for just one variable
            for v in isus_vars:
                ncVar = v.replace(' ', '_', 42)
                try:
                    exec("%s_list.append(r['%s'])" % (ncVar, v, ))
                except NameError:
                    exec('%s_list = []' % ncVar)
                    exec("%s_list.append(r['%s'])" % (ncVar, v, ))

            lastEs = es

        # Create the NetCDF file
        self.ncFile = netcdf_file(outFile, 'w')
        self.outFile = outFile

        # Trajectory dataset, time is the only netCDF dimension
        self.ncFile.createDimension('time', len(esec_list))
        self.time = self.ncFile.createVariable('time', 'float64', ('time',))
        self.time.standard_name = 'time'
        self.time.units = 'seconds since 1970-01-01'
        self.time[:] = esec_list

        # Record Variables - coordinates for trajectory - save in the instance and use for metadata generation
        self.latitude = self.ncFile.createVariable('latitude', 'float64', ('time',))
        self.latitude.long_name = 'LATITUDE'
        self.latitude.standard_name = 'latitude'
        self.latitude.units = 'degree_north'
        self.latitude[:] = lat_list

        self.longitude = self.ncFile.createVariable('longitude', 'float64', ('time',))
        self.longitude.long_name = 'LONGITUDE'
        self.longitude.standard_name = 'longitude'
        self.longitude.units = 'degree_east'
        self.longitude[:] = lon_list

        self.depth = self.ncFile.createVariable('depth', 'float64', ('time',))
        self.depth.long_name = 'DEPTH'
        self.depth.standard_name = 'depth'
        self.depth.units = 'm'
        self.depth[:] = dep_list

        # isus variables 
        for v in isus_vars:
            ncVar = v.replace(' ', '_', 42)
            # Only Latitude, Longitude, Depth, and Time variables are upper case to match other Glider data
            if v == 'Latitude' or v == 'Longitude':
                exec("self.%s = self.ncFile.createVariable('%s', 'float64', ('time',))" % (ncVar.lower(), ncVar.upper(), ))
            else:
                exec("self.%s = self.ncFile.createVariable('%s', 'float64', ('time',))" % (ncVar.lower(), ncVar, ))
            exec("self.%s.coordinates = 'time depth latitude longitude'" % ncVar.lower())
            exec("self.%s.long_name = '%s'" % (ncVar.lower(), v, ))
            exec("self.%s[:] = %s_list" % (ncVar.lower(), ncVar, ))

        self.add_global_metadata()

        self.ncFile.close()

        # End write_isus()


if __name__ == '__main__':

    # Accept optional argument of data directory name, e.g. /mbari/Tracking/gliders, otherwise current dir is used
    try:
        dataDir = sys.argv[1]
    except IndexError:
        dataDir = '.'

    pw = ParserWriter(parentDir=dataDir)
    pw.write_ctd()
    print(("Wrote %s" % pw.outFile))

    pw.write_isus()
    print(("Wrote %s" % pw.outFile))

