#!/bin/bash

LOGIN=odssadm
RH=zuma.rc.mbari.org
##RH=odss.mbari.org

DIR=/data/simz/2013_Aug/carson/pctd
LOCALDIR=`echo $DIR | cut -d/ -f6`  # -f must match last directory
rsync -rv $LOGIN@$RH:$DIR  .
../../CANON/toNetCDF/pctdToNetcdf.py -i $LOCALDIR -t "Profile CTD data from R/V Rachel Carson during SIMZ - August 2013" 
scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR

# Clean up 
rm -r $LOCALDIR
