function [inf]=stoqs_campaignbydate(urlst,date)
%Search for the campaign available in STOQS for the date given.
%      
%      
%Usage:
%       [camp]=stoqs_campaignbydate('http://odss.mbari.org/canon',datenum(2011,06,21));
%   
%Input :
%        urls=Url of the STOQS server
%        date= Date in Matlab format. Use datenum to convert date to Matlab
%        format
%     
%Output
%        inf= All the structure information for the campaign selected.
%
%   Mike McCann & Brian Schlining & Francisco Lopez
%
%   Last modified
%   19/August/2012

if nargin<2
    inf='';
    disp('-----------------------');
    disp('NOT ENOUGH ARGUMENT');
    disp('-----------------------');
    disp('HELP')
    help stoqs_campaignbydate
    return
    
end

infcs=stoqs_qcampaigns(urlst,0);
inf='';

for i=1:length(infcs)
    st=datenum(infcs(i).startdate);
    en=datenum(infcs(i).enddate);
    if date>st
        if date<en
            inf=infcs(i);
          
        end
    end
end    
