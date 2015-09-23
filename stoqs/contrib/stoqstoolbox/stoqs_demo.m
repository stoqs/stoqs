%DEMO FOR STOQSTOOLBOX
%WILL SHOW THE TWO MOST IMPORTANT FUNCTIONS

    disp('WELCOME TO THE STOQSTOOLBOX DEMO');
    disp('FUNCTION stoqs_showall USE ALL THE TOOL AVAILABLE ON STOQSTOOLBOX');
    disp('TO CONNECT TO A STOQS SERVER AND SHOW ALL THE INFORMATION AVAILABLE ON IT');
    disp('.');
server='http://odss.mbari.org/canon';
    disp('NAME OF THE SERVER:')
    disp(server)
    disp('stoqs_showall(server)')
    disp('PRESS ANY BUTTON TO CONTINUE')
    pause
stoqs_showall(server)
    disp('.');
    disp('.');
    disp('.');
    disp('DOWNLOAD THE DATA FROM STOQS SERVER TO MATLAB')
    disp('WE MUST KNOW:')
    disp('NAME OF OUR STOQS SERVER : http://odss.mbari.org/canon/stoqs_may2012')
    disp('INITIAL DATE : 2012-05-30 00:10:00')
    disp('END DATE: 2012-05-30 01:10:00')
    disp('TOP DEPTH: 1')
    disp('BOTTOM DEPTH: 2')
    disp('VARIABLE STANDARD NAME: sea_water_temperature')
    disp('PLATFORM: dorado')
stoqs_server='http://odss.mbari.org/canon/stoqs_may2012';
dateini='2012-05-30 00:10:00';
datend='2012-05-30 01:10:00';
top='1';
bottom='2';
standard='sea_water_temperature';
platform='dorado';
    disp('.');
    disp('.');
    disp('.');
d=stoqs_down(stoqs_server,dateini,datend,top,bottom,platform,'',standard);
    disp('IN THE VARIABLE "d"  WE HAVE ALL THE STRUCTURE DATA DOWNLOAD FROM STOQS')
    disp('.')
    disp('MAKE A PLOT OF THE DATA DOWNLOAD, PRESS ANY KEY')
    pause
scatter(d.time,d.depth*-1,10,d.value);
t=colorbar;
datetick('x','HH');
set(get(t,'ylabel'),'String', 'Temperature','FontSize',18);
xlabel('Hours','FontSize',18);
ylabel('Depth','FontSize',18);
set(gca,'FontSize',18);

disp('IN THE FOLDER DEMO YOU WILL FIND SOME EXAMPLES TO USE STOQSTOOLBOX FOR MODEL VALIDATION');

