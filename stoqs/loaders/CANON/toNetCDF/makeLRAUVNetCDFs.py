#!/usr/bin/env python
__author__ = 'dcline'


import os
import sys
import logging
import re
import pydap
import json
import lrauvNc4ToNetcdf
from coards import to_udunits, from_udunits
from thredds_crawler.crawl import Crawl
from datetime import datetime, timedelta

# Set up global variables for logging output to STDOUT
logger = logging.getLogger('monitorTethysHotSpotLogger')
fh = logging.StreamHandler()
f = logging.Formatter("%(levelname)s %(asctime)sZ %(filename)s %(funcName)s():%(lineno)d %(message)s")
fh.setFormatter(f)
logger.addHandler(fh)
logger.setLevel(logging.DEBUG)

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
        parser.add_argument('-u', '--inUrl',action='store', help='url where processed data logs are.', default='http://elvis.shore.mbari.org/thredds/catalog/LRAUV/daphne/missionlogs/2015/.*.nc4$',required=False)
        parser.add_argument('-i', '--inDir',action='store', help='url where processed data logs are.', default='/mbari/LRAUV/daphne/missionlogs/2015/',required=False)
        parser.add_argument('-a', '--appendString',action='store', help='string to append to the data file created; used to differentiate engineering and science data files', default='sci',required=True)
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
        parser.add_argument('--start', action='store', help='Start time in YYYYMMDDTHHMMSS format', default='20150518T000000', required=False)
        parser.add_argument('--end', action='store', help='Start time in YYYYMMDDTHHMMSS format', default=None, required=False)

        args = parser.parse_args()

        return args


def getNcStartEnd(urlNcDap, timeAxisName):
    '''Find the lines in the html with the .nc file, then open it and read the start/end times
    return url to the .nc  and start/end as datetime objects.
    '''
    logger.debug('open_url on urlNcDap = %s', urlNcDap)

    try:
        df = pydap.client.open_url(urlNcDap)
    except pydap.exceptions.ServerError as e:
        logger.warn(e)
        raise ServerError("Can't read %s time axis from %s" % (timeAxisName, urlNcDap))

    try:
        timeAxisUnits = df[timeAxisName].units
    except KeyError as e:
        logger.warn(e)
        raise ServerError("Can't read %s time axis from %s" % (timeAxisName, urlNcDap))

    if timeAxisUnits == 'seconds since 1970-01-01T00:00:00Z' or timeAxisUnits == 'seconds since 1970/01/01 00:00:00Z':
        timeAxisUnits = 'seconds since 1970-01-01 00:00:00'    # coards is picky

    try:
        startDatetime = from_udunits(df[timeAxisName][0][0], timeAxisUnits)
        endDatetime = from_udunits(df[timeAxisName][-1][0], timeAxisUnits)
    except pydap.exceptions.ServerError as e:
        logger.warn(e)
        raise ServerError("Can't read start and end dates of %s from %s" % (timeAxisUnits, urlNcDap))
    except ValueError as e:
        logger.warn(e)
        raise ServerError("Can't read start and end dates of %s from %s" % (timeAxisUnits, urlNcDap))

    return startDatetime, endDatetime


def processResample(pw, url_in, inDir, resample_freq, parms, rad_to_deg, appendString):
    '''
    Created resampled LRAUV data netCDF file
    '''
    url_o = None

    logger.debug('url = %s', url_in)
    url_out = url.replace('.nc4', '_' + resample_freq + '_' + appendString + '.nc')
    base_in =  '/'.join(url.split('/')[-3:])
    base_out = '/'.join(url_out.split('/')[-3:])

    out_file = os.path.join(inDir,  base_out)
    in_file =  os.path.join(inDir,  base_in)

    logger.debug('Calling pw.process with file = %s', in_file)

    try:
        pw.processResampleNc4File(in_file, out_file, parms, resample_freq, rad_to_deg)
    except TypeError as e:
        logger.warn('Problem reading data from %s', url)
        logger.warn('Assuming data are invalid and skipping')
        logger.warn(e)
        raise e
    except IndexError as e:
        logger.warn('Problem interpolating data from %s', url)
        raise e
    except KeyError as e:
        raise ServerError("Key error - can't read parameters from %s" % (url))
    except ValueError as e:
        raise ServerError("Value error - can't read parameters from %s" % (url))

    url_o = url_out
    return url_o


if __name__ == '__main__':

    args = process_command_line()
    parms = ''

    # Check formatting of json arguments - this is easy to mess up
    try:
        parms = json.loads(args.parms)
    except Exception as e:
        logger.warn('Parameter argument invalid %s' % args.parms)
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

    # Get directory list from sites
    s = args.inUrl.rsplit('/',1)
    files = s[1]
    url = s[0]
    logger.info("Crawling %s for %s files" % (url, files))

    skips = Crawl.SKIPS + ['.*cfg.*', '.*mat.*', '.*slate.*', '.*state.*', '.*sbd.*']

    #c = Crawl(os.path.join(url, 'catalog.xml'), select=[files], debug=True, skip=skips)
    c = Crawl(os.path.join(url, 'catalog.xml'), select=[files], debug=True)

    for d in c.datasets:
        logger.debug('Found %s' % d.id)

    all_urls = [s.get("url") for d in c.datasets for s in d.services if s.get("service").lower() == "opendap"]
    urls = []

    for u in all_urls:
        try:
            startDatetime, endDatetime = getNcStartEnd(u, 'depth_time')
        except Exception as e:
            continue

        logger.debug('startDatetime, endDatetime = %s, %s', startDatetime, endDatetime)

        if start is not None and startDatetime <= start :
            logger.info('startDatetime = %s out of bounds with user-defined startDatetime = %s' % (startDatetime, start))
            continue

        if end is not None and endDatetime >= end :
            logger.info('endDatetime = %s out of bounds with user-defined endDatetime = %s' % (endDatetime, end))
            continue

        urls.append(u)

    pw = lrauvNc4ToNetcdf.InterpolatorWriter()

    # Look in time order - oldest to newest
    convert_radians = True
    for url in sorted(urls):
        try:
            processResample(pw, url, args.inDir, args.resampleFreq, parms, convert_radians, args.appendString)
        except ServerError as e:
            logger.warn(e)
            continue
        except Exception as e:
            logger.warn(e)
            continue

