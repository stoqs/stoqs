function [extra]=extract_points(model,d)
%
%
%  Usage
%
%   Get the value for the nearest node of the model to the insitu
%   measurement. It's use in the function model_vs_stoqs
%
% Input
%   
%   Model= Model information getting from model_vs_stoqs
%   insit= Insitu measuremente getting from model_vs_stoqs
%
% Ouput
%   extra = Structure with the x,y index(indx,indy), the data model value(pointdata).
%

for i=1:length(d.long)
  [inde,dist]=near(d.long(i),model.lon);
  indy=inde;clear inde;
  [inde,dist]=near(d.lati(i),model.lat);
  indx=inde;clear inde;
  extra.pointdata(i)=model.data_inlevel(indx,indy);
  extra.indx=indx;
  extra.indy=indy;
end

%Get all the insitu measurement in a node and get the mean.
