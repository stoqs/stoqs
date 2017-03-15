#!/usr/bin/env python
__author__    = 'Mike McCann,Duane Edgington,Reiko Michisaki'
__copyright__ = '2015'
__license__   = 'GPL v3'
__contact__   = 'duane at mbari.org'

__doc__ = '''

Master loader for all CANON activities in September 2015

Mike McCann and Duane Edgington
MBARI 23 September 2015

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import datetime  # needed for glider data
import time      # for startdate, enddate args
import csv
import urllib.request, urllib.error, urllib.parse
import urllib.parse
import requests
import thredds_crawler

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader

from thredds_crawler.etree import etree
from thredds_crawler.crawl import Crawl
 
cl = CANONLoader('stoqs_canon_september2015', 'CANON - September-October 2015',
                    description = 'Fall 2015 Front Identification in northern Monterey Bay',
                    x3dTerrains = {
                            '/static/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                                'position': '-2822317.31255 -4438600.53640 3786150.85474',
                                'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                                'centerOfRotation': '-2711557.94 -4331414.32 3801353.46',
                                'VerticalExaggeration': '10',
                                'speed': '.1',
                            }
                    },
                    grdTerrain = os.path.join(parentDir, 'Monterey25.grd')
                  )

# Set start and end dates for all loads from sources that contain data 
# beyond the temporal bounds of the campaign
startdate = datetime.datetime(2015, 9, 8)                 # Changed to 8th to include pre CANON LRAUV test data
enddate = datetime.datetime(2015, 10, 16)                 # Fixed end two days after end of CANON cruises

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'

#####################################################################
#  DORADO 
#####################################################################
# special location for dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2015/netcdf/'
cl.dorado_files = [
                    'Dorado389_2015_265_03_265_03_decim.nc',
                    'Dorado389_2015_267_01_267_01_decim.nc',
                    'Dorado389_2015_285_00_285_00_decim.nc',
                    'Dorado389_2015_286_00_286_00_decim.nc', 
                    'Dorado389_2015_287_00_287_00_decim.nc',
                  ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                    'fl700_uncorr', 'salinity', 'biolume', 'rhodamine',
                    'roll', 'pitch', 'yaw',
                    'sepCountList', 'mepCountList' ]

#####################################################################
#  LRAUV 
#####################################################################
def find_urls(base, search_str):
    INV_NS = "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
    url = os.path.join(base, 'catalog.xml')
    print("Crawling: %s" % url)
    skips = Crawl.SKIPS + [".*Courier*", ".*Express*", ".*Normal*, '.*Priority*", ".*.cfg$" ]
    u = urllib.parse.urlsplit(url)
    name, ext = os.path.splitext(u.path)
    if ext == ".html":
        u = urllib.parse.urlsplit(url.replace(".html", ".xml"))
    url = u.geturl()
    urls = []
    # Get an etree object
    try:
        r = requests.get(url)
        tree = etree.XML(r.text.encode('utf-8'))

        # Crawl the catalogRefs:
        for ref in tree.findall('.//{%s}catalogRef' % INV_NS):

            try:
                # get the mission directory name and extract the start and ending dates
                mission_dir_name = ref.attrib['{http://www.w3.org/1999/xlink}title']
                dts = mission_dir_name.split('_')
                dir_start =  datetime.datetime.strptime(dts[0], '%Y%m%d')
                dir_end =  datetime.datetime.strptime(dts[1], '%Y%m%d')

                # if within a valid range, grab the valid urls
                if dir_start >= startdate and dir_end <= enddate:
                    catalog = ref.attrib['{http://www.w3.org/1999/xlink}href']
                    c = Crawl(os.path.join(base, catalog), select=[search_str], skip=skips)
                    d = [s.get("url") for d in c.datasets for s in d.services if s.get("service").lower() == "opendap"]
                    for url in d:
                        urls.append(url)
            except Exception as ex:
                print("Error reading mission directory name %s" % ex)

    except BaseException:
        print("Skipping %s (error parsing the XML )" % url)

    return urls


# Load netCDF files produced (binned, etc.) by Danelle Cline
# These binned files are created with the makeLRAUVNetCDFs.sh script in the
# toNetCDF directory. You must first edit and run that script once to produce 
# the binned files before this will work
  
# Get directory list from thredds server
platforms = ['tethys', 'daphne', 'makai']

for p in platforms:
    base =  'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/' + p + '/missionlogs/2015/'
    dods_base = 'http://dods.mbari.org/opendap/data/lrauv/' + p + '/missionlogs/2015/'
    setattr(cl, p + '_files', []) 
    setattr(cl, p + '_base', dods_base)
    setattr(cl, p + '_parms' , ['temperature', 'salinity', 'chlorophyll', 'nitrate', 'oxygen','bbp470', 'bbp650','PAR'
                                'yaw', 'pitch', 'roll', 'control_inputs_rudder_angle', 'control_inputs_mass_position',
                                'control_inputs_buoyancy_position', 'control_inputs_propeller_rotation_rate',
                                'health_platform_battery_charge', 'health_platform_average_voltage',
                                'health_platform_average_current','fix_latitude', 'fix_longitude',
                                'fix_residual_percent_distance_traveled_DeadReckonUsingSpeedCalculator',
                                'pose_longitude_DeadReckonUsingSpeedCalculator',
                                'pose_latitude_DeadReckonUsingSpeedCalculator',
                                'pose_depth_DeadReckonUsingSpeedCalculator',
                                'fix_residual_percent_distance_traveled_DeadReckonUsingMultipleVelocitySources',
                                'pose_longitude_DeadReckonUsingMultipleVelocitySources',
                                'pose_latitude_DeadReckonUsingMultipleVelocitySources',
                                'pose_depth_DeadReckonUsingMultipleVelocitySources'])
    urls_eng = find_urls(base, '.*2S_eng.nc$')
    urls_sci = find_urls(base, '.*10S_sci.nc$')
    urls = urls_eng + urls_sci
    files = []
    if len(urls) > 0 :
        for url in sorted(urls):
            file = '/'.join(url.split('/')[-3:])
            files.append(file)
    setattr(cl, p + '_files', files) 
    setattr(cl, p  + '_startDatetime', startdate) 
    setattr(cl, p + '_endDatetime', enddate)

######################################################################
#  GLIDERS
######################################################################
# Glider data files from CeNCOOS thredds server
# L_662
cl.l_662_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_files = [ 'OS_Glider_L_662_20150813_TS.nc' ]
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = startdate
cl.l_662_endDatetime = enddate


######################################################################
# Wavegliders
######################################################################
# WG Tiny - All instruments combined into one file - one time coordinate
cl.wg_Tiny_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Waveglider/wgTiny/'
cl.wg_Tiny_files = [ 'wgTiny_Canon2015_Sep.nc'  ]
cl.wg_Tiny_parms = [ 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal',  'bb_470', 'bb_650', 'chl',
                    'beta_470', 'beta_650', 'pCO2_water', 'pCO2_air', 'pH', 'O2_conc' ]
cl.wg_Tiny_startDatetime = startdate
cl.wg_Tiny_endDatetime = enddate

# WG OA - All instruments combined into one file - one time coordinate
cl.wg_oa_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Waveglider/wgOA/'
cl.wg_oa_files = [ 'wgOA_Canon2015_Sep.nc'  ]
cl.wg_oa_parms = [ 'distance', 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal', 'O2_conc',
                   'O2_sat', 'beta_470', 'bb_470', 'beta_700', 'bb_700', 'chl', 'pCO2_water', 'pCO2_air', 'pH' ]
cl.wg_oa_startDatetime = startdate
cl.wg_oa_endDatetime = enddate

######################################################################
#  WESTERN FLYER: September 29 - Oct 5 (7 days)
######################################################################
# UCTD
cl.wfuctd_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Ships/Western_Flyer/uctd/'
cl.wfuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.wfuctd_files = [
                  'canon15m01.nc', 'canon15m02.nc',   
                  'canon15m03.nc', 'canon15m04.nc',   
                  'canon15m05.nc', 'canon15m06.nc', 'canon15m07.nc', 'canon15m08.nc', 'canon15m09.nc', 'canon15m10.nc',
                  'canon15m11.nc', 'canon15m12.nc',  
                  ]

# PCTD
cl.wfpctd_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Ships/Western_Flyer/pctd/'
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl' , 'oxygen']
cl.wfpctd_files = [
                  'canon15c01.nc', 'canon15c02.nc', 'canon15c03.nc', 'canon15c04.nc',  
                  'canon15c05.nc', 'canon15c06.nc', 'canon15c07.nc', 'canon15c08.nc',  
                  'canon15c09.nc', 'canon15c10.nc', 'canon15c11.nc', 'canon15c12.nc',  
                  'canon15c13.nc', 'canon15c14.nc', 'canon15c15.nc', 'canon15c16.nc',  
                  'canon15c17.nc', 'canon15c18.nc', 'canon15c19.nc', 'canon15c20.nc',  
                  'canon15c21.nc', 'canon15c22.nc', 'canon15c23.nc', 'canon15c24.nc',  
                  'canon15c25.nc',  
                  'canon15c26.nc', 'canon15c27.nc', 'canon15c28.nc', 'canon15c29.nc', 'canon15c30.nc',
                  'canon15c31.nc', 'canon15c32.nc', 'canon15c33.nc', 'canon15c34.nc', 'canon15c35.nc', 
                  'canon15c36.nc', 'canon15c37.nc', 'canon15c38.nc', 'canon15c39.nc', 'canon15c40.nc', 
                  'canon15c41.nc', 'canon15c42.nc', 'canon15c43.nc', 'canon15c44.nc', 'canon15c45.nc', 
                  'canon15c46.nc', 'canon15c47.nc', 'canon15c48.nc', 'canon15c49.nc', 'canon15c50.nc', 
                  'canon15c51.nc', 'canon15c52.nc', 'canon15c53.nc', 'canon15c54.nc', 'canon15c55.nc',
                  'canon15c56.nc', 'canon15c57.nc',   
                  ]

######################################################################
#  RACHEL CARSON: September 22-24 (265-xxx) Oct 12 - Oct 14
######################################################################
# UCTD
cl.rcuctd_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Ships/Rachel_Carson/uctd/'
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.rcuctd_files = [
                  '26515plm01.nc', '26615plm01.nc', '26715plm01.nc', 
                  '28215plm01.nc', '28515plm01.nc', '28615plm01.nc', '28715plm01.nc', 
                  ]

# PCTD
cl.rcpctd_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Ships/Rachel_Carson/pctd/'
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.rcpctd_files = [
                  '26515c01.nc', '26515c02.nc', '26515c03.nc',
                  '26615c01.nc', '26615c02.nc',
                  '26715c01.nc', '26715c02.nc', 
                  '28215c01.nc', '28215c02.nc', '28215c03.nc',
                  '28515c01.nc', '28515c02.nc',
                  '28615c01.nc', '28615c02.nc',
                  '28715c01.nc', '28715c02.nc', '28715c04.nc', ## note there is no 28715c03.nc
                  ]

#####################################################################
# JOHN MARTIN
#####################################################################
##cl.JMuctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Ships/Martin/uctd/' 
##cl.JMuctd_parms = ['TEMP', 'PSAL', 'turb_scufa', 'fl_scufa' ]
##cl.JMuctd_files = [ 'jhmudas_2013101.nc', 'jhmudas_2013102.nc', 'jhmudas_2013103.nc', 'jhmudas_2013911.nc', 'jhmudas_2013913.nc', 
##                    'jhmudas_2013916.nc', 'jhmudas_2013917.nc', 'jhmudas_2013919.nc', 'jhmudas_2013923.nc', 'jhmudas_2013930.nc', ]

##cl.JMpctd_base = cl.dodsBase + 'CANON_september2013/Platforms/Ships/Martin/pctd/' 
##cl.JMpctd_parms = ['TEMP', 'PSAL', 'xmiss', 'wetstar', 'oxygen' ]
##cl.JMpctd_files = [ 
##                    '25613JMC01.nc', '25613JMC02.nc', '25613JMC03.nc', '25613JMC04.nc', '25613JMC05.nc', 
##                    '26013JMC01.nc', '26013JMC02.nc', '26013JMC03.nc', '26013JMC04.nc', 
##                    '26213JMC01.nc', '26213JMC02.nc', '26213JMC03.nc', '26213JMC04.nc', '26213JMC05.nc', '26613JMC01.nc',
##                    '26613JMC02i1.nc', '26613JMC02.nc', '26613JMC03.nc', '27513JMC01.nc', '27513JMC02.nc', '27513JMC03.nc', 
##                    '27513JMC04.nc', '27513JMC05.nc', '27613JMC01.nc', '27613JMC02.nc', '27613JMC03.nc', '27613JMC04.nc',
##                  ]

######################################################################
#  MOORINGS
######################################################################
# Mooring M1 Combined file produced by DPforSSDS processing - for just the duration of the campaign
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/201507/'
cl.m1_files = [
                'OS_M1_20150729hourly_CMSTV.nc',
                'm1_hs2_20150730.nc',
              ]
cl.m1_parms = [
                'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
                'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
                'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR', 
                'bb470', 'bb676', 'fl676',
              ]
cl.m1_startDatetime = startdate
cl.m1_endDatetime = enddate

# Mooring 0A1
cl.oa1_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Moorings/OA1/'
cl.oa1_files = [
               'OA1_Canon2015_Sep.nc'
               ]
cl.oa1_parms = [
               'wind_dir', 'avg_wind_spd', 'atm_press', 'air_temp', 'water_temp',
               'sal', 'O2_conc', 'chl', 'pCO2_water', 'pCO2_air', 'pH',
              ]
cl.oa1_startDatetime = startdate
cl.oa1_endDatetime = enddate

# Mooring 0A2
cl.oa2_base = cl.dodsBase + 'CANON/2015_Sep/Platforms/Moorings/OA2/'
cl.oa2_files = [
               'OA2_Canon2015_Sep.nc'
               ]
cl.oa2_parms = [
               'wind_dir', 'avg_wind_spd', 'atm_press', 'air_temp', 'water_temp',
               'sal', 'O2_conc', 'chl', 'pCO2_water', 'pCO2_air', 'pH',
               ]
cl.oa2_startDatetime = startdate
cl.oa2_endDatetime = enddate

# ESP MOORINGS

#######################################################################################

###################################################################################################
# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/ 
#                                   
#   copied to local CANONSep2015 dir
###################################################################################################
##cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data/CANONSep2013')
##cl.subsample_csv_files = [
##'STOQS_CANON13_CARBON_GFF.csv', 'STOQS_CANON13_CHL_1U.csv', 'STOQS_CANON13_CHL_5U.csv', 'STOQS_CANON13_CHLA.csv',
##'STOQS_CANON13_CHL_GFF.csv', 'STOQS_CANON13_NO2.csv', 'STOQS_CANON13_NO3.csv', 'STOQS_CANON13_PHAEO_1U.csv',
##'STOQS_CANON13_PHAEO_5U.csv', 'STOQS_CANON13_PHAEO_GFF.csv', 'STOQS_CANON13_PO4.csv', 'STOQS_CANON13_SIO4.csv',

##'STOQS_25913RC_CHL_1U.csv', 'STOQS_25913RC_CHL_5U.csv', 'STOQS_25913RC_CHLA.csv', 'STOQS_25913RC_CHL_GFF.csv',
##'STOQS_25913RC_NO2.csv', 'STOQS_25913RC_NO3.csv', 'STOQS_25913RC_PHAEO_1U.csv', 'STOQS_25913RC_PHAEO_5U.csv',
##'STOQS_25913RC_PHAEO_GFF.csv', 'STOQS_25913RC_PO4.csv', 'STOQS_25913RC_SIO4.csv',

##'STOQS_26013RC_CHL_1U.csv', 'STOQS_26013RC_CHL_5U.csv', 'STOQS_26013RC_CHLA.csv', 'STOQS_26013RC_CHL_GFF.csv',
##'STOQS_26013RC_NO2.csv', 'STOQS_26013RC_NO3.csv', 'STOQS_26013RC_PHAEO_1U.csv', 'STOQS_26013RC_PHAEO_5U.csv',
##'STOQS_26013RC_PHAEO_GFF.csv', 'STOQS_26013RC_PO4.csv', 'STOQS_26013RC_SIO4.csv',

##'STOQS_26113RC_CHL_1U.csv', 'STOQS_26113RC_CHL_5U.csv', 'STOQS_26113RC_CHLA.csv', 'STOQS_26113RC_CHL_GFF.csv',
##'STOQS_26113RC_NO2.csv', 'STOQS_26113RC_NO3.csv', 'STOQS_26113RC_PHAEO_1U.csv', 'STOQS_26113RC_PHAEO_5U.csv',
##'STOQS_26113RC_PHAEO_GFF.csv', 'STOQS_26113RC_PO4.csv', 'STOQS_26113RC_SIO4.csv',

##'STOQS_27313RC_CHLA.csv',

##'STOQS_27413RC_CHLA.csv',

##'STOQS_27513RC_CHLA.csv', 'STOQS_27513RC_CHL_GFF.csv', 'STOQS_27513RC_NO2.csv', 'STOQS_27513RC_NO3.csv',
##'STOQS_27513RC_PHAEO_GFF.csv', 'STOQS_27513RC_PO4.csv', 'STOQS_27513RC_SIO4.csv',

##'STOQS_27613RC_CHLA.csv',
##                         ]


###################################################################################################################

# Execute the load
cl.process_command_line()

if cl.args.test:
    cl.loadL_662(stride=100) 

    ##cl.load_wg_tex(stride=10)
    ##cl.load_wg_oa(stride=10) 

    cl.loadDorado(stride=100)
    ##cl.loadDaphne(stride=100)
    ##cl.loadTethys(stride=100)

    ##cl.loadRCuctd(stride=10)
    ##cl.loadRCpctd(stride=10)
    ##cl.loadJMuctd(stride=10)
    ##cl.loadJMpctd(stride=10)
    ##cl.loadWFuctd(stride=10)   
    ##cl.loadWFpctd(stride=10)

    cl.loadM1(stride=10)

    ##cl.loadSubSamples()

elif cl.args.optimal_stride:

    cl.loadL_662(stride=2)

    ##cl.load_wg_tex(stride=2)
    ##cl.load_wg_oa(stride=2)

    cl.loadM1(stride=1)
    #cl.loadDorado(stride=2)
    ##cl.loadDaphne(stride=100)
    ##cl.loadTethys(stride=100)
    #cl.loadRCuctd(stride=2)
    #cl.loadRCpctd(stride=2)

    ##cl.loadSubSamples()

else:
    cl.stride = cl.args.stride

    '''cl.loadL_662()
    cl.load_wg_Tiny()
    ##cl.load_wg_tex()  ## no waveglider Tex in this campaign
    cl.load_wg_oa() 
    cl.loadM1()
    cl.load_oa1()   
    cl.load_oa2()  
    cl.loadDorado()
    cl.loadTethys()
    cl.loadDaphne()
    cl.loadMakai()
    cl.loadRCuctd()
    cl.loadRCpctd() 
    cl.loadWFuctd()   
    cl.loadWFpctd()'''
    cl.loadTethys()

    ##cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print("All Done.")

