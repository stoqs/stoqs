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
#   cat MWTransects_Vntna_DR.csv | cut -d, -f3,4 | uniq > mw93dives.txt
# To get the list of dives for ROVCTDloader.py --dives, execute:
#   ./format_dives.py ~/Downloads/mw93dives.txt
#
# Create the database with:
#   docker-compose run --rm stoqs stoqs/loaders/load.py --db stoqs_rovctd_mw93 --create_only --clobber --noinput
#
# Execute this script in the Docker container:
#   docker-compose run --rm stoqs /bin/bash
#   cd /srv/stoqs/loaders/ROVCTD
#   ./loadTransectDives_mw93.sh

./ROVCTDloader.py --database stoqs_rovctd_mw93 --dives \
D147 D181 D200 D238 D311 D416 D433 D449 D478 D544 \
D595 D646 D691 D787 D832 D870 D907 D924 D996 T103 \
T257 T411 T511 T624 T648 T649 T650 T683 T686 T687 \
T688 T762 T763 T764 T835 T836 T837 T894 T895 T896 \
T995 T1111 V526 V535 V537 V541 V581 V582 V585 V586 \
V591 V595 V600 V619 V636 V637 V642 V656 V659 V670 \
V682 V685 V690 V695 V702 V709 V710 V717 V745 V753 \
V754 V757 V762 V766 V767 V778 V783 V789 V798 V805 \
V818 V821 V822 V829 V849 V856 V859 V861 V867 V902 \
V918 V936 V966 V968 V972 V973 V977 V982 V990 V991 \
V999 V1004 V1232 V1236 V1247 V1253 V1272 V1273 V1291 V1292 \
V1320 V1321 V1331 V1335 V1338 V1340 V1352 V1359 V1360 V1365 \
V1366 V1380 V1381 V1400 V1414 V1428 V1436 V1457 V1458 V1459 \
V1479 V1480 V1488 V1521 V1528 V1529 V1530 V1541 V1545 V1575 \
V1581 V1582 V1583 V1595 V1598 V1610 V1612 V1623 V1637 V1654 \
V1668 V1669 V1679 V1695 V1696 V1697 V1702 V1715 V1732 V1736 \
V1755 V1756 V1776 V1790 V1795 V1796 V1806 V1832 V1833 V1834 \
V1845 V1880 V1885 V1964 V2002 V2016 V2035 V2069 V2087 V2096 \
V2100 V2111 V2165 V2184 V2213 V2243 V2274 V2282 V2329 V2346 \
V2354 V2394 V2409 V2421 V2455 V2469 V2472 V2481 V2494 V2507 \
V2543 V2557 V2571 V2584 V2608 V2613 V2624 V2636 V2645 V2661 \
V2681 V2702 V2715 V2736 V2757 V2770 V2776 V2802 V2804 V2811 \
V2812 V2834 V2849 V2868 V2882 V2911 V2921 V2933 V2949 V2973 \
V2983 V2993 V3006 V3018 V3066 V3079 V3092 V3130 V3142 V3157 \
V3168 V3181 V3196 V3205 V3229 V3249 V3267 V3285 V3291 V3313 \
V3320 V3334 V3354 V3363 V3385 V3409 V3417 V3429 V3453 V3463 \
V3481 V3514 V3536 V3559 V3571 V3595 V3600 V3603 V3607 V3621 \
V3630 V3646 V3656 V3668 V3682 V3685 V3692 V3700 V3707 V3715 \
V3725 V3731 V3736 V3742 V3748 V3750 V3755 V3766 V3767 V3774 \
V3781 V3792 V3804 V3821 V3827 V3836 V3848 V3862 V3880 V3886 \
V3900 V3908 V3931 V3937 V3948 V3954 V3974 V3986 V3992 V3995 \
V4006 V4029 V4031 V4044 V4047 V4068 V4080 V4193 V4329 \
--campaignName 'Midwater Transect dives 1993 - 2021' \
--campaignDescription 'Midwater Transect dives made with Ventana, Tiburonm, and Doc Ricketts from 1993 - 2021'
