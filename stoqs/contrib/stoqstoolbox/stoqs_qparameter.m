function [infpa,parname] = stoqs_qparameter(u,show)

%Get info from parameters in STOQS campaign data base
%   
%Usage:
%
%   inf=stoqs_qparameter('http://odss.mbari.org/canon/stoqs_may2012',1);
%Input :

%   u = Url direction of the STOQS data server. Ex: http://odss.mbari.org/canon/default
%   show = Show the info on the screen or not. If show=1 , show the info,
%               if show=0 doesn't show it.

%Output
%   infc = Get the parameter info available on the STOQS data server
%   platname = Name of the parameter to acces it with the parameter ID.
%               Knowing the ID you can get the platname easily.
% 
%   Francisco Lopez & Mike McCann & Brian Schlining 
%
%   Last modified
%   19/August/2012



if nargin<2
    parname='';infpa='';
    disp('-----------------------');
    disp('NOT ENOUGH ARGUMENT');
    disp('-----------------------');
    disp('HELP')
    help stoqs_qparameter;
    return
    
end

infpa=stoqs_info(u,'parameter');

if isempty(infpa)
    parname=''
else
    for i=1:length(infpa);parname{infpa(i).id}=infpa(i).name;end

    if show==1
      fprintf('%s\n','PARAMETERS');
      for i=1:length(parname)  
         fprintf('    %s\n',char(parname(i)));
      end
    end
end
