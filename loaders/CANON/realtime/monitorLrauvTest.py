python monitorLrauv.py --start '20150914T000000'  -d  'Tethys Monterey data - September 2015' --contourDir '/tmp/TestMonitorLrauv' --contourUrl 'http://dods.mbari.org/opendap/data/lrauv/stoqs/' -o /tmp/TestMonitorLrauv \
-u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/tethys/realtime/cell-logs/20150914T225647/.*Priority.nc4$' \
-b 'stoqs_lrauv' -c 'September 2015 testing' \
--append --parms bin_mean_mass_concentration_of_chlorophyll_in_sea_water bin_mean_sea_water_temperature sea_water_salinity  mass_concentration_of_oxygen_in_sea_water downwelling_photosynthetic_photon_flux_in_sea_water mole_concentration_of_nitrate_in_sea_water   --plotgroup bin_mean_mass_concentration_of_chlorophyll_in_sea_water bin_mean_sea_water_temperature sea_water_salinity
