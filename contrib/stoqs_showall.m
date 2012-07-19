function stoqs_showall(u)
%Show on the screen all the main information in a STOQS server
%
%      
%Usage:
%
%    stoqs_showcampaign('http://odss.mbari.org/canon');
%Input :
%
%   u = Url direction of the STOQS data server. Ex: http://odss.mbari.org/canon
%   
%
% 

%   Brian Schlining & Francisco Lopez
%   12/July/2012
%
% Last review 16/July/2012
%---------------------CAMPAIGN----------------

infcs=stoqs_qcampaigns(u,0);
for i=1:length(infcs)
    stoqs_showcampaign(u,char(infcs(i)))
end