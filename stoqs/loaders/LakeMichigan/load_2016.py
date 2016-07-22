#!/usr/bin/env python
__author__    = 'Danelle Cline'
__copyright__ = '2016'
__license__   = 'GPL v3'
__contact__   = 'dcline at mbari.org'

__doc__ = '''

Master loader for LRAUV Lake Michigan 2016 experiment

Danelle Cline
MBARI 21 July 2016

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

from LakeMichigan import LakeMILoader
from loaders import FileNotFound
from thredds_crawler.crawl import Crawl
from thredds_crawler.etree import etree

cl = LakeMILoader('stoqs_michigan2016', 'Lake Michigan LRAUV Experiment 2016',
                    description = 'LRAUV 2016 Experiment in Lake Michigan',
                  )

# Set start and end dates for all loads from sources that contain data
# beyond the temporal bounds of the campaign
#
startdate = datetime.datetime(2016, 7, 24)      # Fixed start
enddate = datetime.datetime(2016, 8, 24)        # Fixed end


# default location of thredds and dods data:
cl.tdsBase = 'http://odss.mbari.org/thredds/'
cl.dodsBase = cl.tdsBase + 'dodsC/'

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

                    print 'Found mission directory ' + dts[0]
                    print 'Searching if within range %s and %s  %s %s' % (startdate, enddate, dir_start, dir_end)
                    catalog = ref.attrib['{http://www.w3.org/1999/xlink}href']
                    c = Crawl(os.path.join(base, catalog), select=[search_str], skip=skips)
                    d = [s.get("url") for d in c.datasets for s in d.services if s.get("service").lower() == "opendap"]
                    for url in d:
                        urls.append(url)
            except Exception as ex:
                print "Error reading mission directory name %s" % ex

    except BaseException:
        print "Skipping %s (error parsing the XML)" % url

    if not urls:
        raise FileNotFound('No urls matching "{}" found in {}'.format(search_str, os.path.join(base, 'catalog.html')))

    return urls

# Load netCDF files produced (binned, etc.) by Danelle Cline
# These binned files are created with the makeLRAUVNetCDFs.sh script in the
# toNetCDF directory. You must first edit and run that script once to produce
# the binned files before this will work

# Get directory list from thredds server
platforms = ['tethys']

for p in platforms:
    base =  'http://elvis64.shore.mbari.org:8080/thredds/catalog/LRAUV/' + p + '/missionlogs/2016/'
    dods_base = 'http://dods.mbari.org/opendap/data/lrauv/' + p + '/missionlogs/2016/'
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
    try:
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

    except FileNotFound:
        continue

# Execute the load
cl.process_command_line()

if cl.args.test:

    cl.loadTethys(stride=100)

else:
    cl.loadTethys()


print "All Done."


