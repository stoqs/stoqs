#!/bin/bash
cd /opt/stoqsgit_dj1.8/venv-stoqs/bin
source activate
cd /opt/stoqsgit_dj1.8/stoqs/loaders/CANON/realtime
post='--post'
#post=''
debug=''
#debug='--debug'
export SLACKTOKEN=${SLACKTOCKEN}
database='stoqs_ps2017'
urlbase='http://elvis.shore.mbari.org/thredds/catalog/LRAUV'
declare -a searchstr=("/realtime/sbdlogs/2017/.*shore.nc4$" "/realtime/cell-logs/.*Priority.nc4$" "/realtime/cell-logs/.*Normal.nc4$")
declare -a platforms=("tethys" "daphne" "makai")

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
    python monitorLrauv.py --start '20170515T000000' --end '20170917T000000' -d  'LRAUV Monterey data - Post Season 2017' --productDir '/mbari/ODSS/data/other/routine/Products/LRAUV' \
--contourDir '/mbari/LRAUV/stoqs' --contourUrl 'http://dods.mbari.org/opendap/data/lrauv/stoqs/' -o /mbari/LRAUV/${platform}/${directory}/ -i /mbari/LRAUV/${platform}/${search} \
    -u ${urlbase}/${platform}/${search} -b ${database} -c 'LRAUV Monterey data - Post Season 2017'  --append --autoscale \
    --iparm bin_mean_mass_concentration_of_chlorophyll_in_sea_water \
--booleanPlotGroup front \
--plotDotParmName vertical_temperature_homogeneity_index \
    --parms bin_median_mass_concentration_of_chlorophyll_in_sea_water \
front \
vertical_temperature_homogeneity_index \
    bin_mean_mass_concentration_of_chlorophyll_in_sea_water \
    bin_median_mass_concentration_of_chlorophyll_in_sea_water \
    bin_mean_sea_water_temperature \
    bin_median_sea_water_temperature \
    bin_mean_sea_water_temperature  \
    bin_median_sea_water_temperature  \
    bin_mean_sea_water_salinity \
    bin_median_sea_water_salinity \
    sea_water_salinity \
    sea_water_temperature  \
    mass_concentration_of_oxygen_in_sea_water  \
    downwelling_photosynthetic_photon_flux_in_sea_water \
    --plotgroup \
front \
vertical_temperature_homogeneity_index \
    bin_mean_mass_concentration_of_chlorophyll_in_sea_water \
    bin_mean_sea_water_temperature \
    bin_mean_sea_water_salinity \
    $latest24plot $post $debug > /tmp/monitorLrauv${platform}.out 2>&1
    done
done

