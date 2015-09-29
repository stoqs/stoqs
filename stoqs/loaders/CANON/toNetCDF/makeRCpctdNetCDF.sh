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
# modified 23 September 2014 Duane Edgington for Fall CANON campaign 

LOGIN=odssadm
##RH=zuma.rc.mbari.org  
# make RH point to the system containing the working location of the profile CTD files
# for the fall 2014 campaign this is normandy.shore.mbari.org
RH=odss.mbari.org

DIR=/data/canon/2015_Sep/Platforms/Ships/Rachel_Carson/pctd
LOCALDIR=`echo $DIR | cut -d/ -f8`  # -f must match last directory
rsync -rv $LOGIN@$RH:$DIR  .
./pctdToNetcdf.py -i $LOCALDIR -t "Profile CTD data from R/V Rachel Carson during CANON  September 2015" -a V0:rhodamine:V
scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
rm -r $LOCALDIR

