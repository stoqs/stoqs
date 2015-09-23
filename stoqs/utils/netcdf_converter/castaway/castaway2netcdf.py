#!/usr/bin/env python
import os
import sys
import csv
import time
import coards
import datetime
import re
import numpy as np
from pupynere import netcdf_file

#Code to convert a castaway ctd file to netcdf. 
#Use: castaway2netcdf folder cast_file netcdf_file
#  Ex: ./castaway2netcdf . test.csv foo.nc   ->Convert the file test.csv in this directory to the netcdf file foo.nc

#Example of a castaway file

#% Electronics calibration date,0001-01-01
#% Conductivity calibration date,2010-07-28
#% Temperature calibration date,2010-07-28
#% Pressure calibration date,2010-07-28
#%
#Time (Seconds),Pressure (Decibar),Temperature (Celsius),Conductivity (MicroSiemens per Centimeter)
#0.2,0,18.792793273925781,294.99874877929688


class ParserWriter(object):
    '''
    Handle all information needed to parse LR Waveglider CSV files and produce 
    NetCDF for each of them
    '''

    def __init__(self, parentDir,Infi, Outfi):
        self.parentDir = parentDir
	self.infile = Infi
	self.outfile = Outfi

    def write_nc(self):

#+++++++++++++++OPEN THE DATA FILE++++++++++++++++++++++++++++++++++
	f = open(inFile,"r")
	header = f.readlines() #read the file
	f.close()

#+++++++++++++++++++++HEADER+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#Extract all the header information, and the time, latitude,longitude
	SearchString = r"% ([\w\() ]+),([\d\w\:\-\.  ]+)" #search string for the header
	for Line in header:
	    Result = re.search(SearchString,Line) #Save the result of the search and look for the match with time,latitude,longitude  
	    if Result:
	      if Result.group(1) == "Cast time (UTC)": 
		  itime = Result.group(2)
	      if Result.group(1) == "Start latitude":
		  lat = Result.group(2)
	      if Result.group(1) == "Start longitude":
		  lon = Result.group(2)
	print itime, lat,lon   #We have the time, latitude and longitude extract from the header

#++++++++++++++++++LOAD DATA+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        fl=28 #Number of the first line after headers
	res = header[fl:]  #read all the data without the headers
    #+++++ START get the variables name and units++++++++++++  
	searchname=r"([\w+]+) ([\(\w+\)]+),([\w+]+) ([\(\w+\)]+),([\w+]+) ([\(\w+\)]+),([\w+]+) ([\(\w+\ \)]+)"
	v = re.search(searchname,res[0])
	  #Build a new colum label so DictReader could use the name as libraries
	res[0]=v.group(1) + ',' + v.group(3) + ',' + v.group(5) + ',' + v.group(7)
    #+++++ END get the variables name and units++++++++++++  


	data = csv.DictReader(res)
	ex = ['Pressure','Temperature','Conductivity']
	esec_list = []
#        print data['Temperature']
	i=0
	for r in data:
	    gmtDTString = r['Time'] #read the variable time and save it in CF-1.0 nercdf convention
	    tt = time.strptime(itime, '%Y-%m-%d %H:%M:%S') #Initial date
	    diff = datetime.datetime(*tt[:6]) - datetime.datetime(1970,1,1,0,0,0)
	    esec_list.append(diff.days * 86400 + diff.seconds  + float(gmtDTString))	    
	    for v in ex:
              try:
                  exec "%s_list.append(r['%s'])" % (v, v, ) #Try to add an element to the list, if the list doesn't exist and give an error, create it in the next two lines
              except NameError:
                  exec '%s_list = []' % v
                  exec "%s_list.append(r['%s'])" % (v, v, )


#++++++++++++++++++++++CREATE THE NETCDF FILE++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#       Create the NetCDF file
        self.ncFile = netcdf_file(outFile, 'w')
        self.outFile = outFile

        # Trajectory dataset, time is the only netCDF dimension
        self.ncFile.createDimension('time', len(esec_list))

        self.time = self.ncFile.createVariable('time', 'float64', ('time',))
        self.time.units = 'seconds since 1970-01-01'
        self.time[:] = esec_list

        # Write  variables 
            # Only Latitude, Longitude, Depth, and Time variables are upper case to match other Glider data
#            if v == 'Latitude' or v == 'Longitude':
        self.longitude = self.ncFile.createVariable('longitude', 'float64', ('time',))
	self.longitude[:]=lon
        self.latitude = self.ncFile.createVariable('latitude', 'float64', ('time',))
	self.latitude[:]=lat
        for v in ex:
            ncVar = v.replace(' ', '_', 42)

#                exec "self.%s = self.ncFile.createVariable('%s', 'float64', ('TIME',))" % (ncVar.lower(), ncVar.upper(), )
#            else:
            exec "self.%s = self.ncFile.createVariable('%s', 'float64', ('time',))" % (v, v, )
            exec "self.%s.long_name = '%s'" % (v, v, )
            exec "self.%s[:] = %s_list" % (v, v, )

        # Fudge up a depth variable with a value of zero
        self.depth = self.ncFile.createVariable('depth', 'float64', ('time',))
        self.depth.long_name = 'Depth'
        self.depth.standard_name = 'depth'
        self.depth.units = 'm'
#        self.depth[:] = np.zeros(len(self.time[:]))
	self.depth[:] = Pressure_list
        self.add_global_metadata()

        self.ncFile.close()

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
        self.ncFile.cdm_data_type = 'station'
        self.ncFile.CF_featureType = 'station'
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
    try:
        dataDir = sys.argv[1]
    except IndexError:
        dataDir = '.'

    try:
        inFile = sys.argv[2]
    except IndexError:
        inFile='test.csv' 

    try:
        outFile = sys.argv[3]
    except IndexError:
	outFile='foo.nc'
 
    

    netc = ParserWriter(parentDir=dataDir, Infi=inFile, Outfi=outFile)
    netc.write_nc()
