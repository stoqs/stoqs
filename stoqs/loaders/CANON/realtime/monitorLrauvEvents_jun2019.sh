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
database='stoqs_lrauv_jun2019'
urlbase='http://dods.mbari.org/opendap/data/lrauv/'
latest24plot='--latest24hr'

python monitorLrauvEvents.py \
--vehicles whoidhs \
-d  'LRAUV data - June 2019' --productDir '/mbari/ODSS/data/other/routine/Products/LRAUV' \
--contourDir /tmp/stoqs \
--contourUrl 'http://dods.mbari.org/opendap/data/lrauv/stoqs/' \
-o /mbari/LRAUV/stoqs \
-i /mbari/LRAUV \
-u $urlbase \
-b $database \
-c 'LRAUV data - June 2019'  \
--append --autoscale \
--iparm depth \
--booleanPlotGroup front \
--plotDotParmName vertical_temperature_homogeneity_index \
--parms depth concentration_of_chromophoric_dissolved_organic_matter_in_sea_water \
mass_concentration_of_oxygen_in_sea_water  \
--plotparms depth concentration_of_chromophoric_dissolved_organic_matter_in_sea_water \
mass_concentration_of_oxygen_in_sea_water  \
--plotgroup \
front \
chlorophyll \
temperature \
salinity \
VTHI \
$latest24plot $post $debug #> /tmp/monitorLrauvEvents.out 2>&1
