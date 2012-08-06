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
%        Get one model output for every insitudata
%           .pointdata = Value of the nearest node to the insitu data                        
%           .indx,indy = Index of the node nearest to the insitu data
%        Get one mean insitu data for every model node where there are in
%        situ data
%           .insitumean = Mean of all the insitu measurement inside the
%                         same model node.
%           .node  = Value of the model node nearest to the insitu data
%           
%           
%
joi(length(model.lat),length(model.lon))=0;
cjoi=joi;
if isempty(d.vari)
  extra.pointdata(1)=NaN;
  extra.indx(1)=NaN;
  extra.indy(1)=NaN;
  extra.modeltime(1)=model.date;
  extra.time(1)=NaN;
else

 for i=1:length(d.long)
  [inde,dist]=near(d.long(i),model.lon);
  indy=inde;clear inde;
  [inde,dist]=near(d.lati(i),model.lat);
  indx=inde;clear inde;
  extra.pointdata(i)=model.data_inlevel(indx,indy);
  extra.indx(i)=indx;
  extra.indy(i)=indy;
  extra.modeltime(i)=model.date;
  joi(indx,indy)=joi(indx,indy)+d.vari(i);
  cjoi(indx,indy)=cjoi(indx,indy)+1;  
  extra.time(i)=d.time(i);
 end



%ux=unique(extra.indx);
%uy=unique(extra.indy);
%k=1;
%for i=1:length(ux)
%    for j=1:length(uy)
%        extra.insitumean(k)=joi(ux(i),uy(j))/cjoi(ux(i),uy(j));
%        extra.node(k)=model.data_inlevel(ux(i),uy(j));
%        k=k+1;
%    end
%end
end

    
