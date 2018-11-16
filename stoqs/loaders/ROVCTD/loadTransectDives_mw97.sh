#!/bin/bash
#
# Load an initial subset of Midwater Lab transect dives as provided by Rob Sherlock:
# 
# From: Rob Sherlock <robs@mbari.org>
# Subject: Re: STOQS loader
# Date: October 3, 2014 at 12:40:08 PM PDT
# To: Mike McCann <mccann@mbari.org>
# 
# Ok, thanks Mike!
# 
# If you could import the following mix of Ventana and Doc Ricketts’ dives into STOQS, that’d be great:
# 2014:  V3766, V3767, V3774, D646
# 2013:  D449, D478, V3736
# 2011: V3607, V3630, V3646
# 2009: V3334, V3363, V3417
# 2007: V2983, V3006, V3079
# 2005: V2636, V2661, V2715
# 2003: V2329, V2354, V2421
# 2001: T257, V1964, V2069
# 1999: V1575, V1610, V1668
# 1997: V1236, V1247, V1321
# 
# If that’s too many, it’d be fine to load 2014, 2013, 2009, 2005, 2001, 1997 (n=19 dives). If that’s too m any, let me know.
# 
# Thanks!
# Rob

./ROVCTDloader.py --database stoqs_rovctd_mw97 --dives \
V1236 V1247 V1321 V1575 V1610 V1668 T257 V1964 \
V2069 V2329 V2354 V2421 V2636 V2661 V2715 V2983 V3006 \
V3079 V3334 V3363 V3417 V3607 V3630 V3646 D449 D478 \
V3736 V3766 V3767 V3774 D646 \
--bbox -122.1 36.65 -122.0 36.75 \
--campaignName 'Midwater Transect dives 1997 - 2014' \
--campaignDescription 'Midwater Transect dives made with Ventana and Doc Ricketts from 1997 - 2014. Three to four dives/year selected, representing spring, summer and fall (~ beginning upwelling, upwelling and post-upwelling)'

