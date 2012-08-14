function outp=stoqs_down(varargin)
%Get data from a STOQS database, 
%       Example
%           Get all the oxygen data from platform dorado:
%           d=stoqs_down('http://odss-staging.shore.mbari.org/canon/stoqs_may2012','2012-05-30 00:10:00','2012-05-30 01:10:00',0,0.5,'oxygen','');
%       Input
%          The input in order are:
% 			URL of the STOQS server
% 			Start time in the format 'yyyy-mm-dd+HH:MM:SS'
% 			End time in the format 'yyyy-mm-dd+HH:MM:SS'%
%			Minimum depth
% 			Maximum depth
% 			Parameter to get the data. You must use the standard name of
% 			      the variable using the CF-Metadata conventions
% 			      (http://cf-pcmdi.llnl.gov/documents/cf-standard-names/standard-name-table/19/cf-standard-name-table.html)
%			Platform name. If want all the platform name don?t write 
%				  any name
%       Ouput
%           outp = Structure with the information,
%           platform,time,longitude,latitude, depth and variable values of
%           the query point 
%
%   Mike McCann & Brian Schlining & Francisco Lopez
%   1/July/2012
%
%   Last modified
%   9/August/2012



%query=[varargin{1} '/mpbytimeparm.json?measurement__instantpoint__activity__platform__name=' varargin{7} '&measurement__depth__gte=' varargin{4} '&measurement__depth__lte=' varargin{5} '&parameter__standard_name=' varargin{6} '&measurement__instantpoint__timevalue__gt=' varargin{2} '&measurement__instantpoint__timevalue__lt=' varargin{3}];

if nargin<7
    outp='';
    disp('-----------------------');
    disp('NOT ENOUGH ARGUMENT');
    disp('-----------------------');
    disp('HELP')
    help stoqs_down_json;
    return
    
end


if isempty(char(varargin{7})) %Build a different query if the user want to get all the data from all the platforms, or from one plaftorm
    query=[varargin{1} '/mpbytimeparm.json?measurement__depth__gte=' varargin{4} '&measurement__depth__lte=' varargin{5} '&parameter__standard_name=' varargin{6} '&measurement__instantpoint__timevalue__gt=' varargin{2} '&measurement__instantpoint__timevalue__lt=' varargin{3}];
else

    query=[varargin{1} '/mpbytimeparm.json?measurement__instantpoint__activity__platform__name=' varargin{7} '&measurement__depth__gte=' varargin{4} '&measurement__depth__lte=' varargin{5} '&parameter__standard_name=' varargin{6} '&measurement__instantpoint__timevalue__gt=' varargin{2} '&measurement__instantpoint__timevalue__lt=' varargin{3}];
end


try
    url = java.net.URL(query);
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
    info=loadjson(a); %Read de information, Convert java.string to string with char, so loadjson could convert it to a struct.
    er=0;
end

a=struct2cell(info); %Convert the structure array to cell array

%Save the data in a new structure with standard names.
outp.platform=cell2mat(squeeze(a(6,:,:)));
outp.time=squeeze(datenum(a(4,:,:),'yyyy-mm-ddTHH:MM:SS'));
f=cell2mat(a(7,:,:));  %covnert a cell array into a single matrix
outp.longitude=squeeze(f(1,1,:));
outp.latitude=squeeze(f(1,2,:));
outp.depth=cell2mat(squeeze(a(1,:,:)));
outp.value=cell2mat(squeeze(a(3,:,:)));
outp.parametername=cell2mat(squeeze(a(2,:,:)));
outp.standardname=cell2mat(squeeze(a(5,:,:)));
