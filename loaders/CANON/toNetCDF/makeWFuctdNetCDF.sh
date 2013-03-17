#!/bin/bash

# For use on Western Flyer CANON September 2012
# Set Remote Host (RH) to what's appropriate
##RH=192.168.111.177
RH=beach.mbari.org

rsync -rv stoqsadm@$RH:/ODSS/data/canon/2012_Sep/wf/uctd .

./wfuctdToNetcdf.py uctd . c wf_uctd.nc

scp wf_uctd.nc stoqsadm@$RH:/ODSS/data/canon/2012_Sep/wf

# Clean up 
rm -r uctd
rm wf_uctd.nc
