#!/bin/bash
#
# Load all ROV dive data within a bounding box enclosing
# Monterey Bay.

./ROVCTDloader.py --database stoqs_rovctd_mb \
--rov vnta --start 43 --end 4000 \
--campaignName 'Monterey Bay ROVCTD data' \
--campaignDescription 'All dives in Monterey Bay' \
--bbox -122.5 36 -121.75 37.0

./ROVCTDloader.py --database stoqs_rovctd_mb \
--rov tibr --start 42 --end 1163 \
--campaignName 'Monterey Bay ROVCTD data' \
--campaignDescription 'All dives in Monterey Bay' \
--bbox -122.5 36 -121.75 37.0

./ROVCTDloader.py --database stoqs_rovctd_mb \
--rov docr --start 1 --end 1000 \
--campaignName 'Monterey Bay ROVCTD data' \
--campaignDescription 'All dives in Monterey Bay' \
--bbox -122.5 36 -121.75 37.0
