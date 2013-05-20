#!/bin/bash

# For use on Western Flyer CANON September 2012
# Set Remote Host (RH) to what's appropriate
##RH=192.168.111.177
RH=beach.mbari.org

rsync -rv stoqsadm@$RH:/ODSS/data/canon/2012_Sep/wf/uctd .

./uctdToNetcdf.py uctd uctd c 2.0

scp uctd/*.nc stoqsadm@$RH:/data/canon/2012_Sep/wf/uctd

# Clean up 
rm -r uctd

