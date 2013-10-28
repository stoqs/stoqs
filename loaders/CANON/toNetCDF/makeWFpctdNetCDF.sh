#!/bin/bash

# For use on Western Flyer CN13ID October 2012
# Set Remote Host (RH) to what's appropriate
##RH=192.168.111.177
RH=beach.mbari.org

rsync -rv stoqsadm@$RH:/data/canon/2013_Oct/Platforms/Ships/Western_Flyer/pctd .

./pctdToNetcdf.py pctd pctd C

scp pctd/*.nc stoqsadm@$RH:/data/canon/2013_Oct/Platforms/Ships/Western_Flyer/pctd

# Clean up
rm -r pctd

