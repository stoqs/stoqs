
function show_stoqs(u)

%---------------------CAMPAIGN----------------
infc=info_stoqs(u,'campaign');
infp=info_stoqs(u,'platform');


%Show the information about platform

for i=1:length(infc)
    
    fprintf('%s\n','CAMPAIGN');
    fprintf('   %s  from  %s to %s\n',infc(i).name,infc(i).startdate,infc(i).enddate);
    fprintf('      %s\n','PLATFORMS');
    for i=1:length(infp)
        fprintf('        %s\n',infp(i).name);
    end
end





