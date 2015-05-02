#!/bin/bash

# Use for Western Flyer Gulf of California February 2012 data

rsync -rv mccann@elvis.shore.mbari.org:/net/atlas/ifs/mbariarchive/BOG_Archive/DataArchives/Regions/NortheastPacific/CruiseData/GOC.2012/pCTD.GOC12 .

# Copy these files once to beach
# scp pCTD.GOC12/*.hdr stoqsadm@beach.mbari.org:/ODSS/data/goc/GOC_february2012/wf/pctd
# scp pCTD.GOC12/*.btl stoqsadm@beach.mbari.org:/ODSS/data/goc/GOC_february2012/wf/pctd
# rm *bad* *BAD* files that got copied to beach

../../CANON/toNetCDF/pctdToNetcdf.py pCTD.GOC12 pCTD.GOC12 GOC

scp pCTD.GOC12/*.nc stoqsadm@beach.mbari.org:/ODSS/data/goc/GOC_february2012/wf/pctd

# Clean up
rm -r pCTD.GOC12

# Then run loader for GOC_february2012
