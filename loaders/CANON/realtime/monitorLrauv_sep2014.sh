#!/bin/bash 
STOQSDIR=/opt/stoqshg
cd $STOQSDIR/venv-stoqs/bin
source activate
cd $STOQSDIR/loaders/CANON/realtime
python monitorLrauv.py -o /mbari/LRAUV/tethys/realtime/sbdlogs/2014/201409 -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/tethys/realtime/sbdlogs/2014/201409' -b 'stoqs_september2014' -c 'CANON-ECOHAB - September 2014' > $STOQSDIR/loaders/CANON/realtime/monitorLrauv_sep2014.out 2>&1
