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
# Duane Edgington modified for Fall Canon 2018. February 2019

LOGIN=odssadm
RH=odss.mbari.org

#smb://atlas/ODSS/data/other/routine/Platforms/Ships/WesternFlyer/pctd
#DIR=/data/canon/2015_Sep/Platforms/Ships/Western_Flyer/pctd
DIR=/data/other/routine/Platforms/Ships/WesternFlyer/pctd/CN19SC
LOCALDIR=`echo $DIR | cut -d/ -f8`  # -f must match last directory
rsync -rv $LOGIN@$RH:$DIR  .
#./pctdToNetcdf.py -i $LOCALDIR -t "Profile CTD data from R/V Western Flyer during CANON - Spring 2019" 
docker-compose exec stoqs stoqs/loaders/CANON/toNetCDF/pctdToNetcdf.py -i $LOCALDIR -t "Profile CTD data from R/V Western Flyer during CANON - Spring 2019" -a V0:rhodamine:V
scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
rm -r $LOCALDIR

