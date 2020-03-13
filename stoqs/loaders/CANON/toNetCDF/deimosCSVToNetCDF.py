#!/usr/bin/env python
'''
Script to read data from DEIMOS EK60 instrument at MARS and write out NetCDF.

Use the conventions for timeSeriesProfile feature type and write as much metadata as possible.

This script is meant to preserve the data identically as it is reported in the orignal files.

Mike McCann
MBARI 10 June 2019
'''

import os
import sys
import csv
import numpy as np
from collections import defaultdict
from datetime import datetime
from netCDF4 import Dataset

# Add grandparent dir to pythonpath so that we can see the CANON and toNetCDF modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../") )

from CANON.toNetCDF import BaseWriter

class ParserWriter(BaseWriter):
    '''Handle all information needed to parse EK60 CSV output
    and write the data as a CF-compliant NetCDF timeSeriesProfile file.
    '''
    _FillValue = 999
    missing_value = -999

    esec_list = []
    dep_list = []
    ad_list = []

    def _save_data(self, dep_per_time, ad_per_time):
        dep = dep_per_time[0]
        deps = []
        for dl in self.dep_list:
            if dep > dl:
                deps.append(self._FillValue)
            else:
                deps.append(ad_per_time.pop(0))
                dep = dep_per_time[0]

        self.ad_list.append(deps)

    def process_deimos_tsp_csv_file(self):
        '''Process DEIMOS data into a TimeSeriesProfile CF-NetCDF featureType file.
         The .csv file looks like:
Ping_index,Distance_gps,Distance_vl,Ping_date,Ping_time,Ping_milliseconds,Latitude,Longitude,Depth_start,Depth_stop,Range_start,Range_stop,Sample_count
0,-9.9e+37,0.0000000000,2019-10-06,00:00:01,250.0,999.0000000000,999.0000000000,-0.1909107200,999.7994406400,-0.1909107200,999.7994406400,2619,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-9.9e+37,-89.140898,-87.511737,-87.431613,-88.386803,-90.688064,-92.684762,-93.915170,-93.629650,-92.724587,-92.733174,-94.681568,-97.019348,-98.350405,-98.916013,....

        It's simpler than Sam's format with the acoustic intensity data in the None key in equal
        depth bins between Depth_start and Depth_stop.
        '''

        self._FillValue = -9.9e+37
        self.missing_value = -9.9e+37

        self.logger.info(f"Opening file {self.args.inFile} to collect acoustic data")
        with open(self.args.inFile) as fh:
            for count, rec in enumerate(csv.DictReader(fh)):
                self.logger.debug((rec['Ping_index'], rec['Ping_date'], rec['Ping_time'], rec['Sample_count']))
                dt = datetime.strptime(f"{rec['Ping_date']}{rec['Ping_time']}.{float(rec['Ping_milliseconds']):03.0f}", 
                                        "%Y-%m-%d%H:%M:%S.%f")
                if count == 0:
                    first_dt = dt
                    start_dep = float(rec['Depth_start'])
                    stop_dep = float(rec['Depth_stop'])
                    sample_count = int(rec['Sample_count'])

                assert(float(rec['Depth_start']) == start_dep)
                assert(float(rec['Depth_stop']) == stop_dep)
                assert(float(rec['Sample_count']) == sample_count)

                self.esec_list.append((dt - datetime(1970, 1, 1)).total_seconds())
                self.ad_list.append([float(d) for d in rec[None]])

        self.dep_list = np.linspace(start_dep, stop_dep, sample_count)

        self.logger.info(f"Collected {len(self.esec_list)} time steps, from {first_dt} to {dt}, between depths {start_dep} and {stop_dep}")
        self.write_sv(ad_name="sv38")

    def process_deimos_sam_csv_file(self):
        '''The .csv file looks like:
Process_ID, Interval, Layer, Sv_mean, NASC, Height_mean, Depth_mean, Layer_depth_min, Layer_depth_max, Ping_S, Ping_E, Dist_M, Date_M, Time_M, Lat_M, Lon_M, Noise_Sv_1m, Minimum_Sv_threshold_applied, Maximum_Sv_threshold_applied, Standard_deviation, Thickness_mean, Range_mean, Exclude_below_line_range_mean, Exclude_above_line_range_mean
10, 2597618, 7, -76.938230, 0.014737, 0.016895, 6.541552, 6.000000, 7.000000, 0, 112, 0.000000, 20190523, 00:17:39.6930, 999.00000000, 999.00000000, -999.000000, 0, 0, 0.00000004525452, 0.016895, 883.458448, 10.000000, 880.285609
10, 2597618, 8, -71.759814, 0.135963, 0.047305, 7.719744, 7.000000, 8.000000, 0, 112, 0.000000, 20190523, 00:17:39.6930, 999.00000000, 999.00000000, -999.000000, 0, 0, 0.00000013429169, 0.047305, 882.280256, 10.000000, 880.285609
        '''

        last_dt = None
        last_dep = 0

        depths = defaultdict(lambda:0)
        self.logger.info(f"Opening file {self.args.inFile} to collect depths")
        with open(self.args.inFile) as fh:
            for rec in csv.DictReader(fh, skipinitialspace=True):
                # Depth dimension
                dep = (float(rec['Layer_depth_min']) + float(rec['Layer_depth_max'])) / 2.0
                depths[dep] += 1
        self.dep_list = sorted(depths.keys())
        self.logger.info(f"Collected {len(self.dep_list)} depth from {self.dep_list[0]} m to {self.dep_list[-1]} m")

        dep_per_time = []
        ad_per_time = []
        self.logger.info(f"Opening file {self.args.inFile} to collect acoustic data")
        with open(self.args.inFile) as fh:
            for count, rec in enumerate(csv.DictReader(fh, skipinitialspace=True)):
                self.logger.debug(rec['Date_M'], rec['Time_M'], rec['Layer_depth_min'], rec['Depth_mean'], rec['Layer_depth_max'])
                dt = datetime.strptime(rec['Date_M']+rec['Time_M'], "%Y%m%d%H:%M:%S.%f")
                if dt != last_dt:
                    # A new time step encountered
                    if not count % (6 * 24):
                        self.logger.info(f"{dt}")
                    self.esec_list.append((dt - datetime(1970, 1, 1)).total_seconds())
                    if not dep_per_time:
                        first_dt = dt
                    else:
                        self._save_data(dep_per_time, ad_per_time)
                    dep_per_time = []
                    ad_per_time = []

                dep_per_time.append((float(rec['Layer_depth_min']) + float(rec['Layer_depth_max'])) / 2.0)
                ad_per_time.append(float(rec['Sv_mean'])) 
                last_dt = dt
                last_dep = dep

            # Save the last set of depth and acoustic data
            self._save_data(dep_per_time, ad_per_time)

        self.logger.info(f"Collected {len(self.esec_list)} time steps, from {first_dt} to {dt}")
        self.write_sv(ad_name='Sv_mean')

    def write_sv(self, ad_name='Sv_mean'):
        '''Write lists out as NetCDF.
        '''

        # Create the NetCDF file
        outFile = '.'.join(self.args.inFile.split('.')[:-1]) + '.nc'
        outFile = outFile.replace(' ', '_')
        self.ncFile = Dataset(outFile, 'w')

        # If specified on command line override the default generic title with what is specified
        self.ncFile.title = 'DEIMOS Acoustic Data'
        if self.args.title:
            self.ncFile.title = self.args.title

        # Combine any summary text specified on commamd line with the generic summary stating the original source file
        self.ncFile.summary = f"Observational oceanographic data translated from '{self.args.inFile}'"
        if self.args.summary:
            self.ncFile.summary = self.args.summary
            if not self.args.summary.endswith('.'):
                self.ncFile.summary += '.'
            self.ncFile.summary += ' Translated with no modification from original data file %s' % self.args.inFile

        # Text cribbed from the README
        self.ncFile.summary += '''
IMPORTANT: these acoustic data have gone through automated noise-removal
procedures, but have not been fully quality-controlled.  As such, they are
likely to contain spurious signals due to noise, non-biological scatterers, etc.
The data are binned at reduced spatial and temporal resolution and have not been
calibrated.
'''

        self.ncFile.summary += '''THESE DATA ARE NOT "SCIENCE QUALITY" AND SHOULD ONLY BE USED FOR PRELIMINARY VISUALIZATIONS.'

For data appropriate for publications, presentations, etc., please contact:

Kelly Benoit-Bird <kbb@mbari.org>
Chad Waluk <cwaluk@mbari.org>'''

        # If specified on command line override the default generic license with what is specified
        if self.args.license:
            self.ncFile.license = self.args.license

        # timeSeriesProfile dataset, time and depth are the netCDF dimensions with arrays
        self.ncFile.createDimension('time', len(self.esec_list))
        self.time = self.ncFile.createVariable('time', 'float64', ('time',))
        self.time.standard_name = 'time'
        self.time.units = 'seconds since 1970-01-01'
        self.time[:] = self.esec_list

        self.ncFile.createDimension('depth', len(self.dep_list))
        self.depth = self.ncFile.createVariable('depth', 'float64', ('depth',))
        self.depth.standard_name = 'depth'
        self.depth.units = 'm'
        self.depth[:] = self.dep_list

        # Position of MARS - singleton dimensions
        self.ncFile.createDimension('longitude', 1)
        self.longitude = self.ncFile.createVariable('longitude', 'float64', ('longitude',))
        self.longitude.standard_name = 'longitude'
        self.longitude.units = 'degrees_east'
        self.longitude[:] = [-122.18681000]

        self.ncFile.createDimension('latitude', 1)
        self.latitude = self.ncFile.createVariable('latitude', 'float64', ('latitude',))
        self.latitude.standard_name = 'latitude'
        self.latitude.units = 'degrees_north'
        self.latitude[:] = [36.71137000]


        # Record Variables - Acoustic Data
        ad = self.ncFile.createVariable(ad_name, 'float64', ('time', 'depth', 'latitude', 'longitude'), fill_value=self._FillValue)
        ad.long_name = 'SV'
        ad.coordinates = 'time depth latitude longitude'
        ad.units = 'db'
        ad.missing_value = self.missing_value
        ad_array = np.array(self.ad_list)
        ad[:,:,:,:] = ad_array.reshape(ad_array.shape[0], ad_array.shape[1], 1, 1)

        self.add_global_metadata(featureType='timeseriesProfile')

        self.ncFile.close()
        self.logger.info("Wrote %s" % outFile)

        # End write_sv()


if __name__ == '__main__':
    '''Example execution:
    Using process_deimos_sam_csv_file():
        stoqs/loaders/CANON/toNetCDF/deimosCSVToNetCDF.py --sam --inFile deimos-2019-CANON-Spring.csv
    Using process_deimos_tsp_csv_file():
        stoqs/loaders/CANON/toNetCDF/deimosCSVToNetCDF.py --inFile Deimos\ -\ Cleaned\ Smoothed\ Data\ -\ Original\ Full\ Resolution\ -\ 2019-10-06\ 0000to0100.sv.csv
    '''
    pw = ParserWriter()
    pw.process_command_line()
    ##pw.process_deimos_sam_csv_file()
    pw.process_deimos_tsp_csv_file()
    pw.logger.info("Done.")

