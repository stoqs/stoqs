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
import urllib.request, urllib.error, urllib.parse
from datetime import datetime, timedelta
import numpy as np
from netCDF4 import Dataset
from seawater import eos80

from CANON.toNetCDF import BaseWriter
from seabird import get_year_lat_lon, convert_up_to_down, PositionNotFound, HdrFileNotFound

class ParserWriter(BaseWriter):
    '''
    Handle all information needed to parse Western Flyer Underway CTD data from the Seabird software
    generated .asc files and write the data as a CF-compliant NetCDF Trajectory file.
    '''

    def process_asc_files(self):
        '''
        Loop through all .asc files and write each one out as a netCDF file trajectory format

        Processed c*.asc files look like:

      TimeJ       PrDM      DepSM      C0S/m      C1S/m      T090C      T190C        Bat      Xmiss         V1    Sbeox0V         V2  FlECO-AFL         V3     Upoly0         V4        Par         V5       AltM         V6      Sal00      Sal11 Potemp090C Potemp190C  Sigma-###  Sigma-###   Sbeox0PS Sbeox0ML/LSbeox0Mm/Kg       Nbin       Flag
 255.146576    201.000    199.418   3.624490   3.624558     8.9554     8.9567     0.5549    87.0474     4.3840     0.9861     0.9866     0.3602     0.0344  0.0002000     0.0000 1.0000e-12     0.1295     100.00     5.0000    34.0047    34.0043     8.9339     8.9352    26.3492    26.3487   25.01885    1.62677     70.846         45 0.0000e+00
 255.146622    200.000    198.436   3.624405   3.624416     8.9551     8.9556     0.5529    87.0908     4.3862 -9.990e-29     0.9866     0.3557     0.0342  0.0002000     0.0000 1.0000e-12     0.1294     100.00     5.0000    34.0046    34.0042     8.9337     8.9343    26.3492    26.3488 -9.990e-29 -9.990e-29 -9.990e-29         27 0.0000e+00
 255.146622    199.000    197.437   3.624085   3.624098     8.9518     8.9525     0.5547    87.0507     4.3842 -9.990e-29     0.9866     0.3700     0.0348  0.0002000     0.0000 1.0000e-12     0.1294     100.00     5.0000    34.0048    34.0044     8.9306     8.9312    26.3499    26.3494 -9.990e-29 -9.990e-29 -9.990e-29         22 0.0000e+00
        '''

        # Fill up the object's member data item lists from all the files - read only the processed *.asc files that match pattern, 
        self.logger.debug(f"Looking in {self.args.inDir} for files matching pattern {self.args.pattern}")
        fileList = glob(os.path.join(self.args.inDir, self.args.pattern))
        self.logger.debug(f"fileList = {fileList}")
        if not fileList:
            raise FileNotFoundError(f"No files with pattern {self.args.pattern} found in {self.args.inDir}")
    
        fileList.sort()
        for file in fileList:
            if not file.endswith('.asc'):
                continue
            self.logger.info("file = %s" % file)
            if file == './pctd/c0912c01.asc':
                # Special fix for first cast on September 2012 CANON cruise
                self.logger.info("Converting %s up to down" % file)
                file = convert_up_to_down(file)

            try:
                year, lat, lon = get_year_lat_lon(file)
            except HdrFileNotFound as e:
                self.logger.info(e)
                self.logger.info("Please make sure that the archive is consistent with naming of .asc, .btl, and .hdr files")
                continue
            except PositionNotFound as e:
                self.logger.info(e)
                continue

            # Initialize member lists for each file processed
            self.esec_list = []
            self.lat_list = []
            self.lon_list = []
            self.pr_list = [] 
            self.t_list = []
            self.sal_list = []
            self.xmiss_list = []
            self.ecofl_list = []
            self.wetstar_list = []
            self.oxygen_list = []
            if self.args.analog:
                self.an_chan, self.an_var, self.an_units = self.args.analog.split(':')
                self.analog_list = []

            for r in csv.DictReader(open(file, errors='ignore'), delimiter=' ', skipinitialspace=True):
                self.logger.debug(f"r = {r}")
                if not r['TimeJ']:
                    continue
                if r['TimeJ'] == '-9.990e-29':
                    continue
                # A TimeJ value of 1.0 is 0000 hours 1 January, so subtract 1 day
                dt = datetime(year, 1, 1, 0, 0, 0) + timedelta(days=float(r['TimeJ'])) - timedelta(days=1)

                ##print dt
                esDiff = dt - datetime(1970, 1, 1, 0, 0, 0)
                es = 86400 * esDiff.days + esDiff.seconds
                ##print datetime.fromtimestamp(es)
                
                self.esec_list.append(es)
                try:
                    self.lat_list.append(float(r['Latitude']))  # For tow-yo processed data
                except KeyError:
                    self.lat_list.append(lat)

                try:
                    self.lon_list.append(float(r['Longitude'])) # For tow-yo processed data
                except KeyError:
                    self.lon_list.append(lon)

                try:
                    self.pr_list.append(float(r['PrDM']))
                except KeyError:
                    self.pr_list.append(float(r['PrdM']))       # Sub compact rosette
       
                try: 
                    self.t_list.append(r['T190C'])
                except KeyError:
                    pass
                try:
                    self.t_list.append(r['Tv290C'])
                except KeyError:
                    pass

                self.sal_list.append(r['Sal00'])

                try:
                    self.xmiss_list.append(float(r['Xmiss']))
                except ValueError:
                    self.xmiss_list.append(self.missing_value)

                try:
                    self.ecofl_list.append(r['FlECO-AFL'])
                except KeyError:
                    pass
                try:
                    self.wetstar_list.append(r['WetStar'])
                except KeyError:
                    pass
                try:
                    self.oxygen_list.append(r['Sbeox0ML/L'])
                except KeyError:
                    pass

                if self.args.analog:
                    try:
                        self.analog_list.append(r[self.an_chan])
                    except KeyError:
                        pass

            self.write_pctd(file)
    
    def write_pctd(self, inFile):
        '''
        Write lists out as NetCDF using the base name of the file for the .nc file that this creates.
        '''

        outFile = '.'.join(inFile.split('.')[:-1]) + '.nc'

        # Create the NetCDF file
        self.ncFile = Dataset(outFile, 'w')

        # If specified on command line override the default generic title with what is specified
        self.ncFile.title = 'Profile CTD cast data'
        if self.args.title:
            self.ncFile.title = self.args.title

        # Combine any summary text specified on commamd line with the generic summary stating the original source file
        self.ncFile.summary = 'Observational oceanographic data translated with no modification from original data file %s' % inFile
        if self.args.summary:
            self.ncFile.summary = self.args.summary
            if not self.args.summary.endswith('.'):
                self.ncFile.summary += '.'
            self.ncFile.summary += ' Translated with no modification from original data file %s' % inFile

        # If specified on command line override the default generic license with what is specified
        if self.args.license:
            self.ncFile.license = self.args.license

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
        self.depth[:] = eos80.dpth(self.pr_list, self.lat_list)      # Convert pressure to depth

        # Record Variables - Profile CTD Data
        temp = self.ncFile.createVariable('TEMP', 'float64', ('time',))
        temp.long_name = 'Temperature, [ITS-90, deg C]'
        temp.standard_name = 'sea_water_temperature'
        temp.coordinates = 'time depth latitude longitude'
        temp.units = 'Celsius'
        temp[:] = self.t_list

        sal = self.ncFile.createVariable('PSAL', 'float64', ('time',))
        sal.long_name = 'Salinity, Practical [PSU]'
        sal.standard_name = 'sea_water_salinity'
        sal.coordinates = 'time depth latitude longitude'
        sal[:] = self.sal_list

        xmiss = self.ncFile.createVariable('xmiss', 'float64', ('time',), fill_value=self._FillValue)
        xmiss.long_name = 'Beam Transmission, Chelsea/Seatech'
        xmiss.coordinates = 'time depth latitude longitude'
        xmiss.missing_value = self.missing_value
        xmiss.units = '%'
        xmiss[:] = self.xmiss_list

        if self.ecofl_list:
            ecofl = self.ncFile.createVariable('ecofl', 'float64', ('time',))
            ecofl.long_name = 'Fluorescence, WET Labs ECO-AFL/FL'
            ecofl.coordinates = 'time depth latitude longitude'
            ecofl.units = 'mg/m^3'
            ecofl[:] = self.ecofl_list

        if self.wetstar_list:
            wetstar = self.ncFile.createVariable('wetstar', 'float64', ('time',))
            wetstar.long_name = 'Fluorescence, WET Labs WETstar'
            wetstar.coordinates = 'time depth latitude longitude'
            wetstar.units = 'mg/m^3'
            wetstar[:] = self.wetstar_list

        if self.oxygen_list:
            oxygen = self.ncFile.createVariable('oxygen', 'float64', ('time',))
            oxygen.long_name = 'Oxygen, SBE 43'
            oxygen.coordinates = 'time depth latitude longitude'
            oxygen.units = 'ml/l'
            oxygen[:] = self.oxygen_list

        if self.args.analog:
            if self.analog_list:
                analog = self.ncFile.createVariable(self.an_var, 'float64', ('time',))
                analog.coordinates = 'time depth latitude longitude'
                analog.units = self.an_units
                analog[:] = self.analog_list

        self.add_global_metadata()

        self.ncFile.close()
        self.logger.info('Wrote ' + outFile)

        # End write_pctd()


if __name__ == '__main__':

    pw = ParserWriter()
    pw.process_command_line()
    pw.process_asc_files()
    pw.logger.info('Done.')


