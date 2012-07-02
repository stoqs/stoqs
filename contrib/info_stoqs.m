function inf = info_stoqs(u,table,var)

%Get info from a table in STOQS data base
%       inf=info_stoqs('http://192.168.79.138:8000/default','platform')
%Usage:
%
%   t=info_stoqs(u)
%Input :
%   u = Url direction of the STOQS data server. Ex: http://192.168.79.138:8000/default
%Output
% Get the struct variable
% inf with all the information.
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
ur
try
    url = java.net.URL(ur);
catch me
    m = MException([mfilename ':BadURL'], '%s is not a valid URL. Cause: %s', u, me.message);
    throw(m);
end
 

urlStream = url.openStream(); %Open it
isr = java.io.InputStreamReader(urlStream);
br = java.io.BufferedReader(isr);
inf=loadjson(char(readLine(br))); %Read de information, Convert java.string to string with char, so loadjson could convert it to a struct.



