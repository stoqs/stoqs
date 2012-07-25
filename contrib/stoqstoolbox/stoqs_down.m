function outp=stoqs_down(varargin)
%Get data from a STOQS database, 
%           d=stoqs_down('http://192.168.79.141:8000/default','2010-10-27+21:51:55','2010-11-18+10:22:42',0,700,'salinity');
%           d=stoqs_down('http://odss-staging.shore.mbari.org/canon/stoqs_june2011','2011-06-20+20:00:00','2011-06-20+22:00:00',1,4,'sea_water_temperature');
%       Input
%           url = URL of the STOQS server
%           stime =Start time in the format 'yyyy-mm-dd+HH:MM:SS'
%           etime =End time in the format 'yyyy-mm-dd+HH:MM:SS'%
%           mid = Minimum depth
%           mad = Maximum depth
%           par = Parameter to get the data
%       Ouput
%           outp = Structure with the information,
%           platform,time,longitude,latitude, depth and variable values of
%           the query point 
%
%   Brian Schlining & Francisco Lopez
%   1/July/2012
%
%   Last modified
%   20/July/2012

query=[varargin{1} '/query/csv?start_time='  varargin{2} '&end_time=' varargin{3} '&min_depth=' num2str(varargin{4}) '&max_depth=' num2str(varargin{5}) '&parameters=' lower(char(varargin{6}))];


%Get the information from the webpage
url = java.net.URL(query); %Read de URL

urlStream = url.openStream(); %Open it
isr = java.io.InputStreamReader(urlStream);
br = java.io.BufferedReader(isr);



e=1;k=1;
while e==1   
    f(k,1:6)=regexp(char(readLine(br)),',','split');%Save the information as string, and separate it with the separator ','
    if isempty(char(f(k,1)))%Check if I arrived to the end of the text
        e=0;
   end    
    k=k+1;
end

%Separate the information in different variable with the correct type
outp.platform=f(2:end-1,1);
outp.time=datenum(f(2:end-1,2),'yyyy-mm-dd HH:MM:SS');
outp.long=str2double(f(2:end-1,3));
outp.lati=str2double(f(2:end-1,4));
outp.dept=str2double(f(2:end-1,5));
outp.vari=str2double(f(2:end-1,6));


clear url;clear urlStream;clear isr;clear br;clear f