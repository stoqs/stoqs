function outp=stoqs_down(varargin)
% STOQS_DOWN  Download data from a STOQS database directly into a Matlab strucure
%
% Use as:
%   a. data = stoqs_down(json_request_url)
%      - or -
%   b. data = stoqs_down(campaign,start_time,end_time,min_depth,max_depth,platforms,parametername,parameterstandardname);
%
% Arguments:
%  a. 
%   json_request_url = Fully qualified STOQS JSON request url.  Use this 
%                      for requesting data that may include one or more 
%                      Parameter Value constraints.  Copy the URL from the
%                      STOQS web query interface.
%  b.
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
%   Last modified  8 January 2013


global mp_total_count 


%CHECK WHAT KIND OF QUERY IS GOING TO DO AND BUILT IT

if nargin == 8

    query=fullfile(varargin{1}, 'measuredparameter.json?');

    if ~isempty(varargin{2})
        query=[query 'measurement__instantpoint__timevalue__gte=' varargin{2} '&'];
    end    

    if ~isempty(varargin{3})
        query=[query 'measurement__instantpoint__timevalue__lte=' varargin{3} '&'];
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

    % Replace spaces - in time parms - to be URL friendly
    query = strrep(query, ' ', '%20'); 

elseif nargin == 1
    query = varargin{1};
    
else
    outp='';
    disp('-----------------------');
    disp('NOT ENOUGH ARGUMENT');
    disp('-----------------------');
    disp('HELP')
    help stoqs_down_json;
    return
    
end


% First, Get the count 
query_count = strrep(query, '.json', '.count');
mp_total_count = str2num(urlread(query_count));


% Second, Get the data
try
    url = java.net.URL(query);
    disp(['Reading data from: ' query])
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
    %%disp(['CONVERTING FROM JSON ' mp_total_count ' DATA VALUES']);
    % Note: ParameterValues queries will not display the progressbar
    info = stoqs_loadjson(a); % Read the information, Convert java.string to string with char, so loadjson could convert it to a struct.
    er=0;
end

if isempty(info)
   outp='';
   disp('************NO DATA AVAILABLE FOR YOUR QUERY')
else
    % Map database fields to "standard" names in the output structure
    % This method uses the JSON structure and does not rely on specific
    % ordering
    outp = struct(  'platform', [],...
                    'time', [],... 
                    'longitude', [],...
                    'latitude', [],...
                    'depth', [],...
                    'value', [],...
                    'parametername', [],...
                    'standardname', [],... 
                    'units', []);
                
    keys = {    'measurement__instantpoint__activity__platform__name',...
                'measurement__instantpoint__activity__name',...
                'measurement__instantpoint__timevalue',...
                'measurement__geom_x',... % Dummy _x & _y for matching
                'measurement__geom_y',... % fieldMap latitude & longitude
                'measurement__depth',...
                'datavalue',...
                'parameter__id',...
                'parameter__name',...
                'parameter__standard_name',...
                'parameter__units'};
            
    values = {  'platform',...
                'activity',...
                'time',...
                'longitude',...
                'latitude',...
                'depth', ...
                'value',...
                'parameterid',...
                'parametername',...
                'standardname',...
                'units'};
    fieldMap = containers.Map(keys, values);
    
    fields = fieldnames(info);
    for i=1:numel(fields)
        if strcmp(fields{i}, 'measurement__instantpoint__timevalue')
            tvs = {info.(fields{i})};
            dnums = [];
            for j=1:numel(tvs)
                dnums = [ dnums, datenum(tvs{j}, 'yyyy-mm-ddTHH:MM:SS') ];
            end
            outp.(fieldMap(fields{i})) = dnums';
        elseif ~isempty(strfind(fields{i}, 'measurement__geom'))
            g = [info.(fields{i})];
            outp.longitude = g(1:2:end)';
            outp.latitude = g(2:2:end)';
        elseif strcmp(fields{i}, 'measurement__geom__y') 
            continue
        elseif strcmp(fields{i}, 'measurement__geom__x')
            continue
        elseif strcmp(fields{i}, 'datavalue') || strcmp(fields{i}, 'measurement__depth') 
            % vectors
            outp.(fieldMap(fields{i})) = [info.(fields{i})]';
        else
            % cell arrays: platform, parametername, standardname, units
            outp.(fieldMap(fields{i})) = {info.(fields{i})}';
        end
    end

end

