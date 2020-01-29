#!/usr/bin/env python
__author__    = 'Mike McCann, Danelle Cline'
'''
Monitors messages from the Pusher API  for new realtime cell or sbdlog data from LRAUVs.
Use DAPloaders.py to load new data into the stoqs database and posts messages to Slack
when new data is available.

Danelle Cline
MBARI 5 September 2018
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
import re
import pydap
import pysher
import pytz
import json
import time
import queue
from threading import Thread

##from Contour import Contour
from coards import from_udunits
from stoqs.models import InstantPoint
from slacker import Slacker

from django.db.models import Max

# Set up global variables for logging output to STDOUT
logger = logging.getLogger('monitorLrauvEventsLogger')
fh = logging.StreamHandler()
f = logging.Formatter("%(levelname)s %(asctime)sZ %(filename)s %(funcName)s():%(lineno)d %(message)s")
fh.setFormatter(f)
logger.addHandler(fh)
logger.setLevel(logging.DEBUG)

class NoNewHotspotData(Exception):
    pass

class NcFileMissing(Exception):
    def __init__(self, value):
        self.nc4FileUrl = value
    def __str__(self):
        return repr(self.nc4FileUrl)

class ServerError(Exception):
    pass

class IterableQueue():
    def __init__(self,source_queue):
            self.source_queue = source_queue
    def __iter__(self):
        while True:
            try:
               yield self.source_queue.get_nowait()
            except queue.Empty:
               return

class Job: 
    def __init__(self, full_path, url_src):
        self.full_path = full_path
        self.url_src = url_src
        self.activity_name = url_src.split('/')[-2] + '_' + url_src.split('/')[-1].split('.')[0]
        print('New job: {} {}'.format(full_path, url_src))
        return
  
class Loader(Thread):
    '''
    Manages converting and loading nc files into STOQS. Create one of these per each vehicle.
    '''
    def __init__(self, vehicle, slack, args):
        Thread.__init__(self)
        self.q = queue.Queue(maxsize=0)
        self.vehicle = vehicle
        self.slack = slack
        self.args = args
        self.pw = lrauvNc4ToNetcdf.InterpolatorWriter()
        # Assume that the database has already been created with description and terrain information, 
        # so use minimal arguments in constructor
        self.cl = CANONLoader(args.database, args.campaign)
        self.cl.dbAlias = args.database
        self.cl.campaignName = args.campaign

    def put(self, job):
        found = False
        # only place jobs in the queue with unique URLs
        for j in IterableQueue(self.q):
            if job.url_src in j.url_src:
                found = True
        if not found:
            self.q.put(job)

    def run(self):
        while True:
            if not self.q.empty():
                job = self.q.get()
                self.q.task_done()
                print('===>loading {}'.format(job.full_path))
                try:
                    url_dest, start_date, end_date = self.load(job)
                    # if last item in the queue, update animations 
                    if self.q.empty():
                        print('===> update animations {}'.format(url_dest))
                        log_url = re.sub('\.nc$', '.png', url_dest)

                        try:
                          if self.update(start_date, end_date, url_dest) and self.slack:
                            print('==========================> posting to slack')
                            message = 'LRAUV log data loaded into STOQS <{} plot|{}> '.format(log_url, job.activity_name)
                            print(message)
                            # self.slack.chat.post_message("#lrauvs", message)
                        except Exception as e:
                            logger.warning(e)
                            print('==========================> posting to slack')
                            message = 'LRAUV log data loaded into STOQS <{}> '.format(job.activity_name)
                            print(message)
                            # self.slack.chat.post_message("#lrauvs", message)
                          # self.slack.chat.post_message("#lrauvs", message)
                except ServerError as e:
                    logger.warning(e)
                    continue
                except Exception as e:
                    logger.warning(e)
                    continue
            else:
                time.sleep(1)

    def update(self, start_date, end_date, url_dest):
        try:

          endDatetimeUTC = pytz.utc.localize(end_date)
          startDatetimeUTC = pytz.utc.localize(start_date)

          # format contour output file name replacing file extension with .png
          if "sbd" in url_dest:
            outFile = os.path.join(self.args.outDir, '/'.join(url_dest.split('/')[-3:]).split('.')[0] + '.png')
          else:
            outFile = os.path.join(self.args.outDir, '/'.join(url_dest.split('/')[-2:]).split('.')[0] + '.png')

          title = 'MBARI LRAUV Survey - ' + self.vehicle

          logger.debug('out file {}'.format(outFile))
          contour = Contour(startDatetimeUTC, endDatetimeUTC, self.args.database, [self.vehicle], self.args.plotgroup,
                            title, outFile, self.args.autoscale, self.args.plotDotParmName, self.args.booleanPlotGroup)
          contour.run()

          # Round the UTC time to the local time and do the query for the 24 hour period the log file falls into
          startDatetime = startDatetimeUTC
          startDateTimeLocal = startDatetime.astimezone(pytz.timezone('America/Los_Angeles'))
          startDateTimeLocal = startDateTimeLocal.replace(hour=0, minute=0, second=0, microsecond=0)
          startDateTimeUTC24hr = startDateTimeLocal.astimezone(pytz.utc)

          endDatetime = startDateTimeLocal
          endDateTimeLocal = endDatetime.replace(hour=23, minute=59, second=0, microsecond=0)
          endDateTimeUTC24hr = endDateTimeLocal.astimezone(pytz.utc)

          outFile = (self.args.contourDir + '/' + self.vehicle + '_log_' + startDateTimeUTC24hr.strftime('%Y%m%dT%H%M%S') +
                     '_' + endDateTimeUTC24hr.strftime('%Y%m%dT%H%M%S') + '.png')
          url = (self.args.contourUrl + self.vehicle + '_log_' + startDateTimeUTC24hr.strftime('%Y%m%dT%H%M%S') + '_' +
                 endDateTimeUTC24hr.strftime('%Y%m%dT%H%M%S') + '.png')

          logger.debug('out file {} url: {}'.format(outFile, url))
          c = Contour(startDateTimeUTC24hr, endDateTimeUTC24hr, self.args.database, [self.vehicle], self.args.plotgroup, title,
                      outFile, self.args.autoscale, self.args.plotDotParmName, self.args.booleanPlotGroup)
          c.run()

          return True

        except Exception as ex:
            logger.warning(ex)

        return False

    def get_times(self, url):
        '''Find the lines in the html with the .nc file, then open it and read the start/end times
        return url to the .nc  and start/end as datetime objects.
        '''
        logger.debug('open_url on url = {}'.format(url))
        df = pydap.client.open_url(url)
        time_axis_name = 'Time'
        try:
            time_units = df[time_axis_name].units
        except KeyError as e:
            logger.warning(e)
            raise ServerError("Can't read {} time axis from {}".format(time_axis_name, url))

        if time_units == 'seconds since 1970-01-01T00:00:00Z' or time_units == 'seconds since 1970/01/01 00:00:00Z':
            time_units = 'seconds since 1970-01-01 00:00:00'  # coards is picky

        try:
            start = from_udunits(df[time_axis_name][0][0].data, time_units)
            end = from_udunits(df[time_axis_name][-1][0].data, time_units)
        except pydap.exceptions.ServerError as e:
            logger.warning(e)
            raise ServerError("Can't read start and end dates of %s from %s" % (time_units, url))
        except ValueError as e:
            logger.warning(e)
            raise ServerError("Can't read start and end dates of %s from %s" % (time_units, url))

        return start, end

    def get_bounds(self, url, timeAxisName):
        '''Find the lines in the html with the .nc file, then open it and read the start/end times
        return url to the .nc  and start/end as datetime objects.
        '''
        logger.debug('open_url on url = {}'.format(url))
        df = pydap.client.open_url(url)
        try:
            time_units = df[timeAxisName].units
        except KeyError as e:
            logger.warning(e)
            raise ServerError("Can't read {} time axis from {}".format(timeAxisName, url))

        if time_units == 'seconds since 1970-01-01T00:00:00Z' or time_units == 'seconds since 1970/01/01 00:00:00Z':
            time_units = 'seconds since 1970-01-01 00:00:00'  # coards is picky

        try:
            startDatetime = from_udunits(df[timeAxisName][0][0].data, time_units)
            endDatetime = from_udunits(df[timeAxisName][-1][0].data, time_units)
        except pydap.exceptions.ServerError as e:
            logger.warning(e)
            raise ServerError("Can't read start and end dates of %s from %s" % (time_units, url))
        except ValueError as e:
            logger.warning(e)
            raise ServerError("Can't read start and end dates of %s from %s" % (time_units, url))

        return startDatetime, endDatetime
    
    def process_decimated(self, job):
        '''
        Process decimated LRAUV data
        '''
        logger.debug('url = {}'.format(job.url_src))
        path = os.path.dirname(job.full_path)
        base_fname = os.path.splitext(job.full_path)[0] 
        in_file = os.path.join(path, base_fname + '.nc4')
        out_file_i = os.path.join(path, base_fname + '_i.nc')
        start, end = self.get_bounds(job.url_src, 'Time')
        logger.debug('start, end = {}, {}'.format(start, end))

        if start is not None and start < start:
            raise ServerError(
                'start = {} out of bounds with user-defined start = {}'.format(start, start))

        if end is not None and end > end:
            raise ServerError('end = {} out of bounds with user-defined end = {}'.format(end, end))

        url_i = None
 
        logger.debug('Calling pw.processNc4FileDecimated with out_file_i = {} in_file = {}'.format(out_file_i, in_file))
        try:
            if not self.args.debug:
                self.pw.processNc4FileDecimated(job.url_src, in_file, out_file_i, self.args.parms, json.loads(self.args.groupparms),
                                           self.args.iparm)
                url_i = job.url_src.replace('.nc', '_i.nc') 

        except TypeError:
            logger.warning('Problem reading data from {}'.format(job.url_src))
            logger.warning('Assuming data are invalid and skipping')
        except IndexError:
            logger.warning('Problem interpolating data from {}'.format(job.url_src))
        except KeyError:
            raise ServerError("Key error - can't read parameters from {}".format(job.url_src))
        except ValueError:
            raise ServerError("Value error - can't read parameters from {}".format(job.url_src))


        return url_i, start, end

    def load(self, job):
        data_start = None
        print('====>Processing decimated nc file {}'.format(job.activity_name))
        (url_dest, start, end) = self.process_decimated(job)

        print('====>Loading {}'.format(job.activity_name))
        if self.args.append:
            core_name = job.activity_name.split('_')[0]
            # Return datetime of last timevalue - if data are loaded from multiple activities return the earliest last datetime value
            data_start = \
            InstantPoint.objects.using(self.args.database).filter(activity__name__contains=core_name).aggregate(
                Max('timevalue'))['timevalue__max']

        coord = {} 
        for p in self.args.plotparms:
            coord[p] = {'time': p + '_time', 'latitude': p + '_latitude', 'longitude': p + '_longitude',
                        'depth': p + '_depth'}
        try:
            if not self.args.debug:
                logger.info("Instantiating Lrauv_Loader for url = {}".format(url_dest))
                DAPloaders.runLrauvLoader(cName = self.args.campaign,
                                                  cDesc = None,
                                                  aName = job.activity_name,
                                                  aTypeName = 'LRAUV mission',
                                                  pName = self.vehicle,
                                                  pTypeName = 'auv',
                                                  pColor = self.cl.colors[self.vehicle],
                                                  url = url_dest,
                                                  parmList = self.args.parms,
                                                  dbAlias = self.args.database,
                                                  stride = int(self.args.stride),
                                                  startDatetime = start,
                                                  dataStartDatetime = data_start,
                                                  endDatetime = end,
                                                  contourUrl = self.args.contourUrl,
                                                  auxCoords = coord,
                                                  timezone = 'America/Los_Angeles',
                                                  command_line_args = self.args)
        except DAPloaders.NoValidData:
            logger.info("No measurements in this log set. Activity was not created as there was nothing to load.")

        except pydap.exceptions.ServerError as e:
            logger.warning(e)

        except DAPloaders.ParameterNotFound as e:
            logger.warning(e)

        except DAPloaders.InvalidSliceRequest as e:
            logger.warning(e)

        except Exception as e:
            logger.warning(e)
            
        return url_dest, start, end

def process_command_line():
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
                        default='http://elvis.shore.mbari.org/thredds/catalog/LRAUV/',required=True)
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
    parser.add_argument('--vehicles', action='store', help='List of vehicles to monitor', nargs='*',
                        default= ['daphne', 'makai', 'ahi', 'opah', 'tethys', 'aku'])
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
    args = parser.parse_args()
    return args

def run():
    args = process_command_line()
    slack = None
    if args.post:
        token = os.environ['SLACKTOKEN']
        slack = Slacker(token)

    pusher = pysher.Pusher(os.environ['APPKEY'])
    event_name = "event-array"
    vehicles = args.vehicles
    print('Monitoring {} vehicles'.format(vehicles))

    l = {}
    # create a loader thread per each vehicle
    for v in vehicles:
        l[v] = Loader(v, slack, args)
        l[v].setDaemon(True)
        l[v].start()
      
    # add a logging handler to see the raw communication data
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(logging.StreamHandler(sys.stdout))

    def channel_callback(data):
        d1 = json.loads(data, cls=json.JSONDecoder)
        for d in d1: 
            vehicle = d['vehicleName']
            event_type = d['eventType']
            if any([vehicle == i for i in vehicles]):
                if 'dataProcessed' in event_type:
                    path = d['path']
                    d = path.split('/')
                    print('======> data processed {} {}'.format(path, d))
                    if len(d) == 3: # from sbdlog - we only know from the path structure with year year/isodate/
                        full_path = os.path.join(args.inDir, vehicle, 'realtime', 'sbdlogs', path, 'shore.nc')
                        url_src = args.inUrl +  full_path.split(args.inDir)[-1]
                        print('Checking if {} exists'.format(full_path))
                        if os.path.exists(full_path):
                            l[vehicle].put(Job(full_path, url_src))
                            
                    else: # from cell
                        full_path = os.path.join(args.inDir, vehicle, 'realtime', 'cell-logs', path, 'cell-Priority.nc')
                        print('Checking if {} exists'.format(full_path)) 
                        url_src = args.inUrl +  full_path.split(args.inDir)[-1]
                        if os.path.exists(full_path):
                            l[vehicle].put(Job(full_path, url_src))
                            
                        full_path = os.path.join(args.inDir, vehicle, 'realtime', 'cell-logs', path, 'cell-Normal.nc')
                        print('Checking if {} exists'.format(full_path)) 
                        url_src = args.inUrl +  full_path.split(args.inDir)[-1]
                        if os.path.exists(full_path):
                            l[vehicle].put(Job(full_path, url_src))

    def connect_handler(data):
        print("connect_handler: {}".format(data))
        channel = pusher.subscribe('td-events')
        channel.bind(event_name, channel_callback)

    pusher.connection.bind('pusher:connection_established', connect_handler)
    pusher.connect()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    run()
