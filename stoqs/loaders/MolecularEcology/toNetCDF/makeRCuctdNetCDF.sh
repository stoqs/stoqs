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

LOGIN=mccann
RH=odss.mbari.org

##LOGIN=odssadm
##RH=zuma.rc.mbari.org


##DIR=/data/canon/2013_Mar/carson/uctd
##LOCALDIR=`echo $DIR | cut -d/ -f6`  # -f must match last directory
##rsync -rv $LOGIN@$RH:$DIR  .
##./uctdToNetcdf.py --inDir $LOCALDIR --pattern "*.asc" --depth 1.5 --title "Underway CTD data from R/V Rachel Carson CANON - ECOHAB March 2013"
##scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
##rm -r $LOCALDIR

##DIR=/data/canon/2013_Sep/Platforms/Ships/Rachel_Carson/uctd
##LOCALDIR=`echo $DIR | cut -d/ -f8`  # -f must match last directory
##rsync -rv $LOGIN@$RH:$DIR  .
##./uctdToNetcdf.py --inDir $LOCALDIR --pattern "*.asc" --depth 1.5 --title "Underway CTD data from R/V Rachel Carson CANON - ECOHAB September 2013"
##scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
##rm -r $LOCALDIR

##DIR=/data/simz/2014_spring/Platforms/Ships/Rachel_Carson/uctd
##LOCALDIR=`echo $DIR | cut -d/ -f8`  # -f must match last directory
##rsync -rv $LOGIN@$RH:$DIR  .
##./uctdToNetcdf.py --inDir $LOCALDIR --pattern "*.asc" --depth 1.5 --title "Underway CTD data from R/V Rachel Carson CANON - SIMZ Spring 2014"
##scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
##rm -r $LOCALDIR

# mkdir /mbari/ODSS/data/simz/2014_Jul/Platforms/Ships/Rachel_Carson/uctd/
# cp /mbari/DMO/MDUC_CORE_CTD_200103/DATA/2014_210_212_SIMZ_RC/2014simzplm0[5-7].* /mbari/ODSS/data/simz/2014_Jul/Platforms/Ships/Rachel_Carson/uctd/

DIR=/data/simz/2014_Jul/Platforms/Ships/Rachel_Carson/uctd
LOCALDIR=`echo $DIR | cut -d/ -f8`  # -f must match last directory
rsync -rv $LOGIN@$RH:$DIR  .
../../CANON/toNetCDF/uctdToNetcdf.py --inDir $LOCALDIR --pattern "*.asc" --depth 1.5 --title "Underway CTD data from R/V Rachel Carson CANON - SIMZ July 2014"
scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
##rm -r $LOCALDIR

##DIR=/data/simz/2014_Oct/carson/uctd
##LOCALDIR=`echo $DIR | cut -d/ -f6`  # -f must match last directory
##rsync -rv $LOGIN@$RH:$DIR  .
##../../CANON/toNetCDF/uctdToNetcdf.py --inDir $LOCALDIR --pattern "*.asc" --depth 1.5 --title "Underway CTD data from R/V Rachel Carson CANON - SIMZ October 2014"
##scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
##rm -r $LOCALDIR

