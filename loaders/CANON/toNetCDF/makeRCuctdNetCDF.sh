#!/bin/bash

LOGIN=stoqsadm
##RH=zuma.rc.mbari.org
RH=odss.mbari.org


# Rachel Carson CANON - ECOHAB March 2013
##DIR=/data/canon/2013_Mar/carson/uctd
##LOCALDIR=`echo $DIR | cut -d/ -f6`  # -f must match last directory
##rsync -rv $LOGIN@$RH:$DIR .
##./uctdToNetcdf.py --inDir $LOCALDIR --pattern "*.asc" --depth 1.5
##scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR

# Rachel Carson CANON - ECOHAB September 2013
DIR=/data/canon/2013_Sep/Platforms/Ships/Rachel_Carson/uctd
LOCALDIR=`echo $DIR | cut -d/ -f8`  # -f must match last directory
rsync -rv $LOGIN@$RH:$DIR  .
./uctdToNetcdf.py --inDir $LOCALDIR --pattern "*.asc" --depth 1.5 --title "Underway CTD data from R/V Rachel Carson CANON - ECOHAB September 2013"
scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR

# Clean up 
rm -r $LOCALDIR
