#!/bin/bash 
STOQSDIR=/home/dcline/dev/stoqshg
cd ~/dev/venv-stoq/bin
source activate
cd $STOQSDIR/loaders/CANON/realtime

#python monitorLrauv.py -o /LRAUV/makai/realtime/sbdlogs/2014/201410 -u 'http://localhost:8080/thredds/catalog/LRAUV/makai/realtime/sbdlogs/2014/201410' -b 'stoqs_september2014' -c 'CANON-ECOHAB - September 2014' -p sea_water_temperature sea_water_salinity mass_concentration_of_chlorophyll_in_sea_water --append --interpFreq '500L' --resampleFreq '2Min'

#python monitorLrauv.py -o /LRAUV/makai/realtime/sbdlogs/2014/201410 -u 'http://localhost:8080/thredds/catalog/LRAUV/makai/realtime/sbdlogs/2014/201410' -b 'stoqs_september2014' -c 'CANON-ECOHAB - September 2014' -p /rhodamine/voltage --append

#python monitorLrauv.py -o /tmp/TestMonitorLrauv -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/makai/realtime/sbdlogs/2014/201410' -b 'stoqs_september2014' -c 'CANON-ECOHAB - September 2014' --parms sea_water_temperature sea_water_salinity mass_concentration_of_chlorophyll_in_sea_water --append --interpFreq '500L' --resampleFreq '2Min' 

python monitorLrauv.py -o /tmp/TestMonitorLrauv -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/makai/realtime/sbdlogs/2014/201410' -b 'stoqs_september2014' -c 'CANON-ECOHAB - September 2014' --parms  /rhodamine/voltage  --append 