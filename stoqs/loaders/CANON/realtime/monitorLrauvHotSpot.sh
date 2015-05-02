#!/bin/bash 
cd /opt/stoqshg/venv-stoqs/bin
source activate
cd /opt/stoqshg/loaders/CANON/realtime
python monitorLrauvHotSpot.py -d  'Test Daphne hotspot data' -o /mbari/LRAUV/daphne/realtime/hotspotlogs -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/daphne/realtime/hotspotlogs' -b 'stoqs_canon_apr2014_t' -c 'CANON-ECOHAB - April 2014 for testing' > /tmp/monitorLrauvHotSpot.log 2>&1
date >> /tmp/monitorLrauvHotSpot.log
