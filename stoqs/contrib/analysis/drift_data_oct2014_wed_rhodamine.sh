#!/bin/bash
# Thursday's rhodamine deployment start time

PRODUCTION=false
#PRODUCTION=true
if [ "$PRODUCTION" = true ]
then
    cd /home/stoqsadm/dev/stoqshg
    source venv-stoqs/bin/activate
    cd contrib/analysis
    DATABASE=stoqs_september2014
    PRODUCTDIR=/data/canon/2014_Sep/Products/STOQS_Plots
    MAPDIR=/data/mapserver/mapfiles/2014Fall/drift
    LOGFILE='/home/stoqsadm/dev/stoqshg/contrib/analysis/drift_data_oct2014_wed_rhodamine.out'
else
    # Set DATABASE_URL, e.g.:
    # export DATABASE_URL=postgis://everyone:guest@kraken.shore.mbari.org:5433/stoqs
    DATABASE=stoqs_september2014
    PRODUCTDIR=.
    MAPDIR=.
    LOGFILE=/dev/tty
fi

START=20141008T180000
END=20141015T230000

TRACKINGSERVER=odss.mbari.org

# R_CARSON for the time of rhodamine pumping
# stella(s) for just the times in the water
# Stride daphne and makai to avoid spurious fixes

##    http://odss.mbari.org/trackingdb/position/daphne/between/$START/20141001T180000/stride/11/data.csv \
./drift_data.py --database $DATABASE --adcpPlatform M1_Mooring --adcpMinDepth 25 --adcpMaxDepth 35 --trackData \
    http://$TRACKINGSERVER/trackingdb/position/R_CARSON/between/20141008T170000/20141008T190000/data.csv \
    http://$TRACKINGSERVER/trackingdb/position/m1/between/$START/$END/data.csv \
    http://$TRACKINGSERVER/trackingdb/position/makai_ac/between/20141008T170000/$END/data.csv \
    --stoqsData "http://stoqs.mbari.org:8000/stoqs_september2014/api/measuredparameter.csv?parameter__name=rhodamine&measurement__instantpoint__activity__platform__name=dorado&measurement__instantpoint__timevalue__gt=2014-10-08 21:45:56&measurement__instantpoint__timevalue__lt=2014-10-08 21:50:44&measurement__depth__gte=23.56&measurement__depth__lte=34.07&rhodamine_MIN=0.1007&rhodamine_MAX=0.3987" \
    --start $START --end $END \
    --geotiffFileName $MAPDIR/drift_since_$START.tiff \
    --kmlFileName $PRODUCTDIR/drift_since_$START.kml \
    --pngFileName $PRODUCTDIR/drift_since_$START.png \
    --verbose \
    > $LOGFILE 2>&1

date >> $LOGFILE

