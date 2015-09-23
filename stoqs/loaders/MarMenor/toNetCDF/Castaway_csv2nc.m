% Castaway_csv2nc - Convert all of the csv data files in directory to NetCDF
%
% This program will loop through all the comma separated value (original)
% Castaway-formatted data files in the current directory, build global
% metadata attributes from the header in each csv file, and write the data
% out to a Climate Forecast convention 'trajectory' netCDF data file using
% the same base name as the original data file.
%
% Other m-files required: gen_AUV_ncfile and SNCTOOLS toolbox 
%
% Author: Mike McCann
% Work address: MBARI, 7700 Sandholdt Rd, Moss Landing, CA 95039  USA
% Author e-mail: mccann@mbaril.org
% Website: http://www.mbaril.org
% Creation: 18-Nov-2011

files = dir('*.csv');
pointCount = 0;
for i=1:length(files),
    
    [path, base, ext] = fileparts(files(i).name);
    dataFile = files(i).name;
    
    % Make sure we start with empty metadata for each data file
    clear metadata;
    metadata.vehicle_name = 'Castaway';
    metadata.institution = 'UPCT';
    metadata.ship_name = 'Sorell';
    
    % Open file
    disp(['Reading file for metadata: ' dataFile]); 
    try
        fid = fopen(dataFile);
        tline = fgetl(fid);
    catch me
        disp(['Cannot read file ' dataFile])
        continue
    end
    
    % Save everything from the header into metadata
    finishedHeader = 0;
    while ischar(tline) & ~finishedHeader
        indx = findstr(tline, ',');
        fieldname = strrep(tline(3:indx-1), ' ', '_');
        fieldname = strrep(strrep(fieldname, '(', ''), ')', '');
        value = tline(indx+1:end);
        if isempty(value)
                value = '';
        end
        metadata = setfield(metadata, fieldname, value);
        
        if strfind(tline, 'Pressure calibration date')
            finishedHeader = 1;
        end
        tline = fgetl(fid);
    end

    % Must have lat & lon to proceed
    if isempty(metadata.Start_latitude) | isempty(metadata.Start_longitude),
        continue
    end
    
    % Compute time from filename that looks like 10G100648_20111105_062743.csv
    s = regexp(dataFile, '(\d\d\d\d)(\d\d)(\d\d)_(\d\d)(\d\d)(\d\d)', 'match');
    d = datenum(s, 'yyyymmdd_HHMMss');
    dateString = datestr(d, 'yyyy-mm-ddTHH:MM:ss');  % Remove ';' to echo back to confirm we properly parsed it
    esecs = (d - datenum(1970,1,1,0,0,0)) * 86400;
    
    % Pressure (Decibar),Depth (Meter),Temperature (Celsius),Conductivity (MicroSiemens per Centimeter),Specific conductance (MicroSiemens per Centimeter),Salinity (Practical Salinity Scale),Sound velocity (Meters per Second),Density (Kilograms per Cubic Meter)
    newName = java.util.Hashtable;      % Map Castaway column names to simple names for reading by mfcvsread()
    newName.put('Time (Seconds)', 'time');
    newName.put('Pressure (Decibar)', 'pressure');
    newName.put('Depth (Meter)', 'depth');
    newName.put('Temperature (Celsius)', 'temperature');
    newName.put('Conductivity (MicroSiemens per Centimeter)', 'conductivity');
    newName.put('Specific conductance (MicroSiemens per Centimeter)', 'specificconductivity');
    newName.put('Salinity (Practical Salinity Scale)', 'salinity');
    newName.put('Sound velocity (Meters per Second)', 'soundvelicity');
    newName.put('Density (Kilograms per Cubic Meter)', 'density');
      
    % Write the data to a separate file with simplified header so that we can read it back into a structure with mfcsvread
    newFile = [base '_simple.scsv'];
    newHeader = '';
    fout = fopen(newFile, 'w');
    dataRecordCount = 0;
    while ischar(tline)
        if strfind(tline, 'Pressure (Decibar),')
            vars = regexp(tline, ',', 'split'); 
            for i=1:length(vars)
                newName.get(vars(i));
                newHeader = [newHeader ',' newName.get(char(vars(i)))];
                
            end
            fwrite(fout, [newHeader(2:end) char(10)]);
        elseif newHeader
            fwrite(fout, [tline char(10)]);
            dataRecordCount = dataRecordCount +1;
        end
        tline = fgetl(fid);
    end            
    fclose(fout);
    fclose(fid);
    
    if dataRecordCount == 0,
        delete(newFile)
        continue
    end
    
    % Read data file into M structure
    disp(['Reading file for its data: ' newFile])
    M = mfcsvread(newFile);
    
    % Compute a time array for the cast data so that we can use the
    % trajectory data type for the netCDF file
    time = linspace(esecs, esecs + str2num(metadata.Cast_duration_Seconds), length(M.pressure));
    pointCount = pointCount + length(M.pressure);
    
    latitude = ones(length(M.pressure),1) * str2num(metadata.Start_latitude);
    longitude = ones(length(M.pressure),1) * str2num(metadata.Start_longitude);
    
    if ~isfield(M, 'depth')
        M.depth = NaN * ones(length(M.pressure),1);
    end
    if ~isfield(M, 'salinity')
        M.salinity = NaN * ones(length(M.pressure),1);
    end
    
    % Write netCDF file
    ncFile = [base '.nc'];
    gen_AUV_ncfile(ncFile, metadata, time, latitude, ...
       longitude, M.depth, M.conductivity, M.temperature, M.pressure, M.salinity)

    disp(['Wrote file: ' ncFile '.  Accumulated pointCount = ' num2str(pointCount)])
   
    delete(newFile)
    
end
