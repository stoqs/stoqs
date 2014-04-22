function [infp,platname] = stoqs_qplatform(u,show)

%Get info from platforms in STOQS campaign data base
%       inf=stoqs_qplatform('http://odss.mbari.org/canon/default',1);
%Usage:
%
%   inf=stoqs_qplatform('http://odss.mbari.org/canon/stoqs_may2012',1);
%Input :

%   u = Url direction of the STOQS data server. Ex: http://odss.mbari.org/canon/default
%   show = Show the info on the screen or not. If show=1 , show the info,
%               if show=0 doesn't show it.

%Output
%   infc = Get the platform info available on the STOQS data server
%   platname = Name of the platform to acces it with the platform ID.
%               Knowing the ID you can get the platname easily.
% 
%   Francisco Lopez & Mike McCann & Brian Schlining 
%
%   Last modified
%   19/August/2012

if nargin<2
    platname='';infp='';
    disp('-----------------------');
    disp('NOT ENOUGH ARGUMENT');
    disp('-----------------------');
    disp('HELP')
    help stoqs_qplatform;
    return
    
end

infp=stoqs_info(u,'platform');

if isempty(infp)
    platname='';
else
    for i=1:length(infp);platname{infp(i).id}=infp(i).name;end

    if show==1
       fprintf('%s\n','PLATFORMS');
       for i=1:length(platname)  
            fprintf('    %s\n',char(platname(i)));
       end
    end
end 
