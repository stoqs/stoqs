function inf = stoqs_info(u,table,var)

%Get info from a table in STOQS data base
%       inf=info_stoqs('http://odss.mbari.org/canon/default','platform');
%       infc=info_stoqs(u,'activity.json?campaign=','2');
%Usage:
%
%   t=info_stoqs(u)
%Input :
%   Could use 2 o 3 parameter in the input
%   u = Url direction of the STOQS data server. Ex: http://192.168.79.138:8000/default
%   table = table to get the information
%   var= value of the parameter of the query to do to the table
%Output
% Get the struct variable inf with all the information.
% 

%   Brian Schlining & Francisco Lopez
%   30/June/2012
% Last review 30/June/2012

%Load the information
switch nargin
    case 2
    ur=[u '/' table '.json'];
    case 3
    ur=[u '/' table var];
end

try
    url = java.net.URL(ur);
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
    inf='';
else    
    inf=loadjson(a); %Read de information, Convert java.string to string with char, so loadjson could convert it to a struct.
    er=0;
end


