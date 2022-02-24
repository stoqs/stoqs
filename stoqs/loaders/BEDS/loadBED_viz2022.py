#!/usr/bin/env python
'''
Loader for bench test for qualification in 2022

Mike McCann
MBARI 11 Feb 2022
'''

import os
import sys
parent_dir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parent_dir)  # So that CCE is found
from CCE import CCELoader

from collections import namedtuple
from DAPloaders import NoValidData
from datetime import datetime
import numpy as np
import timing

# See stoqs/loaders/CCE/bed2netcdf/makeBEDNetCDF_2022.sh for the origin of these files

# [mccann@elvis BenchTests]$ ls -R
# .:
# 2021-12-30-Test-124min	2022-01-03-Test-244min-Acoustic  2022-01-04-Test-484min
# 
# ./2021-12-30-Test-124min:

files_124 = [f"2021-12-30-Test-124min/{f}" for f in sorted("""
20200654_full.nc  20200674_full.nc  20200694_full.nc  20200714_full.nc	20200734_full.nc  20200754_full.nc  20200774_full.nc
20200655_full.nc  20200675_full.nc  20200695_full.nc  20200715_full.nc	20200735_full.nc  20200755_full.nc  20200775_full.nc
20200656_full.nc  20200676_full.nc  20200696_full.nc  20200716_full.nc	20200736_full.nc  20200756_full.nc  20200776_full.nc
20200657_full.nc  20200677_full.nc  20200697_full.nc  20200717_full.nc	20200737_full.nc  20200757_full.nc  20200777_full.nc
20200658_full.nc  20200678_full.nc  20200698_full.nc  20200718_full.nc	20200738_full.nc  20200758_full.nc  20200778_full.nc
20200659_full.nc  20200679_full.nc  20200699_full.nc  20200719_full.nc	20200739_full.nc  20200759_full.nc  20200779_full.nc
20200660_full.nc  20200680_full.nc  20200700_full.nc  20200720_full.nc	20200740_full.nc  20200760_full.nc  20200780_full.nc
20200661_full.nc  20200681_full.nc  20200701_full.nc  20200721_full.nc	20200741_full.nc  20200761_full.nc  20200781_full.nc
20200662_full.nc  20200682_full.nc  20200702_full.nc  20200722_full.nc	20200742_full.nc  20200762_full.nc  20200782_full.nc
20200663_full.nc  20200683_full.nc  20200703_full.nc  20200723_full.nc	20200743_full.nc  20200763_full.nc  20200783_full.nc
20200664_full.nc  20200684_full.nc  20200704_full.nc  20200724_full.nc	20200744_full.nc  20200764_full.nc  20200784_full.nc
20200665_full.nc  20200685_full.nc  20200705_full.nc  20200725_full.nc	20200745_full.nc  20200765_full.nc  20200785_full.nc
20200666_full.nc  20200686_full.nc  20200706_full.nc  20200726_full.nc	20200746_full.nc  20200766_full.nc  20200786_full.nc
20200667_full.nc  20200687_full.nc  20200707_full.nc  20200727_full.nc	20200747_full.nc  20200767_full.nc  20200787_full.nc
20200668_full.nc  20200688_full.nc  20200708_full.nc  20200728_full.nc	20200748_full.nc  20200768_full.nc
20200669_full.nc  20200689_full.nc  20200709_full.nc  20200729_full.nc	20200749_full.nc  20200769_full.nc
20200670_full.nc  20200690_full.nc  20200710_full.nc  20200730_full.nc	20200750_full.nc  20200770_full.nc
20200671_full.nc  20200691_full.nc  20200711_full.nc  20200731_full.nc	20200751_full.nc  20200771_full.nc
20200672_full.nc  20200692_full.nc  20200712_full.nc  20200732_full.nc	20200752_full.nc  20200772_full.nc
20200673_full.nc  20200693_full.nc  20200713_full.nc  20200733_full.nc	20200753_full.nc  20200773_full.nc""".split())]

# ./2022-01-03-Test-244min-Acoustic:
files_244 = [f"2022-01-03-Test-244min-Acoustic/{f}" for f in sorted("""
20200857_full.nc  20200877_full.nc  20200897_full.nc  20200917_full.nc	20200937_full.nc  20200957_full.nc  20200977_full.nc
20200858_full.nc  20200878_full.nc  20200898_full.nc  20200918_full.nc	20200938_full.nc  20200958_full.nc  20200978_full.nc
20200859_full.nc  20200879_full.nc  20200899_full.nc  20200919_full.nc	20200939_full.nc  20200959_full.nc  20200979_full.nc
20200860_full.nc  20200880_full.nc  20200900_full.nc  20200920_full.nc	20200940_full.nc  20200960_full.nc  20200980_full.nc
20200861_full.nc  20200881_full.nc  20200901_full.nc  20200921_full.nc	20200941_full.nc  20200961_full.nc  20200981_full.nc
20200862_full.nc  20200882_full.nc  20200902_full.nc  20200922_full.nc	20200942_full.nc  20200962_full.nc  20200982_full.nc
20200863_full.nc  20200883_full.nc  20200903_full.nc  20200923_full.nc	20200943_full.nc  20200963_full.nc  20200983_full.nc
20200864_full.nc  20200884_full.nc  20200904_full.nc  20200924_full.nc	20200944_full.nc  20200964_full.nc  20200984_full.nc
20200865_full.nc  20200885_full.nc  20200905_full.nc  20200925_full.nc	20200945_full.nc  20200965_full.nc  20200985_full.nc
20200866_full.nc  20200886_full.nc  20200906_full.nc  20200926_full.nc	20200946_full.nc  20200966_full.nc  20200986_full.nc
20200867_full.nc  20200887_full.nc  20200907_full.nc  20200927_full.nc	20200947_full.nc  20200967_full.nc  20200987_full.nc
20200868_full.nc  20200888_full.nc  20200908_full.nc  20200928_full.nc	20200948_full.nc  20200968_full.nc  20200988_full.nc
20200869_full.nc  20200889_full.nc  20200909_full.nc  20200929_full.nc	20200949_full.nc  20200969_full.nc  20200989_full.nc
20200870_full.nc  20200890_full.nc  20200910_full.nc  20200930_full.nc	20200950_full.nc  20200970_full.nc  20200990_full.nc
20200871_full.nc  20200891_full.nc  20200911_full.nc  20200931_full.nc	20200951_full.nc  20200971_full.nc  20200991_full.nc
20200872_full.nc  20200892_full.nc  20200912_full.nc  20200932_full.nc	20200952_full.nc  20200972_full.nc  20200992_full.nc
20200873_full.nc  20200893_full.nc  20200913_full.nc  20200933_full.nc	20200953_full.nc  20200973_full.nc  20200993_full.nc
20200874_full.nc  20200894_full.nc  20200914_full.nc  20200934_full.nc	20200954_full.nc  20200974_full.nc  20200994_full.nc
20200875_full.nc  20200895_full.nc  20200915_full.nc  20200935_full.nc	20200955_full.nc  20200975_full.nc
20200876_full.nc  20200896_full.nc  20200916_full.nc  20200936_full.nc	20200956_full.nc  20200976_full.nc""".split())]

# ./2022-01-04-Test-484min:
files_484 = [f"2022-01-04-Test-484min/{f}" for f in sorted("""
20200995_full.nc  20201014_full.nc  20201033_full.nc  20201052_full.nc	20201071_full.nc  20201090_full.nc  20201109_full.nc
20200996_full.nc  20201015_full.nc  20201034_full.nc  20201053_full.nc	20201072_full.nc  20201091_full.nc  20201110_full.nc
20200997_full.nc  20201016_full.nc  20201035_full.nc  20201054_full.nc	20201073_full.nc  20201092_full.nc  20201111_full.nc
20200998_full.nc  20201017_full.nc  20201036_full.nc  20201055_full.nc	20201074_full.nc  20201093_full.nc  20201112_full.nc
20200999_full.nc  20201018_full.nc  20201037_full.nc  20201056_full.nc	20201075_full.nc  20201094_full.nc  20201113_full.nc
20201000_full.nc  20201019_full.nc  20201038_full.nc  20201057_full.nc	20201076_full.nc  20201095_full.nc  20201114_full.nc
20201001_full.nc  20201020_full.nc  20201039_full.nc  20201058_full.nc	20201077_full.nc  20201096_full.nc  20201115_full.nc
20201002_full.nc  20201021_full.nc  20201040_full.nc  20201059_full.nc	20201078_full.nc  20201097_full.nc  20201116_full.nc
20201003_full.nc  20201022_full.nc  20201041_full.nc  20201060_full.nc	20201079_full.nc  20201098_full.nc  20201117_full.nc
20201004_full.nc  20201023_full.nc  20201042_full.nc  20201061_full.nc	20201080_full.nc  20201099_full.nc  20201118_full.nc
20201005_full.nc  20201024_full.nc  20201043_full.nc  20201062_full.nc	20201081_full.nc  20201100_full.nc  20201119_full.nc
20201006_full.nc  20201025_full.nc  20201044_full.nc  20201063_full.nc	20201082_full.nc  20201101_full.nc  20201120_full.nc
20201007_full.nc  20201026_full.nc  20201045_full.nc  20201064_full.nc	20201083_full.nc  20201102_full.nc  20201121_full.nc
20201008_full.nc  20201027_full.nc  20201046_full.nc  20201065_full.nc	20201084_full.nc  20201103_full.nc  20201122_full.nc
20201009_full.nc  20201028_full.nc  20201047_full.nc  20201066_full.nc	20201085_full.nc  20201104_full.nc  20201123_full.nc
20201010_full.nc  20201029_full.nc  20201048_full.nc  20201067_full.nc	20201086_full.nc  20201105_full.nc  20201124_full.nc
20201011_full.nc  20201030_full.nc  20201049_full.nc  20201068_full.nc	20201087_full.nc  20201106_full.nc  20201125_full.nc
20201012_full.nc  20201031_full.nc  20201050_full.nc  20201069_full.nc	20201088_full.nc  20201107_full.nc  20201126_full.nc
20201013_full.nc  20201032_full.nc  20201051_full.nc  20201070_full.nc	20201089_full.nc  20201108_full.nc""".split())]


class CCE_2015_Campaign:

    def __init__(self, db_alias='stoqs_beds_viz2022', campaign_name='BEDS Qualification Bench Tests'):
        self.cl = CCELoader(db_alias, campaign_name,
                description = 'Bentic Event Detector data visualization database',
                x3dTerrains = { 
                    'https://stoqs.mbari.org/x3d/MontereyCanyonBeds_1m+5m_1x_src/MontereyCanyonBeds_1m+5m_1x_src_scene.x3d': {
                        'name': 'MontereyCanyonBeds_1m+5m_1x',
                        'position': '2232.80938 10346.25515 3543.76722',
                        'orientation': '-0.98394 0.16804 -0.06017 1.25033',
                        'centerOfRotation': '0 0 0',
                        'VerticalExaggeration': '1',
                        'geoOrigin': '36.80, -121.87, -400',
                        'speed': '1.0',
                        'zNear': '100.0',
                        'zFar': '30000.0',
                        'selected': '1'
                    },
                    'https://stoqs.mbari.org/x3d/Monterey25_1x/Monterey25_1x_src_scene.x3d': {
                        'name': 'Monterey25_1x',
                        'position': '-32985.28634 88026.90417 22334.02600',
                        'orientation': '-0.99875 -0.04772 0.01482 1.31683',
                        'centerOfRotation': '-20564.015827789044 -1956.065669754069 14112.954469753739',
                        'VerticalExaggeration': '1',
                        'geoOrigin': '36.80, -121.87, -400',
                        'speed': '1.0',
                        'zNear': '-1',
                        'zFar': '-1',
                    },
                 },
                 # Do not check in .grd files to the repository, keep them in the loaders directory
                 grdTerrain=os.path.join(parent_dir, 'MontereyCanyonBeds_1m+5m.grd'),
                 ##grdTerrain=os.path.join(parent_dir, 'Monterey25.grd'),
               )

        # Base OPeNDAP server
        self.cl.bed_base = 'http://dods.mbari.org/opendap/data/beds/BenchTests/'

        self.cl.bed_parms = ['XA', 'YA', 'ZA', 'A', 'XR', 'YR', 'ZR', 'ROT_RATE', 'ROT_COUNT',
                        'BED_DEPTH', 'BED_DEPTH_LI', 'TUMBLE_RATE', 'TUMBLE_COUNT',
                        'ROT_X', 'ROT_Y', 'ROT_Z', 'AXIS_X', 'AXIS_Y', 'AXIS_Z', 'ANGLE']


        self.cl.bed_files = files_124 + files_244 + files_484
        self.cl.bed_platforms = ["BED00" for f in self.cl.bed_files ]
        self.cl.bed_depths = [-10 for f in self.cl.bed_files ]
        self.cl.bed_framegrabs = ["" for f in self.cl.bed_files ]

        self.cl.process_command_line()


if __name__ == '__main__':
    campaign = CCE_2015_Campaign()
    if campaign.cl.args.test:
        campaign.cl.loadBEDS(stride=1, featureType='timeSeries')

    elif campaign.cl.args.optimal_stride:
        campaign.cl.loadBEDS(stride=1, featureType='timeSeries')

    else:
        campaign.cl.stride = campaign.cl.args.stride
        campaign.cl.loadBEDS(featureType='timeSeries')

    # Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
    campaign.cl.addTerrainResources()

    campaign.cl.logger.info("All Done.")

