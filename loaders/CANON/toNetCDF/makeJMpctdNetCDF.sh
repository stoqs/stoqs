#!/bin/bash

# For use with the John Martin Septemember 2013 data
# Set Remote Host (RH) to what's appropriate
##RH=192.168.111.177
RH=beach.mbari.org

rsync -rv stoqsadm@$RH:/data/canon/2013_Sep/Platforms/Ships/Martin/pctd .

./pctdToNetcdf.py pctd pctd 2

scp pctd/*.nc stoqsadm@$RH:/data/canon/2013_Sep/Platforms/Ships/Martin/pctd

# Clean up
rm -r pctd

