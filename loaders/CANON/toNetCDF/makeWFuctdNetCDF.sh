#!/bin/bash
#
# Shell script to make a local copy of original underway CTD data files for uctdToNetcdf.py to
# make .nc files and then copy them back to the catalog.  The user will be prompted for the 
# password to $LOGIN@$RH.  Loads for previous campaigns may be commented so as to keep a record
# of conversions.
#
# --
# Mike McCann
# 15 January 2014

LOGIN=odssadm
RH=odss.mbari.org


DIR=/data/canon/2014_Sep/Platforms/Ships/Western_Flyer/uctd
LOCALDIR=`echo $DIR | cut -d/ -f8`  # -f must match last directory
rsync -rv $LOGIN@$RH:$DIR  .
cd $LOCALDIR
rm canon13*.* #only keep canon14 stuff
cd ..
./uctdToNetcdf.py --inDir $LOCALDIR --pattern "*.asc" --depth 2.0 --title "Underway CTD data from R/V Western Flyer during CANON - ECOHAB September 2014"
scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
rm -r $LOCALDIR

