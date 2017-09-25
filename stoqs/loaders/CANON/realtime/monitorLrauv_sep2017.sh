#!/bin/bash
cd /opt/stoqsgit_dj1.8/venv-stoqs/bin
source activate
cd /opt/stoqsgit_dj1.8/stoqs/loaders/CANON/realtime
post='--post'
debug=''
export SLACKTOKEN=${SLACKTOCKEN}
database='stoqs_canon_september2017'
urlbase='http://elvis.shore.mbari.org/thredds/catalog/LRAUV'
declare -a searchstr=("/realtime/sbdlogs/2017/.*shore.nc4$" "/realtime/cell-logs/.*Priority.nc4$" "/realtime/cell-logs/.*Normal.nc4$")
declare -a platforms=("daphne" "ahi")

pos=$(( ${#searchstr[*]} - 1 ))
last=${searchstr[$pos]}

for platform in "${platforms[@]}"
do
    for search in "${searchstr[@]}"
    do
        # get everything before the last /  - this is used as the directory base for saving the interpolated .nc files
        directory=`echo ${search} | sed 's:/[^/]*$::'`
        python monitorLrauv.py --start '20170920T000000' --end '20171020T000000' -d  'CANON September 2017 Experiment in Monterey Bay' --productDir '/mbari/ODSS/data/canon/2017_Sep/Products/LRAUV' \
 	--contourDir '/mbari/LRAUV/stoqs/' --contourUrl 'http://dods.mbari.org/opendap/data/lrauv/stoqs/' -o /mbari/LRAUV/${platform}/${directory}/ -i /mbari/LRAUV/${platform}/${directory}/ \
        -u ${urlbase}/${platform}/${search} -b ${database} -c 'CANON - September 2017'  --append --autoscale \
        --iparm chlorophyll  --booleanPlotGroup front --plotDotParmName VTHI  --parms chlorophyl front VTHI salinity temperature oxygen PAR \
        --plotgroup front VTHI chlorophyll temperature salinity \
        --latest24hr $post $debug > /tmp/monitorLrauv${platform}.out 2>&1
    done
done

