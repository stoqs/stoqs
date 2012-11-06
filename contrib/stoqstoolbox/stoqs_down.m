function outp=stoqs_down(varargin)
% STOQS_DOWN  Download data from a STOQS database directly into a Matlab strucure
%
% Use as:
%   data = stoqs_down(campaign,start_time,end_time,min_depth,max_depth,platforms,parametername,parameterstandardname);
%
% Arguments:
%   campaign = Base url for a campaign from a stoqs server
%
%   Arguments that constrain retreival of data (set to '' for no constraint):
%     start_time            = Start date and time in format yyyy-mm-dd HH:MM:SS
%     end_time              = End date and time in format yyyy-mm-dd HH:MM:SS
%     min_depth             = Minimum depth in meters
%     max_depth             = Maximum depth in meters
%     platforms             = Name of platform
%     parametername         = Parameter name
%     parameterstandardname = Parameter standard_name 
%
% Return:
%   A structure like:
%     data = 
%              platform: {366x1 cell}
%                  time: [366x1 double]
%             longitude: [366x1 double]
%              latitude: [366x1 double]
%                 depth: [366x1 double]
%                 value: [366x1 double]
%         parametername: {366x1 cell}
%          standardname: {366x1 cell}
%
% Example:
%   
%   campaign = 'http://odss.mbari.org/canon/stoqs_september2012/';
%   start_time = '2012-09-09 15:22:19';
%   end_time = '2012-09-09 17:09:33';
%   min_depth = 2.61;
%   max_depth = 104.38;
%   parametername = '';
%   parameterstandardname = 'sea_water_temperature';
%   platforms = '';
%   
%   data = stoqs_down(campaign, start_time, end_time, min_depth, max_depth, platforms, parametername, parameterstandardname);
%
% Notes:
%   The stoqs web query user interface (Measurement Data Access -> stoqstoolbox) provides the argument 
%   arguments for stoqs_down() for the selections made using the graphical web query interface.
%
%   Francisco Lopez, Mike McCann, & Brian Schlining 
%   Last modified  31 October 2012


%CHECK INPUT ERRORS

global mp_total_count 

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


% First, Get the count 
query_count = strrep(query, '.json', '.count');         % Get count

try
    url_count = java.net.URL(query_count);
catch me
    m = MException([mfilename ':BadURL'], '%s is not a valid URL. Cause: %s', query_count, me.message);
    throw(m);
end

% Get the count so that we can show progress toward our goal
urlStream = url_count.openStream(); 
isr = java.io.InputStreamReader(urlStream);
br = java.io.BufferedReader(isr);
mp_total_count = char(readLine(br));


% Second, Get the data
query = strrep(query, ' ', '%20');                      % Replace spaces - in time parms - to be URL friendly
disp(['START THE JSON QUERY: ']);
try
    url = java.net.URL(query);
    disp(['CONNECTED TO THE SERVER AND READING DATA FROM: ' query])
catch me
    m = MException([mfilename ':BadURL'], '%s is not a valid URL. Cause: %s', query, me.message);
    throw(m);
end


% Open stream to the .json data
urlStream = url.openStream(); 
isr = java.io.InputStreamReader(urlStream);
br = java.io.BufferedReader(isr);



a = char(readLine(br));
if isempty(a)
    error=['ERROR : Couldnt get the information for table ' table ' **************'];
    disp(error)
    outp='';
else    
    disp(['CONVERTING FROM JSON ' mp_total_count ' DATA VALUES']);
    info = stoqs_loadjson(a); % Read the information, Convert java.string to string with char, so loadjson could convert it to a struct.
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
outp.units=squeeze(a(8,:,:));
end

disp('END THE JSON QUERY');


