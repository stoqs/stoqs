#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__doc__ = '''

Script to read data from Western Flyer Seabird underway ctd .asc files and 
write them to netCDF files.  

Use the conventions for Trajectory feature type and write as much metadata as possible.

This script is meant to preserve the data identically as it is reported in the
.asc files.  

Mike McCann
MBARI 17 September 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@license: __license__
'''

import os
import sys
import csv
import time
from glob import glob
import coards
import urllib2
from datetime import datetime, timedelta
import numpy as np
from pupynere import netcdf_file

# Add grandparent dir to pythonpath so that we can see the CANON and toNetCDF modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../") )

from CANON.toNetCDF import BaseWriter

class ParserWriter(BaseWriter):
    '''
    Handle all information needed to parse Western Flyer Underway CTD data from the Seabird software
    generated .asc files and write the data as a CF-compliant NetCDF Trajectory file.
    '''

    def __init__(self, inDir, outDir, beginFileString):
        '''
        Override BaseWriter's constructor as we need some additional parameters
        '''
        self.inDir = inDir
        self.outDir = outDir
        self.beginFileString = beginFileString

    def process_files(self, depth):
        '''
        Loop through all .asc files and load data into lists.  Pass in a float for @depth for intake depth in meters.  Flyer is about 2m, Carson is about 1.5m.

        Processed c*.asc files look like:

      TimeJ   Latitude  Longitude      C0S/m      T090C      T190C      Sal00      Xmiss        Bat         V1    WetStar         V0     Upoly0         V2 Nbin       Flag
 259.284912   36.11671 -122.19104   4.150175    15.4155    15.2129    33.3560    81.7596     0.8056     4.2088     4.1208     0.3327  33.292633     2.3317 6 0.0000e+00
 259.285583   36.11664 -122.19093   4.150087    15.4121    15.2068    33.3581    81.8932     0.7990     4.2155     4.0995     0.3313  33.521572     2.3409 6 0.0000e+00
 259.286285   36.11653 -122.19081   4.148937    15.4002    15.2046    33.3579    81.8649     0.8004     4.2141     4.0903     0.3307  32.890720     2.3156 6 0.0000e+00

        The realtime.asc file looks like:
        (No header, but the same columns except that the Flag column is replaced by Unix epoch seconds)

       261.7066551        36.114080      -122.200600         4.1550689        16.91964        16.69642        32.15976        76.97320         1.04685         3.96825         3.25088 0.27473        32.75335775         2.31013 1347926255
       261.7067708        36.114440      -122.200360         4.1560253        16.91517        16.74474        32.17160        79.59720         0.91277         4.10012         3.28751 0.27717        32.50915751         2.30037 1347926265
       261.7068866        36.114800      -122.200120         4.1555998        16.91589        16.72590        32.16735        79.86446         0.89936         4.11355         3.30582 0.27839        31.59340659         2.26374 1347926275

        '''

        # Fill up the object's member data item lists from all the files - read only the processed c*.asc files, 
        # the realtime.asc data will be processed by the end of the cruise
        fileList = glob(os.path.join(self.inDir, self.beginFileString + '*.asc'))
        fileList.sort()
        for file in fileList:
            print "file = %s" % file

            self.esec_list = []
            self.lat_list = []
            self.lon_list = []
            self.dep_list = []          # Nominal depth, e.g. 2.0 for Western Flyer, 1.5 for Rachel Carson
            self.t1_list = []
            self.sal_list = []
            self.xmiss_list = []
            self.wetstar_list = []

            # Open .hdr file to get the year, parse year from a line like this:
            # * System UTC = Sep 15 2012 06:49:50
            for line in open('.'.join(file.split('.')[:-1]) + '.hdr'):
                if line.find('NMEA UTC (Time)') != -1:
                    year = int(line.split(' ')[7])
                    ##print "year = %d" % year
                    break

            for r in csv.DictReader(open(file), delimiter=' ', skipinitialspace=True):
                # A TimeJ value of 1.0 is 0000 hours 1 January, so subtract 1 day
                dt = datetime(year, 1, 1, 0, 0, 0) + timedelta(days=float(r['TimeJ'])) - timedelta(days=1)
                ##print 'dt = ', dt
                esDiff = dt - datetime(1970, 1, 1, 0, 0, 0)
                es = 86400 * esDiff.days + esDiff.seconds
                ##print 'es = ', es, datetime.fromtimestamp(es)
                ##print 'r = ', r
                
                self.esec_list.append(es)
                self.lat_list.append(r['Latitude'])
                self.lon_list.append(r['Longitude'])
                self.dep_list.append(depth) 
        
                self.t1_list.append(r['T190C'])
                self.sal_list.append(r['Sal00'])
                self.xmiss_list.append(r['Xmiss'])
                self.wetstar_list.append(r['WetStar'])

            self.write_ctd(file[:-4]+'.nc')

    def write_ctd(self, outFile='uctd.nc'):
        '''
        Write lists out as NetCDF.
        '''

        # Create the NetCDF file
        self.ncFile = netcdf_file(outFile, 'w')
        self.outFile = outFile

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
        self.latitude[:] = self.lat_list

        self.longitude = self.ncFile.createVariable('longitude', 'float64', ('time',))
        self.longitude.long_name = 'LONGITUDE'
        self.longitude.standard_name = 'longitude'
        self.longitude.units = 'degree_east'
        self.longitude[:] = self.lon_list

        self.depth = self.ncFile.createVariable('depth', 'float64', ('time',))
        self.depth.long_name = 'DEPTH'
        self.depth.standard_name = 'depth'
        self.depth.units = 'm'
        self.depth[:] = self.dep_list

        # Record Variables - Underway CTD Data
        temp = self.ncFile.createVariable('TEMP', 'float64', ('time',))
        temp.long_name = 'Temperature, 2 [ITS-90, deg C]'
        temp.standard_name = 'sea_water_temperature'
        temp.coordinates = 'time depth latitude longitude'
        temp.units = 'Celsius'
        temp[:] = self.t1_list

        sal = self.ncFile.createVariable('PSAL', 'float64', ('time',))
        sal.long_name = 'Salinity, Practical [PSU]'
        sal.standard_name = 'sea_water_salinity'
        sal.coordinates = 'time depth latitude longitude'
        sal[:] = self.sal_list

        xmiss = self.ncFile.createVariable('xmiss', 'float64', ('time',))
        xmiss.long_name = 'Beam Transmission, Chelsea/Seatech'
        xmiss.coordinates = 'time depth latitude longitude'
        xmiss.units = '%'
        xmiss[:] = self.xmiss_list

        wetstar = self.ncFile.createVariable('wetstar', 'float64', ('time',))
        wetstar.long_name = 'Fluorescence, WET Labs WETstar'
        wetstar.coordinates = 'time depth latitude longitude'
        wetstar.units = 'mg/m^3'
        wetstar[:] = self.wetstar_list

        self.add_global_metadata()

        self.ncFile.close()
        print "Wrote %s" % pw.outFile

        # End write_ctd()


if __name__ == '__main__':

    # Accept optional arguments of input data directory name and output directory name
    # If not specified then the uctd is used. The third argument is the character(s) at
    # the begining of the .asc file names.  The fourrh is the intake water depth in m.
    try:
        inDir = sys.argv[1]
    except IndexError:
        inDir = 'uctd'
    try:
        outDir = sys.argv[2]
    except IndexError:
        outDir = 'uctd'
    try:
        beginFileString = sys.argv[3]
    except IndexError:
        beginFileString = 'c'
    try:
        depth = sys.argv[5]
    except IndexError:
        depth = 1.5

    pw = ParserWriter(inDir, outDir, beginFileString)
    pw.process_files(depth)
    ##pw.read_asc_files(depth)
    ##pw.write_ctd(ncFilename)


