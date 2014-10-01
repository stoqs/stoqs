#!/bin/bash
# Thursday's rhodamine deployment start time

cd /home/stoqsadm/dev/stoqshg
source venv-stoqs/bin/activate
cd contrib/analysis

START=20140925T170000
END=20141010T230000

PRODUCTDIR=/data/canon/2014_Sep/Products/STOQS_Plots
MAPDIR=/data/mapserver/mapfiles/2014Fall/drift

# R_CARSON for the time of rhodamine pumping
# stella(s) for just the times in the water
# Stride daphne to avoid spurious fixes

./drift_data.py --database stoqs_september2014 --adcpPlatform M1_Mooring --adcpMinDepth 35 --adcpMaxDepth 45 --trackData \
    http://odss.mbari.org/trackingdb/position/stella101/between/20140925T180000/20140929T150000/data.csv \
    http://odss.mbari.org/trackingdb/position/R_CARSON/between/20140925T150000/20140925T200000/data.csv \
    http://odss.mbari.org/trackingdb/position/m1/between/$START/$END/data.csv \
    http://odss.mbari.org/trackingdb/position/daphne/between/$START/$END/stride/11/data.csv \
    http://odss.mbari.org/trackingdb/position/wgTiny/between/$START/$END/data.csv \
    --extent -122.3 36.3 -121.75 37.0 \
    --start $START --end $END \
    --kmlFileName $PRODUCTDIR/drift_since_$START.kml \
    --pngFileName $PRODUCTDIR/drift_since_$START.png \
    --geotiffFileName $MAPDIR/drift_since_$START.tiff \
    > /home/stoqsadm/dev/stoqshg/contrib/analysis/drift_data_sept2014_thur_rhodamine.out 2>&1
