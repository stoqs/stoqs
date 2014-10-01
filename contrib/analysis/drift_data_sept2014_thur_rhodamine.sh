#!/bin/bash
# Thursday's rhodamine deployment start time

START=20140925T170000
END=20141001T230000

./drift_data.py --database stoqs_september2014_kraken --adcpPlatform M1_Mooring --adcpMinDepth 35 --adcpMaxDepth 45 --trackData \
    http://odss.mbari.org/trackingdb/position/stella101/between/20140925T180000/20140929T150000/data.csv \
    http://odss.mbari.org/trackingdb/position/R_CARSON/between/20140925T150000/20140925T200000/data.csv \
    http://odss.mbari.org/trackingdb/position/m1/between/20140925T150000/20140929T040000/data.csv \
    http://odss.mbari.org/trackingdb/position/daphne/between/$START/$END/stride/11/data.csv \
    http://odss.mbari.org/trackingdb/position/wgTiny/between/$START/$END/data.csv \
    --extent -122.3 36.3 -121.75 37.0 \
    --start $START --end $END --kmlFileName thur_tues.kml \
    --pngFileName thur_tues.png --geotiffFileName thur_tues.tiff
