#!/bin/bash
if [ -z "$STOQS_HOME" ]; then
  echo "Set STOQS_HOME variable first, e.g. STOQS_HOME=/src/stoqsgit"
  exit 1
fi
if [ -z "$DATABASE_URL" ]; then
  echo "Set DATABASE_URL variable first"
  exit 1
fi
cd "$STOQS_HOME/stoqs/loaders/CANON/realtime"
post='--post'
debug=''
#debug='--debug'
export SLACKTOKEN=${SLACKTOCKEN}
database='stoqs_canon_september2018'
urlbase='http://dods.mbari.org/opendap/data/lrauv/'
latest24plot='--latest24hr'

python monitorLrauvEvents.py \
--vehicles tethys daphne \
-d  'LRAUV Monterey data - September 2018' --productDir '/mbari/ODSS/data/other/routine/Products/LRAUV' \
--contourDir /tmp/stoqs \
--contourUrl 'http://dods.mbari.org/opendap/data/lrauv/stoqs/' \
-o /mbari/LRAUV/stoqs \
-i /mbari/LRAUV \
-u $urlbase \
-b $database \
-c 'LRAUV Monterey data - September Season 2018'  \
--append --autoscale \
--iparm depth \
--booleanPlotGroup front \
--plotDotParmName vertical_temperature_homogeneity_index \
--parms depth bin_median_mass_concentration_of_chlorophyll_in_sea_water \
front \
depth \
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
chlorophyll \
temperature \
salinity \
VTHI \
$latest24plot $post $debug #> /tmp/monitorLrauvEvents.out 2>&1
