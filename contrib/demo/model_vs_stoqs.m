function [model,d]=model_vs_stoqs(urlo,depth,range)
%Compare in-situ data with model output
%
%
%   Input
%       urlo= OPeNDAP ROMS output to use
%       depth= Depth at we want to compare the data
%       range = Range of +/- depth where to look for in-situ measurement.
%       Example -> If we said mode_vs_stoqs(5,2), will look for all the
%       data between 3m(5-2) and 7m(5+2)
%
%   Usage
%       [query,d]=model_vs_stoqs('http://ourocean.jpl.nasa.gov:8080/thredds/dodsC/MBNowcast/mb_das_2011062021.nc',5,2)
%
%   Output
%
%
%   Francisco Lopez-Castejon
%   19/July/2012
%


%-----------    MODEL WORK -------------------
%Select the OpenDap Server to get the model output. Get all the model
%output information.
disp('Connecting to the OPeNDAP server')
[model]=load_mb_1km(urlo,depth);
disp('Finish OPeNDAP server connection')



%------------PREPARING QUERY -----------------
%Prepare all the information needed to the STOQS Query.

datestart=datestr(datenum(model.date)-1/24,'yyyy-mm-dd+HH:MM:SS'); %Get one hour after and before model date
datend=datestr(datenum(model.date)+1/24,'yyyy-mm-dd+HH:MM:SS');
min_dep=depth-range; %min(abs(model.depth));
max_dep=depth+range; %max(abs(model.depth))
vari='sea_water_temperature'; %model.name(5)


%------------- GETTING IN-SITU MEASUREMENT ------------
disp('Getting STOQS in-situ measuremt')
%Get the in-situ data
d=stoqs_down('http://odss-staging.shore.mbari.org/canon/stoqs_june2011',datestart,datend,min_dep,max_dep,vari);
disp('All the STOQS measurement download')

%-----------  MAKE SOME PLOTS ----------------

%---Trajectory over 
pcolor(model.lon,model.lat, model.data_inlevel);shading flat;colorbar;hold on
plot(d.long,d.lati)
title(['Monterey Bay ROMS output ' datestr(model.date) ' at ' num2str(model.depth(model.level)) ' m']);
