__author__ = "Danelle Cline"
__copyright__ = "Copyright 2017, MBARI"
__license__ = "GNU License"
__maintainer__ = "Danelle Cline"
__email__ = "dcline at mbari.org"
__status__ = "Development"
__doc__ = '''

This script watches for newly created .nc4 files in the directory specified in the command, e.g.

    monitor.py --inDir `pwd` -x tethys > /tmp/monitor_front.out 2>&1 &

and searches for front detections in the file, then sends a rabbitmq message and slack post of the event

Prerequisites:

@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

import os
import subprocess
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import PatternMatchingEventHandler
import netCDF4
import pandas as pd
import numpy as np
import pika, logging, sys, time, datetime
import pytz

LOG_FILENAME = '/tmp/monitor_front.log'
pid = str(os.getpid())
pidfile = '/tmp/monitor_front.pid'

# Set up global variables for logging output to STDOUT
logger = logging.getLogger('LRAUVMonitorFront')
sh = logging.StreamHandler()
fh = logging.FileHandler(LOG_FILENAME)
f = logging.Formatter("%(levelname)s %(asctime)sZ %(filename)s %(funcName)s():%(lineno)d %(message)s")
fh.setFormatter(f)
sh.setFormatter(f)
logger.addHandler(sh)
logger.addHandler(fh)
logger.setLevel(logging.DEBUG)

# Helper for computing nearest time in a pandas time series
def fcl(df, dtObj):
  return df.iloc[np.argmin(np.abs(df.index.to_pydatetime() - dtObj))]

# Command line parse
def process_command_line():
  import argparse
  from argparse import RawTextHelpFormatter

  examples = 'Examples:' + '\n\n'
  examples += sys.argv[0] + "-i /mbari/LRAUV/ \n"
  parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                   description='monitor for front detection in .nc4 files',
                                   epilog=examples)
  parser.add_argument('-p','--platforms', action='store', help='List of space separated platforms to monitor',
                      nargs='*',
                      default=['tethys', 'daphne'], required=True)
  parser.add_argument('-s','--searchDir', action='store', help='List of space separated string subdirectories, '
                                                               'leaving off the beginning slash ',
                      nargs='*',
                      default=['realtime/sbdlogs/2017/', 'realtime/cell-logs/'])
  parser.add_argument('-i', '--inDir', action='store', help='base directory to read incoming .nc4 files ',
                      default='/mbari/LRAUV/', required=True)

  pargs = parser.parse_args()
  if pargs.platforms == None:
    print("Missing required argument: -p/--platforms")
    sys.exit(1)
  if pargs.inDir == None:
    print("Missing required argument: -i/--inDir")
    sys.exit(1)

  return pargs

class StreamHandler(PatternMatchingEventHandler):
  patterns = ["*.nc4"]
  concat_proc = None
  init = False
  rmq_channel = None
  platform = None

  def __init__(self, rmq_channel, platform):
    logger.info('Initializing platform {0} pattern *.nc4'.format(platform))
    self.rmq_channel = rmq_channel
    self.platform = platform
    super(StreamHandler, self).__init__()
    self.init = True

  def run_command(self, cmd, background):

    logger.debug('Executing ' + cmd)
    subproc = subprocess.Popen(cmd, env=os.environ)

    if not background:
      out, err = subproc.communicate()

      if subproc.returncode == 0:
        return True
      else:
        logger.error("Error running " + cmd)
        logger.error(str(err))
        return False

  def createSeriesPydap(self, df, name, tname):
      v = df[name]
      v_t = df[tname]
      data = np.asarray(v_t)
      data[data/1e10 < -1.] = 'NaN'
      data[data/1e10 > 1.] ='NaN'
      v_time_epoch = data
      v_time = pd.to_datetime(v_time_epoch[:],unit='s')
      v_time_series = pd.Series(v[:],index=v_time)
      return v_time_series

  def createSeriesPydapGroup(self, df, name, tname):
      v = df.variables[name]
      v_t = df.variables[tname]
      data = np.asarray(v_t)
      data[data/1e10 < -1.] = 'NaN'
      data[data/1e10 > 1.] ='NaN'
      v_time_epoch = data
      v_time = pd.to_datetime(v_time_epoch[:],unit='s')
      v_time_series = pd.Series(v[:],index=v_time)
      return v_time_series

  def getClosest(self, actual_time, coord_ts, temperature_ts):
      coord_value = {}
      time_epoch = actual_time
      time_dt = pd.to_datetime(time_epoch, unit='s')
      temperature = 'unknown'

      for c in coord_ts.keys():
        c_df = coord_ts[c]
        i = np.argmin(np.abs(c_df.index.to_pydatetime() - time_dt))
        coord_value[c] = c_df.iloc[i]

      if temperature_ts is not None:
        i = np.argmin(np.abs(temperature_ts.index.to_pydatetime() - time_dt))
        temperature = temperature_ts.iloc[i]

      return coord_value, temperature

  def scanNc4File(self, in_file):
    if not self.init:
      logger.info('Waiting for init')
      return

    df = netCDF4.Dataset(in_file, mode='r')
    coord =  ['latitude','longitude','depth']
    coord_ts = {}
    temperature_ts = None
    front_times = []

    for c in coord:
      coord_ts[c] = self.createSeriesPydap(df, c, c + '_time')

    if 'CTD_NeilBrown' in df.groups:
      temperature_ts = self.createSeriesPydapGroup(df.groups['CTD_NeilBrown'], 'bin_mean_sea_water_temperature', 'bin_mean_sea_water_temperature_time')

    if 'sea_water_temperature' in df.variables:
      temperature_ts = self.createSeriesPydap(df, 'sea_water_temperature', 'sea_water_temperature_time')

    if 'StratificationFrontDetector' in df.groups:
      g = df.groups['StratificationFrontDetector']
      key = 'front'
      if key in g.variables:
        front_ts = self.createSeriesPydapGroup(g, 'front', 'front_time')

        # find the all front detections
        front_ts_actual = front_ts[(front_ts > 0)]

        # arbitrarily choose the beginning and ending of that front
        if len(front_ts_actual) == 0:
          logger.info("========> No front detected")
          return

        try:
          for t in front_ts_actual.index:
            coord_value, temperature = self.getClosest(t, coord_ts, temperature_ts)
            front_time_epoch = t
            front_time_dt = pd.to_datetime(front_time_epoch, unit='s')
            utc = front_time_dt
            local_tz = pytz.timezone('America/Los_Angeles')
            utc_tz = pytz.timezone('UTC')
            utc = utc.replace(tzinfo=utc_tz)
            pst = utc.astimezone(local_tz)

            message = "========>Front detected:  "
            message += '\ntime: {}'.format(utc.isoformat())
            message += '\nlocal time: {}'.format(pst.isoformat())
            message += '\nlat/lon: {},{}'.format(coord_value['latitude'], coord_value['longitude'])
            message += '\ndepth: {}'.format(coord_value['depth'])
            message += '\ntemperature: {}'.format(temperature)
            logger.info(message)

            # auv,thysFr,1493829848,38.6,-121.23,lrauvFrontDetect,
            rmq_message = 'auv,{}Fr,{},{},{},lrauvFrontDetect,,,'.format(self.platform,
                                                                             time.mktime(pst.timetuple()),
                                                                             coord_value['latitude'],
                                                                             coord_value['longitude'])
            logger.info('{}'.format(rmq_message))
            if self.rmq_channel.basic_publish(body=rmq_message, exchange='auvs', routing_key='normandy_persist_auvs'):
              logger.info('Message {} has been delivered'.format(rmq_message))
            else:
              logger.warning('Message {} has NOT been delivered'.format(rmq_message))
        except Exception as ex:
          logger.error(ex)


  def process(self, event):
    """
    event.event_type
        'modified' | 'created' | 'moved' | 'deleted'
    event.is_directory
        True | False
    event.src_path
        path/to/observed/file
    """
    try:
      logger.info('=======>File {} {}<========='.format(event.src_path, event.event_type))
      # delay in case file being copied
      logger.info('Waiting 3 seconds to introduce slight delay in case still writing {}'.format(event.src_path))
      time.sleep(3)
      self.scanNc4File(str(event.src_path))
      logger.info('=======>Done scanning file<=========')

    except Exception as ex:
      logger.error(ex)

  def on_created(self, event):
    self.process(event)

if __name__ == '__main__':

  try:

    os.environ['SLACKTOKEN']

    vargs = process_command_line()

    vhost = 'trackingvhost'
    credentials = pika.PlainCredentials('tracking', 'MBARItracking')
    parameters = pika.ConnectionParameters('messaging.shore.mbari.org',
                                           5672,
                                           vhost,
                                           credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    if os.path.isfile(pidfile):
      logger.info("%s already exists, exiting" % pidfile)
      print("%s already exists, exiting" % pidfile)
      sys.exit()

    open(pidfile, 'w').write(pid)

    observers = []
    for platform in vargs.platforms:
      for dir in vargs.searchDir:
        try:
          observer = Observer()
          search_path = os.path.join(vargs.inDir, platform, dir)
          logger.info("Setting file observer for path {}".format(search_path))
          observer.schedule(StreamHandler(channel, platform), path=search_path, recursive=True)
          observer.start()
          logger.info("Waiting for next .nc4 file in {}...".format(search_path))
          observers.append(observer)
        except Exception as ex:
          logger.error(ex)
    try:
      while True:
        time.sleep(1)
    except KeyboardInterrupt:
      for observer in observers:
        observer.stop()
      connection.close()
    except Exception:
      for observer in observers:
        observer.stop()
      connection.close()
    finally:
      if os.path.isfile(pidfile):
        os.unlink(pidfile)

    for observer in observers:
      observer.join()

  except Exception as ex:
    logger.info(ex)
  finally:
    if os.path.isfile(pidfile):
      os.unlink(pidfile)
