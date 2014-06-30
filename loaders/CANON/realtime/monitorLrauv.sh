#!/bin/bash 
cd /opt/stoqshg/venv-stoqs/bin
source activate
cd /opt/stoqshg/loaders/CANON/realtime
python monitorLrauvHotSpot.py -d  'Daphne Monterey data - June 2014' -o /mbari/LRAUV/daphne/realtime/sbdlogs/2014/201406 -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/daphne/realtime/sbdlogs/2014/201406' -b 'stoqs_june2014_t' -c 'June 2014 daphne testing' > /tmp/monitorLrauv.log 2>&1
date >> /tmp/monitorLrauv.log
