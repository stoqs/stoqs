function infact = stoqs_qparameter_in_activity(urlc,acti,show)

%Get the parameter measured by an activity
%      
%Usage:
%
%   infact=stoqs_qparameter_in_activity('http://odss.mbari.org/canon/default',1,1);
%Input :

%   u = Url direction of the STOQS data server and campaign. Ex:
%   http://odss.mbari.org/canon/default
%   acti= ID of the activity to query the parameter
%   show = Show the info on the screen or not. If show=1 , show the info,
%               if show=0 doesn't show it.

%Output
% Get the activityparameter available in the campaign selected
% 

%   Brian Schlining & Francisco Lopez
%   30/June/2012
% Last review 16/July/2012


infact=stoqs_info(urlc,'activityparameter.json?activity=',acti);
[infp,parname]=stoqs_qparameter(urlc,0);

if show==1
    for i=1:length(infact)  
       fprintf('           %s\n',char(parname(infact(i).parameter)));
    end
end