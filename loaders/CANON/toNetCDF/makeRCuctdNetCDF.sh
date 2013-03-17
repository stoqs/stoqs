#!/bin/bash

# For use on Rachel Carson CANON - ECOHAB March 2013
# Set Remote Host (RH) to what's appropriate
##RH=192.168.111.177
RH=zuma.rc.mbari.org

rsync -rv odssadm@$RH:/data/canon/2013_Mar/carson/uctd .

./uctdToNetcdf.py uctd . 0 rc_uctd.nc

scp rc_uctd.nc odssadm@$RH:/data/canon/2013_Mar/carson

# Clean up 
rm -r uctd
rm rc_uctd.nc
