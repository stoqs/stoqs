
function infcs=stoqs_qcampaigns(u,show)

%Get the name of all the campaigns available in a STOQS server
%      
%Usage:
%
%  inf=stoqs_qcampaigns('http://odss.mbari.org/canon/',1);
%Input :
%
%   u = Url direction of the STOQS data server. Ex: http://odss.mbari.org/canon/
%   show = Show the info on the screen or not. If show=1 , show the info,
%               if show=0 doesn't show it.
%
%Output
% Get the campaigns available on the STOQS data server
% 
%
%   Francisco Lopez & Mike McCann & Brian Schlining 
%
%   Last modified
%   19/August/2012

if nargin<2
    infcs='';
    disp('-----------------------');
    disp('NOT ENOUGH ARGUMENT');
    disp('-----------------------');
    disp('HELP')
    help stoqs_qcampaigns
    return
    
end

infcs=stoqs_info(u,'campaigns');

if isempty(infcs)
else
    if show==1
    
         fprintf('%s\n','CAMPAIGNS');
     for i=1:length(infcs)  
         fprintf('   %s from %s to %s\n',char(infcs(i).name),char(infcs(i).startdate),char(infcs(i).enddate));
     end
    end
end
