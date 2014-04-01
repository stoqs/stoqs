#!/bin/bash

LOGIN=stoqsadm
##RH=zuma.rc.mbari.org
RH=odss.mbari.org

# John Martin CANON - ECOHAB September 2013
DIR=/data/canon/2013_Sep/Platforms/Ships/Martin/uctd
LOCALDIR=`echo $DIR | cut -d/ -f8`  # -f must match last directory
rsync -rv $LOGIN@$RH:$DIR  .
./uctdToNetcdf.py -i $LOCALDIR -f Martin_UDAS -p "jhmudas_[0-9][0-9][0-9][0-9][0-9][0-9][0-9].txt" -d 2.0 -t "Underway CTD data from R/V John Martin during CANON - ECOHAB September 2013" 
scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR

# Clean up 
rm -r $LOCALDIR
