
function stoqs_showcampaign(u,camp)
%Show on the screen all the main information about a campaign in a STOQS
%database
%      
%Usage:
%
%    stoqs_showcampaign('http://odss.mbari.org/canon/','stoqs_may2012');
%Input :
%
%   u = Url direction of the STOQS data server. Ex: http://odss.mbari.org/canon
%   camp = name of the campaign you want to do the query. ex='default'
%
% 
%   Francisco Lopez & Mike McCann & Brian Schlining 
%
%   Last modified
%   19/August/2012
% 
%---------------------CAMPAIGN----------------

if nargin<2
    disp('-----------------------');
    disp('NOT ENOUGH ARGUMENT');
    disp('-----------------------');
    disp('HELP')
    help stoqs_showcampaign;
    return
    
end

urlc=[u '/' camp];

infc=stoqs_qcampaign(urlc,1);

[infp,platname]=stoqs_qplatform(urlc,1); %Get the platform information and a vector of platform with de ID

[infpa,parname]=stoqs_qparameter(urlc,1) ; %Get the parameter information and a vector of platform with de I




