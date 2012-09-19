#!/bin/bash

# For use on Western Flyer CANON September 2012

rsync -rv stoqsadm@192.168.111.177:/ODSS/data/canon/2012_Sep/wf/pctd .

./wfpctdToNetcdf.py

scp pctd/*.nc stoqsadm@192.168.111.177:/ODSS/data/canon/2012_Sep/wf/pctd

