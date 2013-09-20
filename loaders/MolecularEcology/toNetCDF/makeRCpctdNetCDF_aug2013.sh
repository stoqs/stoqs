#!/bin/bash

# For use on Rachel Carson CANON-ECOHAB March 2013
# Set Remote Host (RH) to what's appropriate
##RH=192.168.111.177
RH=zuma.rc.mbari.org
##RH=odss.mbari.org

rsync -rv odssadm@$RH:/data/simz/2013_Aug/carson/pctd .

../../CANON/toNetCDF/pctdToNetcdf.py pctd pctd s

scp pctd/*.nc odssadm@$RH:/data/simz/2013_Aug/carson/pctd

# Clean up
rm -r pctd

