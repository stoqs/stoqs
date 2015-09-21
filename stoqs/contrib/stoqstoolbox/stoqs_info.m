function inf = stoqs_info(u,table,var)
%
%Get info from a table in STOQS data base
%       inf=stoqs_info('http://odss.mbari.org/canon/stoqs_may2012','platform');
%       infc=info_stoqs(u,'activity.json?campaign=','1');
%Usage:
%
%   t=info_stoqs(u)
%Input :
%   Could use 2 o 3 parameter in the input
%   u = Url direction of the STOQS data server. Ex: http://odss.mbari.org/canon/stoqs_may2012
%   table = table to get the information
%   var= value of the parameter of the query to do to the table
%Output
% Get the struct variable inf with all the information.
% 
%   Francisco Lopez & Mike McCann & Brian Schlining 
%
%   Last modified
%   19/August/2012

%Load the information

if nargin<2
    inf='';
    disp('-----------------------');
    disp('NOT ENOUGH ARGUMENT');
    disp('-----------------------');
    disp('HELP')
    help stoqs_info
    return
    
end

% Campaign information
switch nargin
    case 2
    ur=[u '/' table '.json'];
    case 3
    ur=[u '/' table var];
end

try
    disp(['Opening ' ur ])
    url = java.net.URL(ur);
catch me
    m = MException([mfilename ':BadURL'], '%s is not a valid URL. Cause: %s', ur, me.message);
    throw(m);
end
 
urlStream = url.openStream(); 
isr = java.io.InputStreamReader(urlStream);
br = java.io.BufferedReader(isr);

a=char(readLine(br));
if isempty(a)
    error=['ERROR : Couldnt get the information for table ' table ' **************'];
    disp(error)
    inf='';
else    
    inf = stoqs_loadjson(a); % Parse json response, Convert java.string to string with char, so loadjson could convert it to a struct.
    er=0;
end


