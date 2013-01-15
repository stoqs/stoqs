#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__doc__ = '''

Script to read data from Western Flyer Seabird profile ctd .asc files and 
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
# Add grandparent dir to pythonpath so that we can see the CANON and toNetCDF modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../") )
import csv
import time
from glob import glob
import coards
import urllib2
from datetime import datetime, timedelta
import numpy as np
from pupynere import netcdf_file
from seawater import csiro

from CANON.toNetCDF import BaseWriter
from seabird import get_year_lat_lon, convert_up_to_down

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

    def process_asc_files(self):
        '''
        Loop through all .asc files and write each one out as a netCDF file trajectory format

        Processed c*.asc files look like:

      TimeJ       PrDM      DepSM      C0S/m      C1S/m      T090C      T190C        Bat      Xmiss         V1    Sbeox0V         V2  FlECO-AFL         V3     Upoly0         V4        Par         V5       AltM         V6      Sal00      Sal11 Potemp090C Potemp190C  Sigma-###  Sigma-###   Sbeox0PS Sbeox0ML/LSbeox0Mm/Kg       Nbin       Flag
 255.146576    201.000    199.418   3.624490   3.624558     8.9554     8.9567     0.5549    87.0474     4.3840     0.9861     0.9866     0.3602     0.0344  0.0002000     0.0000 1.0000e-12     0.1295     100.00     5.0000    34.0047    34.0043     8.9339     8.9352    26.3492    26.3487   25.01885    1.62677     70.846         45 0.0000e+00
 255.146622    200.000    198.436   3.624405   3.624416     8.9551     8.9556     0.5529    87.0908     4.3862 -9.990e-29     0.9866     0.3557     0.0342  0.0002000     0.0000 1.0000e-12     0.1294     100.00     5.0000    34.0046    34.0042     8.9337     8.9343    26.3492    26.3488 -9.990e-29 -9.990e-29 -9.990e-29         27 0.0000e+00
 255.146622    199.000    197.437   3.624085   3.624098     8.9518     8.9525     0.5547    87.0507     4.3842 -9.990e-29     0.9866     0.3700     0.0348  0.0002000     0.0000 1.0000e-12     0.1294     100.00     5.0000    34.0048    34.0044     8.9306     8.9312    26.3499    26.3494 -9.990e-29 -9.990e-29 -9.990e-29         22 0.0000e+00
        '''

        # Fill up the object's member data item lists from all the files - read only the processed c*.asc files, 
        # the realtime.asc data will be processed by the end of the cruise
        fileList = glob(os.path.join(self.inDir, self.beginFileString + '*.asc'))
        fileList.sort()
        for file in fileList:
            print "file = %s" % file
            if file == './pctd/c0912c01.asc':
                print "Converting %s up to down" % file
                file = convert_up_to_down(file)

            year, lat, lon = get_year_lat_lon(file)

            # Initialize member lists for each file processed
            self.esec_list = []
            self.lat_list = []
            self.lon_list = []
            self.pr_list = [] 
            self.t1_list = []
            self.sal_list = []
            self.xmiss_list = []
            self.ecofl_list = []

            for r in csv.DictReader(open(file), delimiter=' ', skipinitialspace=True):
                if not r['TimeJ']:
                    continue
                # A TimeJ value of 1.0 is 0000 hours 1 January, so subtract 1 day
                dt = datetime(year, 1, 1, 0, 0, 0) + timedelta(days=float(r['TimeJ'])) - timedelta(days=1)

                ##print dt
                esDiff = dt - datetime(1970, 1, 1, 0, 0, 0)
                es = 86400 * esDiff.days + esDiff.seconds
                ##print datetime.fromtimestamp(es)
                
                self.esec_list.append(es)
                self.lat_list.append(lat)
                self.lon_list.append(lon)
                self.pr_list.append(float(r['PrDM']))
        
                self.t1_list.append(r['T190C'])
                self.sal_list.append(r['Sal00'])
                self.xmiss_list.append(r['Xmiss'])
                self.ecofl_list.append(r['FlECO-AFL'])

            self.write_pctd(file)
    
    def write_pctd(self, inFile):
        '''
        Write lists out as NetCDF using the base name of the file for the .nc file that this creates.
        '''

        outFile = '.'.join(inFile.split('.')[:-1]) + '.nc'

        # Create the NetCDF file
        self.ncFile = netcdf_file(outFile, 'w')
        self.outFile = outFile

        # Trajectory dataset, time is the only netCDF dimension
        self.ncFile.createDimension('time', len(self.esec_list))
        self.time = self.ncFile.createVariable('time', 'float64', ('time',))
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
        self.depth[:] = csiro.depth(self.pr_list, self.lat_list)      # Convert pressure to depth

        # Record Variables - Underway CTD Data
        temp = self.ncFile.createVariable('TEMP', 'float64', ('time',))
        temp.long_name = 'Temperature, 2 [ITS-90, deg C]'
        temp.standard_name = 'sea_water_temperature'
        temp.units = 'Celsius'
        temp[:] = self.t1_list

        sal = self.ncFile.createVariable('PSAL', 'float64', ('time',))
        sal.long_name = 'Salinity, Practical [PSU]'
        sal.standard_name = 'sea_water_salinity'
        sal[:] = self.sal_list

        xmiss = self.ncFile.createVariable('xmiss', 'float64', ('time',))
        xmiss.long_name = 'Beam Transmission, Chelsea/Seatech'
        xmiss.units = '%'
        xmiss[:] = self.xmiss_list

        ecofl = self.ncFile.createVariable('ecofl', 'float64', ('time',))
        ecofl.long_name = 'Fluorescence, WET Labs ECO-AFL/FL'
        ecofl.units = 'mg/m^3'
        ecofl[:] = self.ecofl_list

        self.add_global_metadata()

        self.ncFile.close()

        # End write_pctd()


if __name__ == '__main__':

    # Accept optional arguments of input data directory name and output directory name
    # If not specified then the current directory is used
    try:
        inDir = sys.argv[1]
    except IndexError:
        inDir = '.'
    try:
        outDir = sys.argv[2]
    except IndexError:
        outDir = '.'
    try:
        beginFileString = sys.argv[3]
    except IndexError:
        beginFileString = 'c'               # Default of 'c' for CANON cruise data files

    pw = ParserWriter(inDir, outDir, beginFileString)
    pw.process_asc_files()


