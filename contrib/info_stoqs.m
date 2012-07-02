function inf = info_stoqs(u)

%Get info from a STOQS data basej, platform, date, variables,
%       inf=info_stoqs('http://192.168.79.138:8000/default')
%Usage:
%
%   t=info_stoqs(u)
%Input :
%   u = Url direction of the STOQS data server. Ex: http://192.168.79.138:8000/default
%Output
% Show in the screen all the basic information and get the struct variable
% inf with all the information.
% 

%   Brian Schlining & Francisco Lopez
%   30/June/2012


%Load the information

ur=[u '/platform.json'];
url = java.net.URL(ur); %Read de URL

urlStream = url.openStream(); %Open it
isr = java.io.InputStreamReader(urlStream);
br = java.io.BufferedReader(isr);
inf=loadjson(char(readLine(br))); %Read de information, Convert java.string to string with char, so loadjson could convert it to a struct.

%Show the information
l=length(inf(:));
fprintf('%s\n','PLATAFORMAS');
fprintf('%s\n',inf(1:l).name);

