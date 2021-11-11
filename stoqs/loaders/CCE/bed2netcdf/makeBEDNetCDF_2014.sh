#!/bin/bash

# For use on MBARI's internal network with appropriate credentials

# Copy decoded files from ProjectLibrary to local working directory
mkdir decoded
rsync -v "mccann@elvis64.shore.mbari.org:/mbari/ProjectLibrary/901006.BEDS/BEDS.Data/CanyonEvents/20140218/BED3/decoded/*.OUT" decoded
rsync -v "mccann@elvis64.shore.mbari.org:/mbari/ProjectLibrary/901006.BEDS/BEDS.Data/CanyonEvents/20140330/BED3/decoded/*.OUT" decoded


cd decoded
for f in 30100046.EVT.OUT 30100049.EVT.OUT
do
    f_out=`sed -e 's/\(\.EVT\.OUT\)/_trajectory.nc/' <<< $f`
    ../bed2netcdf.py --input $f --output $f_out -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
        --bed_name BED03 \
        --seconds_offset 25200 \
        --title "BED03 Event Trajectory on 18 February 2014"

done
# This event started at depth 565.6 and ended at 565.6, so process as a stationary event
../bed2netcdf.py --input 30100048.EVT.OUT --output 30100048.nc --lon -121.814686 --lat 36.799725 --depth 565.6 \
    --bed_name BED03 \
    --seconds_offset 25200 \
    --title "BED03 Event on 18 February 2014"
    

# There are stationary events in 30100520, 30100522, and 30100525, but 30100518 is a big one
for f in 30100518.EVT.OUT
do
    f_out=`sed -e 's/\(\.EVT\.OUT\)/_trajectory.nc/' <<< $f`
    ../bed2netcdf.py --input $f --output $f_out -t ../MontereyCanyonBeds_1m+5m_profile.ssv \
        --bed_name BED03 \
        --seconds_offset 25200 \
        --title "BED03 Event Trajectory on 30 March 2014"
done


# Copy to OPeNDAP server
scp 3010004[6-9]*.nc mccann@elvis64.shore.mbari.org:/var/www/dods_html/data/beds/CanyonEvents/20140218/BED3/netcdf
scp 30100518_trajectory.nc mccann@elvis64.shore.mbari.org:/var/www/dods_html/data/beds/CanyonEvents/20140330/BED3/netcdf

# Clean up 
##cd ..
##rm -r decoded

