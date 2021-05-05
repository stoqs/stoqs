#!/bin/bash
#
# Shell script to make a local copy of original underway CTD data files for uctdToNetcdf.py to
# make .nc files and then copy them back to the catalog.  The user will be prompted for the 
# password to $LOGIN@$RH.  Loads for previous campaigns may be commented so as to keep a record
# of conversions.
#
# For running on a Docker-based installation give the script a docker argument from the docker
# direcory, e.g.:
#   cd $STOQS_HOME/docker
#   ../stoqs/loaders/CANON/toNetCDF/makeWFuctdNetCDF.sh docker
#
# --
# Mike McCann
# 22 February 2019

# Connection to MBARI host that holds CTD data and serves .nc files via OPeNDAP
LOGIN=odssadm
RH=odss.mbari.org

# Directories and titles for Western Flyer Profile CTD data - Keep previously processed data commented out
#DIR=/data/canon/2015_Sep/Platforms/Ships/Western_Flyer/uctd
#TITLE="Underway CTD data from R/V Western Flyer during CANON - September 2015"
DIR=/data/other/routine/Platforms/Ships/WesternFlyer/uctd
##PATTERN="cn18s*"
##TITLE="Underway CTD data from R/V Western Flyer during CANON - May 2018"
##PATTERN="cn18f*"
##TITLE="Underway CTD data from R/V Western Flyer during CANON - September 2018"
##PATTERN="CN19SM*"
##TITLE="Underway CTD data from R/V Western Flyer during CANON - May 2019"
PATTERN="CN21Sm*"
TITLE="Underway CTD data from R/V Western Flyer during CANON - April 2021"
# Set local processing directory
LOCALDIR=`basename $DIR`

# Copy the data from DIR and create the .nc files - You will be prompted for credentials
rsync -rv $LOGIN@$RH:$DIR/$PATTERN $LOCALDIR
if [ "$1" == "docker" ]
then
    docker-compose exec stoqs stoqs/loaders/CANON/toNetCDF/uctdToNetcdf.py -i /srv/docker/$LOCALDIR -p "$PATTERN" -t "$TITLE" -d 2.0 --min_psal 30
else
    ./uctdToNetcdf.py --inDir $LOCALDIR --pattern "$PATTERN" --title "$TITLE" --depth 2.0
fi

# Copy the .nc files back to the MBARI DAP host - You will be prompted for credentials 
scp $LOCALDIR/*.nc $LOGIN@$RH:$DIR
if [ "$1" == "docker" ]
then
    rm -r $LOCALDIR
else
    echo "Not removing $LOCALDIR"
fi

