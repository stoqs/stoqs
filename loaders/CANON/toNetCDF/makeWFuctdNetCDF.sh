#!/bin/bash

# For use on Western Flyer CN13ID October 2013
# Set Remote Host (RH) to what's appropriate
##RH=192.168.111.177
RH=beach.mbari.org

rsync -rv stoqsadm@$RH:/data/canon/2013_Oct/Platforms/Ships/Western_Flyer/uctd .

./uctdToNetcdf.py uctd uctd C 2.0

scp uctd/*.nc stoqsadm@$RH:/data/canon/2013_Oct/Platforms/Ships/Western_Flyer/uctd

# Clean up 
rm -r uctd

