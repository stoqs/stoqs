#!/bin/bash

# $Id: $

# For use on MBARI's internal network with appropriate credentials

# For testing removal of tides from fullDownload Watch files

# Copy data from the archive to a local working directory
mkdir watched
rsync -rv "mccann@elvis.shore.mbari.org:/mbari/ProjectLibrary/901006.BEDS/BEDS.Data/Deployment_Data_Full/BED9/20160407_20170110/decoded/9010000[4-9].WAT.OUT" watched
cd watched

# Process all .WAT files to NetCDF - stride every 600 for 1-minute samples of IMU data
for f in 9010000[4-9].WAT.OUT
do
    ../bed2netcdf.py --input $f --bed_name BED09 \
        --lon -121.823313 --lat 36.796156 --depth 202 \
        --title 'BED09 Watch Data' \
        --stride_imu 600
done


# Copy the netcdf files to CCE_Processed
scp 9010000[4-9].nc mccann@elvis.shore.mbari.org:/mbari/CCE_Processed/BEDs/BED09/MBCCE_BED09_20160408_Watch/netcdf

