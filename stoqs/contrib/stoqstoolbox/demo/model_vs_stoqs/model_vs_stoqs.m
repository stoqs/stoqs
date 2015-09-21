function [model,insit]=model_vs_stoqs(urlo,depth,range,drange,show)
%Compare in-situ data with model output
%
%
%   Input
%       urlo= OPeNDAP ROMS output to use
%       depth= Depth at we want to compare the data (m)
%       range = Range of +/- depth where to look for in-situ measurement.
%       drange = Date regane where to look for in-situ data (hours) 
%       Example -> If we said mode_vs_stoqs(5,2), will look for all the
%       data between 3m(5-2) and 7m(5+2)
%       show = If is 1 make some plots.
%
%   Usage
%       [query,d]=model_vs_stoqs('http://ourocean.jpl.nasa.gov:8080/thredds/dodsC/MBNowcast/mb_das_2011062021.nc',5,0.1,2,1);
%
%   Output
%
%
%   Francisco Lopez-Castejon
%   19/August/2012
%
stoqs_server='http://odss.mbari.org/canon';

%-----------    MODEL WORK -------------------
%Select the OpenDap Server to get the model output. Get all the model
%output information.
disp(['Using NCTOOLBOX to read model data from ' urlo])
[model]=load_mb_1km(urlo,depth);



%------------PREPARING QUERY -----------------
%Prepare all the information needed to the STOQS Query.

datestart=datestr(datenum(model.date)-drange/24,'yyyy-mm-dd+HH:MM:SS'); %Get one hour after and before model date
datend=datestr(datenum(model.date)+drange/24,'yyyy-mm-dd+HH:MM:SS');
min_dep=depth-range; %min(abs(model.depth));
max_dep=depth+range; %max(abs(model.depth))
vari='sea_water_temperature'; %model.name(5)


%------------- GETTING IN-SITU MEASUREMENT ------------
disp(['Using STOQSTOOLBOX to look for data at ' stoqs_server])
%Get the in-situ data
[camp]=stoqs_campaignbydate(stoqs_server,model.date);


if isempty(camp)
    
else
    stoq_campaign=[stoqs_server '/' char(camp.dbAlias)]; %Build the url direction of the stoqs server for the campaign needed for the model date
    insit=stoqs_down(stoq_campaign,datestart,datend,min_dep,max_dep,'',vari,'');
end



%-----------  MAKE SOME PLOTS ----------------

%---Trajectory over
if show==1
 if isempty(model)
 else
    figure(1)
        min_color=min([min(min(model.data_inlevel)) min(insit.value)]);
        max_color=max([max(max(model.data_inlevel)) max(insit.value)]);
        pcolor(model.longitude,model.latitude, model.data_inlevel);hold on;shading flat;t=colorbar;set(gca, 'CLim', [min_color, max_color]);hold on
        set(get(t,'ylabel'),'String', 'Temperature','FontSize',18);set(gca,'FontSize',18);
        scatter(insit.longitude,insit.latitude,60,insit.value,'filled');t=colorbar;set(gca, 'CLim', [min_color, max_color]);set(get(t,'ylabel'),'String', 'Temperature','FontSize',18);
        plot(insit.longitude(1),insit.latitude(1),'x');hold on;
        plot(insit.longitude,insit.latitude,'wo');
        title(['Monterey Bay ROMS output ' datestr(model.date) ' at ' num2str(model.depth(model.level)) ' m'],'FontSize',18);

        %-------------- GET THE NEAREST MODEL POINT TO THE INSITU MEASUREMENT
        ext=extract_points(model,insit);

        
    figure(3)

      plot(insit.time,insit.value,'x');datetick('x',15);hold on;plot(ext.modeltime,ext.pointdata,'.r');legend('In situ measurement','Model output','FontSize',18);
      datetick('x',15);xlabel('HOURS','FontSize',18);ylabel('Temperature','FontSize',18)
      set(gca,'FontSize',18)
 end
end
