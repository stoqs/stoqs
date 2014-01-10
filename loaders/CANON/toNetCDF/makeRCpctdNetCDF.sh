#!/bin/bash

# For use for Rachel Carson September 2013 Profile CTD data
# Set Remote Host (RH) to what's appropriate
##RH=192.168.111.177
RH=beach.mbari.org

rsync -rv stoqsadm@$RH:/data/canon/2013_Sep/Platforms/Ships/Rachel_Carson/pctd .

./pctdToNetcdf.py pctd pctd 2

scp pctd/*.nc stoqsadm@$RH:/data/canon/2013_Sep/Platforms/Ships/Rachel_Carson/pctd

# Clean up
rm -r pctd

