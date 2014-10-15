#!/bin/bash 
STOQSDIR=/opt/stoqshg
cd $STOQSDIR/venv-stoqs/bin
source activate
cd $STOQSDIR/loaders/CANON/realtime

##python monitorLrauv.py -o /mbari/LRAUV/tethys/realtime/sbdlogs/2014/201409 -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/tethys/realtime/sbdlogs/2014/201409' -b 'stoqs_september2014' -c 'CANON-ECOHAB - September 2014' --parms sea_water_temperature sea_water_salinity mass_concentration_of_chlorophyll_in_sea_water voltage --append > $STOQSDIR/loaders/CANON/realtime/monitorLrauv_sep2014_tethys.out 2>&1
python monitorLrauv.py -o /mbari/LRAUV/tethys/realtime/sbdlogs/2014/201410 -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/tethys/realtime/sbdlogs/2014/201410' -b 'stoqs_september2014' -c 'CANON-ECOHAB - September 2014' --parms sea_water_temperature sea_water_salinity mass_concentration_of_chlorophyll_in_sea_water voltage --append --interpFreq '500L' --resampleFreq '2Min' > $STOQSDIR/loaders/CANON/realtime/monitorLrauv_sep2014_tethys.out 2>&1

python monitorLrauv.py -o /mbari/LRAUV/tethys/realtime/sbdlogs/2014/201410 -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/tethys/realtime/sbdlogs/2014/201410' -b 'stoqs_september2014' -c 'CANON-ECOHAB - September 2014' --parms  /rhodamine/voltage  --append > $STOQSDIR/loaders/CANON/realtime/monitorLrauv_sep2014_tethys.out 2>&1

##python monitorLrauv.py -o /mbari/LRAUV/daphne/realtime/sbdlogs/2014/201409 -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/daphne/realtime/sbdlogs/2014/201409' -b 'stoqs_september2014' -c 'CANON-ECOHAB - September 2014' --parms sea_water_temperature sea_water_salinity mass_concentration_of_chlorophyll_in_sea_water --append > $STOQSDIR/loaders/CANON/realtime/monitorLrauv_sep2014_daphne.out 2>&1
python monitorLrauv.py -o /mbari/LRAUV/daphne/realtime/sbdlogs/2014/201410 -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/daphne/realtime/sbdlogs/2014/201410' -b 'stoqs_september2014' -c 'CANON-ECOHAB - September 2014' --parms sea_water_temperature sea_water_salinity mass_concentration_of_chlorophyll_in_sea_water --append --interpFreq '500L' --resampleFreq '2Min' > $STOQSDIR/loaders/CANON/realtime/monitorLrauv_sep2014_daphne.out 2>&1

python monitorLrauv.py -o /mbari/LRAUV/daphne/realtime/sbdlogs/2014/201410 -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/daphne/realtime/sbdlogs/2014/201410' -b 'stoqs_september2014' -c 'CANON-ECOHAB - September 2014' --parms  /rhodamine/voltage  --append > $STOQSDIR/loaders/CANON/realtime/monitorLrauv_sep2014_daphne.out 2>&1

##python monitorLrauv.py -o /mbari/LRAUV/makai/realtime/sbdlogs/2014/201409 -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/makai/realtime/sbdlogs/2014/201409' -b 'stoqs_september2014' -c 'CANON-ECOHAB - September 2014' --parms sea_water_temperature sea_water_salinity mass_concentration_of_chlorophyll_in_sea_water --append > $STOQSDIR/loaders/CANON/realtime/monitorLrauv_sep2014_makai.out 2>&1
python monitorLrauv.py -o /mbari/LRAUV/makai/realtime/sbdlogs/2014/201410 -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/makai/realtime/sbdlogs/2014/201410' -b 'stoqs_september2014' -c 'CANON-ECOHAB - September 2014' --parms sea_water_temperature sea_water_salinity mass_concentration_of_chlorophyll_in_sea_water --append --interpFreq '500L' --resampleFreq '2Min' > $STOQSDIR/loaders/CANON/realtime/monitorLrauv_sep2014_makai.out 2>&1

python monitorLrauv.py -o /mbari/LRAUV/makai/realtime/sbdlogs/2014/201410 -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/makai/realtime/sbdlogs/2014/201410' -b 'stoqs_september2014' -c 'CANON-ECOHAB - September 2014' --parms  /rhodamine/voltage  --append > $STOQSDIR/loaders/CANON/realtime/monitorLrauv_sep2014_makai.out 2>&1
