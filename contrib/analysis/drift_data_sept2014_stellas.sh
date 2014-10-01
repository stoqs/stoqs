#!/bin/bash
# All stella deployments for CANON-ECOHAB September 2014

#cd /opt/stoqshg
#source venv-stoqs/bin/activate
#cd contrib/analysis

# stella(s) for just the times in the water; see:
# http://odss.mbari.org/data/canon/2014_Sep/Platforms/Drifters/Stella/stella_2014_pos.csv
# TODO: Have the --trackData option read the urls directly from URLs or files like this

./drift_data.py --title 'Stella deployments for CANON-ECOHAB - September 2014' --trackData \
    http://odss.mbari.org/trackingdb/position/stella122/between/20140922T171500/20140923T141500/data.csv\
    http://odss.mbari.org/trackingdb/position/stella101/between/20140922T171500/20140923T140000/data.csv\
    http://odss.mbari.org/trackingdb/position/stella110/between/20140922T171500/20140924T035700/data.csv\
    http://odss.mbari.org/trackingdb/position/stella101/between/20140923T163000/20141010T004500/data.csv\
    http://odss.mbari.org/trackingdb/position/stella103/between/20140923T181500/20140924T171500/data.csv\
    http://odss.mbari.org/trackingdb/position/stella122/between/20140923T192000/20140924T164000/data.csv\
    http://odss.mbari.org/trackingdb/position/stella122/between/20140924T190400/20140925T214500/data.csv\
    http://odss.mbari.org/trackingdb/position/stella103/between/20140925T201500/20140929T171500/data.csv\
    http://odss.mbari.org/trackingdb/position/stella122/between/20140927T205000/20140928T210000/data.csv\
    http://odss.mbari.org/trackingdb/position/stella120/between/20140928T171000/20140929T170000/data.csv\
    http://odss.mbari.org/trackingdb/position/stella111/between/20140928T215000/20140929T180000/data.csv\
    http://odss.mbari.org/trackingdb/position/stella120/between/20140929T171500/20140930T171700/data.csv\
    http://odss.mbari.org/trackingdb/position/stella111/between/20140930T152100/20140930T165000/data.csv\
    http://odss.mbari.org/trackingdb/position/stella120/between/20140930T070000/20141009T070000/data.csv\
    http://odss.mbari.org/trackingdb/position/stella111/between/20141001T142500/20141009T070000/data.csv\
    --kmlFileName stellas.kml --pngFileName stellas.png --geotiffFileName stellas.tiff
