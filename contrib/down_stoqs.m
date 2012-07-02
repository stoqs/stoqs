function outp=down_stoqs(stime,etime,mid,mad,par)
%Get data from a STOQS database, 
%           d=down_stoqs('2010-10-27+21:51:55','2010-11-18+10:22:42','0','700','salinity');
%       Input
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


%Load the information
%stime='2010-10-27+21:51:55';
%etime='2010-11-18+10:22:42';
%mid='0';
%mad='10';
%par='temperature';

query=['http://192.168.79.141:8000/default/query/csv?start_time=' stime '&end_time=' etime '&min_depth=' mid '&max_depth=' mad '&parameters=' par]


%Get the information from the webpage
url = java.net.URL(query); %Read de URL

urlStream = url.openStream(); %Open it
isr = java.io.InputStreamReader(urlStream);
br = java.io.BufferedReader(isr);

%Save the information as string, and separate it with the separator ','
for k=1:10
    f(k,1:6)=regexp(char(readLine(br)),',','split');
end

%Separate the information in different variable with the correct type
outp.platform=f(2:end,1);
outp.time=datenum(f(2:end,2),'yyyy-mm-dd HH:MM:SS');
outp.long=str2double(f(2:end,3));
outp.lati=str2double(f(2:end,4));
outp.dept=str2double(f(2:end,5));
outp.vari=str2double(f(2:end,6));

clear url;clear urlStream;clear isr;clear br;clear f