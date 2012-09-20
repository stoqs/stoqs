#!/bin/bash

# For use on Western Flyer CANON September 2012

rsync -rv stoqsadm@192.168.111.177:/ODSS/data/canon/2012_Sep/wf/uctd .

./wfuctdToNetcdf.py

scp wf_uctd.nc stoqsadm@192.168.111.177:/ODSS/data/canon/2012_Sep/wf

# Clean up 
rm -r uctd
