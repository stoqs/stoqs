#!/bin/bash
#
# Shell script to make a local copy of original profile CTD data files for pctdToNetcdf.py to
# make .nc files and then copy them back to the catalog.  The user will be prompted for the 
# password to $LOGIN@$RH.  Loads for previous campaigns may be commented so as to keep a record
# of conversions.
#
# --
# Mike McCann
# 15 January 2014

LOGIN=stoqsadm
RH=odss.mbari.org


DIR=/data/canon/2013_Sep/Platforms/Ships/Western_Flyer/pctd
LOCALDIR=`echo $DIR | cut -d/ -f8`  # -f must match last directory
rsync -rv $LOGIN@$RH:$DIR  .
./pctdToNetcdf.py -i $LOCALDIR -t "Profile CTD data from R/V Western Flyer during CANON - ECOHAB September 2013" 
scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
rm -r $LOCALDIR


DIR=/data/canon/2013_Oct/Platforms/Ships/Western_Flyer/pctd
LOCALDIR=`echo $DIR | cut -d/ -f8`  # -f must match last directory
rsync -rv $LOGIN@$RH:$DIR  .
./pctdToNetcdf.py -i $LOCALDIR -t "Profile CTD data from R/V Western Flyer during CN13ID - October 2013" -l "Any use requires prior approval from the MBARI CN13ID PI: Dr. Alexandra Worden."
scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
rm -r $LOCALDIR

