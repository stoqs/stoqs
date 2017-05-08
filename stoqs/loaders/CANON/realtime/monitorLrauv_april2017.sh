#!/bin/bash
cd /opt/stoqsgit_dj1.8/venv-stoqs/bin
source activate
cd /opt/stoqsgit_dj1.8/stoqs/loaders/CANON/realtime
post='--post'
#post=''
debug=''
#debug='--debug'
export SLACKTOKEN=${SLACKTOCKEN}
database='stoqs_canon_april2017'
urlbase='http://elvis.shore.mbari.org/thredds/catalog/LRAUV'
declare -a searchstr=("/realtime/cell-logs/.*Normal.nc4$" "/realtime/sbdlogs/2017/.*shore.nc4$" "/realtime/cell-logs/.*Priority.nc4$")
declare -a platforms=("tethys" "aku" "makai" "ahi" "opah" "daphne")

pos=$(( ${#searchstr[*]} - 1 ))
last=${searchstr[$pos]}

parms="{
            \"CTD_NeilBrown\": [
            { \"name\":\"bin_mean_sea_water_salinity\" , \"rename\":\"bin_mean_salinity\" },
            { \"name\":\"bin_mean_sea_water_temperature\" , \"rename\":\"bin_mean_temperature\" }
            ],
            \"VerticalTemperatureHomogeneityIndexCalculator\": [  \
            { \"name\":\"vertical_temperature_homogeneity_index\", \"rename\":\"VTHI\" }
            ],
            \"WetLabsBB2FL\": [  \
            { \"name\":\"bin_mean_mass_concentration_of_chlorophyll_in_sea_water\", \"rename\":\"bin_mean_chlorophyll\" }
            ],
            \"PAR_Licor\": [
            { \"name\":\"bin_mean_downwelling_photosynthetic_photon_flux_in_sea_water\", \"rename\":\"bin_mean_PAR\" }
            ],
            \"ISUS\" : [
            { \"name\":\"bin_mean_mole_concentration_of_nitrate_in_sea_water\", \"rename\":\"bin_mean_nitrate\" }
            ],
            \"Aanderaa_O2\": [
            { \"name\":\"bin_mean_mass_concentration_of_oxygen_in_sea_water\", \"rename\":\"bin_mean_oxygen\" }
            ]
        }"

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
        python monitorLrauv.py --start '20170413T000000' --end '20171231T000000' -d  'KISS CANON Spring 2017 Experiment in Monterey Bay' --productDir '/mbari/ODSS/data/other/routine/Products/LRAUV' \
 	    --contourDir '/mbari/LRAUV/stoqs' --contourUrl 'http://dods.mbari.org/opendap/data/lrauv/stoqs/' \
 	    -i /mbari/LRAUV/${platform}/${directory}/ \
 	    -o /mbari/LRAUV/${platform}/${directory}/ \
        -u ${urlbase}/${platform}/${search} -b ${database} -c 'KISS CANON Spring 2017 Experiment in Monterey Bay'  --append --autoscale \
        --iparm bin_mean_chlorophyll \
	--booleanPlotGroup front \
 	--plotDotParmName VTHI \
 	--parms \
        sea_water_salinity \
        sea_water_temperature \
 	--groupparms "${parms}" \
    --plotparms front \
	    VTHI \
        bin_mean_chlorophyll \
        bin_mean_temperature \
        bin_mean_salinity \
        bin_mean_chlorophyll  \
        bin_mean_PAR \
        sea_water_salinity \
        sea_water_temperature \
    --plotgroup \
	    front \
	    VTHI \
        bin_mean_chlorophyll \
        bin_mean_temperature \
        bin_mean_salinity \
        sea_water_temperature \
        sea_water_salinity \
        $latest24plot $post $debug > /tmp/monitorLrauv${platform}.out 2>&1
    done
done
