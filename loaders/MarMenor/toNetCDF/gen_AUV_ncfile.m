function gen_AUV_ncfile(outFilename, metadata, time, latitude, longitude, depth, conductivity, temperature, pressure, salinity)
%gen_AUV_ncfile - Generates an AUV netcdf file from raw data
% This function creates, defines and fills in a netcdf file with AUV data
%
% Syntax: gen_AUV_ncfile(outFilename, metadata, time, latitude, longitude, depth, conductivity, temperature, pressure, salinity)
%
% Inputs:
%  outFilename - Fully qualified name of the netcdf output file
%  metadata - structure with fields representing global attributes of the dataset
%  time - vector with timestamps
%  latitude - vector with latitudes
%  longitude - vector with longitudes
%  depth - vector with dephts
%  conductivity - vector with conductivities
%  temperature - vector with temperatures
%  pressure - vector with pressures
%  salinity - vector with salinities
%
% Outputs: none
%
% Example:
%  metadata.vehicle_name = 'SPARUS';
%  metadata.institution = 'UdG';
%  gen_AUV_ncfile('Sparus_Cartagena2011.nc', metadata, time, latitude, longitude, depth, conductivity, temperature, pressure, salinity)
%
% Other m-files required: SNCTOOLS toolbox required
% Subfunctions: none
% MAT-files required: none
%
% See also: NC_CREATE_EMPTY, NC_ADD_DIMENSION, NC_ADDVAR, NC_ATTPUT, NC_VARPUT

% Author: Bartolome Garau
% Work address: Parc Bit, Naorte, Bloc A 2 pis. pta. 3; Palma de Mallorca SPAIN. E-07121
% Author e-mail: tgarau@socib.es
% Website: http://www.socib.es
% Creation: 04-Nov-2011

%% Create empty file
	nc_create_empty(outFilename)

%% Create unlimited time dimension 
	recordDimName = 'time';
	nc_add_dimension(outFilename, recordDimName, 0); % UNLIMITED

%% Pregenerate some 'tipical' structure values

	varstruct.Nctype = 'NC_DOUBLE';
	varstruct.Dimension = {recordDimName};

	attArray(1).Name  = 'long_name';
	attArray(2).Name  = 'standard_name';
	attArray(3).Name  = 'units';
	attArray(4).Name  = '_FillValue';
	attArray(4).Value = -1e6;

	lngname = 1;
	stdname = 2;
	unts    = 3;

%% Create coordinate variables

	% Create time variable
	varstruct.Name = 'time';
	
	attArray(lngname).Value = 'epoch time';
	attArray(stdname).Value = 'time';
	attArray(unts   ).Value = 'seconds since 1970-01-01 00:00:00';

	varstruct.Attribute = attArray;
	nc_addvar(outFilename, varstruct);

	% Create latitude variable
	varstruct.Name = 'latitude';
	
	attArray(lngname).Value = 'latitude';
	attArray(stdname).Value = 'latitude';
	attArray(unts   ).Value = 'degree_north';

	varstruct.Attribute = attArray;
	nc_addvar(outFilename, varstruct);

	% Create longitude variable
	varstruct.Name = 'longitude';
	
	attArray(lngname).Value = 'longitude';
	attArray(stdname).Value = 'longitude';
	attArray(unts   ).Value = 'degree_east';

	varstruct.Attribute = attArray;
	nc_addvar(outFilename, varstruct);

	% Create depth variable
	varstruct.Name = 'depth';
	
	attArray(lngname).Value = 'AUV measured depth';
	attArray(stdname).Value = 'depth';
	attArray(unts   ).Value = 'm';

	varstruct.Attribute = attArray;
	nc_addvar(outFilename, varstruct);

%% Create scientific (CTD) variables

	% Create conductivity variable
	varstruct.Name = 'conductivity';
	
	attArray(lngname).Value = 'water conductivity';
	attArray(stdname).Value = 'sea_water_electrical_conductivity';
	attArray(unts   ).Value = 'S m-1';

	varstruct.Attribute = attArray;
	nc_addvar(outFilename, varstruct);
	
	% Create temperature variable
	varstruct.Name = 'temperature';
	
	attArray(lngname).Value = 'water temperature';
	attArray(stdname).Value = 'sea_water_temperature';
	attArray(unts   ).Value = 'Celsius';

	varstruct.Attribute = attArray;
	nc_addvar(outFilename, varstruct);

	% Create pressure variable
	varstruct.Name = 'pressure';
	
	attArray(lngname).Value = 'water pressure';
	attArray(stdname).Value = 'sea_water_pressure';
	attArray(unts   ).Value = 'decibar';
    
    varstruct.Attribute = attArray;
	nc_addvar(outFilename, varstruct);

    % Create salinity variable
	varstruct.Name = 'salinity';
	
	attArray(lngname).Value = 'water salinity';
	attArray(stdname).Value = 'sea_water_salinity';
	attArray(unts   ).Value = '1';

	varstruct.Attribute = attArray;
	nc_addvar(outFilename, varstruct);

%% Insert global metadata

	nc_attput(outFilename, nc_global, 'title', 'AUV Survey Data');
	nc_attput(outFilename, nc_global, 'netcdf_version', '3.6');
	nc_attput(outFilename, nc_global, 'Convention', 'CF-1.4');

	dateString = datestr(now, 'yyyy-mm-ddThh:MM:ss');

	nc_attput(outFilename, nc_global, 'date_created', dateString);
	nc_attput(outFilename, nc_global, 'date_update', dateString);
	nc_attput(outFilename, nc_global, 'date_modified', dateString);
 
	nc_attput(outFilename, nc_global, 'cdm_data_type', 'trajectory');
	nc_attput(outFilename, nc_global, 'CF_featureType', 'trajectory'); 
	nc_attput(outFilename, nc_global, 'data_mode', 'R');

	nc_attput(outFilename, nc_global, 'geospatial_lat_min', min(latitude));
	nc_attput(outFilename, nc_global, 'geospatial_lat_max', max(latitude));

	nc_attput(outFilename, nc_global, 'geospatial_lon_min', min(longitude));
	nc_attput(outFilename, nc_global, 'geospatial_lon_max', max(longitude));

	nc_attput(outFilename, nc_global, 'geospatial_vertical_min', min(depth)); 
	nc_attput(outFilename, nc_global, 'geospatial_vertical_max', max(depth));

	nc_attput(outFilename, nc_global, 'geospatial_lat_units', 'degree_north');
	nc_attput(outFilename, nc_global, 'geospatial_lon_units', 'degree_east');

	nc_attput(outFilename, nc_global, 'geospatial_vertical_units', 'm');
	nc_attput(outFilename, nc_global, 'geospatial_vertical_positive', 'down');

	matlabTime = datenum([1970, 1, 1, 0, 0, min(time)]); 
	dateString = datestr(matlabTime, 'yyyy-mm-ddThh:MM:ss');
	nc_attput(outFilename, nc_global, 'time_coverage_start', dateString);

	matlabTime = datenum([1970, 1, 1, 0, 0, max(time)]); 
	dateString = datestr(matlabTime, 'yyyy-mm-ddThh:MM:ss');
	nc_attput(outFilename, nc_global, 'time_coverage_end', dateString);

	licenseStatement = 'Approved for public release. Distribution Unlimited.';
	nc_attput(outFilename, nc_global, 'distribution_statement', licenseStatement);
	nc_attput(outFilename, nc_global, 'license', licenseStatement);

    attNames = fieldnames(metadata);
    for idx = 1:length(attNames);
        currAttName = attNames{idx};
        nc_attput(outFilename, nc_global, currAttName, metadata.(currAttName));
    end;
    
%% Fill in the dataset

	nc_varput(outFilename, 'time',         time);
	nc_varput(outFilename, 'latitude',     latitude);
	nc_varput(outFilename, 'longitude',    longitude);
	nc_varput(outFilename, 'depth',        depth);

	nc_varput(outFilename, 'conductivity', conductivity);
	nc_varput(outFilename, 'temperature',  temperature);
	nc_varput(outFilename, 'pressure',     pressure);
    nc_varput(outFilename, 'salinity',     salinity);

end
