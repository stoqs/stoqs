
function stoqs_showcampaign(u,camp)
%Show on the screen all the main information about a campaign in a STOQS
%database
%      
%Usage:
%
%    stoqs_showcampaign('http://odss.mbari.org/canon/','default');
%Input :
%
%   u = Url direction of the STOQS data server. Ex: http://odss.mbari.org/canon
%   camp = name of the campaign you want to do the query. ex='default'
%
% 

%   Brian Schlining & Francisco Lopez
%   12/July/2012
%
% Last review 16/July/2012
%---------------------CAMPAIGN----------------

urlc=[u '/' camp];

infc=stoqs_qcampaign(urlc,1);

[infp,platname]=stoqs_qplatform(urlc,1); %Get the platform information and a vector of platform with de ID

[infpa,parname]=stoqs_qparameter(urlc,1) ; %Get the parameter information and a vector of platform with de I


%We want to show for each campain, what platform are and the variable who
%each measure.
%for i=1:length(infc) %Loop the campaign
%    infa=stoqs_qactivity(u,camp,1);   %Get the activities for a campaign
%    for j=1:length(infa)
%        infact=stoqs_qparameter_in_platformactivity(infa,num2str(infa(i).id),1);
%    end
%end

