
function stoqs_show(u)
%u='http://192.168.79.141:8000/default';
%---------------------CAMPAIGN----------------
infc=info_stoqs(u,'campaign');
infp=info_stoqs(u,'platform');
%infa=info_stoqs(u,'activity'); %conect to the table activity to get the ID of each of the activities
infpa=info_stoqs(u,'parameter');


%Get the ID of each plataform and the name. Create a vector of the names,
%where the position of the name is the ID, so I can get easily the name of
%the platform
for i=1:length(infp);platname{infp(i).id}=infp(i).name;end

%Get the ID of each parameter and the name. Create a vector of the names,
%where the position of the name is the ID, so I can get easily the name of
%the parameter
for i=1:length(infpa);parname{infpa(i).id}=infpa(i).name;end




%We want to show for each campain, what platform are and the variable who
%each measure.
for i=1:length(infc)
    fprintf('%s\n','CAMPAIGN');
    fprintf('   %s  from  %s to %s\n',infc(i).name,infc(i).startdate,infc(i).enddate);
    fprintf('      %s\n','PLATFORMS');
    infa=info_stoqs(u,'activity.json?campaign=',num2str(infc(i).id));
    for j=1:length(infa)
        infact=info_stoqs(u,'activityparameter.json?activity=',num2str(infa(i).id));
        fprintf('        %s\n',char(platname(infa(j).platform)));
        for k=1:length(infact)
            fprintf('              %s\n',char(parname(infact(k).parameter)));
        end    
    end
end

