#!/bin/bash

LOGIN=stoqsadm
##RH=zuma.rc.mbari.org
RH=odss.mbari.org

# John Martin CANON - ECOHAB September 2013
DIR=/data/canon/2013_Sep/Platforms/Ships/Martin/pctd
LOCALDIR=`echo $DIR | cut -d/ -f8`  # -f must match last directory
rsync -rv $LOGIN@$RH:$DIR  .
./pctdToNetcdf.py -i $LOCALDIR -t "Profile CTD data from R/V John Martin during CANON - ECOHAB September 2013" 
scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR

# Clean up 
rm -r $LOCALDIR
