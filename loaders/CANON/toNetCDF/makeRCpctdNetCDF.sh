#!/bin/bash

# For use on Rachel Carson CANON-ECOHAB March 2013
# Set Remote Host (RH) to what's appropriate
##RH=192.168.111.177
##RH=zuma.rc.mbari.org
RH=odss.mbari.org

rsync -rv stoqsadm@$RH:/data/canon/2013_Mar/carson/pctd .

./pctdToNetcdf.py pctd pctd 0

scp pctd/*.nc stoqsadm@$RH:/data/canon/2013_Mar/carson/pctd

# Clean up
rm -r pctd

