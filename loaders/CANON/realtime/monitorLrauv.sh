#!/bin/bash 
cd /opt/stoqshg/venv-stoqs/bin
source activate
cd /opt/stoqshg/loaders/CANON/realtime
python monitorLrauvHotSpot.py -d  'Daphne Monterey data' -o /mbari/LRAUV/daphne/realtime/sbdlogs/2014/201405 -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/daphne/realtime/sbdlogs/2014/201405' -b 'stoqs_may2014_t' -c 'May 2014 daphne testing' > /tmp/monitorLrauv.log 2>&1
date >> /tmp/monitorLrauv.log
