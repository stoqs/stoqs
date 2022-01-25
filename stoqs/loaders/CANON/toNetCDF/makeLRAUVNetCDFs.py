#!/usr/bin/env python
__author__    = 'Danelel Cline'
__copyright__ = '2016'
__license__   = 'GPL v3'
__contact__   = 'dcline at mbari.org'

__doc__ = '''

Creates interpolated netCDF files for all LRAUV data; engineering and science data

Execute from cron on kraken like:
docker-compose run -u 1087 -T -v /dev/shm:/dev/shm -v /tmp:/tmp -v /mbari/LRAUV:/mbari/LRAUV stoqs stoqs/loaders/CANON/toNetCDF/makeLRAUVNetCDFs.py --trackingdb --nudge --start 20120901 --end 20121001

To debug:
docker-compose run -u 1087 --rm -v /dev/shm:/dev/shm -v /tmp:/tmp -v /mbari/LRAUV:/mbari/LRAUV stoqs stoqs/loaders/CANON/toNetCDF/makeLRAUVNetCDFs.py --trackingdb --nudge --start 20120901 --end 20121001

'''

import os
import sys
import calendar
import logging
import re
import pydap
import json
import netCDF4
import lrauvNc4ToNetcdf
import requests
import time

from argparse import ArgumentParser, RawTextHelpFormatter
from coards import to_udunits, from_udunits
from dateutil.relativedelta import relativedelta
from thredds_crawler.crawl import Crawl
from urllib.parse import urlparse
from datetime import datetime
from loaders.LRAUV.make_load_scripts import lrauvs

# Set up global variables for logging output to STDOUT

SCI_PARMS = {'/':           [{'name': 'concentration_of_colored_dissolved_organic_matter_in_sea_water',
                              'rename': 'colored_dissolved_organic_matter'}],
             'Aanderaa_O2': [{'name': 'mass_concentration_of_oxygen_in_sea_water',
                              'rename': 'oxygen'}],
             'CTD_NeilBrown': [{'name': 'sea_water_salinity', 'rename': 'salinity'},
                               {'name': 'sea_water_temperature', 'rename': 'temperature'}],
             'CTD_Seabird': [{'name': 'sea_water_salinity', 'rename': 'salinity'},
                             {'name': 'sea_water_temperature', 'rename': 'temperature'}],
             'ISUS': [{'name': 'mole_concentration_of_nitrate_in_sea_water',
                       'rename': 'nitrate'}],
             'PAR_Licor': [{'name': 'downwelling_photosynthetic_photon_flux_in_sea_water',
                            'rename': 'PAR'}],
             'WetLabsBB2FL': [{'name': 'mass_concentration_of_chlorophyll_in_sea_water',
                               'rename': 'chlorophyll'},
                              {'name': 'OutputChl', 'rename': 'chl'},
                              {'name': 'Output470', 'rename': 'bbp470'},
                              {'name': 'Output650', 'rename': 'bbp650'}],
             'WetLabsSeaOWL_UV_A': [{'name': 'concentration_of_chromophoric_dissolved_organic_matter_in_sea_water',
                                     'rename': 'chromophoric_dissolved_organic_matter'},
                                    {'name': 'mass_concentration_of_chlorophyll_in_sea_water',
                                     'rename': 'chlorophyll'},
                                    {'name': 'BackscatteringCoeff700nm',
                                     'rename': 'BackscatteringCoeff700nm'},
                                    {'name': 'VolumeScatCoeff117deg700nm',
                                     'rename': 'VolumeScatCoeff117deg700nm'},
                                    {'name': 'mass_concentration_of_petroleum_hydrocarbons_in_sea_water',
                                     'rename': 'petroleum_hydrocarbons'}]}

ENG_PARMS = {'BPC1': [{'name': 'platform_battery_charge',
                       'rename': 'health_platform_battery_charge'},
                      {'name': 'platform_battery_voltage',
                       'rename': 'health_platform_average_voltage'}],
             'BuoyancyServo': [{'name': 'platform_buoyancy_position',
                                'rename': 'control_inputs_buoyancy_position'}],
             'DeadReckonUsingMultipleVelocitySources': [{'name': 'fix_residual_percent_distance_traveled',
                                                         'rename': 'fix_residual_percent_distance_traveled_DeadReckonUsingMultipleVelocitySources'},
                                                        {'name': 'longitude',
                                                         'rename': 'pose_longitude_DeadReckonUsingMultipleVelocitySources'},
                                                        {'name': 'latitude',
                                                         'rename': 'pose_latitude_DeadReckonUsingMultipleVelocitySources'},
                                                        {'name': 'depth',
                                                         'rename': 'pose_depth_DeadReckonUsingMultipleVelocitySources'}],
             'DeadReckonUsingSpeedCalculator': [{'name': 'fix_residual_percent_distance_traveled',
                                                 'rename': 'fix_residual_percent_distance_traveled_DeadReckonUsingSpeedCalculator'},
                                                {'name': 'longitude',
                                                 'rename': 'pose_longitude_DeadReckonUsingSpeedCalculator'},
                                                {'name': 'latitude',
                                                 'rename': 'pose_latitude_DeadReckonUsingSpeedCalculator'},
                                                {'name': 'depth',
                                                 'rename': 'pose_depth_DeadReckonUsingSpeedCalculator'}],
             'ElevatorServo': [{'name': 'platform_elevator_angle',
                                'rename': 'control_inputs_elevator_angle'}],
             'MassServo': [{'name': 'platform_mass_position',
                            'rename': 'control_inputs_mass_position'}],
             'NAL9602': [{'name': 'time_fix', 'rename': 'fix_time'},
                         {'name': 'latitude_fix', 'rename': 'fix_latitude'},
                         {'name': 'longitude_fix', 'rename': 'fix_longitude'}],
             'Onboard': [{'name': 'platform_average_current',
                          'rename': 'health_platform_average_current'}],
             'RudderServo': [{'name': 'platform_rudder_angle',
                              'rename': 'control_inputs_rudder_angle'}],
             'ThrusterServo': [{'name': 'platform_propeller_rotation_rate',
                                'rename': 'control_inputs_propeller_rotation_rate'}]}

SCIENG_PARMS = {**SCI_PARMS, **ENG_PARMS}

REALTIME_SCIENG_PARMS = SCIENG_PARMS
for group, parmlist in REALTIME_SCIENG_PARMS.items():
    for parmdict in parmlist:
        for k, parm in parmdict.items():
            if k == 'name':
                if parm == 'sea_water_salinity':
                    REALTIME_SCIENG_PARMS[group].append({'name': f"bin_mean_{parm}", 'rename': f"bin_mean_{parm}"})
                    REALTIME_SCIENG_PARMS[group].append({'name': f"bin_median_{parm}", 'rename': f"bin_median_{parm}"})
                if parm == 'sea_water_temperature':
                    REALTIME_SCIENG_PARMS[group].append({'name': f"bin_mean_{parm}", 'rename': f"bin_mean_{parm}"})
                    REALTIME_SCIENG_PARMS[group].append({'name': f"bin_median_{parm}", 'rename': f"bin_median_{parm}"})
                if parm == 'mass_concentration_of_chlorophyll_in_sea_water':
                    REALTIME_SCIENG_PARMS[group].append({'name': f"bin_mean_{parm}", 'rename': f"bin_mean_{parm}"})
                    REALTIME_SCIENG_PARMS[group].append({'name': f"bin_median_{parm}", 'rename': f"bin_median_{parm}"})


class ServerError(Exception):
    pass

class Make_netCDFs():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    def process_command_line(self):
        examples = 'Examples:' + '\n\n'
        examples += sys.argv[0] + " -i /mbari/LRAUV/daphne/missionlogs/2015/ -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/daphne/missionlogs/2015/.*.nc4$' -r '10S'"
        parser = ArgumentParser(formatter_class=RawTextHelpFormatter,
                                description='Read lRAUV data transferred over hotstpot and .nc file in compatible CF1-6 Discrete Sampling Geometry for for loading into STOQS',
                                epilog=examples)
        parser.add_argument('-u', '--inUrl',action='store', help='url where processed data logs are. Will be constructed from --platform if not provided.')
        parser.add_argument('-i', '--inDir',action='store', help='url where processed data logs are. Will be constructed from --platform if not provided.')
        parser.add_argument('-a', '--appendString',action='store', help='string to append to the data file created; used to differentiate engineering and science data files',
                            choices=['scieng', 'sci', 'eng'], default='scieng')
        parser.add_argument('-r', '--resampleFreq', action='store', 
                            help='Optional resampling frequency string to specify how to resample interpolated results e.g. 2S=2 seconds, 5Min=5 minutes,H=1 hour,D=daily', default='2S')
        parser.add_argument('-p', '--parms', action='store', help='List of JSON formatted parameter groups, variables and renaming of variables. Will override default for --appendString.')
        parser.add_argument('--start', action='store', help='Start time in YYYYMMDDTHHMMSS format')
        parser.add_argument('--end', action='store', help='End time in YYYYMMDDTHHMMSS format')
        parser.add_argument('--clobber', action='store_true', help='Overwrite any existing output .nc files')
        parser.add_argument('--platform', action='store', help='Platform name: tethys, daphne, ahi, ...')
        parser.add_argument('--previous_month', action='store_true', help='Create files for the previous month')
        parser.add_argument('--current_month', action='store_true', help='Create files for the current month')
        parser.add_argument('--realtime', action='store_true', help='Processed realtime telemetered data rather that delayed mode log files')
        parser.add_argument('--remove_gps_outliers', action='store_true', help='Remove bad GPS fixes before nudging positions')
        parser.add_argument('-v', '--verbose', nargs='?', choices=[1,2,3], type=int, help='Turn on verbose output. 1: INFO, 2:DEBUG, 3:TDS Crawler', const=1, default=0)

        self.args = parser.parse_args()
        self.args.nudge = True
        self.args.trackingdb = True

        if self.args.verbose == 2:
            self.logger.setLevel(logging.DEBUG)
        elif self.args.verbose == 1:
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.WARNING)

    def assign_parms(self):
        '''Assign the parms dictionary accordingly. Set to parms associated 
        with appendString, override if --parms specified
        '''
        if self.args.appendString == 'scieng':
            parms = SCIENG_PARMS
        if self.args.appendString == 'sci':
            parms = SCI_PARMS
        if self.args.appendString == 'eng':
            parms = ENG_PARMS

        if self.args.parms:
            # Check formatting of json arguments - this is easy to mess up
            try:
                parms = json.loads(self.args.parms)
            except Exception as e:
                self.logger.warning('Parameter argument invalid {}'.format(self.args.parms))
                exit(-1)

        return parms

    def assign_dates(self):
        # Three possible options from command line
        if self.args.start and self.args.end:
            try:
                start = datetime.strptime(self.args.start, '%Y%m%dT%H%M%S')
            except ValueError:
                start = datetime.strptime(self.args.start, '%Y%m%d')
            try:
                end = datetime.strptime(self.args.end, '%Y%m%dT%H%M%S')
            except ValueError:
                end = datetime.strptime(self.args.end, '%Y%m%d')
            self.logger.info(f"Setting start and end dates for start and end arguments: {start}, {end}")

        elif self.args.previous_month:
            prev_mon = datetime.today() - relativedelta(months=1)
            start = datetime.strptime(f"{prev_mon.strftime('%Y%m')}01", '%Y%m%d')
            end = start + relativedelta(months=1)
            self.logger.info(f"Setting start and end dates for previous_month: {start}, {end}")

        elif self.args.current_month:
            curr_mon = datetime.today()
            start = datetime.strptime(f"{curr_mon.strftime('%Y%m')}01", '%Y%m%d')
            end = start + relativedelta(months=1)
            self.logger.info(f"Setting start and end dates for current_month: {start}, {end}")

        return start, end

    def assign_ins(self, start, end, platform):
        '''Default is to return inDir and inURL given platform and datetime parameters
        '''
        if self.args.realtime:
            if not self.args.inDir:
                self.inDir = f"/mbari/LRAUV/{platform}/realtime/sbdlogs/{start.year}"
            if not self.args.inUrl:
                self.inUrl = f"http://elvis.shore.mbari.org/thredds/catalog/LRAUV/{platform}/realtime/sbdlogs/{start.year}/.*shore.nc4"
        else:
            if not self.args.inDir:
                self.inDir = f"/mbari/LRAUV/{platform}/missionlogs/{start.year}"
            if not self.args.inUrl:
                self.inUrl = f"http://elvis.shore.mbari.org/thredds/catalog/LRAUV/{platform}/missionlogs/{start.year}/.*.nc4"

    def find_urls(self, base, select, startdate, enddate):
        cat_url = os.path.join(base, 'catalog.xml')
        u = urlparse(cat_url)
        name, ext = os.path.splitext(u.path)
        if ext == ".html":
            u = urlparse(cat_url.replace(".html", ".xml"))
        cat_url = u.geturl()
        urls = []

        if self.args.realtime:
            self.logger.info(f"Attempting to crawl {cat_url} for realtime shore.nc4 files")
            skips = Crawl.SKIPS + [".*Courier*", ".*Express*", ".*Normal*, '.*Priority*", ".*.cfg$", ".*.js$", ".*.kml$",  ".*.log$"]
            crawl_debug = False
            if self.args.verbose > 2:
                crawl_debug = True
            rt_cat = Crawl(cat_url, select=[".*shore.nc4"], skip=skips, debug=crawl_debug)

            for url in [s.get("url") for d in rt_cat.datasets for s in d.services if s.get("service").lower() == "opendap"]:
                dir_start = datetime.strptime(url.split('/')[-2], '%Y%m%dT%H%M%S')
                if startdate <= dir_start and dir_start <= enddate:
                    self.logger.debug(f"Adding url {url}")
                    urls.append(url)
        else:
            self.logger.debug(f"Attempting to Crawl {cat_url} looking for .dlist files")
            skips = Crawl.SKIPS + [".*Courier*", ".*Express*", ".*Normal*, '.*Priority*", ".*.cfg$" ]
            dlist_cat = Crawl(cat_url, select=[".*dlist"], skip=skips)

            self.logger.info(f"Crawling {cat_url} for {files} files to make {self.args.resampleFreq}_{self.args.appendString}.nc files")
            for dataset in dlist_cat.datasets:
                # get the mission directory name and extract the start and ending dates
                dlist = os.path.basename(dataset.id)
                mission_dir_name = dlist.split('.')[0]
                dts = mission_dir_name.split('_')
                dir_start =  datetime.strptime(dts[0], '%Y%m%d')
                dir_end =  datetime.strptime(dts[1], '%Y%m%d')

                # if within a valid range, grab the valid urls
                self.logger.debug(f"Checking if .dlist {dlist} is within {startdate} and {enddate}")
                if (startdate <= dir_start and dir_start <= enddate) or (startdate <= dir_end and dir_end <= enddate):
                    catalog = '{}_{}/catalog.xml'.format(dir_start.strftime('%Y%m%d'), dir_end.strftime('%Y%m%d'))
                    self.logger.debug(f"Crawling {os.path.join(base, catalog)}")
                    log_cat = Crawl(os.path.join(base, catalog), select=[select], skip=skips)
                    self.logger.debug(f"Getting opendap urls from datasets {log_cat.datasets}")
                    for url in [s.get("url") for d in log_cat.datasets for s in d.services if s.get("service").lower() == "opendap"]:
                        self.logger.debug(f"Adding url {url}")
                        urls.append(url)
        if not urls:
            self.logger.info("No URLs found.")

        return urls

    def validate_urls(self, potential_urls):
        urls = []
        for url in potential_urls:
            if self.args.realtime:
                try:
                    startDatetime, endDatetime = self.getNcStartEnd(url, 'depth_time')
                except (pydap.exceptions.ServerError, IndexError) as e:
                    self.logger.info(f"Failed to get start and end times from {url}: {e.__class__.__name__}: {e}")
                    continue
            else:
                try:
                    startDatetime, endDatetime = self.getNcStartEnd(url, 'time_time')
                    self.logger.debug('startDatetime, endDatetime = {}, {}'.format(startDatetime, endDatetime))
                except Exception as e:
                    # Write a message to the .log file for the expected output file so that
                    # lrauv-data-file-audit.sh can detect the problem
                    log_file = os.path.join(self.inDir, '/'.join(url.split('/')[9:]))
                    log_file = log_file.replace('.nc4', '_' + self.args.resampleFreq + '_' + self.args.appendString + '.log')

                    fh = logging.FileHandler(log_file, 'w+')
                    frm = logging.Formatter("%(levelname)s %(asctime)sZ %(filename)s %(funcName)s():%(lineno)d %(message)s")
                    fh.setFormatter(frm)
                    self.logger.addHandler(fh)
                    self.logger.warning(f"Can't get start and end date from .nc4: time_time not found in {url}")
                    self.logger.warning(f"{e}")
                    fh.close()
                    sh = logging.StreamHandler()
                    sh.setFormatter(frm)
                    self.logger.handlers = [sh]
                    continue

            if start is not None and startDatetime <= start :
                self.logger.info('startDatetime = {} out of bounds with user-defined startDatetime = {}'.format(startDatetime, start))
                continue

            if end is not None and endDatetime >= end :
                self.logger.info('endDatetime = {} out of bounds with user-defined endDatetime = {}'.format(endDatetime, end))
                continue

            urls.append(url)

        return urls

    def getNcStartEnd(self, urlNcDap, timeAxisName):
        '''Find the lines in the html with the .nc file, then open it and read the start/end times
        return url to the .nc  and start/end as datetime objects.
        '''
        self.logger.debug('open_url on urlNcDap = {}'.format(urlNcDap))

        base_in =  '/'.join(urlNcDap.split('/')[-3:])
        in_file = os.path.join(self.inDir, base_in) 
        df = netCDF4.Dataset(in_file, mode='r')

        timeAxisUnits = df[timeAxisName].units

        if timeAxisUnits == 'seconds since 1970-01-01T00:00:00Z' or timeAxisUnits == 'seconds since 1970/01/01 00:00:00Z':
            timeAxisUnits = 'seconds since 1970-01-01 00:00:00'    # coards is picky

        try:
            startDatetime = from_udunits(df[timeAxisName][0].data, timeAxisUnits)
            endDatetime = from_udunits(df[timeAxisName][-1].data, timeAxisUnits)
        except pydap.exceptions.ServerError as ex:
            self.logger.warning(ex)
            raise ServerError("Can't read start and end dates of {} from {}".format(timeAxisUnits, urlNcDap))
        except ValueError as ex:
            self.logger.warning(ex)
            raise ServerError("Can't read start and end dates of {} from {}".format(timeAxisUnits, urlNcDap))

        return startDatetime, endDatetime


    def processResample(self, pw, url_in, resample_freq, parms, rad_to_deg, appendString):
        '''
        Created resampled LRAUV data netCDF file
        '''
        url_o = None

        self.logger.debug('url = {}'.format(url_in))
        url_out = url_in.replace('.nc4', '_' + resample_freq + '_' + appendString + '.nc')
        base_in =  '/'.join(url_in.split('/')[-3:])
        base_out = '/'.join(url_out.split('/')[-3:])

        out_file = os.path.join(self.inDir,  base_out)
        in_file =  os.path.join(self.inDir,  base_in)

        try:
            if not os.path.exists(out_file) or self.args.clobber:
                # The trackingdb and nudge args are needed here via self.args
                pw.processResampleNc4File(in_file, out_file, parms, resample_freq, rad_to_deg, self.args)
            else:
                self.logger.info(f"Not calling processResampleNc4File() for {out_file}: file exists")
        except TypeError as te:
            self.logger.warning('Problem reading data from {}'.format(url_in))
            self.logger.warning('Assuming data are invalid and skipping')
            self.logger.warning(te)
            raise te
        except IndexError as ie:
            self.logger.warning('Problem interpolating data from {}'.format(url_in))
            raise ie
        except KeyError:
            raise ServerError("Key error - can't read parameters from {}".format(url_in))

        url_o = url_out
        return url_o


    def processDecimated(self, pw, url_in, start, end, current_log=False):
        '''
        Process realtime (sbdlog) LRAUV data
        '''
        self.logger.debug('url_in = %s', url_in)
        url_i = None

        base_fname = '/'.join(url_in.split('/')[-3:]).split('.')[0]
        inFile = os.path.join(self.inDir, base_fname + '.nc4')
        outFile_i = os.path.join(self.inDir, base_fname + '_i.nc')
        try:
            file_start, file_end = self.getNcStartEnd(url_in, 'depth_time')
            self.logger.debug('file_start, file_end = %s, %s', file_start, file_end)
        except (IndexError, ) as e:
            self.logger.info(f"Failed to get start and end times from {url_in}: {e.__class__.__name__}: {e}")
            return url_i, None, None

        # The renamed parameters to put into the shore_i.nc file, need 'depth' for interp parameter
        # - include all possible parms, but no coordiantes except depth
        parms = set()
        for group, parmlist in REALTIME_SCIENG_PARMS.items():
            for parmdict in parmlist:
                for k, parm in parmdict.items():
                    if k == 'name':
                        if 'latitude' in parm or 'longitude' in parm or 'time' in parm:
                            continue
                        parms.add(parm)
        parms = sorted(list(parms))

        if (start <= file_start and file_start <= end) or (start  <= file_end and file_end <= end):
            try:
                # Always overwrite the last (most current, potentially updating) file
                if not os.path.exists(outFile_i) or self.args.clobber or current_log:
                    if current_log:
                        mn.logger.info(f"current_log = {current_log}")
                    self.logger.debug('Calling pw.processNc4FileDecimated with outFile_i = %s inFile = %s', outFile_i, inFile)
                    pw.processNc4FileDecimated(url, inFile, outFile_i, parms, '2S', REALTIME_SCIENG_PARMS, 'depth')
                else:
                    self.logger.info(f"Not calling processNc4FileDecimated() for {outFile_i}: file exists")
            except (KeyError, TypeError, IndexError, ValueError, lrauvNc4ToNetcdf.MissingCoordinate) as e :
                self.logger.debug(f"Problem with: {url}")
                self.logger.info(f"Not creating {outFile_i}: {e.__class__.__name__}: {e}")
            else:
                url_i = url.replace('.nc4', '_i.nc')

        return url_i, file_start, file_end


if __name__ == '__main__':

    mn = Make_netCDFs()
    mn.process_command_line()
    parms = mn.assign_parms()

    if mn.args.platform:
        platforms = [mn.args.platform]
    else:
        platforms = lrauvs

    pw = lrauvNc4ToNetcdf.InterpolatorWriter()
    if mn.args.verbose == 2:
        pw.logger.setLevel(logging.DEBUG)
    elif mn.args.verbose == 1:
        pw.logger.setLevel(logging.INFO)
    else:
        pw.logger.setLevel(logging.WARNING)

    if mn.args.inUrl:
        convert_radians = True
        mn.inDir = '/mbari/' + '/'.join(mn.args.inUrl.split('/')[5:9])
        mn.processResample(pw, mn.args.inUrl, mn.args.resampleFreq, parms, convert_radians, mn.args.appendString)
        sys.exit()

    start, end = mn.assign_dates()
    if mn.args.realtime:
        for platform in platforms:
            mn.assign_ins(start, end, platform)
            url, files = mn.inUrl.rsplit('/', 1)
            potential_urls = mn.find_urls(url, files, start, end)
            urls = sorted(mn.validate_urls(potential_urls))
            for url in urls:
                current_log = False
                if url == urls[-1] or url == urls[-2]:
                    current_log = True
                mn.logger.info(f"Processing realtime file: {url}")
                url_src, startDatetime, endDatetime = mn.processDecimated(pw, url, start, end, current_log)
    else:
        for platform in platforms:
            mn.assign_ins(start, end, platform)
            url, files = mn.inUrl.rsplit('/', 1)
            potential_urls = mn.find_urls(url, files, start, end)
            urls = mn.validate_urls(potential_urls)

            convert_radians = True
            for url in sorted(urls):
                try:
                    mn.processResample(pw, url, mn.args.resampleFreq, parms, convert_radians, mn.args.appendString)
                except ServerError as e:
                    mn.logger.warning(e)
                    continue

    mn.logger.info(f"Done executing: {' '.join(sys.argv)}")
