#!/bin/bash

# For use on Western Flyer CANON September 2012

scp stoqsadm@192.168.111.177:/ODSS/data/canon/2012_Sep/waveglider/tracking/waveglider_gpctd_WG.txt .
scp stoqsadm@192.168.111.177:/ODSS/data/canon/2012_Sep/waveglider/tracking/waveglider_pco2_WG.txt .
./wgToNetcdf.py
scp waveglider_gpctd_WG.nc stoqsadm@192.168.111.177:/ODSS/data/canon/2012_Sep/waveglider/netcdf
scp waveglider_pco2_WG.nc stoqsadm@192.168.111.177:/ODSS/data/canon/2012_Sep/waveglider/netcdf
