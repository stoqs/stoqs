#!/bin/bash
#
# Load Midwater Lab transect dives as provided by Rob Sherlock:
# From: robs <robs@mbari.org>
# Subject: STOQS?
# Date: July 25, 2023 at 5:27:43 PM PDT
# To: Mike McCann <mccann@mbari.org>
# 
# Hi Mike,
# 
# Can you please update the Ventana and Doc Ricketts Midwater dives on STOQS from 2014 to 12/2017
# (plus a single ROV dive from 2019)? I’ll attach a spreadsheet with the dive numbers and dates.
# If you need anything else, let me know but I may not be able to get it to you until after
# I return from vacation the second week of August.
# 
# I will also include a list of Astrid Leitner’s Topography transects (“Topo” dives).
# If it’s possible to create a campaign list for those as well, that’d be super. A lower priority,
# but both will be helpful later in August for sure.
# 
# Thanks Mike!
# Rob
# 
# Sorted spreadsheet by rov, dive and saved as .csv, then:
#   cat TopoTransects.csv | cut -d, -f3,4 | uniq > topomwdives.txt
# To get the list of dives for ROVCTDloader.py --dives, execute:
#   ./format_dives.py ~/Downloads/topomwdives.txt
#
# Create the database with:
#   docker-compose run --rm stoqs stoqs/loaders/load.py --db stoqs_rovctd_mwtopo --create_only --clobber --noinput
#
# Execute this script in the Docker container:
#   docker-compose run --rm stoqs /bin/bash
#   cd /srv/stoqs/loaders/ROVCTD
#   ./loadTopoDives_mw.sh

./ROVCTDloader.py --database stoqs_rovctd_mwtopo --dives \
D1152 D1218 D1220 D1222 D1224 D1225 D1266 D1268 D1271 D1272 \
D1309 D1310 D1312 D1313 D1343 D1345 D1347 D1349 D1350 D1352 \
D1353 V4253 \
--campaignName 'Midwater Topo dives 2019 - 2021' \
--campaignDescription 'Midwater Topo dives - Astrid Leitner’s Topography transects' \
# -v

