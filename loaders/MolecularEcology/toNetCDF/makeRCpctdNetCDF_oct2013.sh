#!/bin/bash

# For use on Shore following Rachel Carson SIMZ October 2013
RH=odss.mbari.org

# From: Erich Rienecker <erich@mbari.org>
# Subject: Re: October 2013 SIMZ CTD data
# Date: October 31, 2013 9:45:13 AM PDT
# To: Mike McCann <mccann@mbari.org>
# 
# Found at:
# 
# /Tornado/DMO/MDUC_CORE_CTD_200103/Data/2013_224to301_RC_SIMZ

# Original files copied to odss.mbari.org from /mbari/DMO/MDUC_CORE_CTD_200103/DATA/2013_224to301_RC_SIMZ/:
# scp /mbari/DMO/MDUC_CORE_CTD_200103/DATA/2013_224to301_RC_SIMZ/PCTD/*.asc stoqsadm@odss.mbari.org:/data/canon/2013_Oct/Platforms/Ships/Rachel_Carson/pctd/
# scp /mbari/DMO/MDUC_CORE_CTD_200103/DATA/2013_224to301_RC_SIMZ/PCTD/*.hdr stoqsadm@odss.mbari.org:/data/canon/2013_Oct/Platforms/Ships/Rachel_Carson/pctd/
# scp /mbari/DMO/MDUC_CORE_CTD_200103/DATA/2013_224to301_RC_SIMZ/PCTD/*.btl stoqsadm@odss.mbari.org:/data/canon/2013_Oct/Platforms/Ships/Rachel_Carson/pctd/

rsync -rv stoqsadm@$RH:/data/canon/2013_Oct/Platforms/Ships/Rachel_Carson/pctd .

../../CANON/toNetCDF/pctdToNetcdf.py pctd pctd s

scp pctd/*.nc stoqsadm@$RH:/data/canon/2013_Oct/Platforms/Ships/Rachel_Carson/pctd

# Clean up
rm -r pctd

