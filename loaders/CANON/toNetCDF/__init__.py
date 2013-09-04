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
        self.parentInDir = parentInDir
        self.parentOutDir = parentOutDir
            
    def add_global_metadata(self):
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

