#!/bin/bash
if [ -z "$STOQS_HOME" ]; then
  echo "Set STOQS_HOME variable first, e.g. STOQS_HOME=/opt/stoqsgit"
  exit 1
fi
if [ -z "$DATABASE_URL" ]; then
  echo "Set DATABASE_URL variable first"
  exit 1
fi
cd "$STOQS_HOME/stoqs/loaders/CANON/realtime"

urlbase='http://dods.mbari.org/thredds/catalog/LRAUV'
year=2019

declare -a searchstr=("/realtime/sbdlogs/${year}/.*shore.nc4$")
# Note that there is no year directory for in cell-logs - crawling for cell-logs takes longer - uncomment to process cell-logs
##declare -a searchstr=("/realtime/sbdlogs/2019/.*shore.nc4$" "/realtime/cell-logs/.*Priority.nc4$" "/realtime/cell-logs/.*Normal.nc4$")
declare -a platforms=('ahi' 'aku' 'brezo' 'daphne' 'galene' 'makai' 'opah' 'pontus' 'tethys' 'triton' 'whoidhs')

for platform in "${platforms[@]}"
do
    for search in "${searchstr[@]}"
    do
        directory=`echo ${search} | sed 's:/[^/]*$::'`
        echo "Executing monitorLrauv.py for directory = ${directory}"
        python monitorLrauv.py --start '20191001T000000' --end '20191031T000000' \
 	                           -o /mbari/LRAUV/${platform}/${directory}/ -i /mbari/LRAUV/${platform}/${directory} \
        -u ${urlbase}/${platform}${search} \
        --iparm depth \
        --parms depth chlorophyll temperature salinity mass_concentration_of_oxygen_in_sea_water \
        --plotparms depth chlorophyll temperature salinity mass_concentration_of_oxygen_in_sea_water  
    done
done

