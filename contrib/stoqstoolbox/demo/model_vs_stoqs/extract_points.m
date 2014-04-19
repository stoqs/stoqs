function [extra]=extract_points(model,insit)
%
%
%  Usage
%
%   Get the value for the nearest node of the model to the insitu
%   measurement. It's use in the function model_vs_stoqs. You will get one
%   model value for each in situ measurement.
%
% Input
%   
%   Model= Model information getting from model_vs_stoqs
%   insit= Insitu measuremente getting from model_vs_stoqs
%
% Ouput
%   extra = Structure with the x,y index(indx,indy), the data model value(pointdata).
%        Get one model output for every insitudata
%           .pointdata = Value of the nearest node to the insitu data                        
%           .indx,indy = Index of the node nearest to the insitu data
%           .modeltime = Model time.
%           .time = Time of each of the in situ measurement
%           .longitude,latitude = Longitude and Latitude of the node that have in situ
%           measurement.
%
%
%   Francisco Lopez-Castejon
%   19/August/2012

if isempty(insit.value)
  extra.pointdata(1)=NaN;
  extra.indx(1)=NaN;
  extra.indy(1)=NaN;
  extra.latitude(1)=NaN;
  extra.longitude(1)=NaN;
  extra.modeltime(1)=model.date;

else

 for i=1:length(insit.longitude)
  [inde,dist]=near(insit.longitude(i),model.longitude);
  indy=inde;clear inde;
  [inde,dist]=near(insit.latitude(i),model.latitude);
  indx=inde;clear inde;
  extra.pointdata(i)=model.data_inlevel(indx,indy);
  extra.indx(i)=indx;
  extra.indy(i)=indy;
  extra.modeltime(i)=model.date;
  extra.latitude(i)=model.latitude(indx);
  extra.longitude(i)=model.longitude(indy);
 
 end



end

    
