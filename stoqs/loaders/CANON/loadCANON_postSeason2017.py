#!/usr/bin/env python
__author__ = 'Mike McCann,Duane Edgington,Reiko Michisaki,Danelle Cline'
__copyright__ = '2017'
__license__ = 'GPL v3'
__contact__ = 'duane at mbari.org'

__doc__ = '''

Master loader for all *postSeason* (after KISS/CANON April season) activities in 2017

Mike McCann, Duane Edgington, Danelle Cline
MBARI 7 April 2017

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime  # needed for glider data

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
import timing

cl = CANONLoader('stoqs_ps2017', 'post Season 2017',
                 description='post season 2017 observations in Monterey Bay',
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

# Set start and end dates for all loads from sources that contain data
# beyond the temporal bounds of the campaign
#
startdate = datetime.datetime(2017, 5, 16)  # Fixed start. May 15, 2017
enddate = datetime.datetime(2017, 9, 17)  # Fixed end. September 17, 2017

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'


#####################################################################
#  DORADO
#####################################################################
# special location for dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2017/netcdf/'
cl.dorado_files = [
                    'Dorado389_2017_157_00_157_00_decim.nc',
                    'Dorado389_2017_248_01_248_01_decim.nc',
                  ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                    'fl700_uncorr', 'salinity', 'biolume',
                    'sepCountList', 'mepCountList',
                    'roll', 'pitch', 'yaw',
                  ]

#####################################################################
#  LRAUV
#####################################################################

# Load netCDF files produced (binned, etc.) by Danelle Cline
# These binned files are created with the makeLRAUVNetCDFs.sh script in the
# toNetCDF directory. You must first edit and run that script once to produce
# the binned files before this will work

# Use the default parameters provided by loadLRAUV() calls below

######################################################################
#  GLIDERS
######################################################################
# Glider data files from CeNCOOS thredds server
# L_662
cl.l_662_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_files = [
                   'OS_Glider_L_662_20170328_TS.nc'  ]
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = startdate
cl.l_662_endDatetime = enddate

# Glider data files from CeNCOOS thredds server
# L_662a updated parameter names in netCDF file
cl.l_662a_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662a_files = [
                   'OS_Glider_L_662_20170328_TS.nc',
                   'OS_Glider_L_662_20170713_TS.nc',
                  ]
cl.l_662a_parms = ['temperature', 'salinity', 'fluorescence','oxygen']
cl.l_662a_startDatetime = startdate
cl.l_662a_endDatetime = enddate

# SG_539 ## KISS glider from Caltech/JPL
cl.sg539_base = cl.dodsBase + 'Activity/canon/2017_Apr/Platforms/Gliders/SG539/'
cl.sg539_files = ['p539{:04d}.nc'.format(i) for i in range(1,291)] ## index needs to be 1 higher than terminal file name
cl.sg539_parms = ['temperature', 'salinity']
cl.sg539_startDatetime = startdate
cl.sg539_endDatetime = enddate

# SG_621 ## KISS glider from Caltech/JPL
cl.sg621_base = cl.dodsBase + 'Activity/canon/2017_Apr/Platforms/Gliders/SG621/'
cl.sg621_files = ['p621{:04d}.nc'.format(i) for i in range(1,291)] ## index needs to be 1 higher than terminal file name
cl.sg621_parms = ['temperature', 'salinity'] # 'aanderaa4330_dissolved_oxygen' throws DAPloader KeyError
cl.sg621_startDatetime = startdate
cl.sg621_endDatetime = enddate


# NPS_34a updated parameter names in netCDF file
## The following loads decimated subset of data telemetered during deployment
cl.nps34a_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.nps34a_files = [ 'OS_Glider_NPS_G34_20170405_TS.nc' ]
cl.nps34a_parms = ['temperature', 'salinity','fluorescence']
cl.nps34a_startDatetime = startdate
cl.nps34a_endDatetime = enddate

# Slocum Teledyne nemesis Glider
## from ioos site ## these files proved to be not compatible with python loader
## cl.slocum_nemesis_base = 'https://data.ioos.us/gliders/thredds/dodsC/deployments/mbari/Nemesis-20170412T0000/'
## cl.slocum_nemesis_files = [ 'Nemesis-20170412T0000.nc3.nc' ]
##   from cencoos directory, single non-aggregated files
cl.slocum_nemesis_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/Nemesis/nemesis_201705/'
cl.slocum_nemesis_files = [
         'nemesis_20170802T164114_rt0.nc',
         'nemesis_20170802T143316_rt0.nc',
         'nemesis_20170802T074856_rt0.nc',
         'nemesis_20170802T054207_rt0.nc',
         'nemesis_20170801T224159_rt0.nc',
         'nemesis_20170801T203357_rt0.nc',
         'nemesis_20170801T134404_rt0.nc',
         'nemesis_20170801T114608_rt0.nc',
         'nemesis_20170801T045140_rt0.nc',
         'nemesis_20170801T024630_rt0.nc',
         'nemesis_20170731T215536_rt0.nc',
         'nemesis_20170731T175018_rt0.nc',
         'nemesis_20170731T163435_rt0.nc',
         'nemesis_20170731T135614_rt0.nc',
         'nemesis_20170731T130623_rt0.nc',
         'nemesis_20170731T085458_rt0.nc',
         'nemesis_20170731T075418_rt0.nc',
         'nemesis_20170731T053440_rt0.nc',
         'nemesis_20170731T024757_rt0.nc',
         'nemesis_20170730T232116_rt0.nc',
         'nemesis_20170730T220127_rt0.nc',
         'nemesis_20170730T172236_rt0.nc',
         'nemesis_20170730T160052_rt0.nc',
         'nemesis_20170730T123423_rt0.nc',
         'nemesis_20170730T111811_rt0.nc',
         'nemesis_20170730T075203_rt0.nc',
         'nemesis_20170730T043018_rt0.nc',
         'nemesis_20170730T014946_rt0.nc',
         'nemesis_20170729T223958_rt0.nc',
         'nemesis_20170729T180711_rt0.nc',
         'nemesis_20170729T163952_rt0.nc',
         'nemesis_20170729T120406_rt0.nc',
         'nemesis_20170729T103422_rt0.nc',
         'nemesis_20170729T062910_rt0.nc',
         'nemesis_20170729T050731_rt0.nc',
         'nemesis_20170729T005531_rt0.nc',
         'nemesis_20170728T234146_rt0.nc',
         'nemesis_20170728T191357_rt0.nc',
         'nemesis_20170728T174405_rt0.nc',
         'nemesis_20170728T144548_rt0.nc',
         'nemesis_20170728T135341_rt0.nc',
         'nemesis_20170728T120328_rt0.nc',
         'nemesis_20170728T082026_rt0.nc',
         'nemesis_20170728T065008_rt0.nc',
         'nemesis_20170728T020224_rt0.nc',
         'nemesis_20170728T003740_rt0.nc',
         'nemesis_20170727T201640_rt0.nc',
         'nemesis_20170727T185806_rt0.nc',
         'nemesis_20170727T140627_rt0.nc',
         'nemesis_20170727T124215_rt0.nc',
         'nemesis_20170727T081022_rt0.nc',
         'nemesis_20170727T064036_rt0.nc',
         'nemesis_20170727T040522_rt0.nc',
         'nemesis_20170727T011008_rt0.nc',
         'nemesis_20170726T202359_rt0.nc',
         'nemesis_20170726T185647_rt0.nc',
         'nemesis_20170726T145126_rt0.nc',
         'nemesis_20170726T134447_rt0.nc',
         'nemesis_20170726T094330_rt0.nc',
         'nemesis_20170726T082748_rt0.nc',
         'nemesis_20170726T035610_rt0.nc',
         'nemesis_20170726T022602_rt0.nc',
         'nemesis_20170725T214737_rt0.nc',
         'nemesis_20170725T202355_rt0.nc',
         'nemesis_20170725T153825_rt0.nc',
         'nemesis_20170725T141045_rt0.nc',
         'nemesis_20170725T113500_rt0.nc',
         'nemesis_20170725T064654_rt0.nc',
         'nemesis_20170725T052001_rt0.nc',
         'nemesis_20170725T004503_rt0.nc',
         'nemesis_20170724T231833_rt0.nc',
         'nemesis_20170724T184805_rt0.nc',
         'nemesis_20170724T172054_rt0.nc',
         'nemesis_20170724T124541_rt0.nc',
         'nemesis_20170724T112102_rt0.nc',
         'nemesis_20170724T063958_rt0.nc',
         'nemesis_20170724T051406_rt0.nc',
         'nemesis_20170724T002801_rt0.nc',
         'nemesis_20170723T230624_rt0.nc',
         'nemesis_20170723T201025_rt0.nc',
         'nemesis_20170723T152710_rt0.nc',
         'nemesis_20170723T140003_rt0.nc',
         'nemesis_20170723T092636_rt0.nc',
         'nemesis_20170723T080002_rt0.nc',
         'nemesis_20170723T045647_rt0.nc',
         'nemesis_20170723T014217_rt0.nc',
         'nemesis_20170722T210653_rt0.nc',
         'nemesis_20170722T194011_rt0.nc',
         'nemesis_20170722T145730_rt0.nc',
         'nemesis_20170722T133318_rt0.nc',
         'nemesis_20170722T084057_rt0.nc',
         'nemesis_20170722T071710_rt0.nc',
         'nemesis_20170722T023909_rt0.nc',
         'nemesis_20170722T011732_rt0.nc',
         'nemesis_20170721T142653_rt0.nc',
         'nemesis_20170721T130319_rt0.nc',
         'nemesis_20170721T094435_rt0.nc',
         'nemesis_20170721T073751_rt0.nc',
         'nemesis_20170721T061212_rt0.nc',
         'nemesis_20170721T012602_rt0.nc',
         'nemesis_20170721T000303_rt0.nc',
         'nemesis_20170720T221558_rt0.nc',
         'nemesis_20170720T193933_rt0.nc',
         'nemesis_20170720T172301_rt0.nc',
         'nemesis_20170720T161601_rt0.nc',
         'nemesis_20170720T124914_rt0.nc',
         'nemesis_20170720T103534_rt0.nc',
         'nemesis_20170720T030426_rt0.nc',
         'nemesis_20170719T235211_rt0.nc',
         'nemesis_20170719T214451_rt0.nc',
         'nemesis_20170719T193222_rt0.nc',
         'nemesis_20170719T175246_rt0.nc',
         'nemesis_20170719T154203_rt0.nc',
         'nemesis_20170719T095229_rt0.nc',
         'nemesis_20170719T074920_rt0.nc',
         'nemesis_20170719T021159_rt0.nc',
         'nemesis_20170718T235945_rt0.nc',
         'nemesis_20170718T220638_rt0.nc',
         'nemesis_20170718T202048_rt0.nc',
         'nemesis_20170718T181447_rt0.nc',
         'nemesis_20170718T161041_rt0.nc',
         'nemesis_20170718T123924_rt0.nc',
         'nemesis_20170718T100913_rt0.nc',
         'nemesis_20170718T030605_rt0.nc',
         'nemesis_20170718T003550_rt0.nc',
         'nemesis_20170717T225306_rt0.nc',
         'nemesis_20170717T194648_rt0.nc',
         'nemesis_20170713T133400_rt0.nc',
         'nemesis_20170713T083009_rt0.nc',
         'nemesis_20170713T033021_rt0.nc',
         'nemesis_20170712T221950_rt0.nc',
         'nemesis_20170712T182306_rt0.nc',
         'nemesis_20170712T131225_rt0.nc',
         'nemesis_20170712T113810_rt0.nc',
         'nemesis_20170712T013943_rt0.nc',
         'nemesis_20170711T151953_rt0.nc',
         'nemesis_20170711T051721_rt0.nc',
         'nemesis_20170710T184225_rt0.nc',
         'nemesis_20170710T084654_rt0.nc',
         'nemesis_20170710T061910_rt0.nc',
         'nemesis_20170709T203614_rt0.nc',
         'nemesis_20170709T152405_rt0.nc',
         'nemesis_20170709T092357_rt0.nc',
         'nemesis_20170708T233313_rt0.nc',
         'nemesis_20170708T134536_rt0.nc',
         'nemesis_20170708T041331_rt0.nc',
         'nemesis_20170707T230019_rt0.nc',
         'nemesis_20170707T143540_rt0.nc',
         'nemesis_20170707T045318_rt0.nc',
         'nemesis_20170706T234359_rt0.nc',
         'nemesis_20170706T165221_rt0.nc',
         'nemesis_20170706T112745_rt0.nc',
         'nemesis_20170706T023143_rt0.nc',
         'nemesis_20170705T162440_rt0.nc',
         'nemesis_20170705T105820_rt0.nc',
         'nemesis_20170705T053524_rt0.nc',
         'nemesis_20170704T194246_rt0.nc',
         'nemesis_20170704T142546_rt0.nc',
         'nemesis_20170704T094940_rt0.nc',
         'nemesis_20170704T000007_rt0.nc',
         'nemesis_20170703T141025_rt0.nc',
         'nemesis_20170703T085553_rt0.nc',
         'nemesis_20170703T023257_rt0.nc',
         'nemesis_20170702T161924_rt0.nc',
         'nemesis_20170702T110930_rt0.nc',
         'nemesis_20170702T061444_rt0.nc',
         'nemesis_20170702T011255_rt0.nc',
         'nemesis_20170701T160018_rt0.nc',
         'nemesis_20170701T071345_rt0.nc',
         'nemesis_20170630T222720_rt0.nc',
         'nemesis_20170630T173522_rt0.nc',
         'nemesis_20170630T110615_rt0.nc',
         'nemesis_20170630T015155_rt0.nc',
         'nemesis_20170629T163441_rt0.nc',
         'nemesis_20170629T074645_rt0.nc',
         'nemesis_20170629T053350_rt0.nc',
         'nemesis_20170628T203214_rt0.nc',
         'nemesis_20170628T153535_rt0.nc',
         'nemesis_20170628T081951_rt0.nc',
         'nemesis_20170628T044931_rt0.nc',
         'nemesis_20170627T230751_rt0.nc',
         'nemesis_20170627T181716_rt0.nc',
         'nemesis_20170627T143008_rt0.nc',
         'nemesis_20170627T111028_rt0.nc',
     'nemesis_20170627T100458_rt0.nc',
     'nemesis_20170627T065410_rt0.nc',
     'nemesis_20170627T055010_rt0.nc',
     'nemesis_20170627T030255_rt0.nc',
     'nemesis_20170627T015656_rt0.nc',
     'nemesis_20170627T003014_rt0.nc',
     'nemesis_20170626T125204_rt0.nc',
     'nemesis_20170626T063820_rt0.nc',
     'nemesis_20170626T020942_rt0.nc',
     'nemesis_20170626T002808_rt0.nc',
     'nemesis_20170625T211411_rt0.nc',
     'nemesis_20170625T175752_rt0.nc',
     'nemesis_20170625T161851_rt0.nc',
     'nemesis_20170625T113953_rt0.nc',
     'nemesis_20170625T100128_rt0.nc',
     'nemesis_20170625T051433_rt0.nc',
     'nemesis_20170625T033537_rt0.nc',
     'nemesis_20170624T222400_rt0.nc',
     'nemesis_20170624T204533_rt0.nc',
     'nemesis_20170624T162944_rt0.nc',
     'nemesis_20170624T145344_rt0.nc',
     'nemesis_20170624T103011_rt0.nc',
     'nemesis_20170624T084537_rt0.nc',
     'nemesis_20170624T041625_rt0.nc',
     'nemesis_20170624T023728_rt0.nc',
     'nemesis_20170623T215842_rt0.nc',
     'nemesis_20170623T201935_rt0.nc',
     'nemesis_20170623T161449_rt0.nc',
     'nemesis_20170623T144819_rt0.nc',
     'nemesis_20170623T110652_rt0.nc',
     'nemesis_20170623T095512_rt0.nc',
     'nemesis_20170623T061340_rt0.nc',
     'nemesis_20170623T044941_rt0.nc',
     'nemesis_20170623T010108_rt0.nc',
     'nemesis_20170622T234639_rt0.nc',
     'nemesis_20170622T210037_rt0.nc',
     'nemesis_20170622T181539_rt0.nc',
     'nemesis_20170622T142146_rt0.nc',
     'nemesis_20170622T130053_rt0.nc',
     'nemesis_20170622T090152_rt0.nc',
     'nemesis_20170622T073820_rt0.nc',
     'nemesis_20170622T033157_rt0.nc',
     'nemesis_20170622T021130_rt0.nc',
     'nemesis_20170621T223441_rt0.nc',
     'nemesis_20170621T211407_rt0.nc',
     'nemesis_20170621T200349_rt0.nc',
     'nemesis_20170621T161435_rt0.nc',
     'nemesis_20170621T145707_rt0.nc',
     'nemesis_20170621T111036_rt0.nc',
     'nemesis_20170621T094708_rt0.nc',
     'nemesis_20170621T043307_rt0.nc',
     'nemesis_20170621T005328_rt0.nc',
     'nemesis_20170620T233602_rt0.nc',
     'nemesis_20170620T181248_rt0.nc',
     'nemesis_20170620T144356_rt0.nc',
     'nemesis_20170620T134058_rt0.nc',
     'nemesis_20170620T091119_rt0.nc',
     'nemesis_20170620T051321_rt0.nc',
     'nemesis_20170620T042254_rt0.nc',
     'nemesis_20170620T011720_rt0.nc',
     'nemesis_20170620T002630_rt0.nc',
     'nemesis_20170619T212104_rt0.nc',
     'nemesis_20170619T203601_rt0.nc',
     'nemesis_20170619T191725_rt0.nc',
     'nemesis_20170619T164233_rt0.nc',
     'nemesis_20170619T152214_rt0.nc',
     'nemesis_20170619T130231_rt0.nc',
     'nemesis_20170619T114652_rt0.nc',
     'nemesis_20170619T092805_rt0.nc',
     'nemesis_20170619T071003_rt0.nc',
     'nemesis_20170619T035459_rt0.nc',
     'nemesis_20170619T013543_rt0.nc',
     'nemesis_20170618T223418_rt0.nc',
     'nemesis_20170618T201159_rt0.nc',
     'nemesis_20170618T153453_rt0.nc',
     'nemesis_20170618T050847_rt0.nc',
     'nemesis_20170617T234920_rt0.nc',
     'nemesis_20170617T145155_rt0.nc',
     'nemesis_20170617T111159_rt0.nc',
     'nemesis_20170617T081343_rt0.nc',
     'nemesis_20170617T051114_rt0.nc',
     'nemesis_20170617T024727_rt0.nc',
     'nemesis_20170616T234825_rt0.nc',
     'nemesis_20170616T161419_rt0.nc',
     'nemesis_20170616T113224_rt0.nc',
     'nemesis_20170616T073354_rt0.nc',
     'nemesis_20170616T061525_rt0.nc',
     'nemesis_20170616T045723_rt0.nc',
     'nemesis_20170616T034025_rt0.nc',
     'nemesis_20170616T022320_rt0.nc',
     'nemesis_20170615T201837_rt0.nc',
     'nemesis_20170615T162845_rt0.nc',
     'nemesis_20170615T150909_rt0.nc',
     'nemesis_20170615T091443_rt0.nc',
     'nemesis_20170615T071148_rt0.nc',
     'nemesis_20170615T024931_rt0.nc',
     'nemesis_20170614T231830_rt0.nc',
     'nemesis_20170614T215355_rt0.nc',
     'nemesis_20170614T180452_rt0.nc',
     'nemesis_20170614T101448_rt0.nc',
     'nemesis_20170614T100251_rt0.nc',
     'nemesis_20170614T071757_rt0.nc',
     'nemesis_20170614T050846_rt0.nc',
     'nemesis_20170613T132822_rt0.nc',
     'nemesis_20170613T102553_rt0.nc',
     'nemesis_20170613T093530_rt0.nc',
     'nemesis_20170613T050552_rt0.nc',
     'nemesis_20170613T034826_rt0.nc',
     'nemesis_20170613T011744_rt0.nc',
     'nemesis_20170613T002036_rt0.nc',
     'nemesis_20170612T232845_rt0.nc',
     'nemesis_20170612T230506_rt0.nc',
     'nemesis_20170612T224043_rt0.nc',
     'nemesis_20170612T221830_rt0.nc',
     'nemesis_20170612T220420_rt0.nc',
     'nemesis_20170612T211158_rt0.nc',
     'nemesis_20170612T205057_rt0.nc',
     'nemesis_20170612T202927_rt0.nc',
     'nemesis_20170612T200632_rt0.nc',
     'nemesis_20170612T195520_rt0.nc',
     'nemesis_20170612T182055_rt0.nc',
     'nemesis_20170612T175717_rt0.nc',
     'nemesis_20170612T162140_rt0.nc',
     'nemesis_20170612T155857_rt0.nc',
     'nemesis_20170612T114213_rt0.nc',
     'nemesis_20170612T063929_rt0.nc',
     'nemesis_20170612T043328_rt0.nc',
     'nemesis_20170611T221425_rt0.nc',
     'nemesis_20170611T200852_rt0.nc',
     'nemesis_20170611T155019_rt0.nc',
     'nemesis_20170611T121144_rt0.nc',
     'nemesis_20170611T081133_rt0.nc',
     'nemesis_20170611T020532_rt0.nc',
     'nemesis_20170611T000300_rt0.nc',
     'nemesis_20170610T194457_rt0.nc',
     'nemesis_20170610T164015_rt0.nc',
     'nemesis_20170610T144002_rt0.nc',
     'nemesis_20170610T095333_rt0.nc',
     'nemesis_20170610T063445_rt0.nc',
     'nemesis_20170610T021235_rt0.nc',
     'nemesis_20170610T000555_rt0.nc',
     'nemesis_20170609T220825_rt0.nc',
     'nemesis_20170609T201551_rt0.nc',
     'nemesis_20170609T181759_rt0.nc',
     'nemesis_20170609T162208_rt0.nc',
     'nemesis_20170609T135938_rt0.nc',
     'nemesis_20170609T104040_rt0.nc',
     'nemesis_20170609T071844_rt0.nc',
     'nemesis_20170609T031918_rt0.nc',
     'nemesis_20170608T224720_rt0.nc',
     'nemesis_20170608T162653_rt0.nc',
     'nemesis_20170608T131023_rt0.nc',
     'nemesis_20170608T115600_rt0.nc',
     'nemesis_20170608T090244_rt0.nc',
     'nemesis_20170608T050720_rt0.nc',
     'nemesis_20170608T035223_rt0.nc',
     'nemesis_20170607T232801_rt0.nc',
     'nemesis_20170607T221250_rt0.nc',
     'nemesis_20170607T124645_rt0.nc',
     'nemesis_20170607T082530_rt0.nc',
     'nemesis_20170607T071109_rt0.nc',
     'nemesis_20170607T024635_rt0.nc',
     'nemesis_20170607T013138_rt0.nc',
     'nemesis_20170606T232855_rt0.nc',
     'nemesis_20170606T162949_rt0.nc',
     'nemesis_20170606T135926_rt0.nc',
     'nemesis_20170606T104755_rt0.nc',
     'nemesis_20170606T073515_rt0.nc',
     'nemesis_20170606T041119_rt0.nc',
     'nemesis_20170606T005242_rt0.nc',
     'nemesis_20170605T220319_rt0.nc',
     'nemesis_20170605T214014_rt0.nc',
     'nemesis_20170605T201032_rt0.nc',
     'nemesis_20170605T195421_rt0.nc',
     'nemesis_20170605T192754_rt0.nc',
     'nemesis_20170605T192154_rt0.nc',
     'nemesis_20170605T190215_rt0.nc',
     'nemesis_20170605T182540_rt0.nc',
     'nemesis_20170605T181639_rt0.nc',
     'nemesis_20170605T175026_rt0.nc',
     'nemesis_20170605T173341_rt0.nc',
     'nemesis_20170605T172532_rt0.nc',
     'nemesis_20170605T165426_rt0.nc',
     'nemesis_20170605T163445_rt0.nc',
     'nemesis_20170605T160451_rt0.nc',
     'nemesis_20170605T155545_rt0.nc',
     'nemesis_20170605T153248_rt0.nc',
     'nemesis_20170605T144633_rt0.nc',
     'nemesis_20170605T142610_rt0.nc',
     'nemesis_20170605T140517_rt0.nc',
     'nemesis_20170605T134244_rt0.nc',
     'nemesis_20170605T133123_rt0.nc',
     'nemesis_20170605T125647_rt0.nc',
     'nemesis_20170605T122648_rt0.nc',
     'nemesis_20170605T121747_rt0.nc',
     'nemesis_20170605T115724_rt0.nc',
     'nemesis_20170605T113455_rt0.nc',
     'nemesis_20170605T105045_rt0.nc',
     'nemesis_20170605T103058_rt0.nc',
     'nemesis_20170605T101125_rt0.nc',
     'nemesis_20170605T100224_rt0.nc',
     'nemesis_20170605T093840_rt0.nc',
     'nemesis_20170605T085723_rt0.nc',
     'nemesis_20170605T084821_rt0.nc',
     'nemesis_20170605T082804_rt0.nc',
     'nemesis_20170605T080811_rt0.nc',
     'nemesis_20170605T074535_rt0.nc',
     'nemesis_20170605T071546_rt0.nc',
     'nemesis_20170605T065629_rt0.nc',
     'nemesis_20170605T062311_rt0.nc',
     'nemesis_20170605T060359_rt0.nc',
     'nemesis_20170605T054929_rt0.nc',
     'nemesis_20170605T050503_rt0.nc',
     'nemesis_20170605T044238_rt0.nc',
     'nemesis_20170605T041948_rt0.nc',
     'nemesis_20170605T035606_rt0.nc',
     'nemesis_20170605T034104_rt0.nc',
     'nemesis_20170605T005826_rt0.nc',
     'nemesis_20170605T002844_rt0.nc',
     'nemesis_20170605T000511_rt0.nc',
     'nemesis_20170604T235056_rt0.nc',
     'nemesis_20170604T231136_rt0.nc',
     'nemesis_20170604T222544_rt0.nc',
     'nemesis_20170604T215648_rt0.nc',
     'nemesis_20170604T214442_rt0.nc',
     'nemesis_20170604T211211_rt0.nc',
     'nemesis_20170604T201106_rt0.nc',
     'nemesis_20170604T195905_rt0.nc',
     'nemesis_20170604T191949_rt0.nc',
     'nemesis_20170604T185456_rt0.nc',
     'nemesis_20170604T184046_rt0.nc',
     'nemesis_20170604T175012_rt0.nc',
     'nemesis_20170604T172424_rt0.nc',
     'nemesis_20170604T165644_rt0.nc',
     'nemesis_20170604T164739_rt0.nc',
     'nemesis_20170604T161918_rt0.nc',
     'nemesis_20170604T152606_rt0.nc',
     'nemesis_20170604T145912_rt0.nc',
     'nemesis_20170604T143232_rt0.nc',
     'nemesis_20170604T140349_rt0.nc',
     'nemesis_20170604T134847_rt0.nc',
     'nemesis_20170604T090929_rt0.nc',
     'nemesis_20170604T083801_rt0.nc',
     'nemesis_20170604T082355_rt0.nc',
     'nemesis_20170604T074050_rt0.nc',
     'nemesis_20170604T070704_rt0.nc',
     'nemesis_20170604T061419_rt0.nc',
     'nemesis_20170604T055701_rt0.nc',
     'nemesis_20170604T041553_rt0.nc',
     'nemesis_20170604T033006_rt0.nc',
     'nemesis_20170604T025533_rt0.nc',
     'nemesis_20170604T024332_rt0.nc',
     'nemesis_20170604T021137_rt0.nc',
     'nemesis_20170604T010742_rt0.nc',
     'nemesis_20170604T003504_rt0.nc',
     'nemesis_20170604T000128_rt0.nc',
     'nemesis_20170603T234923_rt0.nc',
     'nemesis_20170603T231300_rt0.nc',
     'nemesis_20170603T221303_rt0.nc',
     'nemesis_20170603T211524_rt0.nc',
     'nemesis_20170603T210022_rt0.nc',
     'nemesis_20170603T202530_rt0.nc',
     'nemesis_20170603T194751_rt0.nc',
     'nemesis_20170603T185917_rt0.nc',
     'nemesis_20170603T182509_rt0.nc',
     'nemesis_20170603T174845_rt0.nc',
     'nemesis_20170603T171330_rt0.nc',
     'nemesis_20170603T164011_rt0.nc',
     'nemesis_20170603T155030_rt0.nc',
     'nemesis_20170603T145341_rt0.nc',
     'nemesis_20170603T143840_rt0.nc',
     'nemesis_20170603T140209_rt0.nc',
     'nemesis_20170603T120321_rt0.nc',
     'nemesis_20170603T110123_rt0.nc',
     'nemesis_20170603T104922_rt0.nc',
     'nemesis_20170603T101143_rt0.nc',
     'nemesis_20170603T092947_rt0.nc',
     'nemesis_20170603T081038_rt0.nc',
     'nemesis_20170603T075536_rt0.nc',
     'nemesis_20170603T065659_rt0.nc',
     'nemesis_20170603T062115_rt0.nc',
     'nemesis_20170603T060405_rt0.nc',
     'nemesis_20170603T045810_rt0.nc',
     'nemesis_20170603T042556_rt0.nc',
     'nemesis_20170603T035139_rt0.nc',
     'nemesis_20170603T032009_rt0.nc',
     'nemesis_20170603T030252_rt0.nc',
     'nemesis_20170603T015735_rt0.nc',
     'nemesis_20170603T012127_rt0.nc',
     'nemesis_20170603T004617_rt0.nc',
     'nemesis_20170603T003116_rt0.nc',
     'nemesis_20170602T235614_rt0.nc',
     'nemesis_20170602T224821_rt0.nc',
     'nemesis_20170602T223620_rt0.nc',
     'nemesis_20170602T213749_rt0.nc',
     'nemesis_20170602T205955_rt0.nc',
     'nemesis_20170602T204520_rt0.nc',
     'nemesis_20170602T193231_rt0.nc',
     'nemesis_20170602T191428_rt0.nc',
     'nemesis_20170602T161817_rt0.nc',
     'nemesis_20170602T154246_rt0.nc',
     'nemesis_20170602T150558_rt0.nc',
     'nemesis_20170602T145135_rt0.nc',
     'nemesis_20170602T133919_rt0.nc',
     'nemesis_20170602T130433_rt0.nc',
     'nemesis_20170602T123015_rt0.nc',
     'nemesis_20170602T121824_rt0.nc',
     'nemesis_20170602T035831_rt0.nc',
     'nemesis_20170602T034630_rt0.nc',
     'nemesis_20170602T031402_rt0.nc',
     'nemesis_20170602T022205_rt0.nc',
     'nemesis_20170602T020731_rt0.nc',
     'nemesis_20170602T005704_rt0.nc',
     'nemesis_20170602T002407_rt0.nc',
     'nemesis_20170602T001206_rt0.nc',
     'nemesis_20170601T231849_rt0.nc',
     'nemesis_20170601T230141_rt0.nc',
     'nemesis_20170601T203805_rt0.nc',
     'nemesis_20170601T200413_rt0.nc',
     'nemesis_20170601T195003_rt0.nc',
     'nemesis_20170601T185315_rt0.nc',
     'nemesis_20170601T181952_rt0.nc',
     'nemesis_20170601T173035_rt0.nc',
     'nemesis_20170601T165654_rt0.nc',
     'nemesis_20170601T164249_rt0.nc',
     'nemesis_20170531T123420_rt0.nc',
     'nemesis_20170531T110458_rt0.nc',
     'nemesis_20170531T075749_rt0.nc',
     'nemesis_20170531T054816_rt0.nc',
     'nemesis_20170531T041837_rt0.nc',
     'nemesis_20170530T234408_rt0.nc',
     'nemesis_20170530T222117_rt0.nc',
     'nemesis_20170530T164946_rt0.nc',
     'nemesis_20170530T162243_rt0.nc',
     'nemesis_20170530T093925_rt0.nc',
     'nemesis_20170530T081552_rt0.nc',
     'nemesis_20170530T032943_rt0.nc',
     'nemesis_20170530T020545_rt0.nc',
     'nemesis_20170529T225603_rt0.nc',
     'nemesis_20170529T194811_rt0.nc',
     'nemesis_20170529T124603_rt0.nc',
     'nemesis_20170529T112157_rt0.nc',
     'nemesis_20170529T063830_rt0.nc',
     'nemesis_20170529T050859_rt0.nc',
     'nemesis_20170529T015243_rt0.nc',
     'nemesis_20170528T223629_rt0.nc',
     'nemesis_20170528T185447_rt0.nc',
     'nemesis_20170528T184330_rt0.nc',
     'nemesis_20170528T170454_rt0.nc',
     'nemesis_20170528T160831_rt0.nc',
     'nemesis_20170528T112348_rt0.nc',
     'nemesis_20170528T100054_rt0.nc',
     'nemesis_20170528T053214_rt0.nc',
     'nemesis_20170528T040242_rt0.nc',
     'nemesis_20170527T231641_rt0.nc',
     'nemesis_20170527T214948_rt0.nc',
     'nemesis_20170527T171105_rt0.nc',
     'nemesis_20170527T154646_rt0.nc',
     'nemesis_20170527T044348_rt0.nc',
     'nemesis_20170527T041737_rt0.nc',
     'nemesis_20170527T024137_rt0.nc',
     'nemesis_20170527T021517_rt0.nc',
     'nemesis_20170527T003346_rt0.nc',
     'nemesis_20170527T000735_rt0.nc',
     'nemesis_20170526T222801_rt0.nc',
     'nemesis_20170526T220153_rt0.nc',
     'nemesis_20170526T203042_rt0.nc',
     'nemesis_20170526T200734_rt0.nc',
     'nemesis_20170526T183156_rt0.nc',
     'nemesis_20170526T180825_rt0.nc',
     'nemesis_20170526T163330_rt0.nc',
     'nemesis_20170526T160626_rt0.nc',
     'nemesis_20170526T121341_rt0.nc',
     'nemesis_20170526T105013_rt0.nc',
     'nemesis_20170526T061608_rt0.nc',
     'nemesis_20170526T044948_rt0.nc',
     'nemesis_20170526T032021_rt0.nc',
     'nemesis_20170525T223801_rt0.nc',
     'nemesis_20170525T211045_rt0.nc',
     'nemesis_20170525T113745_rt0.nc',
     'nemesis_20170525T103515_rt0.nc',
     'nemesis_20170525T062339_rt0.nc',
     'nemesis_20170525T051746_rt0.nc',
     'nemesis_20170525T010321_rt0.nc',
     'nemesis_20170525T000010_rt0.nc',
     'nemesis_20170524T222242_rt0.nc',
     'nemesis_20170524T215537_rt0.nc',
     'nemesis_20170524T135521_rt0.nc',
     'nemesis_20170524T094523_rt0.nc',
     'nemesis_20170524T084556_rt0.nc',
     'nemesis_20170524T043222_rt0.nc',
     'nemesis_20170524T033227_rt0.nc',
     'nemesis_20170523T232103_rt0.nc',
     'nemesis_20170523T221907_rt0.nc',
     'nemesis_20170523T140631_rt0.nc',
     'nemesis_20170523T095914_rt0.nc',
     'nemesis_20170523T085648_rt0.nc',
     'nemesis_20170523T044334_rt0.nc',
     'nemesis_20170523T033739_rt0.nc',
     'nemesis_20170523T005329_rt0.nc',
     'nemesis_20170522T221419_rt0.nc',
     'nemesis_20170522T164523_rt0.nc',
     'nemesis_20170522T110435_rt0.nc',
     'nemesis_20170522T035314_rt0.nc',
     'nemesis_20170522T011513_rt0.nc',
     'nemesis_20170521T214337_rt0.nc',
     'nemesis_20170521T190757_rt0.nc',
     'nemesis_20170521T121658_rt0.nc',
     'nemesis_20170521T094040_rt0.nc',
     'nemesis_20170521T031344_rt0.nc',
     'nemesis_20170521T005558_rt0.nc',
     'nemesis_20170520T203141_rt0.nc',
     'nemesis_20170520T164104_rt0.nc',
     'nemesis_20170520T145331_rt0.nc',
     'nemesis_20170520T092254_rt0.nc',
     'nemesis_20170520T072247_rt0.nc',
     'nemesis_20170520T021356_rt0.nc',
     'nemesis_20170520T003138_rt0.nc',
     'nemesis_20170519T183707_rt0.nc',
     'nemesis_20170519T171119_rt0.nc',
     'nemesis_20170519T123731_rt0.nc',
     'nemesis_20170519T111110_rt0.nc',
     'nemesis_20170519T081331_rt0.nc',
     'nemesis_20170519T072016_rt0.nc',
     'nemesis_20170519T033005_rt0.nc',
     'nemesis_20170519T020312_rt0.nc',
     'nemesis_20170518T203246_rt0.nc',
     'nemesis_20170518T175850_rt0.nc',
     'nemesis_20170518T111837_rt0.nc',
     'nemesis_20170518T095213_rt0.nc',
     'nemesis_20170518T052321_rt0.nc',
     'nemesis_20170518T035923_rt0.nc',
     'nemesis_20170518T003020_rt0.nc',
     'nemesis_20170517T233411_rt0.nc',
     'nemesis_20170517T192529_rt0.nc',
     'nemesis_20170517T160316_rt0.nc',
     'nemesis_20170517T132043_rt0.nc',
     'nemesis_20170517T100013_rt0.nc',
     'nemesis_20170517T070541_rt0.nc',
     'nemesis_20170517T051340_rt0.nc',
     'nemesis_20170517T031304_rt0.nc',
     'nemesis_20170517T011840_rt0.nc',
     'nemesis_20170516T234527_rt0.nc',
     'nemesis_20170516T220534_rt0.nc',
     'nemesis_20170516T212019_rt0.nc',
     'nemesis_20170516T195855_rt0.nc',
     'nemesis_20170516T185544_rt0.nc',
     'nemesis_20170516T180257_rt0.nc',
     'nemesis_20170516T170849_rt0.nc',

                          ]
cl.slocum_nemesis_parms = [ 'temperature', 'salinity', 'u', 'v' ] #'oxygen', 'cdom', 'opbs', 'fluorescence' not populated
cl.slocum_nemesis_startDatetime = startdate
cl.slocum_nemesis_endDatetime = enddate


######################################################################
# Wavegliders
######################################################################
# WG Tex - All instruments combined into one file - one time coordinate
##cl.wg_tex_base = cl.dodsBase + 'CANON_september2013/Platforms/Gliders/WG_Tex/final/'
##cl.wg_tex_files = [ 'WG_Tex_all_final.nc' ]
##cl.wg_tex_parms = [ 'wind_dir', 'wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal', 'density', 'bb_470', 'bb_650', 'chl' ]
##cl.wg_tex_startDatetime = startdate
##cl.wg_tex_endDatetime = enddate

# WG Tiny - All instruments combined into one file - one time coordinate
cl.wg_Tiny_base = 'http://dods.mbari.org/opendap/data/waveglider/deployment_data/'
cl.wg_Tiny_files = [
##                     'wgTiny/20170412/realTime/20170412.nc',
##                     'wgTiny/20170605/realTime/20170605.nc',
##                     'wgTiny/20170630/realTime/20170630.nc',
                     'wgTiny/20170412/QC/20170412_QC.nc', ## replace realTime with QC. Load only once.
                     'wgTiny/20170605/QC/20170605_QC.nc', ## replace realTime with QC. Load only once.
                     'wgTiny/20170630/QC/20170630_QC.nc', ## replace realTime with QC. Load only once.
                   ]


cl.wg_Tiny_parms = [ 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal',  'bb_470', 'bb_650', 'chl',
                    'beta_470', 'beta_650', 'pCO2_water', 'pCO2_air', 'pH', 'O2_conc' ]
cl.wg_Tiny_depths = [ 0 ]
cl.wg_Tiny_startDatetime = startdate
cl.wg_Tiny_endDatetime = enddate

# WG OA - All instruments combined into one file - one time coordinate
##cl.wg_oa_base = cl.dodsBase + 'CANON/2015_OffSeason/Platforms/Waveglider/wgOA/'
##cl.wg_oa_files = [ 'Sept_2013_OAWaveglider_final.nc' ]
##cl.wg_oa_parms = [ 'distance', 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal', 'O2_conc',
##                   'O2_sat', 'beta_470', 'bb_470', 'beta_700', 'bb_700', 'chl', 'pCO2_water', 'pCO2_air', 'pH' ]
##cl.wg_oa_startDatetime = startdate
##cl.wg_oa_endDatetime = enddate

######################################################################
#  MOORINGS
######################################################################
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/'
cl.m1_files = [
  '201608/OS_M1_20160829hourly_CMSTV.nc',
  '201708/OS_M1_20170808hourly_CMSTV.nc',
]
cl.m1_parms = [
  'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
  'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
  'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR'
]

cl.m1_startDatetime = startdate
cl.m1_endDatetime = enddate

# Mooring 0A1
#cl.oa1_base = 'http://dods.mbari.org/opendap/data/oa_moorings/deployment_data/OA1/201401/'
#cl.oa1_files = [
#               'OA1_201401.nc'
#               ]
cl.oa1_base = 'http://dods.mbari.org/opendap/data/oa_moorings/deployment_data/OA1/201607/realTime/'
cl.oa1_files = [
               'OA1_201607.nc'  ## new deployment
               ]
cl.oa1_parms = [
               'wind_dir', 'avg_wind_spd', 'atm_press', 'air_temp', 'water_temp',
               'sal', 'O2_conc', 'chl', 'pCO2_water', 'pCO2_air', 'pH',
               ]
cl.oa1_startDatetime = startdate
cl.oa1_endDatetime = enddate

# Mooring 0A2
cl.oa2_base = 'http://dods.mbari.org/opendap/data/oa_moorings/deployment_data/OA2/201609/'
cl.oa2_files = [
               'realTime/OA2_201609.nc'
               ]
cl.oa2_parms = [
               'wind_dir', 'avg_wind_spd', 'atm_press', 'air_temp', 'water_temp',
               'sal', 'O2_conc', 'chl', 'pCO2_water', 'pCO2_air', 'pH',
               ]
cl.oa2_startDatetime = startdate
cl.oa2_endDatetime = enddate


######################################################################
#  RACHEL CARSON: Jan 2017 --
######################################################################
# UCTD
cl.rcuctd_base = cl.dodsBase + 'Other/routine/Platforms/Ships/RachelCarson/uctd/'
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.rcuctd_files = [
#                  '00917plm01.nc',
#                  '03917plm01.nc',
                  ]

# PCTD
cl.rcpctd_base = cl.dodsBase + 'Other/routine/Platforms/Ships/RachelCarson/pctd/'
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.rcpctd_files = [
#                  '00917c01.nc', '00917c02.nc', '00917c03.nc',
#                  '03917c01.nc', '03917c02.nc', '03917c03.nc',
                  ]

######################################################################
#  WESTERN FLYER: Apr 2017 --
######################################################################
# UCTD
cl.wfuctd_base = cl.dodsBase + 'Other/routine/Platforms/Ships/WesternFlyer/uctd/'
cl.wfuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.wfuctd_files = [
                  'canon17sm01.nc',
                  ]

# PCTD
cl.wfpctd_base = cl.dodsBase + 'Other/routine/Platforms/Ships/WesternFlyer/pctd/'
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.wfpctd_files = [
                  'canon17sc01.nc',
                  ]

###################################################################################################
# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/
#   copied to local BOG_Data/CANON_OS2107 dir
###################################################################################################
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data/CANON_OS2017/bctd/')
cl.subsample_csv_files = [
##   'STOQS_00917_OXY_PS.csv',
##   'STOQS_00917_CARBON_GFF.csv',
##   'STOQS_00917_CHL_1U.csv',    'STOQS_00917_FLUOR.csv',
##   'STOQS_00917_CHL_5U.csv', 'STOQS_00917_NH4.csv', 'STOQS_00917_PHAEO_1U.csv',
##   'STOQS_00917_CHLA.csv', 'STOQS_00917_O2.csv', 'STOQS_00917_PHAEO_5U.csv',
##   'STOQS_00917_CHL_GFF.csv',
##   'STOQS_00917_PHAEO_GFF.csv',
                       ]

# Execute the load
cl.process_command_line()

if cl.args.test:

    cl.loadM1(stride=100)
    cl.loadLRAUV('tethys', startdate, enddate, stride=100)
    cl.loadLRAUV('aku', startdate, enddate, stride=100)
    cl.loadLRAUV('ahi', startdate, enddate, stride=100)
    cl.loadLRAUV('opah', startdate, enddate, stride=100)
    cl.loadLRAUV('daphne', startdate, enddate, stride=100)
    cl.loadL_662(stride=100)
    cl.loadL_662(stride=100)
    cl.loadL_662a(stride=100)
    cl.load_NPS34(stride=100)
    cl.load_NPS34a(stride=100)
    cl.load_slocum_nemesis(stride=100)
    cl.load_SG621(stride=100) ## KISS glider
    cl.load_SG539(stride=100) ## KISS glider
    cl.load_wg_Tiny(stride=100)
    cl.load_oa1(stride=100)
    cl.load_oa2(stride=100)
    cl.loadDorado(stride=100)
    cl.loadRCuctd(stride=100)
    cl.loadRCpctd(stride=100)
    cl.loadWFuctd(stride=100)
    cl.loadWFpctd(stride=100)

    cl.loadSubSamples()

elif cl.args.optimal_stride:

    cl.loadL_662(stride=2)
    ##cl.load_NPS29(stride=2)
    #cl.load_NPS34(stride=2)
    cl.load_wg_Tiny(stride=2)
    cl.load_oa1(stride=2)
    cl.load_oa2(stride=2)
    cl.loadM1(stride=2)
    ##cl.loadDorado(stride=2)
    cl.loadRCuctd(stride=2)
    cl.loadRCpctd(stride=2)

    cl.loadSubSamples()

else:
    cl.stride = cl.args.stride

    cl.loadM1()
    cl.loadLRAUV('tethys', startdate, enddate)
    cl.loadLRAUV('aku', startdate, enddate)
    cl.loadLRAUV('ahi', startdate, enddate)
    cl.loadLRAUV('opah', startdate, enddate)
    cl.loadLRAUV('daphne', startdate, enddate)
    ##cl.loadL_662()  ## not in this campaign
    cl.loadL_662a()
    ##cl.load_NPS34()  ## not in this campaign
    cl.load_NPS34a()
    cl.load_slocum_nemesis()
    ##cl.load_SG621(stride=2) ## KISS glider
    ##cl.load_SG539(stride=2) ## KISS glider
    cl.load_wg_Tiny()
    cl.load_oa1()
    cl.load_oa2()
    cl.loadDorado()
    ##cl.loadRCuctd()  ## not in this campaign
    ##cl.loadRCpctd()  ## not in this campaign
    #cl.loadWFuctd()
    #cl.loadWFpctd()

    #cl.loadSubSamples() ## no subSamples yet...

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")
                                                 
