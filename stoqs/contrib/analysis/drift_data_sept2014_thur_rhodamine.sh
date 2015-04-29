#!/bin/bash
# Thursday's rhodamine deployment start time

#PRODUCTION=false
PRODUCTION=true
if [ "$PRODUCTION" = true ]
then
    cd /home/stoqsadm/dev/stoqshg
    source venv-stoqs/bin/activate
    cd contrib/analysis
    DATABASE=stoqs_september2014
    PRODUCTDIR=/data/canon/2014_Sep/Products/STOQS_Plots
    MAPDIR=/data/mapserver/mapfiles/2014Fall/drift
    LOGFILE='/home/stoqsadm/dev/stoqshg/contrib/analysis/drift_data_sept2014_thur_rhodamine.out'
else
    DATABASE=stoqs_september2014_kraken
    PRODUCTDIR=.
    MAPDIR=.
    LOGFILE=/dev/tty
fi

START=20140925T170000
END=20141010T230000

# R_CARSON for the time of rhodamine pumping
# stella(s) for just the times in the water
# Stride daphne and makai to avoid spurious fixes

##    http://odss.mbari.org/trackingdb/position/daphne/between/$START/20141001T180000/stride/11/data.csv \
./drift_data.py --database $DATABASE --adcpPlatform M1_Mooring --adcpMinDepth 35 --adcpMaxDepth 45 --trackData \
    http://odss.mbari.org/trackingdb/position/stella101/between/20140925T180000/20140929T150000/data.csv \
    http://odss.mbari.org/trackingdb/position/R_CARSON/between/20140925T150000/20140925T200000/data.csv \
    http://odss.mbari.org/trackingdb/position/m1/between/$START/$END/data.csv \
    http://odss.mbari.org/trackingdb/position/makai_ac/between/20141001T104000/$END/data.csv \
    http://odss.mbari.org/trackingdb/position/wgTiny/between/$START/$END/data.csv \
    --extent -122.3 36.3 -121.75 37.0 \
    --start $START --end $END \
    --geotiffFileName $MAPDIR/drift_since_$START.tiff \
    --kmlFileName $PRODUCTDIR/drift_since_$START.kml \
    --pngFileName $PRODUCTDIR/drift_since_$START.png \
    > $LOGFILE 2>&1

date >> $LOGFILE

