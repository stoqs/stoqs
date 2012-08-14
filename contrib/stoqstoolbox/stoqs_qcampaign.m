function infc = stoqs_qcampaign(u,show)

%Get info from a campaign in STOQS data base
%      
%Usage:
%
%   inf=stoqs_qcampaign('http://odss.mbari.org/canon/default',1);
%Input :
%
%   u = Url direction of the STOQS data server. Ex: http://odss.mbari.org/canon/default
%   show = Show the info on the screen or not. If show=1 , show the info,
%               if show=0 doesn't show it.
%
%Output
% Get the campaign available on the STOQS data server
% 
%
%   Brian Schlining & Francisco Lopez
%   30/June/2012
% Last review 30/July/2012

infc=stoqs_info(u,'campaign');

if show==1
    for i=1:length(infc)  
       fprintf('%s\n','CAMPAIGN');
        fprintf('   %s\n',infc(i).name);
        fprintf('   From  %s to %s\n',infc(i).startdate,infc(i).enddate);
    end
end