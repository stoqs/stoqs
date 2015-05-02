function stoqs_showall(u)
%Show on the screen all the main information in a STOQS server
%
%      
%Usage:
%
%    stoqs_showall('http://odss.mbari.org/canon');
%Input :
%
%   u = Url direction of the STOQS data server. Ex: http://odss.mbari.org/canon
%   
%
% 
%   Francisco Lopez & Mike McCann & Brian Schlining 
%
%   Last modified
%   19/August/2012


%---------------------CAMPAIGN----------------
if nargin<1
    disp('-----------------------');
    disp('NOT ENOUGH ARGUMENT');
    disp('-----------------------');
    disp('HELP')
    help stoqs_showall;
    return
    
end

infcs=stoqs_qcampaigns(u,0); %get the information of all the campaign available in the server in infcs
for i=1:length(infcs) %For each campaign call the function stoqs_showcampaign.
    stoqs_showcampaign(u,char(infcs(i).dbAlias))
    disp('---------------------------------------------');
end
