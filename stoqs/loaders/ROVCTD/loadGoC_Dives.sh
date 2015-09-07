#!/bin/bash
#
# Load all ROV dive data within a bounding box enclosing the
# Gulf of California dive areas.

./ROVCTDloader.py --database stoqs_rovctd_goc \
--rov vnta --start 43 --end 4000 \
--campaignName 'Gulf of California ROVCTD data' \
--campaignDescription 'All dives in Gulf of California' \
--bbox -120 18 -100 33

./ROVCTDloader.py --database stoqs_rovctd_goc \
--rov tibr --start 42 --end 1163 \
--campaignName 'Gulf of California ROVCTD data' \
--campaignDescription 'All dives in Gulf of California' \
--bbox -120 18 -100 33

./ROVCTDloader.py --database stoqs_rovctd_goc \
--rov docr --start 1 --end 1000 \
--campaignName 'Gulf of California ROVCTD data' \
--campaignDescription 'All dives in Gulf of California' \
--bbox -120 18 -100 33
