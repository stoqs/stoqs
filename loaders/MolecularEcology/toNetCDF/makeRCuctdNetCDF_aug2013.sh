#!/bin/bash

# For use on Rachel Carson CANON - SIMZ August 2013
# Set Remote Host (RH) to what's appropriate
##RH=192.168.111.177
RH=zuma.rc.mbari.org
##RH=odss.mbari.org

rsync -rv odssadm@$RH:/data/simz/2013_Aug/carson/uctd .

../../CANON/toNetCDF/uctdToNetcdf.py uctd uctd s 1.5

scp uctd/*.nc odssadm@$RH:/data/simz/2013_Aug/carson/uctd

# Clean up 
rm -r uctd
