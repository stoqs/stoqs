#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__doc__ = '''

Base classes for writing NetCDF files for CANON campaigns.  Reuse 

Use the conventions for Trajectory feature type and write as much metadata as possible.

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
import coards
import logging
import urllib.request, urllib.error, urllib.parse
import datetime
import numpy as np
from git import Repo

class BaseWriter(object):
    '''
    Common things used by ParserWriters
    '''
    _FillValue = -1.e34
    missing_value = -1.e34

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    logger.addHandler(sh)
    formatter = logging.Formatter("%(levelname)s %(asctime)sZ %(filename)s %(funcName)s():%(lineno)d %(message)s")
    sh.setFormatter(formatter)

    def add_global_metadata(self, featureType='trajectory'):
        '''
        This is the main advantage of using a class for these methods.  This method uses the
        instance variables to write metadata specific for the data that are written.
        '''

        iso_now = datetime.datetime.now().isoformat()

        self.ncFile.netcdf_version = '3.6'
        self.ncFile.Conventions = 'CF-1.6'
        self.ncFile.date_created = iso_now
        self.ncFile.date_update = iso_now
        self.ncFile.date_modified = iso_now
        self.ncFile.featureType = featureType
        self.ncFile.data_mode = 'R'
        if os.environ.get('USER'):
            self.ncFile.user = os.environ.get('USER')
        if os.environ.get('HOSTNAME'):
            self.ncFile.hostname = os.environ.get('HOSTNAME')

        # Record source of the software producing this file
        app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
        repo = Repo(app_dir, search_parent_directories=True)
        self.ncFile.gitorigin = repo.remotes.origin.url
        self.ncFile.gitcommit = repo.head.commit.hexsha

        # Likely TypeError: 'float' object is not subscriptable
        try:
            self.ncFile.geospatial_lat_min = np.min(self.latitude[:])
        except TypeError:
            self.ncFile.geospatial_lat_min = self.latitude
        try:
            self.ncFile.geospatial_lat_max = np.max(self.latitude[:])
        except TypeError:
            self.ncFile.geospatial_lat_max = self.latitude
        try:
            self.ncFile.geospatial_lon_min = np.min(self.longitude[:])
        except TypeError:
            self.ncFile.geospatial_lon_min = self.longitude
        try:
            self.ncFile.geospatial_lon_max = np.max(self.longitude[:])
        except TypeError:
            self.ncFile.geospatial_lon_max = self.longitude

        self.ncFile.geospatial_lat_units = 'degree_north'
        self.ncFile.geospatial_lon_units = 'degree_east'

        self.ncFile.geospatial_vertical_min= np.min(self.depth[:])
        self.ncFile.geospatial_vertical_max= np.max(self.depth[:])
        self.ncFile.geospatial_vertical_units = 'm'
        self.ncFile.geospatial_vertical_positive = 'down'

        self.ncFile.time_coverage_start = coards.from_udunits(self.time[0], self.time.units).isoformat()
        self.ncFile.time_coverage_end = coards.from_udunits(self.time[-1], self.time.units).isoformat()

        self.ncFile.useconst = 'Not intended for legal use. Data may contain inaccuracies.'
        self.ncFile.history = 'Created by STOQS software command "%s" on %s' % (' '.join(sys.argv), iso_now,)

    def add_xarray_global_metadata(self, featureType='trajectory'):
        '''
        This is the main advantage of using a class for these methods.  This method uses the
        instance variables to write metadata specific for the data that are written.
        Used by lrauvNc4ToNetcdf.py ==> Need to manually maintain constency with add_global_metadata()  :-(
        '''

        iso_now = datetime.datetime.now().isoformat()

        self.Dataset.attrs["netcdf_version"] = '3.6'
        self.Dataset.attrs["Conventions"] = 'CF-1.6'
        self.Dataset.attrs["date_created"] = iso_now
        self.Dataset.attrs["date_update"] = iso_now
        self.Dataset.attrs["date_modified"] = iso_now
        self.Dataset.attrs["featureType"] = featureType
        self.Dataset.attrs["data_mode"] = 'R'
        if os.environ.get('USER'):
            self.Dataset.attrs["user"] = os.environ.get('USER')
        if os.environ.get('HOSTNAME'):
            self.Dataset.attrs["hostname"] = os.environ.get('HOSTNAME')

        # Record source of the software producing this file
        app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
        repo = Repo(app_dir, search_parent_directories=True)
        self.Dataset.attrs["gitorigin"] = repo.remotes.origin.url
        self.Dataset.attrs["gitcommit"] = repo.head.commit.hexsha

        # Likely TypeError: 'float' object is not subscriptable
        try:
            self.Dataset.attrs["geospatial_lat_min"] = np.min(self.latitude[:])
        except TypeError:
            self.Dataset.attrs["geospatial_lat_min"] = self.latitude
        try:
            self.Dataset.attrs["geospatial_lat_max"] = np.max(self.latitude[:])
        except TypeError:
            self.Dataset.attrs["geospatial_lat_max"] = self.latitude
        try:
            self.Dataset.attrs["geospatial_lon_min"] = np.min(self.longitude[:])
        except TypeError:
            self.Dataset.attrs["geospatial_lon_min"] = self.longitude
        try:
            self.Dataset.attrs["geospatial_lon_max"] = np.max(self.longitude[:])
        except TypeError:
            self.Dataset.attrs["geospatial_lon_max"] = self.longitude

        self.Dataset.attrs["geospatial_lat_units"] = 'degree_north'
        self.Dataset.attrs["geospatial_lon_units"] = 'degree_east'

        self.Dataset.attrs["geospatial_vertical_min"] = np.min(self.depth[:])
        self.Dataset.attrs["geospatial_vertical_max"] = np.max(self.depth[:])
        self.Dataset.attrs["geospatial_vertical_units"] = 'm'
        self.Dataset.attrs["geospatial_vertical_positive"] = 'down'

        self.Dataset.attrs["time_coverage_start"] = coards.from_udunits(self.time[0], self.time.units).isoformat()
        self.Dataset.attrs["time_coverage_end"] = coards.from_udunits(self.time[-1], self.time.units).isoformat()

        self.Dataset.attrs["useconst"] = 'Not intended for legal use. Data may contain inaccuracies.'
        self.Dataset.attrs["history"] = 'Created by STOQS software command "%s" on %s' % (' '.join(sys.argv), iso_now,)

    def process_command_line(self):
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS. 
        Guidelines for title and summary descriptions derived from NOAA NODC NetCDF Templates: http://www.nodc.noaa.gov/data/formats/netcdf/
        '''

        import argparse
        from argparse import RawTextHelpFormatter

        exampleString = ''
        # Known subclassed applications show some examples here
        if sys.argv[0].find('uctdToNetcdf.py') != -1:
            exampleString = sys.argv[0] + ' -i uctd -d 1.5'
            exampleString += '\n' + sys.argv[0] + ' -i uctd -d 1.5 -t "Underway CTD data from R/V John Martin during CANON - ECOHAB September 2013" '
        if sys.argv[0].find('pctdToNetcdf.py') != -1:
            exampleString = sys.argv[0] + ' -i pctd '
            exampleString += '\n' + sys.argv[0] + ' -i pctd -t "Profile CTD data from R/V Rachel Carson during CANON - ECOHAB March 2013" '

        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Convert data files to NetCDF format for loading into STOQS',
                                         epilog='Examples:' + '\n\n' + exampleString + '\n\nOutput files are written to the input directory.')
        parser.add_argument('-i', '--inDir', action='store', default='.',
                            help='Directory where the input data files are located')
        parser.add_argument('--inFile', action='store', default='.', help='Input data file')
        parser.add_argument('-d', '--depth', action='store', 
                            help='Nominal depth below the sea surface where the water is sampled - for uctd data')
        parser.add_argument('-t', '--title', action='store',
                            help='''title: A short description of the dataset.
Write one sentence that describes the scope of the data contained within the file; answer the five "W's": Who, What, Where, Why, When.
Please use the following construction guidelines for creating a meaningful title for your netCDF file:
- Do not use all capitals or capitalize words other than proper nouns or widely used acronyms. 
- Avoid using acronyms, especially for projects or organizations. If you feel you must include an acronym, spell out the meaning 
  of the acronym then put the acronym in parentheses after the meaning. 
General construction guideline for data set title:
  "Summary of variables and feature type" collected by instrument(s) from the platform(s) in the sea_name(s) from time_coverage_start to time_coverage_end; 
- Here are some good examples: 
  a. Physical and chemical profile data from bottle and conductivity-temperature-depth (CTD) casts from the RV JERE CHASE in the Gulf of Maine from 1982 to 1984; 
  b. Temperature and salinity trajectory data from thermosalinograph measurements from the RV JERE CHASE in the Gulf of Maine from 1982 to 1984;
                            ''')
        parser.add_argument('-s', '--summary', action='store',
                            help='''summary: A paragraph describing the dataset.
Write a paragraph or abstract about the data contained within the file, expanding on the title to provide more information.
                            ''')
        parser.add_argument('-l', '--license', action='store', default='MBARI provides data "as is", with no warranty, express or implied, of the quality or consistency. Data are provided without support and without obligation on the part of the Monterey Bay Aquarium Research Institute to assist in its use, correction, modification, or enhancement.',
                            help='''license: Describe the restrictions to data access and distribution.
                            ''')
        parser.add_argument('-f', '--format', action='store', default='SeaBird',
                            help='''Input file format: The default input file format is SeaBird .asc. Specify 'Martin_UDAS' for that .txt file format.''')
        parser.add_argument('-p', '--pattern', action='store', default='*',
                            help='''Pattern for matching input files in inDir. Specify a pattern according to the rules used by the Unix shell. Quote wild card characters.''')
        parser.add_argument('-a', '--analog', action='store', 
                            help='''Specify an analog channel to process into a netCDF variable. The format is <chan>:<var>:<units>, e.g. V0:rhodmain:volts''')
        parser.add_argument('--min_psal', action='store', type=float, help='Do not convert salinity values below this number')
        parser.add_argument('-v', '--verbose', action='store_true',
                            help='Turn on verbose output')

        self.args = parser.parse_args()

        if self.args.verbose:
            self.logger.setLevel(logging.DEBUG)


if __name__ == '__main__':
    '''
    Simple instantiation test
    '''

    bw = BaseWriter()
    bw.process_command_line()
    print((bw.args))

