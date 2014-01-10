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
import urllib2
import datetime
import numpy as np
from pupynere import netcdf_file

class BaseWriter(object):
    '''
    Common things used by ParserWriters
    '''

    def __init__(self, parentInDir, parentOutDir):
        '''
        Subclassed methods must assign ncFile 'title' and 'summary' attributes to succintly describe the data.

        title: A short description of the dataset.
            Write one sentence that describes the scope of the data contained within the file; answer the five "W's": Who, What, Where, Why, When.
            Please use the following construction guidelines for creating a meaningful title for your netCDF file. 
            Do not use all capitals or capitalize words other than proper nouns or widely used acronyms. 
            Avoid using acronyms, especially for projects or organizations. If you feel you must include an acronym, spell out the meaning 
            of the acronym then put the acronym in parentheses after the meaning. General construction guideline for data set title 
            "Summary of variables and feature type" collected by instrument(s) from the platform(s) in the sea_name(s) from 
            time_coverage_start to time_coverage_end; Here are some good examples: 
            a. Physical and chemical profile data from bottle and conductivity-temperature-depth (CTD) casts from the RV JERE CHASE in the Gulf of Maine from 1982 to 1984; 
            b. Temperature and salinity trajectory data from thermosalinograph measurements from the RV JERE CHASE in the Gulf of Maine from 1982 to 1984;

            A bad example would be: Temperature, Salinity and Chlorophyll Data from WADOE during NWCOP San Juan from the '80's.

        summary: A paragraph describing the dataset.
            Write a paragraph or abstract about the data contained within the file, expanding on the title to provide more information.
        '''

        self.parentInDir = parentInDir
        self.parentOutDir = parentOutDir
        self.ncFile.title = ''
        self.ncFile.summary = ''
            
    def add_global_metadata(self):
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
        self.ncFile.featureType = 'trajectory'
        self.ncFile.data_mode = 'R'
        self.ncFile.geospatial_lat_min = np.min(self.latitude[:])
        self.ncFile.geospatial_lat_max = np.max(self.latitude[:])
        self.ncFile.geospatial_lon_min = np.min(self.longitude[:])
        self.ncFile.geospatial_lon_max = np.max(self.longitude[:])
        self.ncFile.geospatial_lat_units = 'degree_north'
        self.ncFile.geospatial_lon_units = 'degree_east'

        self.ncFile.geospatial_vertical_min= np.min(self.depth[:])
        self.ncFile.geospatial_vertical_max= np.max(self.depth[:])
        self.ncFile.geospatial_vertical_units = 'm'
        self.ncFile.geospatial_vertical_positive = 'down'

        self.ncFile.time_coverage_start = coards.from_udunits(self.time[0], self.time.units).isoformat()
        self.ncFile.time_coverage_end = coards.from_udunits(self.time[-1], self.time.units).isoformat()

        self.ncFile.distribution_statement = 'Any use requires prior approval from the MBARI CANON PI: Dr. Francisco Chavez'
        self.ncFile.license = self.ncFile.distribution_statement
        self.ncFile.useconst = 'Not intended for legal use. Data may contain inaccuracies.'
        self.ncFile.history = 'Created by "%s" on %s' % (' '.join(sys.argv), iso_now,)


    def add_global_timeseries_metadata(self):
        '''
        This is the main advantage of using a class for these methods.  This method uses the
        instance variables to write metadata specific for the data that are written.
        '''

        iso_now = datetime.datetime.now().isoformat()

        self.ncFile.title = ''
        self.ncFile.netcdf_version = '3.6'
        self.ncFile.Conventions = 'CF-1.6'
        self.ncFile.date_created = iso_now
        self.ncFile.date_update = iso_now
        self.ncFile.date_modified = iso_now
        self.ncFile.featureType = 'timeseries'
        self.ncFile.data_mode = 'R'
        self.ncFile.geospatial_lat_min = np.min(self.latitude[:])
        self.ncFile.geospatial_lat_max = np.max(self.latitude[:])
        self.ncFile.geospatial_lon_min = np.min(self.longitude[:])
        self.ncFile.geospatial_lon_max = np.max(self.longitude[:])
        self.ncFile.geospatial_lat_units = 'degree_north'
        self.ncFile.geospatial_lon_units = 'degree_east'

        self.ncFile.geospatial_vertical_min= np.min(self.depth[:])
        self.ncFile.geospatial_vertical_max= np.max(self.depth[:])
        self.ncFile.geospatial_vertical_units = 'm'
        self.ncFile.geospatial_vertical_positive = 'down'

        self.ncFile.time_coverage_start = coards.from_udunits(self.time[0], self.time.units).isoformat()
        self.ncFile.time_coverage_end = coards.from_udunits(self.time[-1], self.time.units).isoformat()

        self.ncFile.distribution_statement = 'Any use requires prior approval from the MBARI CANON PI: Dr. Francisco Chavez'
        self.ncFile.license = self.ncFile.distribution_statement
        self.ncFile.useconst = 'Not intended for legal use. Data may contain inaccuracies.'
        self.ncFile.history = 'Created by "%s" on %s' % (' '.join(sys.argv), iso_now,)


if __name__ == '__main__':

    # Accept optional arguments of input data directory name, e.g. /mbari/Tracking/gliders, and output directory name
    # If not specified then the current directory is used

    try:
        inDir = sys.argv[1]
    except IndexError:
        inDir = '.'
    try:
        outDir = sys.argv[2]
    except IndexError:
        outDir = '.'

    bw = BaseWriter(parentInDir=inDir, parentOutDir=outDir)
    print "bw.parentInDir = %s, bw.parentOutDir = %s" % (bw.parentInDir, bw.parentOutDir)

