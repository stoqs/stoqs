#!/bin/bash

# For use on MBARI's internal network with appropriate credentials

# Copy decoded files from ProjectLibrary to local working directory
mkdir decoded
##rsync -rv mccann@elvis.shore.mbari.org:/mbari/ProjectLibrary/901006.BEDS/BEDS.Data/2013_07_18_Carson/raw/*.EVT raw

# Events  1 -  50: --lat 36.793458 --lon -121.845703 --depth 340
# Events 51 - 248: --lat 36.785428 --lon -121.903602 --depth 530
rsync -rv mccann@elvis64.shore.mbari.org:/mbari/ProjectLibrary/901006.BEDS/BEDS.Data/Deployment_Data_Full/BED1/20130415_20130718/decoded/BED00[0-2][0-9][0-9].EVT.OUT decoded

# Big event on 1 June 2013
rsync -rv "mccann@elvis64.shore.mbari.org:/mbari/ProjectLibrary/901006.BEDS/BEDS.Data/CanyonEvents/20130601/BED1/decoded/BED1/BED0003[8-9].EVT.OUT" decoded

cd decoded
for f in BED000[0-4][0-9].EVT.OUT BED00050.EVT.OUT
do
    ../bed2netcdf.py --input $f --lat 36.793458 --lon -121.845703 --depth 340
done

for f in BED0005[1-9].EVT.OUT BED000[6-9][0-9].EVT.OUT BED00[1-2][0-9][0-9].EVT.OUT
do
    ../bed2netcdf.py --input $f --lat 36.785428 --lon -121.903602 --depth 530
done

# Process big event on 1 June 2013
# --bar_offset value chosen to make most of the trajectory in STOQS 3D appear above the terrain
../bed2netcdf.py -i BED00038.EVT.OUT BED00039.EVT.OUT -o BED01_1_June_2013.nc -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
    --beg_depth 279.1 --end_depth 517.1 \
    --bar_offset -2.4 \
    --title 'BED01 Event Trajectory on 1 June 2013 during first field test of the BED'

# Put netcdf files in ProjectLibrary
##scp raw/*.nc mccann@elvis.shore.mbari.org:/mbari/ProjectLibrary/901006.BEDS/BEDS.Data/2013_07_18_Carson/netcdf

# Copy to OPeNDAP server
scp BED01_1_June_2013.nc mccann@elvis64.shore.mbari.org:/var/www/dods_html/data/beds/CanyonEvents/20130601/BED1/netcdf

# Clean up 
##cd ..
##rm -r decoded

