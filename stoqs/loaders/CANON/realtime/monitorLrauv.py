#!/usr/bin/env python
__author__    = 'Mike McCann, Danelle Cline'
'''
Monitor the dods web site for new realtime hotspot or sbdlog data from LRAUVs and use
DAPloaders.py to load new data into the stoqs database.

Mike McCann
MBARI 12 March 2014
'''

import os
import sys
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))              # loaders is two dirs up
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))           # config is three dirs up
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../CANON/toNetCDF/"))            # for lrauvNc4ToNetcdf
import django
django.setup()

import DAPloaders
from CANON import CANONLoader
import logging
import lrauvNc4ToNetcdf
from datetime import datetime, timedelta
import re
import pydap
import pytz
import json
import webob

##from Contour import Contour
from thredds_crawler.crawl import Crawl
from coards import from_udunits
from loaders.CANON.toNetCDF.makeLRAUVNetCDFs import SCIENG_PARMS
from loaders.LRAUV.make_load_scripts import lrauvs
from stoqs.models import InstantPoint
from slacker import Slacker

from django.db.models import Max

class NoNewHotspotData(Exception):
    pass

  
class NcFileMissing(Exception):
    def __init__(self, value):
        self.nc4FileUrl = value
    def __str__(self):
        return repr(self.nc4FileUrl)
 
class ServerError(Exception):
    pass


class FileNotInYear(Exception):
    pass


class Make_netCDFs():
    logger = logging.getLogger('monitorLrauvLogger')
    fh = logging.StreamHandler()
    f = logging.Formatter("%(levelname)s %(asctime)sZ %(filename)s %(funcName)s():%(lineno)d %(message)s")
    fh.setFormatter(f)
    logger.addHandler(fh)
    logger.setLevel(logging.INFO)

    def getNcStartEnd(self, urlNcDap, timeAxisName):
        '''Find the lines in the html with the .nc file, then open it and read the start/end times
        return url to the .nc  and start/end as datetime objects.
        '''
        self.logger.debug('open_url on urlNcDap = %s', urlNcDap)
        df = pydap.client.open_url(urlNcDap)
        try:
            timeAxisUnits = df[timeAxisName].units
        except KeyError as e:
            self.logger.warning(e)
            raise ServerError("Can't read %s time axis from %s" % (timeAxisName, urlNcDap))

        if timeAxisUnits == 'seconds since 1970-01-01T00:00:00Z' or timeAxisUnits == 'seconds since 1970/01/01 00:00:00Z':
            timeAxisUnits = 'seconds since 1970-01-01 00:00:00'    # coards is picky

        try:
            startDatetime = from_udunits(df[timeAxisName][0][0].data, timeAxisUnits)
            endDatetime = from_udunits(df[timeAxisName][-1][0].data, timeAxisUnits)
        except pydap.exceptions.ServerError as e:
            self.logger.warning(e)
            raise ServerError("Can't read start and end dates of %s from %s" % (timeAxisUnits, urlNcDap))
        except webob.exc.HTTPError as e:
            self.logger.warning(e.comment)
            raise ServerError("Can't read start and end dates of %s from %s" % (timeAxisUnits, urlNcDap))
        except ValueError as e:
            self.logger.warning(e)
            raise ServerError("Can't read start and end dates of %s from %s" % (timeAxisUnits, urlNcDap)) 

        return startDatetime, endDatetime

    def processDecimated(self, args, pw, url, lastDatetime, start, end):
        '''
        Process decimated LRAUV data
        '''
        self.logger.debug('url = %s', url)

        if "sbd" in url:
            base_fname = '/'.join(url.split('/')[-3:]).split('.')[0]
        else:
            base_fname = '/'.join(url.split('/')[-2:]).split('.')[0]

        inFile = os.path.join(args.inDir, base_fname + '.nc4')
        outFile_i = os.path.join(args.outDir, base_fname + '_i.nc')
        startDatetime, endDatetime = self.getNcStartEnd(url, 'depth_time')
        self.logger.debug('startDatetime, endDatetime = %s, %s', startDatetime, endDatetime)
        self.logger.debug('lastDatetime = %s', lastDatetime)

        if start is not None and startDatetime < start :
            raise ServerError('startDatetime = %s out of bounds with user-defined startDatetime = %s' % (startDatetime, start))

        if end is not None and endDatetime > end :
            raise ServerError('endDatetime = %s out of bounds with user-defined endDatetime = %s' % (endDatetime, end))

        url_i = None

        if endDatetime > lastDatetime:
            self.logger.debug('Calling pw.processNc4FileDecimated with outFile_i = %s inFile = %s', outFile_i, inFile)
            try:
                if not args.debug:
                  pw.processNc4FileDecimated(url, inFile, outFile_i, args.parms, json.loads(args.groupparms), args.iparm)

            except TypeError:
                self.logger.warning('Problem reading data from %s', url)
                self.logger.warning('Assuming data are invalid and skipping')
            except IndexError:
                self.logger.warning('Problem interpolating data from %s', url)
            ##except KeyError:
            ##    raise ServerError("Key error - can't read parameters from %s" % (url))
            except ValueError:
                raise ServerError("Value error - can't read parameters from %s" % (url))

            else:
                url_i = url.replace('.nc4', '_i.nc')
        else:
            self.logger.debug('endDatetime <= lastDatetime. Assume that data from %s have already been loaded', url)

        return url_i, startDatetime, endDatetime

    def process_command_line(self):
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n\n'
        examples += 'Run on test database:\n'
        examples += sys.argv[0] + " -d  'Test Daphne hotspot data' -o /mbari/LRAUV/daphne/realtime/hotspotlogs -u 'http://elvis.shore.mbari.org/thredds/catalog/LRAUV/daphne/realtime/hotspotlogs/*.shore.nc4' -b 'stoqs_canon_apr2014_t' -c 'CANON-ECOHAB - March 2014 Test'\n"
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Read lRAUV data transferred over hotstpot and .nc file in compatible CF1-6 Discrete Sampling Geometry for for loading into STOQS',
                                         epilog=examples)
        parser.add_argument('-u', '--inUrl',action='store', help='url where hotspot/cell or other realtime processed data logs are. '
                                                                 ' must map to the same location as -o directory',
                            default='http://elvis.shore.mbari.org/thredds/catalog/LRAUV/tethys/realtime/sbdlogs/2015/201509/20150911T155447/.*shore.nc4$',required=False)
        parser.add_argument('-b', '--database',action='store', help='name of database to load hotspot data to', default='default',required=False)
        parser.add_argument('-c', '--campaign',action='store', help='name of campaign', default='April 2015 testing',required=False)
        parser.add_argument('-s', '--stride',action='store', help='amount to stride data before loading e.g. 10=every 10th point', default=1)
        parser.add_argument('-o', '--outDir', action='store', help='output directory to store interpolated .nc file or log contour output '
                                                                   '- can map to the same location as -u URL', default='/tmp/TestMonitorLrauv', required=False)
        parser.add_argument('-i', '--inDir', action='store', help='input directory  where raw .nc4 files are located '
                                                                  '- must map to the same location as -u URL',
                            default='/tmp/TestMonitorLrauv', required=True)
        parser.add_argument('--zoom', action='store', help='time window in hours to zoom animation',default=6, required=False)
        parser.add_argument('--overlap', action='store', help='time window in hours to overlap animation',default=5, required=False)
        parser.add_argument('--contourUrl', action='store', help='base url to store cross referenced contour plot resources',
                            default='http://dods.mbari.org/opendap/data/lrauv/stoqs/',required=False)
        parser.add_argument('--iparm', action='store', help='parameter to interpolate against; must exist in the -p/--parms list',
                            default='chlorophyll',required=False)
        parser.add_argument('--plotDotParmName', action='store', help='parameter to plot as colored dot in map; must exist in the -p/--parms list',
                            default='VTHI',required=False)
        parser.add_argument('--booleanPlotGroup', action='store', help='List of space separated boolean parameters to plot as symbols in the map against; must exist in the -p/--parms list',
                            default=['front'],required=False)
        parser.add_argument('--contourDir', action='store', help='output directory to store 24 hour contour output',
                            default='/tmp/TestMonitorLrauv/',required=False)
        parser.add_argument('--productDir', action='store', help='output directory to store 24 hour contour output for catalog in ODSS',
                            default='/tmp/TestMonitorLrauv/',required=False)
        parser.add_argument('-d', '--description', action='store', help='Brief description of experiment', default='Daphne Monterey data - April 2015')
        parser.add_argument('--latest24hr', action='store_true', help='create the latest 24 hour plot')
        parser.add_argument('--autoscale', action='store_true', help='autoscale each plot to 1 and 99 percentile',required=False,default=True)
        parser.add_argument('-a', '--append', action='store_true', help='Append data to existing Activity',required=False)
        parser.add_argument('--post', action='store_true', help='Post message to slack about new data. Disable this during initial database load or when debugging',required=False)
        parser.add_argument('--debug', action='store_true', help='Useful for debugging plots - does not allow data loading',required=False, default=False)
        parser.add_argument('--plotparms', action='store', help='List of space separated parameters to plot', nargs='*', default=
                                    ['front', 'VTHI', 'temperature', 'salinity', 'chlorophyll'])
        parser.add_argument('--parms', action='store', help='List of space separated (non group) parameters to load', nargs='*',
                            default= ['front', 'VTHI', 'temperature', 'salinity'])
        parser.add_argument('--groupparms', action='store',
                            help='List of JSON formatted parameter groups, variables and renaming of variables',
                            default='{' \
                                     '"CTD_NeilBrown": [ ' \
                                     '{ "name":"sea_water_salinity" , "rename":"salinity" }, ' \
                                     '{ "name":"bin_mean_sea_water_salinity" , "rename":"salinity" }, ' \
                                     '{ "name":"bin_median_sea_water_salinity" , "rename":"salinity" }, ' \
                                     '{ "name":"sea_water_temperature" , "rename":"temperature" }, ' \
                                     '{ "name":"bin_mean_sea_water_temperature" , "rename":"temperature" }, ' \
                                     '{ "name":"bin_median_sea_water_temperature" , "rename":"temperature" } ' \
                                     '],' \
                                     '"CTD_Seabird": [ ' \
                                     '{ "name":"sea_water_salinity" , "rename":"salinity" }, ' \
                                     '{ "name":"bin_mean_sea_water_salinity" , "rename":"salinity" }, ' \
                                     '{ "name":"bin_median_sea_water_salinity" , "rename":"salinity" }, ' \
                                     '{ "name":"sea_water_temperature" , "rename":"temperature" }, ' \
                                     '{ "name":"bin_mean_sea_water_temperature" , "rename":"temperature" }, ' \
                                     '{ "name":"bin_median_sea_water_temperature" , "rename":"temperature" } ' \
                                     '],' \
                                     '"WetLabsBB2FL": [ ' \
                                     '{ "name":"mass_concentration_of_chlorophyll_in_sea_water", "rename":"chlorophyll" }, ' \
                                     '{ "name":"bin_mean_mass_concentration_of_chlorophyll_in_sea_water", "rename":"chlorophyll" }, ' \
                                     '{ "name":"bin_median_mass_concentration_of_chlorophyll_in_sea_water", "rename":"chlorophyll" }, ' \
                                     '{ "name":"Output470", "rename":"bbp470" }, ' \
                                     '{ "name":"Output650", "rename":"bbp650" } ' \
                                     '],' \
                                     '"PAR_Licor": [ ' \
                                     '{ "name":"downwelling_photosynthetic_photon_flux_in_sea_water", "rename":"PAR" }, ' \
                                     '{ "name":"bin_mean_downwelling_photosynthetic_photon_flux_in_sea_water", "rename":"PAR" }, ' \
                                     '{ "name":"bin_median_downwelling_photosynthetic_photon_flux_in_sea_water", "rename":"PAR" } ' \
                                     '],' \
                                     '"VerticalTemperatureHomogeneityIndexCalculator" : [ ' \
                                     '{ "name":"vertical_temperature_homogeneity_index", "rename":"VTHI" } ' \
                                     '],' \
                                     '"ISUS" : [ ' \
                                     '{ "name":"mole_concentration_of_nitrate_in_sea_water", "rename":"nitrate" }, ' \
                                     '{ "name":"bin_mean_mole_concentration_of_nitrate_in_sea_water", "rename":"nitrate" }, ' \
                                     '{ "name":"bin_median_mole_concentration_of_nitrate_in_sea_water", "rename":"nitrate" } ' \
                                     '],' \
                                     '"Aanderaa_O2": [ ' \
                                     '{ "name":"mass_concentration_of_oxygen_in_sea_water", "rename":"oxygen" }, ' \
                                     '{ "name":"bin_mean_mass_concentration_of_oxygen_in_sea_water", "rename":"oxygen" }, ' \
                                     '{ "name":"bin_median_mass_concentration_of_oxygen_in_sea_water", "rename":"oxygen" } ' \
                                     '] }')
        parser.add_argument('-g', '--plotgroup', action='store', help='List of space separated parameters to plot', nargs='*', default=
                                ['VTHI', 'temperature', 'salinity', 'chlorophyll'])

        parser.add_argument('--start', action='store', help='Start time in YYYYMMDDTHHMMSS format', default='20150911T150000', required=False)
        parser.add_argument('--end', action='store', help='Start time in YYYYMMDDTHHMMSS format', default=None, required=False)
        parser.add_argument('--previous_month', action='store_true', help='Create files for the previous month')
        parser.add_argument('--current_month', action='store_true', help='Create files for the current month')
        parser.add_argument('-v', '--verbose', nargs='?', choices=[1,2], type=int, help='Turn on verbose output. 1: INFO, 2: DEBUG', const=1, default=0)

        self.args = parser.parse_args()

        if self.args.verbose == 2:
            self.logger.setLevel(logging.DEBUG)
        elif self.args.verbose == 1:
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.WARNING)

        args = parser.parse_args()
        return args

    # Checks if file was created within the last delay in minutes; return True if so
    def check_file(self, delay, old_filename, new_filename):
        if not os.path.isfile(old_filename):
            return False

        mod_time = datetime.fromtimestamp(os.stat(old_filename).st_mtime)
        if os.path.isfile(new_filename):
          if os.stat(old_filename).st_size == os.stat(new_filename).st_size:
            return False

        now = datetime.today()
        if now - mod_time > delay:
            return False
        else:
            return True


if __name__ == '__main__':
    mn = Make_netCDFs()
    args = mn.process_command_line()
    platformName = args.inUrl.split('/')[6]

    # Start back a week from now to load in old data
    lastDatetime = datetime.utcnow() - timedelta(days=7)

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

    if args.post:
        token = os.environ['SLACKTOKEN']
        slack = Slacker(token)

    # Assume that the database has already been created with description and terrain information, so use minimal arguments in constructor
    cl = CANONLoader(args.database, args.campaign)
    cl.dbAlias = args.database
    cl.campaignName = args.campaign

    # Get directory list from sites
    url, files = args.inUrl.rsplit('/',1)
    mn.logger.info("Crawling %s for %s files", url, files)
    skips = Crawl.SKIPS + [".*Courier*", ".*Express*", ".*Normal*, '.*Priority*", ".*.cfg$", ".*.js$", ".*.kml$",  ".*.log$"]
    c = Crawl(os.path.join(url, 'catalog.xml'), select=[files], debug=False, skip=skips)

    for d in c.datasets:
        mn.logger.debug('Found %s', d.id)

    urls = [s2.get("url") for d in c.datasets for s2 in d.services if s2.get("service").lower() == "opendap"]

    pw = lrauvNc4ToNetcdf.InterpolatorWriter()
    if mn.args.verbose == 2:
        pw.logger.setLevel(logging.DEBUG)
    elif mn.args.verbose == 1:
        pw.logger.setLevel(logging.INFO)
    else:
        pw.logger.setLevel(logging.WARNING)

    coord = {}

    for p in args.plotparms:
        coord[p] = {'time': p + '_time', 'latitude':  p +'_latitude', 'longitude':  p +'_longitude', 'depth':  p +'_depth'}

    title = 'MBARI LRAUV Survey - ' + platformName

    # Look in time order - oldest to newest and skip over data that doesn't include the starting year to speed up the loads 
    for url in sorted(urls):
        try:
            year_str = '{}'.format(start.year)
            mn.logger.info('Looking for {} in {}'.format(year_str, url))
            if year_str in url:
                ##breakpoint()
                (url_src, startDatetime, endDatetime) = mn.processDecimated(args, pw, url, lastDatetime, start, end)
            else:
                mn.logger.warn('{} not in search year'.format(url))
                continue
                ##raise FileNotInYear('{} not in search year'.format(url))
        except ServerError as e:
            mn.logger.warning(e)
            continue
        except lrauvNc4ToNetcdf.MissingCoordinate as e:
            mn.logger.warning(e)
            continue

        lastDatetime = endDatetime

        if url_src and args.database:
            mn.logger.info("Received new %s file ending at %s in %s", platformName, lastDatetime, url_src)
            aName = url_src.split('/')[-2] + '_' + url_src.split('/')[-1].split('.')[0]
            dataStartDatetime = None

            if args.append:
                core_aName = aName.split('_')[0]
                # Return datetime of last timevalue - if data are loaded from multiple activities return the earliest last datetime value
                dataStartDatetime = InstantPoint.objects.using(args.database).filter(activity__name__contains=core_aName).aggregate(Max('timevalue'))['timevalue__max']

            try:
                if not args.debug:
                    mn.logger.info("Instantiating Lrauv_Loader for url = %s", url_src)
                    lrauvLoad = DAPloaders.runLrauvLoader(cName = args.campaign,
                                                      cDesc = None,
                                                      aName = aName,
                                                      aTypeName = 'LRAUV mission',
                                                      pName = platformName,
                                                      pTypeName = 'auv',
                                                      pColor = cl.colors[platformName],
                                                      url = url_src,
                                                      parmList = args.plotparms,
                                                      dbAlias = args.database,
                                                      stride = int(args.stride),
                                                      startDatetime = startDatetime,
                                                      dataStartDatetime = dataStartDatetime,
                                                      endDatetime = endDatetime,
                                                      contourUrl = args.contourUrl,
                                                      auxCoords = coord,
                                                      timezone = 'America/Los_Angeles',
                                                      command_line_args = args)

                endDatetimeUTC = pytz.utc.localize(endDatetime)
                endDatetimeLocal = endDatetimeUTC.astimezone(pytz.timezone('America/Los_Angeles'))
                startDatetimeUTC = pytz.utc.localize(startDatetime)
                startDatetimeLocal = startDatetimeUTC.astimezone(pytz.timezone('America/Los_Angeles'))

                # format contour output file name replacing file extension with .png
                if args.outDir.startswith('/tmp'):
                    outFile = os.path.join(args.outDir, url_src.split('/')[-1].split('.')[0] + '.png')
                else:
                    if "sbd" in url_src:
                        outFile = os.path.join(args.outDir, '/'.join(url_src.split('/')[-3:]).split('.')[0]  + '.png')
                    else:
                        outFile = os.path.join(args.outDir, '/'.join(url_src.split('/')[-2:]).split('.')[0]  + '.png')

                mn.logger.debug('out file %s', outFile)
                contour = Contour(startDatetimeUTC, endDatetimeUTC, args.database, [platformName], args.plotgroup,
                                  title, outFile, args.autoscale, args.plotDotParmName, args.booleanPlotGroup)
                contour.run()

                # Replace netCDF file with png extension and that is the URL of the log
                logUrl = re.sub('\.nc$','.png', url_src)

                # Round the UTC time to the local time and do the query for the 24 hour period the log file falls into
                startDatetime = startDatetimeUTC
                startDateTimeLocal = startDatetime.astimezone(pytz.timezone('America/Los_Angeles'))
                startDateTimeLocal = startDateTimeLocal.replace(hour=0,minute=0,second=0,microsecond=0)
                startDateTimeUTC24hr = startDateTimeLocal.astimezone(pytz.utc)

                endDatetime = startDateTimeLocal
                endDateTimeLocal = endDatetime.replace(hour=23,minute=59,second=0,microsecond=0)
                endDateTimeUTC24hr = endDateTimeLocal.astimezone(pytz.utc)

                outFile = (args.contourDir + '/' + platformName  + '_log_' + startDateTimeUTC24hr.strftime('%Y%m%dT%H%M%S') +
                           '_' + endDateTimeUTC24hr.strftime('%Y%m%dT%H%M%S') + '.png')
                url = (args.contourUrl + platformName  + '_log_' + startDateTimeUTC24hr.strftime('%Y%m%dT%H%M%S') + '_' +
                       endDateTimeUTC24hr.strftime('%Y%m%dT%H%M%S') + '.png')


                if not os.path.exists(outFile) or args.debug:
                    mn.logger.debug('out file {} url: {}'.format(outFile, url))
                    c = Contour(startDateTimeUTC24hr, endDateTimeUTC24hr, args.database, [platformName], args.plotgroup, title,
                                outFile, args.autoscale, args.plotDotParmName, args.booleanPlotGroup)
                    c.run()

                if args.post:
                    message = 'LRAUV log data processed through STOQS workflow. Log <%s|%s plot> ' % (logUrl, aName)
                    slack.chat.post_message("#lrauvs", message)

            except DAPloaders.NoValidData:
                mn.logger.info("No measurements in this log set. Activity was not created as there was nothing to load.")

            except pydap.exceptions.ServerError as e:
                mn.logger.warning(e)

            except DAPloaders.ParameterNotFound as e:
                mn.logger.warning(e)

            except DAPloaders.InvalidSliceRequest as e:
                mn.logger.warning(e)

            except Exception as e:
                mn.logger.warning(e)
                continue

    # update last 24 hr plot when requested
    if args.latest24hr:
        try:
            mn.logger.info('Plotting latest 24 hours for platform %s ', platformName)
            # Plot the last 24 hours
            nowStart = datetime.utcnow() - timedelta(hours=24)
            nowEnd = datetime.utcnow()
            nowStartDateTimeUTC24hr = pytz.utc.localize(nowStart)
            nowEndDateTimeUTC24hr = pytz.utc.localize(nowEnd)

            outFileLatest = args.contourDir + '/' + platformName  + '_24h_latest.png'
            outFileLatestProduct = args.productDir + '/' + platformName  + '_log_last24hr.png'
            outFileLatestAnim = args.contourDir + '/' + platformName  + '_24h_latest_anim.gif'
            outFileLatestProductAnim = args.productDir + '/' + platformName  + '_log_last24hr_anim.gif'

            c = Contour(nowStartDateTimeUTC24hr, nowEndDateTimeUTC24hr, args.database, [platformName], args.plotgroup,
                        title, outFileLatest, args.autoscale, args.plotDotParmName, args.booleanPlotGroup)
            c.run()

            c = Contour(nowStartDateTimeUTC24hr, nowEndDateTimeUTC24hr, args.database, [platformName], args.plotgroup,
                        title, outFileLatestAnim, args.autoscale, args.plotDotParmName, args.booleanPlotGroup, True, args.zoom, args.overlap)
            c.run()

            if not outFileLatest.startswith('/tmp'):
                # copy to the atlas share that will get cataloged in ODSS
                delay = timedelta(minutes=5)
                if check_file(delay, outFileLatest, outFileLatestProduct):
                    cmd = r'cp %s %s' %(outFileLatest, outFileLatestProduct)
                    mn.logger.debug('%s', cmd)
                    os.system(cmd)

                # copy to the atlas share that will get cataloged in ODSS
                if check_file(delay, outFileLatestAnim, outFileLatestProductAnim):
                    cmd = r'cp %s %s' %(outFileLatestAnim, outFileLatestProductAnim)
                    mn.logger.debug('%s', cmd)
                    os.system(cmd)

        except Exception as e:
            mn.logger.warning(e)

    mn.logger.info('done')

