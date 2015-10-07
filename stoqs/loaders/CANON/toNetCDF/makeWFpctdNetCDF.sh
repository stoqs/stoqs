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
# Duane Edgington modified for Fall Canon 2014. September 29, 2014

LOGIN=odssadm
RH=odss.mbari.org


DIR=/data/canon/2015_Sep/Platforms/Ships/Western_Flyer/pctd
LOCALDIR=`echo $DIR | cut -d/ -f8`  # -f must match last directory
rsync -rv $LOGIN@$RH:$DIR  .
./pctdToNetcdf.py -i $LOCALDIR -t "Profile CTD data from R/V Western Flyer during CANON - September 2015" -a V0:rhodamine:V
scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
rm -r $LOCALDIR

