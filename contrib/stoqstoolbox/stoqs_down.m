function outp=stoqs_down(varargin)
%       Usage
%            Acces to a STOQS server and download a dataset based in a
%            query.
%
%            Time Queries:
%                The user could write a begging and end date. If, for example, he doesnt
%                write  a end date, the program will query to all the data
%                available from the begging date. In the same way, if the
%                query only have a end date, the program will query to all
%                the data available until that date. 
%                        Ex. d=stoqs_down('http://odss-staging.shore.mbari.org/canon/stoqs_may2012','2012-05-30 00:10:00','2012-05-30 01:10:00','1','2','sea_water_temperature','dorado');
%                            Will query to all the data available of
%                            sea_water_temperature
%                            measured by dorado between  2012-05-30 00:10:00 and 2012-05-30 01:10:00
%
%                            between 1 - 2 meters.
%            Depth Queries:
%                The user could write a top and low leve to query. If there
%                is not any depth, the program will query for all the
%                depths. If write the minimum depth, it will search for the
%                minimum to the maximum depth available,and in the same way
%                with the maximum.
%                         Ex. d=stoqs_down('http://odss-staging.shore.mbari.org/canon/stoqs_may2012','2012-05-30 00:10:00','2012-05-30 01:10:00','','3','sea_water_temperature','dorado');
%                             Will query to all the variables measured by
%                             dorado  up 3 m depth between '2010-10-27 21:00:00'and '2010-10-29 23:00:00'
%
%            Variable Query:
%                 MUST use the standard name of he variable following the CF-Metadata conventions
% 			      (http://cf-pcmdi.llnl.gov/documents/cf-standard-names/standard-name-table/19/cf-standard-name-table.html).
% 			      In the case you want to get all the variable,
% 			      leave it empty
%
%           Platform Query:
%                  Name of the platform to query, If is empty will query for all the platform.
%                
%
%
%       Input
%          The input in order are:
% 			URL of the STOQS server
% 			Start time in the format 'yyyy-mm-dd+HH:MM:SS'
% 			End time in the format 'yyyy-mm-dd+HH:MM:SS'
%			Minimum depth in meters
% 			Maximum depth in meters
%			Platform name. Set to '' to get data from all platforms.
% 			Parameter name 
% 			Parameter standard_name - the CF standard_name
%       Ouput
%           outp = Structure with the data structured by 
%                  platform, time, longitude, latitude, depth and parameter values
%
%
%
%   Francisco Lopez & Mike McCann & Brian Schlining 
%
%   Last modified
%   30/October/2012




%CHECK INPUT ERRORS

if nargin<7
    outp='';
    disp('-----------------------');
    disp('NOT ENOUGH ARGUMENT');
    disp('-----------------------');
    disp('HELP')
    help stoqs_down_json;
    return
    
end


%CHECK WHAT KIND OF QUERY IS GOING TO DO AND BUILT IT
disp('PREPARING THE QUERY');

query=fullfile(varargin{1}, 'measuredparameter.json?');

if ~isempty(varargin{2})
    query=[query 'measurement__instantpoint__timevalue__gt=' varargin{2} '&'];
end    

if ~isempty(varargin{3})
    query=[query 'measurement__instantpoint__timevalue__lt=' varargin{3} '&'];
end   

if ~isempty(varargin{4})
    query=[query 'measurement__depth__gte=' num2str(varargin{4}) '&'];
end   

if ~isempty(varargin{5})
    query=[query 'measurement__depth__lte=' num2str(varargin{5}) '&'];
end  

if ~isempty(varargin{6})
    query=[query 'measurement__instantpoint__activity__platform__name=' varargin{6} '&'];
end 

if ~isempty(varargin{7})
    query=[query 'parameter__name=' varargin{7} '&'];
end   

if ~isempty(varargin{8})
    query=[query 'parameter__standard_name=' varargin{8} '&'];
end   





%DO THE JSON QUERY TO STOQS

disp('START THE JSON QUERY');
try
    url = java.net.URL(query);
    disp('CONNECTION TO THE SERVER SUCCESSFULLY')
catch me
    m = MException([mfilename ':BadURL'], '%s is not a valid URL. Cause: %s', u, me.message);
    throw(m);
end

urlStream = url.openStream(); %Open it
isr = java.io.InputStreamReader(urlStream);
br = java.io.BufferedReader(isr);



a=char(readLine(br));
if isempty(a)
    error=['ERROR : Couldnt get the information for table ' table ' **************'];
    disp(error)
    outp='';
else    
    disp('CONVERTING FROM JSON');
    info=loadjson(a); %Read de information, Convert java.string to string with char, so loadjson could convert it to a struct.
    er=0;
end

if isempty(info)
   outp='';
   disp('************NO DATA AVAILABLE FOR YOUR QUERY')
else

a=struct2cell(info); %Convert the structure array to cell array
disp('MEASUREMENTS DOWNLOAD: ' )
disp(length(a(6,:,:)))

%Save the data in a new structure with standard names.
outp.platform=squeeze(a(6,:,:));
outp.time=squeeze(datenum(a(4,:,:),'yyyy-mm-ddTHH:MM:SS'));
f=cell2mat(a(7,:,:));  %covnert a cell array into a single matrix
outp.longitude=squeeze(f(1,1,:));
outp.latitude=squeeze(f(1,2,:));
outp.depth=cell2mat(squeeze(a(1,:,:)));
outp.value=cell2mat(squeeze(a(3,:,:)));
outp.parametername=squeeze(a(2,:,:));
outp.standardname=squeeze(a(5,:,:));
end

disp('END THE JSON QUERY');


