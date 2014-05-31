
function [query]=load_mb_1km(url,de)
%Get the information of the data set selected(url). Information:Date,
%depth, latitude,longitude, and parameter value
%      
%Usage:
%
%   [date]=load_mb_1km('http://ourocean.jpl.nasa.gov:8080/thredds/dodsC/MBNowcast/mb_das_2012052515.nc',5)
%    
%
%Input :
%
%   url = Url direction of the OpenDap data server. Ex: http://ourocean.jpl.nasa.gov:8080/thredds/dodsC/MBNowcast/mb_das_2012052515.nc
%   
%         
%
%Output
%   query = Structure with all the information.
% 
%
%
%   Francisco Lopez-Castejon
%   19/August/2012
 

vari='temp';
%Monterey Bay 1 Km
openset= url; 
mb = ncgeodataset(openset);

dvar_u = mb.geovariable(vari);

grid_u=dvar_u.grid_interop(1:end,1:end,1:end,1:end); %get the grid in the correct form, time, depth.....


level=near(abs(grid_u.z),de); %Get the data model output for the nearest selected depth.




%Build my structure with all the information needed
query.name=dvar_u.attributes;
query.date=grid_u.time;
query.depth=grid_u.z;
query.value=dvar_u.data;
query.longitude=grid_u.lon;
query.latitude=grid_u.lat;
query.data_inlevel= squeeze(dvar_u.data(1,level,1:end,1:end)); 
query.level=level;
