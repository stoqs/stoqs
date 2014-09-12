#!/bin/bash 
cd /opt/stoqshg/venv-stoqs/bin
source activate
cd /opt/stoqshg/loaders/CANON/realtime
python monitorLrauvHotSpot.py -d  'Fall 2014 Dye Release Experiment in Monterey Bay' -o /mbari/LRAUV/tethys/realtime/sbdlogs/2014/201409 -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/tethys/realtime/sbdlogs/2014/201409' -b 'stoqs_september2014' -c 'CANON-ECOHAB - September 2014' > /opt/stoqshg/loaders/CANON/realtime/monitorLrauv_sep2014.out 2>&1
date >> /tmp/monitorLrauv.log
