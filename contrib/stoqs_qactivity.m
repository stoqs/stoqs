function infa = stoqs_qactivity(u,camp,show)

%Get info from the activities in a campaign in STOQS data base
%      
%Usage:
%
%   infa=stoqs_qactivity('http://odss.mbari.org/canon/,'default',1);
%Input :

%   u = Url direction of the STOQS data server. Ex: http://odss.mbari.org/canon
%   camp = name of the campaign you want to do the query. ex='default'
%   show = Show the info on the screen or not. If show=1 , show the info,
%               if show=0 doesn't show it.

%Output
% Get the activity available in the campaign selected
% 

%   Brian Schlining & Francisco Lopez
%   30/June/2012
% Last review 12/July/2012


urlc=[u '/' camp]

infc=stoqs_qcampaign(urlc,show);

infa=stoqs_info(urlc,'activity.json?campaign=',num2str(infc(1).id));

if show==1
    for i=1:length(infa)  
       fprintf('%s\n','ACTIVITY');
       fprintf('   %s n',infa(i).name);
    end
end