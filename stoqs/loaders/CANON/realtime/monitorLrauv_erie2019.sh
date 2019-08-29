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
post='--post'
#post=''
debug=''
##debug='--debug'
database='stoqs_erie2019'
urlbase='http://dods.mbari.org/thredds/catalog/LRAUV'
declare -a searchstr=("/realtime/sbdlogs/2019/.*shore.nc4$" "/realtime/cell-logs/.*Priority.nc4$" "/realtime/cell-logs/.*Normal.nc4$")
##declare -a searchstr=("/realtime/cell-logs/.*Normal.nc4$")
##declare -a searchstr=("/realtime/sbdlogs/2019/.*shore.nc4$")
declare -a platforms=("tethys" "makai")

pos=$(( ${#searchstr[*]} - 1 ))
last=${searchstr[$pos]}

for platform in "${platforms[@]}"
do
    for search in "${searchstr[@]}"
    do
    # only plot the 24 hour plot in the last search group, otherwise this updates the timestamp on the files stored in the odss-data-repo per every search string
    if [[ $search == $last ]]
    then
    latest24plot='--latest24hr'
    else
    latest24plot=''
    fi

        # get everything before the last /  - this is used as the directory base for saving the interpolated .nc files
        directory=`echo ${search} | sed 's:/[^/]*$::'`
        python monitorLrauv.py --start '20190813T000000' --end '20190829T000000' -d  'Lake Erie Makai ESP Deployments in 2019' --productDir '/mbari/ODSS/data/other/routine/Products/LRAUV' \
 	--contourDir '/mbari/LRAUV/stoqs' --contourUrl 'http://dods.mbari.org/opendap/data/lrauv/stoqs/' -o /mbari/LRAUV/${platform}/${directory}/ -i /mbari/LRAUV/${platform}/${directory} \
        -u ${urlbase}/${platform}/${search} -b ${database} -c 'Lake Erie ESP 2019'  --append --autoscale \
        --iparm depth \
        --parms depth chlorophyll temperature salinity mass_concentration_of_oxygen_in_sea_water \
        --plotparms depth chlorophyll temperature salinity mass_concentration_of_oxygen_in_sea_water  
        ##--plotgroup \
        ##chlorophyll
        ##$latest24plot $post $debug > /tmp/monitorLrauv${platform}.out 2>&1
    done
done

