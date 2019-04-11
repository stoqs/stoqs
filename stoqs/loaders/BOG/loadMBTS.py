#!/usr/bin/env python
'''
MBARI Biological Oceanography Group
Master loader for Monterey Bay Time Series data

Mike McCann, Duane Edgington, Danelle Cline
MBARI 8 April 2019
'''

import os
import sys

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
from collections import defaultdict, namedtuple
from datetime import datetime, timedelta
from glob import glob
import timing

cl = CANONLoader('stoqs_mbts', 'BOG - Monterey Bay Time Series',
                 description='MBARI Biological Oceanography Group Monterey Bay Time Series data',
                 x3dTerrains={
                   'https://stoqs.mbari.org/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                     'position': '-2822317.31255 -4438600.53640 3786150.85474',
                     'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                     'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                     'VerticalExaggeration': '10',
                   },
                   'https://stoqs.mbari.org/x3d/Monterey25_1x/Monterey25_1x_src_scene.x3d': {
                     'name': 'Monterey25_1x',
                     'position': '-2822317.31255 -4438600.53640 3786150.85474',
                     'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                     'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                     'VerticalExaggeration': '1',
                   },
                 },
                 grdTerrain=os.path.join(parentDir, 'Monterey25.grd')
                 )

# Email from Marguerite:
# 
# From: Marguerite Blum <mblum@mbari.org>
# Subject: Tethys then Daphne
# Date: April 1, 2019 at 4:51:11 PM PDT
# To: Mike McCann <mccann@mbari.org>
# Cc: Brent Jones <bjones@mbari.org>, Brian Kieft <bkieft@mbari.org>
# Reply-To: Marguerite Blum <mblum@mbari.org>
# 
# Mike,
# Here is a list of the cruises, dates, and vehicles used in the last three years.
# Important notes:
# 1) The sipper number of samples was 9 in 2015, and increased to 15 samples in 2016.
# 2) Tethys was switched out and the guys started using Daphne during spring Canon 2017.
# 3) I have one cruise on 6/30/16 that has samples, but there may not be a deployment. Just be aware of that date. Its the one with a "?".
# 
# BOG_CruiseID    Date    Vehicle
# 18815    7/7/2015    Tethys
# 21515    8/3/2015    Tethys
# 23715    8/25/2015    Tethys
# 28715    10/9/2015    Tethys
# 29915    10/26/2015    Tethys
# 32315    11/19/2015    Tethys
# 34915    12/15/2015    Tethys
# 11216    4/21/2016    Tethys
# 14016    5/19/2016    Tethys
# 16016    6/8/2016    Tethys
# 18016    6/30/2016    ?
# 24416    8/31/2016    Tethys
# CANON16    9/23-27/16    Tethys
# 30616    11/3/2016    Tethys
# 34916    12/14/2016    Tethys
# 00917        Tethys
# 03917    2/13/2017    Tethys
# 06617    3/8/2017    Tethys
# 08717    3/28/2017    Tethys
# 10717    4/18/2017    Tethys
# 18017    6/29/2017    Daphne
# 20017    7/19/2017    Daphne
# aMBTS171    10/5/2017    Daphne
# 30517    11/1/2021    Daphne
# 01618    1/16/2018    Daphne
# 03918    1/31/2018    Daphne
# Cheers,
# 
# Marguerite Blum
# 
# Research Technician
# Dungeon/Nutrient Lab
# c/o MBARI
# 7700 Sandholdt Rd.
# Moss Landing, CA 95039
# 831-775-2080

bog_lrauv_cruises = """18815    7/7/2015    Tethys
21515    8/3/2015    Tethys
23715    8/25/2015    Tethys
28715    10/9/2015    Tethys
29915    10/26/2015    Tethys
32315    11/19/2015    Tethys
34915    12/15/2015    Tethys
11216    4/21/2016    Tethys
14016    5/19/2016    Tethys
16016    6/8/2016    Tethys
18016    6/30/2016    ?
24416    8/31/2016    Tethys
CANON16    9/23-27/16    Tethys
30616    11/3/2016    Tethys
34916    12/14/2016    Tethys
00917        Tethys
03917    2/13/2017    Tethys
06617    3/8/2017    Tethys
08717    3/28/2017    Tethys
10717    4/18/2017    Tethys
18017    6/29/2017    Daphne
20017    7/19/2017    Daphne
aMBTS171    10/5/2017    Daphne
30517    11/1/2021    Daphne
01618    1/16/2018    Daphne
03918    1/31/2018    Daphne
"""

# Get dataset urls by search for strings in .dlist files
##urls = cl.find_lrauv_urls_by_dlist_string('MBTS', platform='tethys', start_year=2015, end_year=2015)

# Set start and end dates for the LRAUVs - missions may start and end several days around cruise date
days_before = 6
days_after = 6
LRAUV_date = namedtuple('LRAUV_date', 'start end')
lrauv_dates = defaultdict(list)

for line in bog_lrauv_cruises.split('\n'):
    print(line)
    try:
        cruise_id, date_str, lrauv_name = line.split()
        mo, da, yr = date_str.split('/')
        dt = datetime(int(yr), int(mo), int(da))
    except ValueError:
        # Likely ValueError: not enough values to unpack (expected 3, got 0)
        print(f"Unable to parse line = {line}")
        continue

    lrauv_dates[lrauv_name.lower()].append(LRAUV_date(
                    dt - timedelta(days=days_before), 
                    dt + timedelta(days=days_after)))

syear = datetime(2015, 1, 1)
eyear = datetime(2015, 12, 31)
##eyear = datetime(2019, 12, 31)

# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.stride = 100
elif cl.args.stride:
    cl.stride = cl.args.stride

for lrauv in ('tethys', 'daphne'):
    cl.loadLRAUV(lrauv, syear, eyear, dlist_str='MBTS', err_on_missing_file=True)

##cl.loadSubSamples() ## no subSamples yet...

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
##cl.addTerrainResources()

print("All Done.")

