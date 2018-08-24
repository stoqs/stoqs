#!/usr/bin/env python
import os
import sys
import csv
import time
import coards
import datetime
import numpy as np
from pupynere import netcdf_file


class ParserWriter(object):
    '''
    Handle all information needed to parse LR Waveglider CSV files and produce 
    NetCDF for each of them
    '''

    def __init__(self, parentDir):
        self.parentDir = parentDir

    def write_nc(self):
        esec_list = []
        ex = ['col1', 'col2','col3','latitude','longitude'] #Colum labels
#        ex = csv.reader(open('info.txt'))
        reader = csv.DictReader(open('test.txt')) #open de the file and save the data in reader
        #Do a list of each label with the data on it
        for r in reader:
            gmtDTString = r['Time'] #read the variable time and save it in CF-1.0 nercdf convention
            tt = time.strptime(gmtDTString, '%Y-%m-%d %H:%M:%S')
            diff = datetime.datetime(*tt[:6]) - datetime.datetime(1970,1,1,0,0,0)
            esec_list.append(diff.days * 86400 + diff.seconds)
            #Create the list of all the variable 
            for v in ex:
                exec('%s_list = []' % (v)) 
                exec("%s_list.append(r['%s'])" % (v,v,))
#======================================================================
#       Create the NetCDF file
        outFile='foo1.nc'
        self.ncFile = netcdf_file(outFile, 'w')
        self.outFile = outFile

        # Trajectory dataset, time is the only netCDF dimension
        self.ncFile.createDimension('TIME', len(esec_list))

        self.time = self.ncFile.createVariable('TIME', 'float64', ('TIME',))
        self.time.units = 'seconds since 1970-01-01'
        self.time[:] = esec_list

        # Write  variables 
        for v in ex:
            ncVar = v.replace(' ', '_', 42)
            # Only Latitude, Longitude, Depth, and Time variables are upper case to match other Glider data
            print(v)
            if v == 'Latitude' or v == 'Longitude':
                exec("self.%s = self.ncFile.createVariable('%s', 'float64', ('TIME',))" % (ncVar.lower(), ncVar.upper(), ))
            else:
                exec("self.%s = self.ncFile.createVariable('%s', 'float64', ('TIME',))" % (ncVar.lower(), ncVar, ))
            exec("self.%s.long_name = '%s'" % (ncVar.lower(), v, ))
            exec("self.%s[:] = %s_list" % (ncVar.lower(), ncVar, ))

        # Fudge up a depth variable with a value of zero
        self.depth = self.ncFile.createVariable('DEPTH', 'float64', ('TIME',))
        self.depth.long_name = 'Depth'
        self.depth.standard_name = 'depth'
        self.depth.units = 'm'
        self.depth[:] = np.zeros(len(self.time[:]))

        self.add_global_metadata()

        self.ncFile.close()

        # End write_pco2()

    def add_global_metadata(self):
        '''
        This is the main advantage of using a class for these methods.  This method uses the
        instance variables to write metadata specific for the data that are written.
        '''

        iso_now = datetime.datetime.now().isoformat()

        self.ncFile.title = ''
        self.ncFile.netcdf_version = '3.6'
        self.ncFile.Convention = 'CF-1.4'
        self.ncFile.date_created = iso_now
        self.ncFile.date_update = iso_now
        self.ncFile.date_modified = iso_now
        self.ncFile.cdm_data_type = 'trajectory'
        self.ncFile.CF_featureType = 'trajectory'
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

    # Accept arguement of data directory name, e.g. /mbari/Tracking/gliders
    dataDir = '/home/flopez/dev/stoqshg/loaders/MarMenor/toNetCDF'
    netc = ParserWriter(parentDir=dataDir)
    netc.write_nc()

