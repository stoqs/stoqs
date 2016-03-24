#!/usr/bin/env python
__author__    = 'Mike McCann,Duane Edgington,Reiko Michisaki'
__copyright__ = '2015'
__license__   = 'GPL v3'
__contact__   = 'duane at mbari.org'

__doc__ = '''

Master loader for all CANON off season activities in 2015

Mike McCann, Duane Edgington, Danelle Cline
MBARI 4 August 2015

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
import urllib2
import urlparse
import requests

parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)  # So that CANON is found

from CANON import CANONLoader
from thredds_crawler.crawl import Crawl
from thredds_crawler.etree import etree

cl = CANONLoader('stoqs_os2015', 'CANON-ECOHAB - Off Season 2015',
                    description = 'CANON Off Season 2015 Experiment in Monterey Bay',
                    x3dTerrains = {
                                    'http://dods.mbari.org/terrain/x3d/Monterey25_10x/Monterey25_10x_scene.x3d': {
                                        'position': '-2822317.31255 -4438600.53640 3786150.85474',
                                        'orientation': '0.89575 -0.31076 -0.31791 1.63772',
                                        'centerOfRotation': '-2711557.9403829873 -4331414.329506527 3801353.4691465236',
                                        'VerticalExaggeration': '10',
                                        'speed': '0.1',
                                    }
                    },
                    grdTerrain = os.path.join(parentDir, 'Monterey25.grd')
                  )

# Set start and end dates for all loads from sources that contain data 
# beyond the temporal bounds of the campaign
#
#startdate = datetime.datetime(2015, 7, 31)                 # Fixed start
startdate = datetime.datetime(2015, 6, 6)                 # Fixed start

#enddate = datetime.datetime(2015, 9, 30)                  # Fixed end
enddate = datetime.datetime(2015, 12, 31)                  # Fixed end. Extend "offseason" to end of year

# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'

#####################################################################
#  DORADO 
#####################################################################
# special location for dorado data
cl.dorado_base = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2015/netcdf/'
cl.dorado_files = [
                   'Dorado389_2015_132_04_132_04_decim.nc',
                   'Dorado389_2015_148_01_148_01_decim.nc',
                   'Dorado389_2015_156_00_156_00_decim.nc',
                                   ]
cl.dorado_parms = [ 'temperature', 'oxygen', 'nitrate', 'bbp420', 'bbp700',
                    'fl700_uncorr', 'salinity', 'biolume', 'rhodamine' ]

#####################################################################
#  LRAUV 
#####################################################################
def find_urls(base, search_str):
    INV_NS = "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
    url = os.path.join(base, 'catalog.xml')
    print "Crawling: %s" % url
    skips = Crawl.SKIPS + [".*Courier*", ".*Express*", ".*Normal*, '.*Priority*", ".*.cfg$" ]
    u = urlparse.urlsplit(url)
    name, ext = os.path.splitext(u.path)
    if ext == ".html":
        u = urlparse.urlsplit(url.replace(".html", ".xml"))
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
                print "Error reading mission directory name %s" % ex

    except BaseException:
        print "Skipping %s (error parsing the XML)" % url

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
# cl.l_662_base = 'http://www.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_base = 'http://legacy.cencoos.org/thredds/dodsC/gliders/Line66/'
cl.l_662_files = [ 'OS_Glider_L_662_20150813_TS.nc' ]
# OS_Glider_L_662_20150813_TS.nc most recent deployment
cl.l_662_parms = ['TEMP', 'PSAL', 'FLU2']
cl.l_662_startDatetime = startdate
cl.l_662_endDatetime = enddate

# NPS_29
#cl.nps29_base = 'http://www.cencoos.org/thredds/dodsC/gliders/Line66/'
#cl.nps29_files = [ 'OS_Glider_NPS_G29_20140930_TS.nc' ]
cl.nps29_parms = ['TEMP', 'PSAL']
cl.nps29_startDatetime = startdate
cl.nps29_endDatetime = enddate

# UCSC_294
#cl.ucsc294_base = 'http://data.ioos.us/gliders/thredds/dodsC/deployments/mbari/UCSC294-20150430T2218/'
#cl.ucsc294_files = [ 'UCSC294-20150430T2218.nc3.nc' ]
#cl.ucsc294_parms = ['TEMP', 'PSAL']
#cl.ucsc294_startDatetime = startdate
#cl.ucsc294_endDatetime = enddate

# UCSC_260
#cl.ucsc260_base = 'http://data.ioos.us/gliders//thredds/dodsC/deployments/mbari/UCSC260-20150520T0000/'
#cl.ucsc260_files = [ 'UCSC260-20150520T0000.nc3.nc'  ]
#cl.ucsc260_parms = ['TEMP', 'PSAL']
#cl.ucsc260_startDatetime = startdate
#cl.ucsc260_endDatetime = enddate


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
cl.wg_Tiny_base = cl.dodsBase + 'CANON/2015_OffSeason/Platforms/Waveglider/wgTiny/'
cl.wg_Tiny_files = [ 
                     'SV3_20150611_QC.nc',
                     'SV3_20151019.nc',    # starts after end of Fall 2015 campaign
                   ]

cl.wg_Tiny_parms = [ 'wind_dir', 'avg_wind_spd', 'max_wind_spd', 'atm_press', 'air_temp', 'water_temp', 'sal',  'bb_470', 'bb_650', 'chl',
                    'beta_470', 'beta_650', 'pCO2_water', 'pCO2_air', 'pH', 'O2_conc' ]
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
#  WESTERN FLYER: not in this cruise
######################################################################
# UCTD
cl.wfuctd_base = cl.dodsBase + 'CANON/2015_May/Platforms/Ships/Western_Flyer/uctd/'
cl.wfuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.wfuctd_files = [
 
                  ]

# PCTD
cl.wfpctd_base = cl.dodsBase + 'CANON/2014_Sep/Platforms/Ships/Western_Flyer/pctd/'
cl.wfpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl' , 'oxygen']
cl.wfpctd_files = [
                  ]

######################################################################
#  RACHEL CARSON: May 2015 -- 
######################################################################
# UCTD
cl.rcuctd_base = cl.dodsBase + 'CANON/2015_OffSeason/Platforms/Ships/Rachel_Carson/uctd/'
cl.rcuctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'wetstar' ]
cl.rcuctd_files = [
                 '18815plm01.nc',
                 '21515plm01.nc',
                 '23715plm01.nc',
                  ]

# PCTD
cl.rcpctd_base = cl.dodsBase + 'CANON/2015_OffSeason/Platforms/Ships/Rachel_Carson/pctd/'
cl.rcpctd_parms = [ 'TEMP', 'PSAL', 'xmiss', 'ecofl', 'oxygen' ]
cl.rcpctd_files = [
                  '18815c01.nc', '18815c02.nc', '18815c03.nc',
                  '21515c01.nc', '21515c02.nc', '21515c03.nc', 
                  '23715c01.nc', '23715c02.nc', '23715c03.nc',
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
#  MOORINGS May 2015
######################################################################
# Mooring M1 Combined file produced by DPforSSDS processing - for just the duration of the campaign
# M1 had a turnaround on July 29, 2015
# http://dods.mbari.org/opendap/hyrax/data/ssdsdata/deployments/m1/201507/OS_M1_20150729hourly_CMSTV.nc
cl.m1_base = 'http://dods.mbari.org/opendap/data/ssdsdata/deployments/m1/201507/'
cl.m1_files = [
                'OS_M1_20150729hourly_CMSTV.nc'
              ]
cl.m1_parms = [
                'eastward_sea_water_velocity_HR', 'northward_sea_water_velocity_HR',
                'SEA_WATER_SALINITY_HR', 'SEA_WATER_TEMPERATURE_HR', 'SW_FLUX_HR', 'AIR_TEMPERATURE_HR',
                'EASTWARD_WIND_HR', 'NORTHWARD_WIND_HR', 'WIND_SPEED_HR'
              ]

cl.m1_startDatetime = startdate
cl.m1_endDatetime = enddate

# Mooring 0A1
cl.oa1_base = cl.dodsBase + 'CANON/2015_OffSeason/Platforms/Moorings/OA1/'
cl.oa1_files = [
               'OA1_Canon2015_OffSeason.nc'
               ]
cl.oa1_parms = [
               'wind_dir', 'avg_wind_spd', 'atm_press', 'air_temp', 'water_temp',
               'sal', 'O2_conc', 'chl', 'pCO2_water', 'pCO2_air', 'pH',
              ]
cl.oa1_startDatetime = startdate
cl.oa1_endDatetime = enddate

# Mooring 0A2
cl.oa2_base = cl.dodsBase + 'CANON/2015_OffSeason/Platforms/Moorings/OA2/'
cl.oa2_files = [
               'OA2_Canon2015_OffSeason.nc'
               ]
cl.oa2_parms = [
               'wind_dir', 'avg_wind_spd', 'atm_press', 'air_temp', 'water_temp',
               'sal', 'O2_conc', 'chl', 'pCO2_water', 'pCO2_air', 'pH',
               ]
cl.oa2_startDatetime = startdate
cl.oa2_endDatetime = enddate

#######################################################################################
# ESP MOORINGS
#######################################################################################
##cl.bruce_moor_base = cl.dodsBase + 'CANON_september2013/Platforms/Moorings/ESP_Bruce/NetCDF/'
##cl.bruce_moor_files = ['Bruce_ctd.nc']
##cl.bruce_moor_parms = [ 'TEMP','PSAL','chl','xmiss','oxygen','beamc',
##                   ]
##cl.bruce_moor_startDatetime = startdate
##cl.bruce_moor_endDatetime = enddate

##cl.mack_moor_base = cl.dodsBase + 'CANON_september2013/Platforms/Moorings/ESP_Mack/NetCDF/'
##cl.mack_moor_files = ['Mack_ctd.nc']
##cl.mack_moor_parms = [ 'TEMP','PSAL','chl','xmiss','oxygen','beamc',
##                   ]
##cl.mack_moor_startDatetime = startdate
##cl.mack_moor_endDatetime = enddate

###################################################################################################
# SubSample data files from /mbari/BOG_Archive/ReportsForSTOQS/ 
#                                   18815 and 21515
#   copied to local BOG_Data/CANON_OS2105 dir
###################################################################################################
cl.subsample_csv_base = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'BOG_Data/CANON_OS2015/')
cl.subsample_csv_files = [
    'STOQS_18815_CARBON_GFF.csv', 'STOQS_18815_CHLA.csv', 'STOQS_18815_CHL_1U.csv', 'STOQS_18815_CHL_5U.csv',
    'STOQS_18815_CHL_GFF.csv', 'STOQS_18815_NO2.csv', 'STOQS_18815_NO3.csv', 'STOQS_18815_PHAEO_1U.csv',
    'STOQS_18815_PHAEO_5U.csv', 'STOQS_18815_PHAEO_GFF.csv', 'STOQS_18815_PO4.csv', 'STOQS_18815_SIO4.csv',

    'STOQS_21515_CARBON_GFF.csv', 'STOQS_21515_CHLA.csv', 'STOQS_21515_CHL_1U.csv', 'STOQS_21515_CHL_5U.csv',
    'STOQS_21515_CHL_GFF.csv', 'STOQS_21515_NO2.csv', 'STOQS_21515_NO3.csv', 'STOQS_21515_PHAEO_1U.csv',
    'STOQS_21515_PHAEO_5U.csv', 'STOQS_21515_PHAEO_GFF.csv','STOQS_21515_PO4.csv', 'STOQS_21515_SIO4.csv',

                          ]

###################################################################################################################

# Execute the load 
cl.process_command_line()

if cl.args.test:

    cl.loadL_662(stride=100) 
    ##cl.load_NPS29(stride=10)
    #cl.load_UCSC294(stride=10) 
    #cl.load_UCSC260(stride=10)

    ##cl.load_wg_tex(stride=10)
    ##cl.load_wg_oa(stride=10)
    cl.load_wg_Tiny(stride=10)

    ##cl.loadDorado(stride=100)
    #cl.loadDaphne(stride=100)
    #cl.loadTethys(stride=100)
    #cl.loadMakai(stride=100)

    cl.loadRCuctd(stride=10)
    cl.loadRCpctd(stride=10)
    ##cl.loadJMuctd(stride=10)
    ##cl.loadJMpctd(stride=10)
    ##cl.loadWFuctd(stride=10)   
    ##cl.loadWFpctd(stride=10)

    cl.loadM1(stride=5)

    ##cl.loadBruceMoor(stride=10)
    ##cl.loadMackMoor(stride=10)

    cl.loadSubSamples()

elif cl.args.optimal_stride:

    cl.loadL_662(stride=2) 
    ##cl.load_NPS29(stride=2) 
    cl.load_wg_Tiny(stride=2)
    cl.loadM1(stride=1)
    ##cl.loadDorado(stride=2)
    cl.loadRCuctd(stride=2)
    cl.loadRCpctd(stride=2)

    cl.loadSubSamples()

else:
    cl.stride = cl.args.stride

    cl.loadL_662()
    ##cl.load_NPS29()
    ##cl.load_UCSC294() 
    ##cl.load_UCSC260()
    cl.load_wg_Tiny()
    cl.loadM1()
    cl.load_oa1()
    cl.load_oa2()
    ##cl.loadDorado()
    #cl.loadDaphne()
    #cl.loadTethys()
    cl.loadMakai()
    cl.loadRCuctd()
    cl.loadRCpctd()
    ##cl.loadWFuctd()   
    ##cl.loadWFpctd()

    cl.loadSubSamples()

# Add any X3D Terrain information specified in the constructor to the database - must be done after a load is executed
cl.addTerrainResources()

print "All Done."

 
