#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__doc__ = '''

Script to read data from CSV file and convert it to CF-NetCDF.
Use the conventions for Trajectory feature type.

Mike McCann
MBARI 29 May 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@license: __license__
'''

import csv
import time
import datetime
from pupynere import netcdf_file


ncFile = netcdf_file('simple.nc', 'w')
ncFile.history = 'Created for a test'

esec_list = []
lat_list = []
lon_list = []
dep_list = []
tem_list = []
sal_list = []
do_list = []

# GPCTD Timestamp, Latitude, Longitude, Pressure(decibars), Temperature(degrees C), Salinity(PSU), Conductivity(S/m), Dissolved Oxygen(frequency), Dissolved Oxygen(mL/L)
# 2012-05-21 20:10:00, 36.7989, -121.8609, 0.280, 12.169, 33.764, 3.889, 4390.700,  5.374
# 2012-05-21 20:10:10, 36.7989, -121.8609, 0.330, 12.148, 33.779, 3.888, 4397.800,  5.387
reader = csv.DictReader(open('waveglider_gpctd_WG.txt'))
for r in reader:
    gmtDTString = r['GPCTD Timestamp']
    tt = time.strptime(gmtDTString, '%Y-%m-%d %H:%M:%S')
    diff = datetime.datetime(*tt[:6]) - datetime.datetime(1970,1,1,0,0,0)

    esec_list.append(diff.days * 86400 + diff.seconds)
    lat_list.append(r[' Latitude'])
    lon_list.append(r[' Longitude'])
    dep_list.append(r[' Pressure(decibars)'])        # decibars is darn close to meters at the surface

    tem_list.append(r[' Temperature(degrees C)'])
    sal_list.append(r[' Salinity(PSU)'])
    do_list.append(r[' Dissolved Oxygen(mL/L)'])

pco2_esec_list = []
pco2_vars = [   'Latitude', 'Longitude', 'EquilPumpOn pco2', 'EquilPumpOn Temp', 'EquilPumpOn Pressure', 
                'EquilPumpOff pco2', 'EquilPumpOff Temp', 'EquilPumpOff Pressure', 'EquilPumpOff Humidity', 
                'ZeroPumpOn pco2', 'ZeroPumpOn Temp', 'ZeroPumpOn Pressure', 'ZeroPumpOff pco2', 'ZeroPumpOff Temp', 
                'ZeroPumpOff Pressure', 'AirPumpOn pco2', 'AirPumpOn Temp', 'AirPumpOn Pressure', 'AirPumpOff pco2', 
                'AirPumpOff Temp', 'AirPumpOff Pressure', 'AirPumpOff Humidity', 'StandardFlowOn Pressure', 
                'StandardFlowOff pco2', 'StandardFlowOff Temp', 'StandardFlowOff Pressure', 
                'StandardFlowOff pco2 Humidity', 'Durafet pH 1', 'Durafet pH 2', 'Durafet pH 3', 'Durafet pH 4', 
                'Durafet pH 5', 'Durafet pH 6', 'Can Humidity'
            ]

# PCO2 Timestamp, Latitude, Longitude, EquilPumpOn pco2, EquilPumpOn Temp, EquilPumpOn Pressure, EquilPumpOff pco2, EquilPumpOff Temp, EquilPumpOff Pressure, EquilPumpOff Humidity, ZeroPumpOn pco2, ZeroPumpOn Temp, ZeroPumpOn Pressure, ZeroPumpOff pco2, ZeroPumpOff Temp, ZeroPumpOff Pressure, AirPumpOn pco2, AirPumpOn Temp, AirPumpOn Pressure, AirPumpOff pco2, AirPumpOff Temp, AirPumpOff Pressure, AirPumpOff Humidity, StandardFlowOn Pressure, StandardFlowOff pco2, StandardFlowOff Temp, StandardFlowOff Pressure, StandardFlowOff pco2 Humidity, Durafet pH 1, Durafet pH 2, Durafet pH 3, Durafet pH 4, Durafet pH 5, Durafet pH 6, Can Humidity
# 2012-05-21 14:01:16, 36.8027, -121.7880,  529.253, 19.815, 90.205,  524.661, 19.890, 102.120, 1.932,   -5.944, 20.074,  96.341, -4.841, 20.096, 103.602, 412.191, 20.270,  92.218, 409.322, 20.335, 101.823,  1.868,  0.000,  0.000,  0.000,  0.000,  0.000, 47.730, 47.700, 47.680, 47.760, 47.670, 47.670,  1.350 
# 2012-05-21 20:56:12, 36.8144, -121.8926,  347.226, 17.569, 89.903,  343.045, 17.600, 101.133, 1.901,   -3.771, 17.663,  94.145, -3.577, 17.663, 101.618, 401.024, 17.726,  92.010, 397.178, 17.746, 102.030,  1.895,  0.000,  0.000,  0.000,  0.000,  0.000, 51.980, 53.500, 54.990, 56.410, 58.120, 59.020,  1.370
reader = csv.DictReader(open('waveglider_pco2_WG.txt'))
for r in reader:
    gmtDTString = r['PCO2 Timestamp']
    tt = time.strptime(gmtDTString, '%Y-%m-%d %H:%M:%S')
    diff = datetime.datetime(*tt[:6]) - datetime.datetime(1970,1,1,0,0,0)

    pco2_esec_list.append(diff.days * 86400 + diff.seconds)

    for v in pco2_vars:
        ncVar = v.replace(' ', '_', 42)
        try:
            exec "%s_list.append(r[' %s'])" % (ncVar, v, )
        except NameError:
            exec '%s_list = []' % ncVar
            exec "%s_list.append(r[' %s'])" % (ncVar, v, )


# Trajectory dataset, time is the only netCDF dimension
ncFile.createDimension('time', len(esec_list))

time = ncFile.createVariable('time', 'int32', ('time',))
time.units = 'seconds since 1970-01-01'
time[:] = esec_list

# Record Variables - coordinates for trajectory
latitude = ncFile.createVariable('latitude', 'float64', ('time',))
latitude.long_name = 'Latitude'
latitude.standard_name = 'latitude'
latitude.units = 'degree_north'
latitude[:] = lat_list

longitude = ncFile.createVariable('longitude', 'float64', ('time',))
longitude.long_name = 'Longitude'
longitude.standard_name = 'longitude'
longitude.units = 'degree_east'
longitude[:] = lon_list

depth = ncFile.createVariable('depth', 'float64', ('time',))
depth.long_name = 'Depth'
depth.standard_name = 'depth'
depth.units = 'm'
depth[:] = dep_list

# CTD variables
temp = ncFile.createVariable('temp', 'float64', ('time',))
temp.long_name = 'Temperature'
temp.standard_name = 'sea_water_temperature'
temp.units = 'Celsius'
temp[:] = tem_list

sal = ncFile.createVariable('salinity', 'float64', ('time',))
sal.long_name = 'Salinity'
sal.standard_name = 'sea_water_salinity'
sal[:] = sal_list

do = ncFile.createVariable('oxygen', 'float64', ('time',))
do.long_name = 'Dissolved Oxygen'
do.units = 'ml/l'
do[:] = do_list

# PCO2 variables - use fill values to pre-populate the arrays that have the same length as the CTD variables

# Trajectory dataset, time is the only netCDF dimension
ncFile.createDimension('pco2_time', len(pco2_esec_list))

pco2_time = ncFile.createVariable('pco2_time', 'int32', ('pco2_time',))
pco2_time.units = 'seconds since 1970-01-01'
pco2_time[:] = pco2_esec_list

for v in pco2_vars:
    print v
    ncVar = v.replace(' ', '_', 42)
    exec "%s = ncFile.createVariable('%s', 'float64', ('pco2_time',))" % (ncVar, ncVar, )
    exec "%s.long_name = '%s'" % (ncVar, v, )
    exec "%s[:] = %s_list" % (ncVar, ncVar, )

ncFile.close()


# function gen_WG_ncfile(outFilename, metadata, time, latitude, longitude, depth, conductivity, temperature, salinity, fluorescence, turbidity)
# %gen_WG_ncfile - Generates an Wave Glider netcdf file from telemetered data
# % This function creates, defines and fills in a netcdf file with Underway
# % data from the Liquid Robotics / MBARI Ocean Acidification waveglider
# % first deployed in the May 2012 CANON experiment
# %
# % Syntax: gen_WG_ncfile(outFilename, metadata, time, latitude, longitude, depth, conductivity, temperature, salinity, fluorescence, turbidity)
# %
# % Inputs:
# %  outFilename - Fully qualified name of the netcdf output file
# %  metadata - structure with fields representing global attributes of the dataset
# %  time - vector with timestamps (unix epoch seconds)
# %  latitude - vector with latitudes
# %  longitude - vector with longitudes
# %  depth - vector with dephts
# %  conductivity - vector with conductivities
# %  temperature - vector with temperatures
# %  salinity - vector with salinities
# %  fluorescence - vector with fluorescence
# %  pressure - vector with pressures
# %
# % Outputs: none
# %
# % Example:
# %  metadata.ship_name = 'JohnMartin';
# %  metadata.institution = 'MBARI';
# %  gen_UDAS_ncfile('27710_jhmudas_v1..nc', metadata, time, latitude, longitude, depth, conductivity, temperature, pressure, salinity, fluorescence, turbidity)
# %
# % Other m-files required: SNCTOOLS toolbox required
# % Subfunctions: none
# % MAT-files required: none
# %
# % See also: NC_CREATE_EMPTY, NC_ADD_DIMENSION, NC_ADDVAR, NC_ATTPUT, NC_VARPUT
# 
# % Original Author: Bartolome Garau
# % Work address: Parc Bit, Naorte, Bloc A 2 pis. pta. 3; Palma de Mallorca SPAIN. E-07121
# % Author e-mail: tgarau@socib.es
# % Website: http://www.socib.es
# % Creation: 04-Nov-2011
# % Modified: Modified for UDAS by Mike McCann 1 March 2012
# 
# %% Create empty file
    # nc_create_empty(outFilename)
# 
# %% Create unlimited time dimension 
#     recordDimName = 'time';
#     nc_add_dimension(outFilename, recordDimName, 0); % UNLIMITED
# 
# %% Pregenerate some 'typical' structure values
# 
#     varstruct.Nctype = 'NC_DOUBLE';
#     varstruct.Dimension = {recordDimName};
# 
#     attArray(1).Name  = 'long_name';
#     attArray(2).Name  = 'standard_name';
#     attArray(3).Name  = 'units';
#     attArray(4).Name  = '_FillValue';
#     attArray(4).Value = -1e6;
# 
#     lngname = 1;
#     stdname = 2;
#     unts    = 3;
# 
# %% Create coordinate variables
# 
#     % Create time variable
#     varstruct.Name = 'time';
#     
#     attArray(lngname).Value = 'epoch time';
#     attArray(stdname).Value = 'time';
#     attArray(unts   ).Value = 'seconds since 1970-01-01 00:00:00';
# 
#     varstruct.Attribute = attArray;
#     nc_addvar(outFilename, varstruct);
# 
#     % Create latitude variable
#     varstruct.Name = 'latitude';
#     
#     attArray(lngname).Value = 'latitude';
#     attArray(stdname).Value = 'latitude';
#     attArray(unts   ).Value = 'degree_north';
# 
#     varstruct.Attribute = attArray;
#     nc_addvar(outFilename, varstruct);
# 
#     % Create longitude variable
#     varstruct.Name = 'longitude';
#     
#     attArray(lngname).Value = 'longitude';
#     attArray(stdname).Value = 'longitude';
#     attArray(unts   ).Value = 'degree_east';
# 
#     varstruct.Attribute = attArray;
#     nc_addvar(outFilename, varstruct);
# 
#     % Create depth variable
#     varstruct.Name = 'depth';
#     
#     attArray(lngname).Value = 'Nominal intake depth';
#     attArray(stdname).Value = 'depth';
#     attArray(unts   ).Value = 'm';
# 
#     varstruct.Attribute = attArray;
#     nc_addvar(outFilename, varstruct);
# 
# %% Create scientific (CTD) variables
# 
#     % Create conductivity variable
#     varstruct.Name = 'conductivity';
#     
#     attArray(lngname).Value = 'water conductivity';
#     attArray(stdname).Value = 'sea_water_electrical_conductivity';
#     attArray(unts   ).Value = 'S m-1';
# 
#     varstruct.Attribute = attArray;
#     nc_addvar(outFilename, varstruct);
#     
#     % Create temperature variable
#     varstruct.Name = 'temperature';
#     
#     attArray(lngname).Value = 'water temperature';
#     attArray(stdname).Value = 'sea_water_temperature';
#     attArray(unts   ).Value = 'Celsius';
# 
#     varstruct.Attribute = attArray;
#     nc_addvar(outFilename, varstruct);
# 
# 
#     % Create salinity variable
#     varstruct.Name = 'salinity';
#     
#     attArray(lngname).Value = 'water salinity';
#     attArray(stdname).Value = 'sea_water_salinity';
#     attArray(unts   ).Value = '1';
# 
#     varstruct.Attribute = attArray;
#     nc_addvar(outFilename, varstruct);
#     
#     % Create fluorescence variable
#     varstruct.Name = 'fluorescence';
#     
#     attArray(lngname).Value = 'Calibrated Fluorescence from Scufa: S/N 0239';
#     attArray(stdname).Value = '';
#     attArray(unts   ).Value = 'NFU';
#     
#     varstruct.Attribute = attArray;
#     nc_addvar(outFilename, varstruct);
# 
#     % Create turbidity variable
#     varstruct.Name = 'turbidity';
#     
#     attArray(lngname).Value = 'Turbidity from Scufa';
#     attArray(stdname).Value = '';
#     attArray(unts   ).Value = 'NTU';
#     
#     varstruct.Attribute = attArray;
#     nc_addvar(outFilename, varstruct);
# 
# 
# %% Insert global metadata
# 
#     nc_attput(outFilename, nc_global, 'title', metadata.title);
#     nc_attput(outFilename, nc_global, 'netcdf_version', '3.6');
#     nc_attput(outFilename, nc_global, 'Convention', 'CF-1.4');
# 
#     dateString = datestr(now, 'yyyy-mm-ddThh:MM:ss');
# 
#     nc_attput(outFilename, nc_global, 'date_created', dateString);
#     nc_attput(outFilename, nc_global, 'date_update', dateString);
#     nc_attput(outFilename, nc_global, 'date_modified', dateString);
#  
#     nc_attput(outFilename, nc_global, 'cdm_data_type', 'trajectory');
#     nc_attput(outFilename, nc_global, 'CF_featureType', 'trajectory'); 
#     nc_attput(outFilename, nc_global, 'data_mode', 'R');
# 
#     nc_attput(outFilename, nc_global, 'geospatial_lat_min', min(latitude));
#     nc_attput(outFilename, nc_global, 'geospatial_lat_max', max(latitude));
# 
#     nc_attput(outFilename, nc_global, 'geospatial_lon_min', min(longitude));
#     nc_attput(outFilename, nc_global, 'geospatial_lon_max', max(longitude));
# 
#     nc_attput(outFilename, nc_global, 'geospatial_vertical_min', min(depth)); 
#     nc_attput(outFilename, nc_global, 'geospatial_vertical_max', max(depth));
# 
#     nc_attput(outFilename, nc_global, 'geospatial_lat_units', 'degree_north');
#     nc_attput(outFilename, nc_global, 'geospatial_lon_units', 'degree_east');
# 
#     nc_attput(outFilename, nc_global, 'geospatial_vertical_units', 'm');
#     nc_attput(outFilename, nc_global, 'geospatial_vertical_positive', 'down');
# 
#     matlabTime = datenum([1970, 1, 1, 0, 0, min(time)]); 
#     dateString = datestr(matlabTime, 'yyyy-mm-ddThh:MM:ss');
#     nc_attput(outFilename, nc_global, 'time_coverage_start', dateString);
# 
#     matlabTime = datenum([1970, 1, 1, 0, 0, max(time)]); 
#     dateString = datestr(matlabTime, 'yyyy-mm-ddThh:MM:ss');
#     nc_attput(outFilename, nc_global, 'time_coverage_end', dateString);
# 
#     licenseStatement = 'Approved for public release. Distribution Unlimited.';
#     nc_attput(outFilename, nc_global, 'distribution_statement', licenseStatement);
#     nc_attput(outFilename, nc_global, 'license', licenseStatement);
# 
#     attNames = fieldnames(metadata);
#     for idx = 1:length(attNames);
#         currAttName = attNames{idx};
#         nc_attput(outFilename, nc_global, currAttName, metadata.(currAttName));
#     end;
#     
# %% Fill in the dataset
# 
#     nc_varput(outFilename, 'time',         time);
#     nc_varput(outFilename, 'latitude',     latitude);
#     nc_varput(outFilename, 'longitude',    longitude);
#     nc_varput(outFilename, 'depth',        depth);
# 
#     nc_varput(outFilename, 'conductivity', conductivity);
#     nc_varput(outFilename, 'temperature',  temperature);
#     nc_varput(outFilename, 'salinity',     salinity);
#     nc_varput(outFilename, 'fluorescence', fluorescence);
#     nc_varput(outFilename, 'turbidity',    turbidity);
# 
# end
# # # 
