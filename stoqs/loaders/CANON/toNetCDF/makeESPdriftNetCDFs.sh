#!/bin/bash

# For use on Western Flyer CANON September 2012
# Set Remote Host (RH) to what's appropriate
##RH=192.168.111.177
RH=beach.mbari.org

scp stoqsadm@$RH:/ODSS/data/canon/2012_Sep/misc/ESPdrift/ESP_ctd.csv .
scp stoqsadm@$RH:/ODSS/data/canon/2012_Sep/misc/ESPdrift/ESP_isus.csv .

./espDriftToNetcdf.py

scp ESP_ctd.nc stoqsadm@$RH:/ODSS/data/canon/2012_Sep/misc/ESPdrift
scp ESP_isus.nc stoqsadm@$RH:/ODSS/data/canon/2012_Sep/misc/ESPdrift

# Clean up
rm ESP_ctd.*
rm ESP_isus.*

