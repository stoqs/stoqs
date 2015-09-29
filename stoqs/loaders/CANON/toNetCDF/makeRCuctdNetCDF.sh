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
# updated Duane Edgington 29 September 2015 for Fall 2015 CANON Cruises 
 
LOGIN=odssadm
##RH=zuma.rc.mbari.org
RH=odss.mbari.org

DIR=/data/canon/2015_Sep/Platforms/Ships/Rachel_Carson/uctd
LOCALDIR=`echo $DIR | cut -d/ -f8`  # -f must match last directory
rsync -rv $LOGIN@$RH:$DIR  .
./uctdToNetcdf.py --inDir $LOCALDIR --pattern "*.asc" --depth 1.5 --title "Underway CTD data from R/V Rachel Carson CANON Sep 2015"
scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
rm -r $LOCALDIR

