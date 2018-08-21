#!/bin/bash
#
# Load all ROV dive data within a bounding box enclosing
# Monterey Bay. This script is designed to add to the dives
# loaded by the loadMB_Dives.sh script, whose dive numbers
# go through the end of 2017.

# These commands may be executed interactively in the container, e.g.:
#   docker-compose exec stoqs /bin/bash
#   cd stoqs/loaders/ROVCTD
# Then copy and paste from below:

# V4135 on 26 July 2018
./ROVCTDloader.py --database stoqs_rovctd_mb \
--rov vnta --start 4001 --end 4135 \
--campaignName 'Monterey Bay ROVCTD data' \
--campaignDescription 'All dives in Monterey Bay' \
--bbox -122.5 36 -121.75 37.0

# D1055 on 15 August 2018
./ROVCTDloader.py --database stoqs_rovctd_mb \
--rov docr --start 1001 --end 1055 \
--campaignName 'Monterey Bay ROVCTD data' \
--campaignDescription 'All dives in Monterey Bay' \
--bbox -122.5 36 -121.75 37.0
