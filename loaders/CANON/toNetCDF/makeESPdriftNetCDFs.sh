#!/bin/bash

# For use on Western Flyer CANON September 2012

scp stoqsadm@192.168.111.177:/ODSS/data/canon/2012_Sep/misc/ESPdrift/ESP_ctd.csv .
scp stoqsadm@192.168.111.177:/ODSS/data/canon/2012_Sep/misc/ESPdrift/ESP_isus.csv .

./espDriftToNetcdf.py

scp ESP_ctd.nc stoqsadm@192.168.111.177:/ODSS/data/canon/2012_Sep/misc/ESPdrift
scp ESP_isus.nc stoqsadm@192.168.111.177:/ODSS/data/canon/2012_Sep/misc/ESPdrift
