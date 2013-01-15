#!/bin/bash

# For use on MBARI's internal network with appropriate credentials

rsync -rv mccann@elvis.shore.mbari.org:/net/atlas/ifs/mbariarchive/BOG_Archive/DataArchives/Regions/NortheastPacific/CruiseData/GOC.2012/UCTD.GOC12 .

./wfuctdToNetcdf.py UCTD.GOC12 UCTD.GOC12 goc

scp wf_uctd.nc stoqsadm@beach.mbari.org:/ODSS/data/goc/GOC_february2012/wf/uctd

# Clean up 
rm -r UCTD.GOC12
rm wf_uctd.nc
