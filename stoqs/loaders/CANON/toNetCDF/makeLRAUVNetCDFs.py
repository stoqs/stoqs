#!/usr/bin/env python
__author__    = 'Danelel Cline'
__copyright__ = '2016'
__license__   = 'GPL v3'
__contact__   = 'dcline at mbari.org'

__doc__ = '''

Creates interpolated netCDF files for all LRAUV data; engineering and science data

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
import logging
import re
import pydap
import json
import netCDF4
import lrauvNc4ToNetcdf
import requests

from coards import to_udunits, from_udunits
from thredds_crawler.crawl import Crawl
from urllib.parse import urlparse
from datetime import datetime

# Set up global variables for logging output to STDOUT
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ServerError(Exception):
    pass

def process_command_line():
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n\n'
        examples += sys.argv[0] + " -i /mbari/LRAUV/daphne/missionlogs/2015/ -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/daphne/missionlogs/2015/.*.nc4$' -r '10S'"
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Read lRAUV data transferred over hotstpot and .nc file in compatible CF1-6 Discrete Sampling Geometry for for loading into STOQS',
                                         epilog=examples)
        parser.add_argument('-u', '--inUrl',action='store', help='url where processed data logs are.', default='http://elvis.shore.mbari.org/thredds/catalog/LRAUV/daphne/missionlogs/2015/.*nc4$',required=False)
        parser.add_argument('-i', '--inDir',action='store', help='url where processed data logs are.', default='/home/vagrant/LRAUV/daphne/missionlogs/2015/',required=False)
        parser.add_argument('-a', '--appendString',action='store', help='string to append to the data file created; used to differentiate engineering and science data files', default='sci',required=False)
        parser.add_argument('-r', '--resampleFreq', action='store', help='Optional resampling frequency string to specify how to resample interpolated results e.g. 2S=2 seconds, 5Min=5 minutes,H=1 hour,D=daily', default='10S')
        parser.add_argument('-p', '--parms', action='store', help='List of JSON formatted parameter groups, variables and renaming of variables', default= '{' \
           '"CTD_NeilBrown": [ ' \
           '{ "name":"sea_water_salinity" , "rename":"salinity" }, ' \
           '{ "name":"sea_water_temperature" , "rename":"temperature" } ' \
           '],' \
           '"WetLabsBB2FL": [ ' \
           '{ "name":"mass_concentration_of_chlorophyll_in_sea_water", "rename":"chlorophyll" }, ' \
           '{ "name":"Output470", "rename":"bbp470" }, ' \
           '{ "name":"Output650", "rename":"bbp650" } ' \
           '],' \
           '"PAR_Licor": [ ' \
           '{ "name":"downwelling_photosynthetic_photon_flux_in_sea_water", "rename":"PAR" } ' \
           '],' \
           '"ISUS" : [ ' \
           '{ "name":"mole_concentration_of_nitrate_in_sea_water", "rename":"nitrate" } ' \
           '],' \
           '"Aanderaa_O2": [ ' \
           '{ "name":"mass_concentration_of_oxygen_in_sea_water", "rename":"oxygen" } ' \
           '] }')
        parser.add_argument('--start', action='store', help='Start time in YYYYMMDDTHHMMSS format', default='20150930T000000', required=False)
        parser.add_argument('--end', action='store', help='Start time in YYYYMMDDTHHMMSS format', default='20151031T000000', required=False)
        parser.add_argument('--trackingdb', action='store_true', help='Attempt to use positions of <name>_ac from the Tracking Database (ODSS)')
        parser.add_argument('--nudge', action='store_true', help='Nudge the dead reckoned positions to meet the GPS fixes')

        args = parser.parse_args()

        return args

def find_urls(base, select, startdate, enddate):
    url = os.path.join(base, 'catalog.xml')
    skips = Crawl.SKIPS + [".*Courier*", ".*Express*", ".*Normal*, '.*Priority*", ".*.cfg$" ]
    u = urlparse(url)
    name, ext = os.path.splitext(u.path)
    if ext == ".html":
        u = urlparse(url.replace(".html", ".xml"))
    url = u.geturl()
    urls = []
    try:
        c = Crawl(url, select=[".*dlist"])

        # Crawl the catalogRefs:
        for dataset in c.datasets:

            try:
                # get the mission directory name and extract the start and ending dates
                dlist = os.path.basename(dataset.id)
                mission_dir_name = dlist.split('.')[0]
                dts = mission_dir_name.split('_')
                dir_start =  datetime.strptime(dts[0], '%Y%m%d')
                dir_end =  datetime.strptime(dts[1], '%Y%m%d')

                # if within a valid range, grab the valid urls
                if dir_start >= startdate and dir_end <= enddate:
                    catalog = '{}_{}/catalog.xml'.format(dir_start.strftime('%Y%m%d'), dir_end.strftime('%Y%m%d'))
                    c = Crawl(os.path.join(base, catalog), select=[select], skip=skips)
                    d = [s.get("url") for d in c.datasets for s in d.services if s.get("service").lower() == "opendap"]
                    for url in d:
                        urls.append(url)
            except Exception as ex:
                print("Error reading mission directory name {}".format(ex))

    except BaseException:
        print("Skipping {} (error parsing the XML XML)".format(url))

    return urls

def getNcStartEnd(inDir, urlNcDap, timeAxisName):
    '''Find the lines in the html with the .nc file, then open it and read the start/end times
    return url to the .nc  and start/end as datetime objects.
    '''
    logger.debug('open_url on urlNcDap = {}'.format(urlNcDap))

    try:
        base_in =  '/'.join(urlNcDap.split('/')[-3:])
        in_file = os.path.join(inDir, base_in) 
        df = netCDF4.Dataset(in_file, mode='r')
    except pydap.exceptions.ServerError as ex:
        logger.warning(ex)
        raise ServerError("Can't read {} time axis from {}".format(timeAxisName, urlNcDap))

    try:
        timeAxisUnits = df[timeAxisName].units
    except KeyError as ex:
        logger.warning(ex)
        raise ServerError("Can't read {} time axis from {}".format(timeAxisName, urlNcDap))

    if timeAxisUnits == 'seconds since 1970-01-01T00:00:00Z' or timeAxisUnits == 'seconds since 1970/01/01 00:00:00Z':
        timeAxisUnits = 'seconds since 1970-01-01 00:00:00'    # coards is picky

    try:
        startDatetime = from_udunits(df[timeAxisName][0].data, timeAxisUnits)
        endDatetime = from_udunits(df[timeAxisName][-1].data, timeAxisUnits)
    except pydap.exceptions.ServerError as ex:
        logger.warning(ex)
        raise ServerError("Can't read start and end dates of {} from {}".format(timeAxisUnits, urlNcDap))
    except ValueError as ex:
        logger.warning(ex)
        raise ServerError("Can't read start and end dates of {} from {}".format(timeAxisUnits, urlNcDap))

    return startDatetime, endDatetime


def processResample(pw, url_in, inDir, resample_freq, parms, rad_to_deg, appendString, args):
    '''
    Created resampled LRAUV data netCDF file
    '''
    url_o = None

    logger.debug('url = {}'.format(url_in))
    url_out = url_in.replace('.nc4', '_' + resample_freq + '_' + appendString + '.nc')
    base_in =  '/'.join(url_in.split('/')[-3:])
    base_out = '/'.join(url_out.split('/')[-3:])

    out_file = os.path.join(inDir,  base_out)
    in_file =  os.path.join(inDir,  base_in)

    try:
        if not os.path.exists(out_file):
            pw.processResampleNc4File(in_file, out_file, parms, resample_freq, rad_to_deg, args)
        else:
            logger.info(f"Not calling processResampleNc4File() for {out_file}: file exists")
    except TypeError as te:
        logger.warning('Problem reading data from {}'.format(url_in))
        logger.warning('Assuming data are invalid and skipping')
        logger.warning(te)
        raise te
    except IndexError as ie:
        logger.warning('Problem interpolating data from {}'.format(url_in))
        raise ie
    except KeyError:
        raise ServerError("Key error - can't read parameters from {}".format(url_in))

    url_o = url_out
    return url_o


if __name__ == '__main__':

    args = process_command_line()
    parms = ''

    # Check formatting of json arguments - this is easy to mess up
    try:
        parms = json.loads(args.parms)
    except Exception as e:
        logger.warning('Parameter argument invalid {}'.format(args.parms))
        exit(-1)

    # Unless start time defined, then start there
    if args.start is not None:
        dt = datetime.strptime(args.start, '%Y%m%dT%H%M%S')
        lastDatetime = dt
        start = dt
    else:
        start = None

    if args.end is not None:
        dt = datetime.strptime(args.end, '%Y%m%dT%H%M%S')
        end = dt
    else:
        end = None

    platformName = None

    # Url name for logs indicates what vehicle logs are being monitored; use this to determine the platform name
    d = re.match(r'.*tethys*',args.inUrl)
    if d:
        platformName = 'tethys'

    d = re.match(r'.*daphne*',args.inUrl)
    if d:
        platformName = 'daphne'

    d = re.match(r'.*makai*',args.inUrl)
    if d:
        platformName = 'makai'

    d = re.match(r'.*aku*',args.inUrl)
    if d:
        platformName = 'aku'

    d = re.match(r'.*opah*',args.inUrl)
    if d:
        platformName = 'opah'

    d = re.match(r'.*ahi*',args.inUrl)
    if d:
        platformName = 'ahi'

    # Get directory list from sites
    s = args.inUrl.rsplit('/',1)
    files = s[1]
    url = s[0]
    logger.info(f"Crawling {url} for {files} files to make {args.resampleFreq}_{args.appendString}.nc files")
	
    # Get possible urls with mission dates in the directory name that fall between the requested times
    all_urls = find_urls(url, files, start, end)
    urls = []

    for u in all_urls:
        try:
            startDatetime, endDatetime = getNcStartEnd(args.inDir, u, 'time_time')
        except Exception as e:
            logger.warn(str(e))
            continue

        logger.debug('startDatetime, endDatetime = {}, {}'.format(startDatetime, endDatetime))

        if start is not None and startDatetime <= start :
            logger.info('startDatetime = {} out of bounds with user-defined startDatetime = {}'.format(startDatetime, start))
            continue

        if end is not None and endDatetime >= end :
            logger.info('endDatetime = {} out of bounds with user-defined endDatetime = {}'.format(endDatetime, end))
            continue

        urls.append(u)

    pw = lrauvNc4ToNetcdf.InterpolatorWriter()

    # Look in time order - oldest to newest
    convert_radians = True
    for url in sorted(urls):
        try:
            processResample(pw, url, args.inDir, args.resampleFreq, parms, convert_radians, args.appendString, args)
        except ServerError as e:
            logger.warning(e)
            continue

