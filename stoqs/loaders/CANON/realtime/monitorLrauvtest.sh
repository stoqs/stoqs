#!/bin/bash 
STOQSDIR=~/dev/stoqshg
cd $STOQSDIR/venv-stoqshg/bin
source activate
cd $STOQSDIR/loaders/CANON/realtime

python monitorLrauv.py -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/tethys/realtime/sbdlogs/2014/201409' -b 'stoqs_september2014' -c 'CANON-ECOHAB - September 2014' --parms sea_water_temperature sea_water_salinity mass_concentration_of_chlorophyll_in_sea_water voltage > $STOQSDIR/loaders/CANON/realtime/monitorLrauv_sep2014_tethys.out 2>&1

