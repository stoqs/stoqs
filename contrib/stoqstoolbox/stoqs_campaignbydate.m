function [inf]=stoqs_campaignbydate(urlst,date)
%Search for the campaign available in STOQS for the date given.
%      
%      
%Usage:
%       [camp]=stoqs_campaignbydate('http://odss-staging.shore.mbari.org/canon',2011,06,21,00,00,00);
%   
%Input :
%        urls=Url of the STOQS server
%        date= Date in Matlab format. Use datenum to convert date to Matlab
%        format
%     
%Output
%        inf= All the structure information for the campaign selected.

%Get the info campaigns available in STOQS server
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
