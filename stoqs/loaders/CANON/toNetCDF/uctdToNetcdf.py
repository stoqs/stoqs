#!/usr/bin/env python
'''
Script to read data from underway ctd files and write them to netCDF files.  

Use the conventions for Trajectory feature type and write as much metadata as possible.

This script is meant to preserve the data identically as it is reported in the orignal files.

Mike McCann
MBARI 11 January 2014
'''

import os
import sys
import csv
import time
import pytz
from glob import glob
from datetime import datetime, timedelta
from netCDF4 import Dataset

# Add grandparent dir to pythonpath so that we can see the CANON and toNetCDF modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../") )

from CANON.toNetCDF import BaseWriter

class ParserWriter(BaseWriter):
    '''
    Handle all information needed to parse Underway CTD data 
    and write the data as a CF-compliant NetCDF Trajectory files.
    '''
    _FillValue = -888888
    missing_value = -999999

    def process_files(self):
        if not self.args.depth:
            raise Exception('Must specify --depth for UCTD data')

        if self.args.format == 'Martin_UDAS':
            self.logger.info("Processing %s .txt files from directory '%s' with pattern '%s'" % (self.args.format, self.args.inDir, self.args.pattern))
            self.process_martinudas_files()
        else:
            self.logger.info("Processing Sea-Bird .asc and .hdr files from directory '%s' with pattern '%s'" % (self.args.inDir, self.args.pattern))
            self.process_seabird_files()

    def initialize_lists(self):
        self.esec_list = []
        self.lat_list = []
        self.lon_list = []
        self.dep_list = []          # Nominal depth, e.g. 2.0 for Western Flyer, 1.5 for Rachel Carson
        self.t1_list = []
        self.sal_list = []
        self.xmiss_list = []
        self.wetstar_list = []
        self.fl_scufa_list = []
        self.turb_scufa_list = []

    def process_seabird_files(self):
        '''
        Loop through all SeaBird .asc files in inDir matching pattern and load data into lists and call the write_ctd() method.

        Processed *.asc files look like:

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

        # Fill up the object's member data item lists from all the files - read only the processed .asc files that match the specified pattern, 
        self.logger.debug(f"Looking in {self.args.inDir} for files matching pattern {self.args.pattern}")
        fileList = glob(os.path.join(self.args.inDir, self.args.pattern))
        self.logger.debug(f"fileList = {fileList}")
        fileList.sort()
        for sb_file in fileList:
            if not sb_file.endswith('.asc'):
                continue
            self.logger.info("sb_file = %s" % sb_file)
            self.initialize_lists()

            # Open .hdr file to get the year, parse year from a line like this:
            # * System UTC = Sep 15 2012 06:49:50
            for line in open('.'.join(sb_file.split('.')[:-1]) + '.hdr'):
                if line.find('NMEA UTC (Time)') != -1:
                    year = int(line.split(' ')[7])
                    ##print "year = %d" % year
                    break

            for r in csv.DictReader(open(sb_file), delimiter=' ', skipinitialspace=True):
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
                self.dep_list.append(self.args.depth) 
                
                self.t1_list.append(r['T090C'])

                psal = r['Sal00']
                if self.args.min_psal:
                    if float(r['Sal00']) < self.args.min_psal:
                        psal = self.missing_value
                self.sal_list.append(psal)
                self.xmiss_list.append(r['Xmiss'])
                self.wetstar_list.append(r['WetStar'])

            self.write_ctd(sb_file)

    def process_martinudas_files(self):
        '''
        Loop through all Martin_UDAS .txt files in inDir matching pattern and load data into lists and call the write_ctd() method.
        Perform some range-checking quality control and describe the QC performed in the summary text added to the netCDF metadata.

        Processed *.txt files look like:

R/V_John_H._Martin_Underway_Data_Acquisition_System
YYYYMMDD HHMMSS_Local GMT Decimal_Julian_Day Decimal_Hour Latitude Longitude Depth Salinity_SBE45 Temperature_degrees_C_SBE45  Conductivity_S/m_SBE45 Raw_Fluorescence_Volts_Scufa Turbidity_Scufa Temperature_degrees_C_Scufa Percent_Humidity Barometer_Inches_Hg Barometer_mBar Air_Temp_C Air_Temp_F Average_Relative_Wind_Direction Average_Relative_Wind_Speed Average_True_Wind_Direction Average_True_Wind_Speed Average_Course_Over_Ground Average_Speed_Over_Ground Vector_Average_Heading  

20130923 084848 15:48:48 266.36722 8.81333 0.'000000 0.0'00000 0.000000  0.937900 17.355200 0.156940 0.000 0.000 0.000 87.000 30.357 1028.000 14.933 58.880 340.333 11.200 27.685 12.491 212.167 16.998 244.609
20130923 084859 15:48:59 266.36735 8.81639 36'48.172 121'47.832 0.000000  1.526000 17.353901 0.249250 0.289 0.280 17.800 87.000 30.357 1028.000 14.900 58.820 345.334 10.867 39.376 6.665 205.033 17.198 211.000
20130923 084906 15:49:06 266.36743 8.81833 36'48.148 121'47.852 0.000000  2.836700 17.313601 0.446990 0.291 0.277 17.800 87.000 30.357 1028.000 14.867 58.760 344.667 12.000 26.573 5.114 196.433 16.998 207.467

        '''

        # Allowed min & max values for range-check QC
        ranges = {  'Salinity_SBE45': (30, 40),
                    'Temperature_degrees_C_Scufa': (8, 20),
                 }

        # Fill up the object's member data item lists from all the files - read only the processed .asc files that match the specified pattern, 
        fileList = glob(os.path.join(self.args.inDir, self.args.pattern))
        fileList.sort()
        for udas_file in fileList:
            self.logger.info("udas_file = %s" % udas_file)
            self.initialize_lists()

            # Need to skip over first line in the data file, assume that the times are in Moss Landing Time zone
            fh = open(udas_file)
            fh.seek(0)
            next(fh)
            localtz = pytz.timezone ("America/Los_Angeles")

            for r in csv.DictReader(fh, delimiter=' ', skipinitialspace=True):
                if self.args.verbose:
                    self.logger.info('r = ', r)
                    for k,v in list(r.items()):
                        self.logger.info('%s: %s' % (k, v))

                # Skip over clearly bad values
                if r['Latitude'] == "0.'000000":
                    continue
                if float(r['Salinity_SBE45']) < ranges['Salinity_SBE45'][0] or float(r['Salinity_SBE45']) > ranges['Salinity_SBE45'][1]:
                    continue

                # Convert local time to GMT
                dt_naive = datetime(int(r['YYYYMMDD'][0:4]), int(r['YYYYMMDD'][4:6]), int(r['YYYYMMDD'][6:8]), 
                                    int(r['HHMMSS_Local'][0:2]), int(r['HHMMSS_Local'][2:4]), int(r['HHMMSS_Local'][4:6]))
                local_dt = localtz.localize(dt_naive, is_dst=None)
                es = time.mktime(local_dt.astimezone(pytz.utc).timetuple())
                if self.args.verbose:
                    self.logger.info(local_dt, local_dt.astimezone(pytz.utc), es)

                self.esec_list.append(es)

                # Convert degrees ' decimal minutes to decimal degrees.  Need to negate longitude
                lat = float(r['Latitude'].split("'")[0]) + float(r['Latitude'].split("'")[1]) / 60.0
                self.lat_list.append(lat)
                lon = float(r['Longitude'].split("'")[0]) + float(r['Longitude'].split("'")[1]) / 60.0
                self.lon_list.append(-lon)
                if self.args.verbose:
                    self.logger.info(lon, lat)

                self.dep_list.append(self.args.depth) 

                # The data 
                self.t1_list.append(r['Temperature_degrees_C_Scufa'])
                self.sal_list.append(r['Salinity_SBE45'])

                turb_scufa_val = self._FillValue
                if r['Turbidity_Scufa']:
                    if r['Turbidity_Scufa'] != 'None':
                        turb_scufa_val = r['Turbidity_Scufa']
                self.turb_scufa_list.append(turb_scufa_val)

                self.fl_scufa_val = self._FillValue
                if r['Raw_Fluorescence_Volts_Scufa']:
                    if r['Raw_Fluorescence_Volts_Scufa'] != 'None':
                        self.fl_scufa_val = r['Raw_Fluorescence_Volts_Scufa']
                self.fl_scufa_list.append(self.fl_scufa_val)

            self.write_ctd(udas_file, ranges)

    def write_ctd(self, inFile, ranges=None):
        '''
        Write lists out as NetCDF.
        '''

        # Create the NetCDF file
        outFile = '.'.join(inFile.split('.')[:-1]) + '.nc'
        self.ncFile = Dataset(outFile, 'w')

        # If specified on command line override the default generic title with what is specified
        self.ncFile.title = 'Underway CTD data'
        if self.args.title:
            self.ncFile.title = self.args.title

        # Combine any summary text specified on commamd line with the generic summary stating the original source file
        self.ncFile.summary = 'Observational oceanographic data translated with no modification from original data file %s' % inFile
        if self.args.summary:
            self.ncFile.summary = self.args.summary
            if not self.args.summary.endswith('.'):
                self.ncFile.summary += '.'
            self.ncFile.summary += ' Translated with no modification from original data file %s' % inFile

        # Add range-checking QC paramters to the summary
        if ranges:
            self.ncFile.summary += '. Range checking QC performed on the following variables with values outside of associated ranges discarded: %s' % ranges

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
        self.depth[:] = self.dep_list

        # Record Variables - Underway CTD Data
        temp = self.ncFile.createVariable('TEMP', 'float64', ('time',), fill_value=self._FillValue)
        temp.long_name = 'Temperature, 2 [ITS-90, deg C]'
        temp.standard_name = 'sea_water_temperature'
        temp.coordinates = 'time depth latitude longitude'
        temp.units = 'Celsius'
        temp.missing_value = self.missing_value
        temp[:] = self.t1_list

        sal = self.ncFile.createVariable('PSAL', 'float64', ('time',), fill_value=self._FillValue)
        sal.long_name = 'Salinity, Practical [PSU]'
        sal.standard_name = 'sea_water_salinity'
        sal.coordinates = 'time depth latitude longitude'
        sal.missing_value = self.missing_value
        sal[:] = self.sal_list

        if self.xmiss_list:
            xmiss = self.ncFile.createVariable('xmiss', 'float64', ('time',), fill_value=self._FillValue)
            xmiss.long_name = 'Beam Transmission, Chelsea/Seatech'
            xmiss.coordinates = 'time depth latitude longitude'
            xmiss.units = '%'
            xmiss.missing_value = self.missing_value
            xmiss[:] = self.xmiss_list

        if self.wetstar_list:
            wetstar = self.ncFile.createVariable('wetstar', 'float64', ('time',), fill_value=self._FillValue)
            wetstar.long_name = 'Fluorescence, WET Labs WETstar'
            wetstar.coordinates = 'time depth latitude longitude'
            wetstar.units = 'mg/m^3'
            wetstar.missing_value = self.missing_value
            wetstar[:] = self.wetstar_list

        if self.turb_scufa_list:
            turb_scufa = self.ncFile.createVariable('turb_scufa', 'float64', ('time',), fill_value=self._FillValue)
            turb_scufa.long_name = 'Turbidity_Scufa'
            turb_scufa.coordinates = 'time depth latitude longitude'
            turb_scufa.units = 'NTU'
            turb_scufa.missing_value = self.missing_value
            turb_scufa[:] = self.turb_scufa_list

        if self.fl_scufa_list:
            fl_scufa = self.ncFile.createVariable('fl_scufa', 'float64', ('time',), fill_value=self._FillValue)
            fl_scufa.long_name = 'Raw_Fluorescence_Volts_Scufa'
            fl_scufa.coordinates = 'time depth latitude longitude'
            fl_scufa.units = 'volts'
            fl_scufa.missing_value = self.missing_value
            fl_scufa[:] = self.fl_scufa_list

        self.add_global_metadata()

        self.ncFile.close()
        self.logger.info("Wrote %s" % outFile)

        # End write_ctd()


if __name__ == '__main__':

    pw = ParserWriter()
    pw.process_command_line()
    pw.process_files()
    pw.logger.info("Done.")


