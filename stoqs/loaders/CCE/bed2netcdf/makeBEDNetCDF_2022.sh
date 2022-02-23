#!/bin/bash

# For use on MBARI's internal network with appropriate credentials
# Execute in stoqs Docker container thusly (for example):
#   ➜  docker git:(master) ✗ docker-compose exec stoqs /bin/bash
#   root@13f8e356b1d7:/srv# cd /srv/stoqs/loaders/CCE/bed2netcdf
#   root@13f8e356b1d7:/srv/stoqs/loaders/CCE/bed2netcdf# ./makeBEDNetCDF_2022.sh

# Background:
# From: Denis Klimov <klimov@mbari.org>
# Subject: BEDS - Qualification - Status Update 1/10/2022
# Date: January 10, 2022 at 8:29:41 PM PST
# To: Roberto Gwiazda <rgwiazda@mbari.org>, Mike McCann <mccann@mbari.org>
# Cc: Charles Paull <paull@mbari.org>, Brian Kieft <bkieft@mbari.org>, Eve Lundsten <eve@mbari.org>,
#     Andrew Hamilton <hamilton@mbari.org>, Larry Bird <bila@mbari.org>
# Reply-To: Denis Klimov <klimov@mbari.org>
# 
# Hello Mike and Roberto, 
# 
# I have 3 sets of BEDS data files along with photos, new manual with updated datas
#  format description, and experiments description (also attached) located here: 
# X:\901006.BEDS\BEDS-Qualification-2021
# 
# Could you try to decode the motion from those data sets, and also check for
# integrity and completeness of captured data while doing it? Also keep in mind
# that the data format was supposedly updated to include heading but I have no
# way to check for this since .EVT and .WAT files have to be decoded first. 
# 
# thanks, 
# 
# Denis Klimov
# Electrical Engineer & Laser Safety Officer
# Monterey Bay Aquarium Research Institute (MBARI)

# Copy decoded files from ProjectLibrary to local working directory - may comment out following execution
mkdir work_dir
scp -r "mccann@elvis.shore.mbari.org:/mbari/ProjectLibrary/901006.BEDS/BEDS-Qualification-2021/2021-12-30-Test-\(3+30\)x4-124min/" work_dir
scp -r "mccann@elvis.shore.mbari.org:/mbari/ProjectLibrary/901006.BEDS/BEDS-Qualification-2021/2022-01-03-Test-\(3+30\)x4-244min\ +\ Acoustic/" work_dir
scp -r "mccann@elvis.shore.mbari.org:/mbari/ProjectLibrary/901006.BEDS/BEDS-Qualification-2021/2022-01-04-Test-\(3+30\)x4-484min/" work_dir

# Gymnastics to deal with spaces in directory names: https://stackoverflow.com/a/22432604/1281657
declare -a dirs=(   "work_dir/2021-12-30-Test-(3+30)x4-124min/BEDS-Files-Downloaded" \
                    "work_dir/2022-01-03-Test-(3+30)x4-244min + Acoustic/BEDS-Files-Downloaded" \
                    "work_dir/2022-01-04-Test-(3+30)x4-484min/BEDS-Files-Downloaded" )

dirslength=${#dirs[@]}
for (( i=0; i<${dirslength}; i++ ));
do
    dir=${dirs[$i]}
    echo "Processing files in $dir"
    echo "=========================================================================="
    pushd "$dir"
    title=$(echo "$dir" | cut -d'/' -f2)
    for f in *.EVT
    do
        ../../../decodeBEDS.py -o $f.OUT $f
        echo ../../../bed2netcdf.py --read_csv --no_tide_removal --input $f.OUT --lat 36.793458 --lon -121.845703 --depth -10 --title "\"$title\""
        ../../../bed2netcdf.py --read_csv --no_tide_removal --input $f.OUT --lat 36.793458 --lon -121.845703 --depth -10 --title "\"$title\""
    done
    popd
done

# Copy to OPeNDAP server simplifying destination directory names for web friendly delivery
##ssh mccann@elvis.shore.mbari.org mkdir /var/www/dods_html/data/beds/BenchTests/2021-12-30-Test-124min
scp -r work_dir/2021-12-30-Test-\(3+30\)x4-124min/BEDS-Files-Downloaded/*.nc mccann@elvis.shore.mbari.org:/var/www/dods_html/data/beds/BenchTests/2021-12-30-Test-124min

##ssh mccann@elvis.shore.mbari.org mkdir /var/www/dods_html/data/beds/BenchTests/2022-01-03-Test-244min-Acoustic
scp -r work_dir/2022-01-03-Test-\(3+30\)x4-244min\ +\ Acoustic/BEDS-Files-Downloaded/*.nc mccann@elvis.shore.mbari.org:/var/www/dods_html/data/beds/BenchTests/2022-01-03-Test-244min-Acoustic

##ssh mccann@elvis.shore.mbari.org mkdir /var/www/dods_html/data/beds/BenchTests/2022-01-04-Test-484min
scp -r work_dir/2022-01-04-Test-\(3+30\)x4-484min/BEDS-Files-Downloaded/*.nc mccann@elvis.shore.mbari.org:/var/www/dods_html/data/beds/BenchTests/2022-01-04-Test-484min

cd ../../..

# Clean up - to indicate that work_dir is temporary
##rm -r work_dir

