#!/bin/bash

# For use on Shore following Rachel Carson SIMZ October 2013
# Set Remote Host (RH) to what's appropriate
##RH=192.168.111.177
##RH=zuma.rc.mbari.org
RH=odss.mbari.org

# From: Erich Rienecker <erich@mbari.org>
# Subject: Re: October 2013 SIMZ CTD data
# Date: October 31, 2013 9:45:13 AM PDT
# To: Mike McCann <mccann@mbari.org>
# 
# Found at:
# 
# /Tornado/DMO/MDUC_CORE_CTD_200103/Data/2013_224to301_RC_SIMZ

# Original files copied to odss.mbari.org from /mbari/DMO/MDUC_CORE_CTD_200103/DATA/2013_224to301_RC_SIMZ/

rsync -rv stoqsadm@$RH:/data/canon/2013_Oct/Platforms/Ships/Rachel_Carson/uctd .

../../CANON/toNetCDF/uctdToNetcdf.py uctd uctd s 1.5

scp uctd/*.nc stoqsadm@$RH:/data/canon/2013_Oct/Platforms/Ships/Rachel_Carson/uctd

# Clean up 
rm -r uctd
