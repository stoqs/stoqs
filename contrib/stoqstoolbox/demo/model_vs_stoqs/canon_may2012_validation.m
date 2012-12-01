%Program to compare all the model output between two dates
% 
% The Monterey Bay ROMS model, give an ouput every 6 hours (3,9,15,21)
% We will try to compare the model ouput for all the time of the CANON 2012
% May campaign (15 May 2012 01:23:30  to 13 Jun 2012 18:24:52 )
%
%   Francisco Lopez-Castejon
%   19/August/2012


sdate=datenum('01 Jun 2012 03:00:00');    %Start date to compare 
edate=datenum('01 Jun 2012 21:00:00');    %End date to compare 
intm=6; %Output model interval
depth=5;
depth_range=0.1;
time_range=3;

%Initizalization the variable
insitu.value=NaN;insitu.time=NaN;insitu.longitude=NaN;insitu.latitude=NaN;insitu.depth=NaN;insitu.platform=NaN;
model.pointdata=NaN;extr.insitumean=NaN;extr.node=NaN;model.date=NaN;

%Get the number of date to compare
num=(edate-sdate)/(intm/24);
for i=1:num
    disp('---------------------------------------------------------');
    disp(['Model time ' datestr(sdate)])
    %Build the url for OPeNDAP server
    urlope=['http://ourocean.jpl.nasa.gov:8080/thredds/dodsC/MBNowcast/mb_das_' datestr(sdate,'yyyy') datestr(sdate,'mm') datestr(sdate,'dd') datestr(sdate,'HH') '.nc'];
    [query,d]=model_vs_stoqs(urlope,depth,depth_range,time_range,0);
    disp(['Downloaded ' num2str(length(d.longitude)) ' measurements'])
     %Get the nearest model node to the insitu measurement
     
    ext=extract_points(query,d);
    
%    extr.insitumean=[extr.insitumean,ext.insitumean];
%    extr.node=[extr.node,ext.node];
    
    model.pointdata=[model.pointdata,ext.pointdata];
    model.date=[model.date,ext.modeltime];
  
        
    
    %Save all the insitu measurement
    insitu.value=[insitu.value;d.value];
    insitu.time=[insitu.time;d.time];
    insitu.longitude=[insitu.longitude;d.longitude];    
    insitu.latitude=[insitu.latitude;d.latitude];      
    insitu.depth=[insitu.depth;d.depth];  
    insitu.platform=[insitu.platform;d.platform];   

    %Prepare the next date
    sdate=datenum(sdate)+intm/24; %I have an output every 6 hours (6/24 days)
end    

      figure(1)
        plot(insitu.time,insitu.value,'x');datetick('x','dd/mm HH:MM');hold on;plot(model.date,model.pointdata,'.r')
        legend('in situ measurement','model output');
      xlabel('Date ( day/month hour:minute)','FontSize',18);ylabel('Temperature','FontSize',18)
      set(gca,'FontSize',18)
