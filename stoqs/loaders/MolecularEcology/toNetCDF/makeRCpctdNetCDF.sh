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

LOGIN=mccann
RH=odss.mbari.org

##LOGIN=odssadm
##RH=zuma.rc.mbari.org


##DIR=/data/canon/2013_Sep/Platforms/Ships/Rachel_Carson/pctd
##LOCALDIR=`echo $DIR | cut -d/ -f8`  # -f must match last directory
##rsync -rv $LOGIN@$RH:$DIR  .
##./pctdToNetcdf.py -i $LOCALDIR -t "Profile CTD data from R/V Rachel Carson during CANON - ECOHAB September 2013" 
##scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
##rm -r $LOCALDIR

# -------------------------------------------------------------------------------------------------------------------------------------------------------
# From: Erich Rienecker <erich@mbari.org>
# Subject: Re: October 2013 SIMZ CTD data
# Date: October 31, 2013 9:45:13 AM PDT
# To: Mike McCann <mccann@mbari.org>
# 
# Found at:
# 
# /Tornado/DMO/MDUC_CORE_CTD_200103/Data/2013_224to301_RC_SIMZ

# Original files copied to odss.mbari.org from /mbari/DMO/MDUC_CORE_CTD_200103/DATA/2013_224to301_RC_SIMZ/:
# scp /mbari/DMO/MDUC_CORE_CTD_200103/DATA/2013_224to301_RC_SIMZ/PCTD/*.asc stoqsadm@odss.mbari.org:/data/canon/2013_Oct/Platforms/Ships/Rachel_Carson/pctd/
# scp /mbari/DMO/MDUC_CORE_CTD_200103/DATA/2013_224to301_RC_SIMZ/PCTD/*.hdr stoqsadm@odss.mbari.org:/data/canon/2013_Oct/Platforms/Ships/Rachel_Carson/pctd/
# scp /mbari/DMO/MDUC_CORE_CTD_200103/DATA/2013_224to301_RC_SIMZ/PCTD/*.btl stoqsadm@odss.mbari.org:/data/canon/2013_Oct/Platforms/Ships/Rachel_Carson/pctd/

##DIR=/data/canon/2013_Oct/Platforms/Ships/Rachel_Carson/pctd
##LOCALDIR=`echo $DIR | cut -d/ -f8`  # -f must match last directory
##rsync -rv $LOGIN@$RH:$DIR  .

# Correct c23 latitude and longitude based on Julio's email of 23 April 2014 - make it the same as c19
##sed -i "s/* NMEA Latitude = 36 54.63 N/* NMEA Latitude = 36 57.02 N/" pctd/simz2013c23.hdr
##sed -i "s/* NMEA Longitude = 121 52.77 W/* NMEA Longitude = 121 55.62 W/" pctd/simz2013c23.hdr
##echo "Copying modified .hdr file back to the server..."
##scp pctd/simz2013c23.hdr $LOGIN@$RH:$DIR

##../../CANON/toNetCDF/pctdToNetcdf.py -i $LOCALDIR -t "Profile CTD data from R/V Rachel Carson during SIMZ October 2013" 

##scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
##rm -r $LOCALDIR

# -------------------------------------------------------------------------------------------------------------------------------------------------------
##DIR=/data/simz/2014_spring/Platforms/Ships/Rachel_Carson/pctd
##LOCALDIR=`echo $DIR | cut -d/ -f8`  # -f must match last directory
##rsync -rv $LOGIN@$RH:$DIR  .
##../../CANON/toNetCDF/pctdToNetcdf.py -i $LOCALDIR -t "Profile CTD data from R/V Rachel Carson during CANON - SIMZ Spring 2014" 
##scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
##rm -r $LOCALDIR

# Original files copied to odss.mbari.org from /mbari/DMO/MDUC_CORE_CTD_200103/DATA/2014_210_212_SIMZ_RC/
# cp /mbari/DMO/MDUC_CORE_CTD_200103/DATA/2014_210_212_SIMZ_RC/simz2014c2[5-9]* /mbari/ODSS/data/simz/2014_Jul/Platforms/Ships/Rachel_Carson/pctd/
# cp /mbari/DMO/MDUC_CORE_CTD_200103/DATA/2014_210_212_SIMZ_RC/simz2014c3[0-9]* /mbari/ODSS/data/simz/2014_Jul/Platforms/Ships/Rachel_Carson/pctd/

DIR=/data/simz/2014_Jul/Platforms/Ships/Rachel_Carson/pctd
LOCALDIR=`echo $DIR | cut -d/ -f8`  # -f must match last directory
##rsync -rv $LOGIN@$RH:$DIR .
../../CANON/toNetCDF/pctdToNetcdf.py -i $LOCALDIR -t "Profile CTD data from R/V Rachel Carson during SIMZ July 2014" 
scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
##rm -r $LOCALDIR

# -------------------------------------------------------------------------------------------------------------------------------------------------------
##DIR=/data/simz/2014_Oct/carson/pctd
##LOCALDIR=`echo $DIR | cut -d/ -f6`  # -f must match last directory
##rsync -rv $LOGIN@$RH:$DIR  .
##../../CANON/toNetCDF/pctdToNetcdf.py -i $LOCALDIR -t "Profile CTD data from R/V Rachel Carson during SIMZ October 2014" 
##scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
##rm -r $LOCALDIR

