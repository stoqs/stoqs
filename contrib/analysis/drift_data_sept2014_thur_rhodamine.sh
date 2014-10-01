#!/bin/bash
# Thursday's rhodamine deployment start time

START=20140925T170000
END=20141010T230000

# R_CARSON for the time of rhodamine pumping
# stella(s) for just the times in the water
# Stride daphne to avoid spurious fixes

./drift_data.py --database stoqs_september2014_kraken --adcpPlatform M1_Mooring --adcpMinDepth 35 --adcpMaxDepth 45 --trackData \
    http://odss.mbari.org/trackingdb/position/stella101/between/20140925T180000/20140929T150000/data.csv \
    http://odss.mbari.org/trackingdb/position/R_CARSON/between/20140925T150000/20140925T200000/data.csv \
    http://odss.mbari.org/trackingdb/position/m1/between/$START/$END/data.csv \
    http://odss.mbari.org/trackingdb/position/daphne/between/$START/$END/stride/11/data.csv \
    http://odss.mbari.org/trackingdb/position/wgTiny/between/$START/$END/data.csv \
    --start $START --end $END \
    --kmlFileName drift_since_$START.kml --pngFileName drift_since_$START.png --geotiffFileName drift_since_$START.tiff
