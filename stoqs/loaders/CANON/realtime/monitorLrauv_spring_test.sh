#!/bin/bash 
cd ~/dev/stoqs/venv-stoqs/bin
source activate
cd ~/dev/stoqs/loaders/CANON/realtime
#python monitorLrauv.py -d  'Daphne Monterey data - April 2015' -t 'http://dods.mbari.org/opendap/data/lrauv/stoqs/' -s 100 -i -o /tmp/TestMonitorLrauv -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/daphne/realtime/sbdlogs/2015/201503/.*shore.nc4$' -b 'stoqs_lrauv' -c 'April 2015 testing' --append --parms sea_water_temperature sea_water_salinity mass_concentration_of_chlorophyll_in_sea_water
#python monitorLrauv.py --start '20150301T000000'  -d  'Daphne Monterey data - April 2015' -s 100 --contourDir '/tmp/TestMonitorLrauv' --contourUrl 'http://dods.mbari.org/opendap/data/lrauv/stoqs/' -o /tmp/TestMonitorLrauv -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/daphne/realtime/sbdlogs/2015/201503/.*shore.nc4$' -b 'stoqs_lrauv' -c 'April 2015 testing' --append --parms sea_water_temperature sea_water_salinity mass_concentration_of_chlorophyll_in_sea_water --plotgroup bin_mean_mass_concentration_of_chlorophyll_in_sea_water,mass_concentration_of_chlorophyll_in_sea_water bin_mean_sea_water_temperature,sea_water_temperature bin_sea_water_salinity,sea_water_salinity
python monitorLrauv.py --start '20150509T000000'  -d  'Daphne Monterey data - April 2015' --contourDir '/tmp/TestMonitorLrauv' --contourUrl 'http://dods.mbari.org/opendap/data/lrauv/stoqs/'
-o /tmp/TestMonitorLrauv -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/daphne/realtime/sbdlogs/2015/201505/20150519T054424/.*shore.nc4$' -b 'stoqs_lrauv' -c 'April 2015 testing'
--append --parms bin_mean_mass_concentration_of_chlorophyll_in_sea_water bin_mean_sea_water_temperature sea_water_salinity  mass_concentration_of_oxygen_in_sea_water downwelling_photosynthetic_photon_flux_in_sea_water mole_concentration_of_nitrate_in_sea_water   --plotgroup bin_mean_mass_concentration_of_chlorophyll_in_sea_water bin_mean_sea_water_temperature sea_water_salinity


#> /tmp/monitorLrauv.log 2>&1 date >> /tmp/monitorLrauv.log
#python monitorLrauv.py -d  'Daphne Monterey data - April 2015' --contourDir '/tmp/TestMonitorLrauv'
# --contourUrl 'http://dods.mbari.org/opendap/data/lrauv/' -s 10 -o /tmp/TestMonitorLrauv
# -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/daphne/realtime/cell-logs/.*Priority.nc4$' -b 'stoqs_lrauv' -c 'April 2015 testing'  --append --parms bin_mean_sea_water_temperature bin_mean_sea_water_salinity bin_mean_mass_concentration_of_chlorophyll_in_sea_water --plotgroup bin_mass_concentration_of_chlorophyll_in_sea_water,mass_concentration_of_chlorophyll_in_sea_water bin_mean_sea_water_temperature,sea_water_temperature bin_sea_water_salinity,sea_water_salinity
#> /tmp/monitorLrauv.log 2>&1 date >> /tmp/monitorLrauv.log

