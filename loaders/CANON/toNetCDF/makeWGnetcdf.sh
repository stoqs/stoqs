#!/bin/bash

# For use on Western Flyer CANON September 2012
# Set Remote Host (RH) to what's appropriate
RH=192.168.111.177
RH=beach.mbari.org

scp stoqsadm@$RH:/ODSS/data/canon/2012_Sep/waveglider/tracking/waveglider_gpctd_WG_CANON_september2012.txt waveglider_gpctd_WG.txt
scp stoqsadm@$RH:/ODSS/data/canon/2012_Sep/waveglider/tracking/waveglider_pco2_WG_CANON_september2012.txt waveglider_pco2_WG.txt
./wgToNetcdf.py
scp waveglider_gpctd_WG.nc stoqsadm@$RH:/ODSS/data/canon/2012_Sep/waveglider/netcdf
scp waveglider_pco2_WG.nc stoqsadm@$RH:/ODSS/data/canon/2012_Sep/waveglider/netcdf

# Clean up
rm waveglider_gpctd_WG.*
rm waveglider_pco2_WG.*

