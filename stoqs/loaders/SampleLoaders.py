'''
The SampleLoaders module contains classes and functions for loading Sample data into STOQS.

The btlLoader module has a load_btl() method that reads data from a Seabird
btl*.asc file and saves the bottle trip events as parent Samples in the STOQS database.

Mike McCann
MBARI 19 Setember 2012
'''

import os
import sys
# Add parent dir to pythonpath so that we can see the loaders and stoqs modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../") )
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
from django.conf import settings
from django.contrib.gis.geos import LineString, Point
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError
from django.db.models import Q, Min, Max, Avg
from django.db.utils import IntegrityError, DataError

from stoqs.models import (Activity, InstantPoint, Sample, SampleType, Resource,
                          SamplePurpose, SampleRelationship, Parameter, SampledParameter,
                          MeasuredParameter, AnalysisMethod, Measurement, Campaign,
                          Platform, PlatformType, ActivityType, ActivityResource,
                          SampleResource, ResourceType, ParameterResource)
from loaders.seabird import get_year_lat_lon
from loaders.gulper import Gulper
from loaders import STOQS_Loader, SkipRecord
from collections import defaultdict, namedtuple
from datetime import datetime, timedelta
from decimal import Decimal
from pydap.model import BaseType, DatasetType
import argparse
import csv
from urllib.request import urlopen, HTTPError
import requests
import logging
from glob import glob
from tempfile import NamedTemporaryFile
import re
from bs4 import BeautifulSoup

# Set up logging for module functions
logger = logging.getLogger(__name__)
# Logging level set in stoqs/config/settings/common.py, but may override here
##logger.setLevel(logging.INFO)

# When settings.DEBUG is True Django will fill up a hash with stats on every insert done to the database.
# "Monkey patch" the CursorWrapper to prevent this.  Otherwise we can't load large amounts of data.
# See http://stackoverflow.com/questions/7768027/turn-off-sql-logging-while-keeping-settings-debug
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.utils import CursorWrapper

if settings.DEBUG:
    BaseDatabaseWrapper.make_debug_cursor = lambda self, cursor: CursorWrapper(cursor, self)

# Constants for utils/STOQSQmanager.py to use
SAMPLED = 'Sampled'
sample_simplify_crit = 0.1

# SampleTypes
GULPER = 'Gulper'
NISKIN = 'Niskin'
NETTOW = 'NetTow'
VERTICALNETTOW = 'VerticalNetTow'       # Must contain NETTOW string so that a filter for
HORIZONTALNETTOW = 'VerticalNetTow'     # name__contains=NETTOW returns both vertical and horizontal net tows
PLANKTONPUMP = 'PlanktonPump'
ESP_FILTERING = 'ESP_filtering'
SIPPER = 'Sipper'
SAMPLE_TYPES = [GULPER, NISKIN, NETTOW, VERTICALNETTOW, HORIZONTALNETTOW, PLANKTONPUMP, ESP_FILTERING, SIPPER]

SIPPER_NUM_ERR = re.compile('Sample (?P<sipper_num>\d+), \(?err_code=(?P<sipper_err>\d+)\)?')
SampleInfo = namedtuple('SampleInfo', 'start end volume summary')
NOWATER = 'no water'

# Have both sample # and no_num versions of regular expressions so as to also get legacy samples
no_num_sampling_start_re = 'ESP sampling state: S_FILTERING'
no_num_sampling_end_re = 'ESP sampling state: S_PROCESSING'
sample_prefix = '\[sample #(?P<seq_num>\d+)\] '
sampling_start_re     = sample_prefix + no_num_sampling_start_re
sampling_end_re       = sample_prefix + no_num_sampling_end_re

# REs for ESP log summary reports, to search the multi-line text with optional matches
lsr_seq_num_re          = r'\[sample #(?P<seq_num>\d+)\]'
lsr_num_messages_re     = r'ESP log summary report \((?P<num_messages>\d+) messages\)'
lsr_cartridge_number_re = r'Selecting Cartridge (?P<cartridge_number>\d+)'
# E.g.: Sampled  1000.0ml
lsr_volume_re           = r'Sampled\s+(?P<volume_num>[-+]?\d*\.\d+)(?P<volume_units>[a-z]{2})'
# E.g.: Cmd::Paused in FILTERING --  during Sample Pump (SP) move after sampling 486.135m
lsr_volume_re_paused    = r'.*[Ss]ampl.+\s+(?P<volume_num>[-+]?\d*\.\d+)(?P<volume_units>[a-z]{2})'
lsr_esp_error_msg_re    = r'(?P<esp_error_message>.+Error in PROCESSING.+)'

# Begining of syslog, E.G.: 2019-08-16T19:51:31.135Z,1565985091.135 [ESPComponent](INFO)
iso_time = r'\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d\.\d*Z'
beg_syslog_re = iso_time + r',(?P<log_esec>\d*\.\d+)\s\[(?P<log_component>[^\]]+)\]\((?P<log_level>[^\)]+)\):\s(?P<log_message>[^\n]+)'

class ClosestTimeNotFoundException(Exception):
    pass

class SingleActivityNotFound(Exception):
    pass

class SubSampleLoadError(Exception):
    pass

def removeNonAscii(s): 
    return "".join(i for i in s if ord(i)<128)

def get_closest_instantpoint(aName, tv, dbAlias):
    '''
    Start with a tolerance of 1 second and double it until we get a non-zero count,
    get the values and find the closest one by finding the one with minimum absolute difference.
    '''
    tol = 1
    num_timevalues = 0
    logger.debug('Looking for tv = %s', tv)
    while tol < 86400:                                      # Fail if not found within 24 hours
        qs = InstantPoint.objects.using(dbAlias).filter(  activity__name__contains = aName,
                                                            timevalue__gte = (tv-timedelta(seconds=tol)),
                                                            timevalue__lte = (tv+timedelta(seconds=tol))
                                                         ).order_by('timevalue')
        if qs.count():
            num_timevalues = qs.count()
            break
        tol = tol * 2

    if not num_timevalues:
        raise ClosestTimeNotFoundException

    logger.debug('Found %d time values with tol = %d', num_timevalues, tol)
    timevalues = [q.timevalue for q in qs]
    logger.debug('timevalues = %s', timevalues)
    i = 0
    i_min = 0
    secdiff = []
    minsecdiff = tol
    for t in timevalues:
        secdiff.append(abs(t - tv).seconds)
        if secdiff[i] < minsecdiff:
            minsecdiff = secdiff[i]
            i_min = i
        logger.debug('i = %d, secdiff = %d', i, secdiff[i])
        i = i + 1

    logger.debug('i_min = %d', i_min)
    return qs[i_min], secdiff[i_min]


class ParentSamplesLoader(STOQS_Loader):
    '''Holds methods customized for reading sample event information from mainly AUV syslog files
    '''
    esp_cartridge_number = 57       # Special for stoqs_canon_may2018
    esp_devices = {}

    def load_gulps(self, activityName, auv_file, dbAlias):
        '''
        auv_file looks like 'Dorado389_2011_111_00_111_00_decim.nc'.  From hard-coded knowledge of MBARI's filesystem
        read the associated _gulper.txt file for the survey and load the gulps as samples in the dbAlias database.
        '''

        # Get the Activity from the Database
        try:
            activity = Activity.objects.using(dbAlias).get(name__contains=activityName)
            self.logger.debug('Got activity = %s', activity)
        except ObjectDoesNotExist:
            self.logger.warn('Failed to find Activity with name like %s.  Skipping GulperLoad.', activityName)
            return
        except MultipleObjectsReturned:
            self.logger.warn('Multiple objects returned for name__contains = %s.  Selecting one by random and continuing...', activityName)
            activity = Activity.objects.using(dbAlias).filter(name__contains=activityName)[0]

        try:
            if NOWATER in (ActivityResource.objects.using(dbAlias)
                                           .get(activity=activity, resource__name='title', 
                                                resource__resourcetype__name='nc_global')
                                           .resource.value.lower()):
                self.logger.warn(f"Found '{NOWATER}' text in title of {activity.name}, not adding Gulpers")
                return
        except ActivityResource.DoesNotExist:
            self.logger.warn(f"Could not find 'title' nc_global attribute in ActivityResource for Activity {activity}")

        # Use the dods server to read over http - works from outside of MBARI's Intranet
        baseUrl = 'http://dods.mbari.org/data/auvctd/surveys/'
        yyyy = auv_file.split('_')[1].split('_')[0]
        survey = auv_file.split(r'_decim')[0]
        # E.g.: http://dods.mbari.org/data/auvctd/surveys/2010/odv/Dorado389_2010_300_00_300_00_Gulper.txt
        gulperUrl = baseUrl + yyyy + '/odv/' + survey + '_Gulper.txt'

        # Get or create SampleType for Gulper
        (gulper_type, created) = SampleType.objects.using(dbAlias).get_or_create(name=GULPER)
        self.logger.debug('sampletype %s, created = %s', gulper_type, created)
        with requests.get(gulperUrl, stream=True) as r:
            if r.status_code != 200:
                self.logger.warn('Cannot read %s, r.status_code = %s', gulperUrl, r.status_code)
                return

            r_decoded = (line.decode('utf-8') for line in r.iter_lines())
            reader = csv.DictReader(r_decoded, dialect='excel-tab')
            for row in reader:
                # Need to subtract 1 day from odv file as 1.0 == midnight on 1 January
                try:
                    timevalue = datetime(int(yyyy), 1, 1) + timedelta(days = (float(row[r'YearDay [day]']) - 1))
                except TypeError as e:
                    self.logger.error('%s.  Skipping this Sample - you may want to fix the input file', e)
                    continue
                try:
                    ip, seconds_diff = get_closest_instantpoint(activityName, timevalue, dbAlias)
                    point = Point(float(row[r'Lon (degrees_east)']) - 360.0, float(row[r'Lat (degrees_north)']))
                    stuple = Sample.objects.using(dbAlias).get_or_create( name = row[r'Bottle Number [count]'],
                                                                        depth = row[r'DEPTH [m]'],
                                                                        geom = point,
                                                                        instantpoint = ip,
                                                                        sampletype = gulper_type,
                                                                        volume = 1800
                                                                      )
                    rtuple = Resource.objects.using(dbAlias).get_or_create( name = 'Seconds away from InstantPoint',
                                                                          value = seconds_diff
                                                                        )

                    # 2nd item of tuples will be True or False dependending on whether the object was created or gotten
                    self.logger.info('Loaded Sample %s with Resource: %s', stuple, rtuple)
                except ClosestTimeNotFoundException:
                    self.logger.warn('ClosestTimeNotFoundException: A match for %s not found for %s', timevalue, activity)

    def load_gulper_activities(self, activity_name, auv_file, db_alias, url, platform_color, sec_bnds: int=1):
        '''Use gulper.Gulper from auv-python to get Gulper bottle times and load Samples
        as Activities like for LRAUV ESPs and Sippers.  auv_file looks like 'dorado_2022.286.01_1S.nc'.
        Look forward and back sec_bnds seconds from Sample time to match measurement data.
        '''
        gulper = Gulper()
        gulper.args = argparse.Namespace()
        gulper.args.mission = auv_file.split("_")[1]
        gulper.args.start_esecs = None
        gulper.args.local = False
        gulper.args.verbose = 0
        bottle_times = gulper.parse_gulpers()
        gulper_names = {}
        for sample_name, sample_esecs in bottle_times.items():
            summary = f"Gulper {sample_name} sampled at esecs = {sample_esecs}"
            gulper_names[sample_name] = SampleInfo(sample_esecs-sec_bnds, sample_esecs+sec_bnds, 0.8, summary)

        pt, _ = PlatformType.objects.using(db_alias).get_or_create(name='auv')
        platform, _ = Platform.objects.using(db_alias).get_or_create(
                                name = "dorado_Gulper",
                                platformtype = pt,
                                color = platform_color
                            )
        gulper_type, _ = SampleType.objects.using(db_alias).get_or_create(name=GULPER)
        self.logger.debug('_save_samples() for gulper_names = %s', gulper_names)
        self._save_samples(db_alias, platform.name, activity_name, gulper_type, gulper_names, url,
                           log_text='3 seconds around Gulper fire time parsed from syslog')

    def _get_lrauv_esp_sample_platform(self, db_alias, lrauv_platform, sample_type, esp_device=None):
        '''Use name of LRAUV platform to construct a new Platform for connecting to an ESP Sample Activity.
        Return existing Platform if it's already been created.
        '''
        if esp_device:
            p_name = f"{lrauv_platform.name}_{sample_type.name.replace('ESP', esp_device)}"
        else:
            p_name = f"{lrauv_platform.name}_{sample_type}"
        pt, _ = PlatformType.objects.using(db_alias).get_or_create(name='auv')
        platform, _ = Platform.objects.using(db_alias).get_or_create(
                                name = p_name,
                                platformtype = pt,
                                color = lrauv_platform.color
                            )
        return platform

    def _create_activity_instantpoint_platform(self, db_alias, platform_name, activity_name, sample_type, url, ses, ees,
                                               sample_name, esp_device=None):
        '''Create an Activity for the Sample and copy the Measurement locations
        to create records for drawing the trace of the long duration sample in the UI
        '''
        campaign = Campaign.objects.using(db_alias).filter(activity__name=activity_name)[0]
        lrauv_platform = Platform.objects.using(db_alias).filter(activity__name=activity_name)[0]
        platform = self._get_lrauv_esp_sample_platform(db_alias, lrauv_platform, sample_type, esp_device)
        at, _ = ActivityType.objects.using(db_alias).get_or_create(name=ESP_FILTERING)

        sdt = datetime.fromtimestamp(ses)
        edt = datetime.fromtimestamp(ees)
        ip_qs = InstantPoint.objects.using(db_alias).filter(activity__name=activity_name,
                                                            timevalue__gte=sdt,
                                                            timevalue__lte=edt).order_by('timevalue')
        if not ip_qs:
            self.logger.warn(f"No InstantPoints for Sample '{sample_name}' between {sdt} and {edt}")
            if db_alias.endswith('_t'):
                self.logger.warn(f"Perhaps doing a high stride test load? - skipping Sample '{sample_name}'")
            else:
                self.logger.warn(f"*** No timevalue data available for Sample '{sample_name}' between {sdt} and {edt}")
                self.logger.warn(f"*** Not loading Sample '{sample_name}' because there is no corresponding measurement or location data.")

            return None, None, None, None, None

        m_qs = Measurement.objects.using(db_alias).filter(instantpoint__activity__name=activity_name,
                                                          instantpoint__timevalue__gte=sdt,
                                                          instantpoint__timevalue__lte=edt)
        qs = m_qs.aggregate(Min('depth'), Max('depth'), Avg('depth'))
        self.logger.info(f"Between {sdt} and {edt} depth__min={qs['depth__min']}, depth__max={qs['depth__max']}")
        duration = edt - sdt
        max_hours = 2
        self.logger.info(f"Sample '{sample_name}' duration: {duration}")
        if duration > timedelta(hours=max_hours):
            self.logger.warn(f"Time duration of Sample '{sample_name}' is longer than {max_hours} hours: duration = {duration}")

        try:
            log_dir = url.split('/')[10]
            short_activity_name = f"{activity_name.split('_')[0]}_{log_dir}"
        except IndexError:
            # Likely not a LRAUV url, a dorado one instead
            short_activity_name = f"{activity_name}"
        if esp_device:
            a_name = f"{short_activity_name}_{sample_type.name.replace('ESP', esp_device)}_{sample_name}"
        else:
            a_name = f"{short_activity_name}_{sample_type}_{sample_name}"
            self.logger.warning(f"esp_device not set, even after checking all syslogs in dlist_dir: {'/'.join(url.split('/')[:10])}")
        self.logger.info(f"Creating (or getting) Activity with name: {a_name}")
        sample_act, _ = Activity.objects.using(db_alias).get_or_create(
                            campaign = campaign,
                            activitytype = at,
                            name = a_name,
                            comment = f'{sample_type} Sample done in conjunction with LRAUV Activity {activity_name}',
                            platform = platform,
                            startdate = ip_qs[0].timevalue,
                            enddate = ip_qs.reverse()[0].timevalue,
                            mindepth = qs['depth__min'],
                            maxdepth = qs['depth__max'],
                       )
        # Update loaded_date after get_or_create() so that we can get the old record if script is re-executed
        self.logger.debug(f"sample_act = {sample_act}")
        sample_act.loaded_date = datetime.utcnow()
        sample_act.save(using=db_alias)

        # Add deep copies of original Activity Measurements to the new Sample Activity to have accurate time and locations
        # and statistics of the MeasuredParameters for the Sample
        self.activity = sample_act
        parameter_counts = defaultdict(lambda:0)
        self.logger.info(f"Creating {len(m_qs)} Measurements for a time series of this Sample Activity")
        for me in m_qs:
            measurement = self.createMeasurement(mtime=me.instantpoint.timevalue, 
                                                 depth=me.depth,
                                                 lon=me.geom.x,
                                                 lat=me.geom.y)
            for mp in MeasuredParameter.objects.using(db_alias).filter(measurement=me):
                parameter_counts[mp.parameter] += 1
                samp_mp = MeasuredParameter(measurement=measurement, 
                                            parameter=mp.parameter, 
                                            datavalue=mp.datavalue)
                samp_mp.save(using=db_alias)

        try:
            self.update_activityparameter_stats(db_alias, sample_act, parameter_counts)
        except ValueError as e:
            self.logger.warn(f"{e}")

        # Time and location of Sample (a single value) is midpoint of start and end times
        sample_tv = ip_qs[int(len(ip_qs)/2)].timevalue
        if len(m_qs.values_list('geom', flat=True)) > 1:
            point = LineString([p for p in m_qs.values_list('geom', flat=True)]).centroid
            maptrack = LineString([p for p in m_qs.values_list('geom', flat=True)]).simplify(tolerance=.001)
        else:
            point = m_qs.values_list('geom', flat=True)[0]
            maptrack = LineString([m_qs.values_list('geom', flat=True)[0], m_qs.values_list('geom', flat=True)[0]])
        self.logger.debug(f"Creating a single point for this Sample with timevalue = {sample_tv} at location {point}")
        sample_ip, _ = InstantPoint.objects.using(db_alias).get_or_create(activity=sample_act, timevalue=sample_tv)
        depth = qs['depth__avg']

        self.logger.debug(f"Creating SimpleDepthTimeSeries for this Sample")
        self.insertSimpleDepthTimeSeries(critSimpleDepthTime=sample_simplify_crit)

        # Associate Resources so that data can be plotted in the Paramter tab of the UI
        self.logger.info(f"Associating Resources for UI display of Parameters tab for sample_act = {sample_act}")
        ncg_res_type, _ = ResourceType.objects.using(self.dbAlias).get_or_create(name='nc_global')
        ui_res_type, _ = ResourceType.objects.using(self.dbAlias).get_or_create(name='ui_instruction')
        ft_res, _ = Resource.objects.using(self.dbAlias).get_or_create(name='featureType',
                                                                       value='trajectory', resourcetype=ncg_res_type)
        ptsd_res, _ = Resource.objects.using(self.dbAlias).get_or_create(name='plotTimeSeriesDepth',
                                                                         value=0, resourcetype=ui_res_type)
        ar, _ = ActivityResource.objects.using(self.dbAlias).get_or_create(activity=sample_act, resource=ft_res)
        self.logger.info(f"ActivityResource.resource = {ar.resource}")
        ar, _ = ActivityResource.objects.using(self.dbAlias).get_or_create(activity=sample_act, resource=ptsd_res)
        self.logger.info(f"ActivityResource.resource = {ar.resource}")
        for parm in parameter_counts:
            pr, _ = ParameterResource.objects.using(self.dbAlias).get_or_create(parameter=parm, resource=ptsd_res)
            self.logger.info(f"parm = {parm}, ParameterResource.resource = {pr.resource}")

        return sample_act, sample_ip, point, depth, maptrack

    def _read_syslog(self, url, levels=('IMPORTANT',), components=('ESPComponent',)):
        syslog_url = "{}/syslog".format('/'.join(url.replace('opendap/', '').split('/')[:-1]))
        self.logger.info(f"Getting {levels} {components} information from {syslog_url}")
        log_rows = []
        esp_device = None
        if 'realtime' in syslog_url:
            self.logger.info(f"String 'realtime' found in {syslog_url} - not attempting to read it")
            return log_rows, esp_device

        with requests.get(syslog_url, stream=True) as resp:
            if resp.status_code != 200:
                self.logger.error(f'Cannot read {syslog_url}, resp.status_code = {resp.status_code}')
                raise FileNotFoundError(f'Cannot read {syslog_url}, resp.status_code = {resp.status_code}')

            following_lines = ''
            prev_message = ''
            prev_line_has_component = False
            for line in (lb.decode(errors='ignore') for lb in resp.iter_lines()):

                # Ugly logic to handle multiple line messages
                lm = re.match(beg_syslog_re, line)
                if lm:
                    if lm.groupdict().get('log_component') in ('ESPComponent',) and lm.groupdict().get('log_level') in levels:
                        # December 2022 while adding Sipper capture: Not sure why there is this prev_line logic...
                        if prev_line_has_component:
                            log_rows.append({'unixTime': float(prev_esec) * 1000, 'text': prev_message})

                        prev_esec = lm.groupdict().get('log_esec')
                        prev_message = lm.groupdict().get('log_message')
                        following_lines = ''
                        prev_line_has_component = True
                    elif 'CANONSampler' in components and 'CANONSampler' in line:
                        if lm.groupdict().get('log_level') in levels:
                            # 'CANONSampler sampling at' text can have components like '[spiral_cast:SampleAtDepth:SampleWrapper:SampleCANONSampler:D]'
                            # Collect all log_rows that match levels, as only err_code=0 has component '[CANONSampler]', let calling routine pull out relevant lines
                            log_rows.append({'unixTime': float(lm.groupdict().get('log_esec')) * 1000, 'text': lm.groupdict().get('log_message')})

                    elif lm.groupdict().get('log_component') == 'ESPComponent' and lm.groupdict().get('log_level') == 'INFO':
                        # Messages like this started appearing in the syslogs in the Fall of 2018
                        # 2020-10-14T05:24:53.794Z,1602653093.794 [ESPComponent](INFO): console:ESPmv1 login: Sending discover...
                        esp_m = re.match('console:(ESP\S+) login', lm.groupdict().get('log_message'))
                        if esp_m:
                            esp_device = esp_m.group(1)

                    else:
                        message = prev_message
                        if prev_line_has_component:
                            if following_lines:
                                message = prev_message + '\n' + following_lines
                        if message:
                            log_rows.append({'unixTime': float(prev_esec) * 1000, 'text': message})
                            prev_message = ''

                        prev_line_has_component = False
                else:
                    if line:
                        following_lines += line + '\n'

        return log_rows, esp_device

    def _read_tethysdash(self, platform_name, url):
        st = url.split('/')[-1].split('_')[0]
        et = url.split('/')[-1].split('_')[1]
        from_time = f"{st[0:4]}-{st[4:6]}-{st[6:8]}T{st[8:10]}:{st[10:12]}Z"
        to_time = f"{et[0:4]}-{et[4:6]}-{et[6:8]}T{et[8:10]}:{et[10:12]}Z"

        # Sanity check the ending year
        try:
            if int(et[0:4]) > datetime.now().year:
                self.logger.warn(f"Not looking for Samples for url = {url} as the to date is > {datetime.now().year}")
                return esp_s_filtering, esp_s_stopping, esp_log_summaries 
        except ValueError:
            # Likely an old slate.nc4 file that got converted to a .nc file
            self.logger.warn(f"Could not parse end date year from url = {url}")
            return

        td_url = f"https://okeanids.mbari.org/TethysDash/api/events?vehicles={platform_name}&from={from_time}&to={to_time}&eventTypes=logImportant&limit=100000"
        self.logger.debug(f"Opening td_url = {td_url}")
        with requests.get(td_url) as resp:
            if resp.status_code != 200:
                self.logger.error('Cannot read %s, resp.status_code = %s', td_url, resp.status_code)
                return

            return resp.json()['result']

    def _get_esp_device(self, url):
        '''Search all syslogs in all log dirs of the parent dlist dir for the ESP device name.
        Cache the results so that subsequent searches can be replaced by a get from the hash.
        '''
        dlist_url = '/'.join(url.split('/')[:10])
        if esp_device := self.esp_devices.get(dlist_url):
            self.logger.debug(f"Returning esp_device from cache: {esp_device}")
            return esp_device

        soup = BeautifulSoup(urlopen(dlist_url).read(), 'lxml')
        link_list = soup.find_all('a')
        sorted(link_list, key=lambda elem: elem.text)
        for link in link_list:
            self.logger.debug(f"Checking for log dir: {link.text}")
            if re.match('\d\d\d\d\d\d\d\dT\d\d\d\d\d\d', link.text):
                syslog_url = os.path.join(dlist_url, link.text, 'syslog')
                self.logger.debug(f"Looking for esp_device in {syslog_url}")
                _, esp_device = self._read_syslog(syslog_url)
                if esp_device:
                    self.esp_devices[dlist_url] = esp_device
                    self.logger.debug(f"Found it: {esp_device}")
                    break

        return esp_device
        
    def _esps_from_json(self, platform_name, url, db_alias, use_syslog=True):
        '''Retrieve Sample information that's available in the syslogurl from the TethysDash REST API
        url looks like 'http://dods.mbari.org/opendap/data/lrauv/tethys/missionlogs/2018/20180906_20180917/20180908T084424/201809080844_201809112341_2S_scieng.nc'
        Construct a TethysDash REST URL that looks like:
        https://okeanids.mbari.org/TethysDash/api/events?vehicles=tethys&from=2018-09-08T00:00&to=2018-09-08T06:00&eventTypes=logImportant&limit=1000
        Query it to build information on each sample in the url.
        Note: The TethysDash database behind this REST URL is used for real-time command and control and is susceptible to lost messages.
              More complete information is in the syslog files.  Let's try and reuse this code by building a similar json data structure from the syslog.
        '''
        esp_s_filtering = []
        esp_s_stopping = []
        esp_log_summaries = []
        esp_log_criticals = []
        esp_device = None

        FILTERING = 'ESP sampling state: S_FILTERING'
        PROCESSING = 'ESP sampling state: S_PROCESSING'
        LOGSUMMARY = 'ESP log summary report'

        if use_syslog:
            log_important, _ = self._read_syslog(url)
            log_critical, _ = self._read_syslog(url, levels=('CRITICAL',))
            esp_device = self._get_esp_device(url)
        else:
            log_important = self._read_tethysdash(platform_name, url)

        if not log_important and not log_critical:
            return esp_s_filtering, esp_s_stopping, esp_log_summaries, esp_log_criticals, esp_device

        Log = namedtuple('Log', 'esec text')
        try:
            esp_s_filtering = [Log(d['unixTime']/1000.0, d['text']) for d in log_important if FILTERING in d['text']]
        except KeyError:
            self.logger.debug(f"No '{no_num_sampling_start_re}' messages found in syslog for {url}")
        try:
            esp_s_stopping = [Log(d['unixTime']/1000.0, d['text']) for d in log_important if PROCESSING in d['text']]
        except KeyError:
            self.logger.debug(f"No '{no_num_sampling_end_re}' messages found in syslog for {url}")
        try:
            esp_log_summaries = [Log(d['unixTime']/1000.0, d['text']) for d in log_important if LOGSUMMARY in d['text']]
        except KeyError:
            self.logger.debug(f"No '{lsr_num_messages_re}' messages found in syslog for {url}")
        try:
            esp_log_criticals = [Log(d['unixTime']/1000.0, d['text']) for d in log_critical]
        except KeyError:
            self.logger.debug(f"No 'critical' messages found in syslog for {url}")

        if esp_s_filtering and esp_s_stopping and esp_log_summaries:
            self.logger.info(f"Parsed {len(esp_log_summaries)} Samples (esp_log_summaries) from syslog for {url}")
        elif esp_s_filtering and esp_s_stopping:
            # LOGSUMMARY messages were added halfway through 2018, before that create a "sequence number" for the Sample
            self.logger.info(f"No '{lsr_num_messages_re}' messages found")
            if 'stoqs_canon_may2018' in db_alias:
                self.logger.info(f"Will assign Cartridge numbers for the Campaign to the Samples - a special fix for stoqs_canon_may2018")
                numbers = range(self.esp_cartridge_number - len(esp_s_filtering), self.esp_cartridge_number)
                for i, filtering, stopping in zip(numbers, esp_s_filtering, esp_s_stopping):
                    self.logger.info(f"Cartridge {i} assigned to Sample that started filtering at {filtering.esec} and stopped at {stopping.esec}") 
                    esp_log_summaries.append(Log(filtering.esec, f"Cartridge {i}"))
                    self.esp_cartridge_number -= 1
            else:
                self.logger.info(f"Will assign sequence numbers per log file to the Samples")
                for i, filtering, stopping in zip(range(len(esp_s_filtering), 0, -1), esp_s_filtering, esp_s_stopping):
                    self.logger.info(f"Sequence {i} assigned to Sample that started filtering at {filtering.esec} and stopped at {stopping.esec}") 
                    esp_log_summaries.append(Log(filtering.esec, f"Sequence {i}"))
            self.logger.info(f"Parsed {len(esp_s_filtering)} Samples from syslog for {url} with no LOGSUMMARY reports")
        else:
            self.logger.info(f"No ESP Samples parsed from syslog for {url}")

        return esp_s_filtering, esp_s_stopping, esp_log_summaries, esp_log_criticals, esp_device

    def _check_leaked_cartridge(self, platform_name, summary):
        # Check for repeated 'Selecting Cartridge' in summary.text and report Disposition
        index = 0
        occurrences = 0
        while index < len(summary.text):
            index = summary.text.find('Selecting Cartridge', index)
            if index == -1:
                break
            occurrences += 1
            if occurrences > 1:
                self.logger.info(f"Repeated 'Selecting Cartridge' message found in {platform_name}'s summary.text: {summary.text}")
                if 'Cmd::SpareCartridge' in summary.text or 'Cartridge::Sampler::Leak' in summary.text:
                    # Assumes that there are multiple 'Selecting Cartridge' messages in summary.text: the last is the one used, the others leaked
                    self.logger.info(f"Found 'Cmd::SpareCartridge' message, using last Cartridge number for sample name")
                    return re.findall(lsr_cartridge_number_re, summary.text, re.MULTILINE)

            index += len('Selecting Cartridge')

        return None, None

    def _validate_summaries(self, platform_name, filterings, stoppings, summaries, criticals):
        '''Ensure that there are the same number of items in filterings, stoppings, summaries and 
        that the sample #s match.  If not then attempt to repair with appropriate warnings.
        '''
        if len(filterings) != len(stoppings):
            self.logger.warn(f"len(filterings) [{len(filterings)}] != len(stoppings) [{len(stoppings)}]")
            self.logger.warn("An ESP error might have occurred, sample times may overlap - check syslog")

        if not (len(filterings) == len(stoppings) == len(summaries)):
            self.logger.warn("Mismatch in the number of filterings, stoppings, summaries")
            self.logger.warn(f"len(filterings) = {len(filterings)}, len(stoppings) = {len(stoppings)}")
            self.logger.warn(f"len(summaries) = {len(summaries)}")

            filter_nums = []
            stop_nums = []
            for filtering, stopping, summary in zip(filterings, stoppings, summaries):
                self.logger.debug(f"summary = {summary}")
                ms = (re.match(sampling_start_re, filtering.text) or 
                      re.match(no_num_sampling_start_re, filtering.text))
                me = (re.match(sampling_end_re, stopping.text) or
                      re.match(no_num_sampling_end_re, stopping.text))
                filter_nums.append(ms.groupdict().get('seq_num'))
                stop_nums.append(me.groupdict().get('seq_num'))

            # 1. Correct case where we have more summaries than filterings
            if len(summaries) > len(filterings):
                to_del = []
                self.logger.info(f"len(summaries) > len(filterings). Checking that numbers in filter_nums match '{sampling_start_re}'")
                for index, summary in enumerate(summaries):
                    lsr_seq_num = re.search(lsr_seq_num_re, summary.text, re.MULTILINE)
                    if lsr_seq_num.groupdict().get('seq_num') not in filter_nums:
                        self.logger.warn(f"Sample seq_num ({lsr_seq_num.groupdict().get('seq_num')}) not found in filter_nums: {filter_nums}")
                        self.logger.warn(f"Likely an error for this cartridge: {summary.text}")
                        crit_err = ''
                        for lc in criticals:
                            lc_seq_num = re.search(lsr_seq_num_re, lc.text, re.MULTILINE)
                            if lsr_seq_num.groupdict().get('seq_num') == lc_seq_num.groupdict().get('seq_num'):
                                crit_err = lc.text
                                break
                        try:
                            lsr_cartridge_number = re.search(lsr_cartridge_number_re, summary.text, re.MULTILINE).groupdict().get('cartridge_number')
                        except AttributeError as e:
                            # Likely: AttributeError: 'NoneType' object has no attribute 'groupdict'
                            self.logger.warn(f"{e}: Could not find cartridge_number in summary.text")
                        else:
                            self.logger.info(f"Not loading Cartridge {lsr_cartridge_number} at index {index}")
                            self.logger.info(f"Disposition of {platform_name} Cartridge {lsr_cartridge_number}: Not saving, no corresponding"
                                             f" {no_num_sampling_start_re} for [sample #{lsr_seq_num.groupdict().get('seq_num')}]"
                                             f" perhaps error indicated in summary.text: {summary.text!r} and"
                                             f" critical error message: {crit_err!r}")
                        to_del.append(index)

                        # Check for repeated 'Selecting Cartridge' in summary.text and report Disposition
                        occurrences = 0
                        while index < len(summary.text):
                            index = summary.text.find('Selecting Cartridge', index)
                            if index == -1:
                                break
                            occurrences += 1
                            if occurrences > 1:
                                lsr_cartridge_number = re.search(lsr_cartridge_number_re, summary.text[index:], re.MULTILINE).groupdict().get('cartridge_number')
                                self.logger.info(f"Disposition of {platform_name} Cartridge {lsr_cartridge_number}: Not saving, repeated entry"
                                                 f" in [sample #{lsr_seq_num.groupdict().get('seq_num')}], see summarytext: {summary.text!r}")
                            index += len('Selecting Cartridge')

                for index in reversed(to_del):
                    self.logger.info(f"Deleting index {index} from summaries list")
                    del summaries[index]

            # 2. Report case where we have more summaries than stoppings
            if len(summaries) > len(stoppings):
                self.logger.info(f"len(summaries) > len(stoppings). Checking that numbers in stop_nums match '{sampling_end_re}'")
                to_del = []
                for index, summary in enumerate(summaries):
                    lsr_seq_num = re.search(lsr_seq_num_re, summary.text, re.MULTILINE)
                    if lsr_seq_num.groupdict().get('seq_num') not in stop_nums:
                        for lc in criticals:
                            lc_seq_num = re.search(lsr_seq_num_re, lc.text, re.MULTILINE)
                            if lsr_seq_num.groupdict().get('seq_num') == lc_seq_num.groupdict().get('seq_num'):
                                lsr_cartridge_number = re.search(lsr_cartridge_number_re, summary.text, re.MULTILINE).groupdict().get('cartridge_number')
                                self.logger.info(f"Disposition of {platform_name} Cartridge {lsr_cartridge_number}: Not saving, no corresponding"
                                                 f" {no_num_sampling_end_re} for [sample #{lsr_seq_num.groupdict().get('seq_num')}] and critical"
                                                 f" error message: {lc.text!r}")
                                to_del.append(index)

                for index in reversed(to_del):
                    self.logger.info(f"Deleting index {index} from summaries list")
                    del summaries[index]

        # Check for use of spare Cartridge following a leak - brute force replacement of number in summary.text
        for index, summary in enumerate(summaries):
            mult_carts = self._check_leaked_cartridge(platform_name, summary)
            if len(mult_carts) > 1:
                Log = namedtuple('Log', 'esec text')
                summaries[index] = Log(summary.esec, summary.text.replace(f"Cartridge {mult_carts[0]}", f"Cartridge {mult_carts[-1]}"))
                self.logger.info(f"Replaced first (leaked={mult_carts[:-1]}) Cartridge number(s) with last (spare_used={mult_carts[-1]})"
                                 f" Cartridge number in summary.text: {summaries[index].text}")

        # Check for and remove duplicate sample #s as in:
        # http://dods.mbari.org/data/lrauv/daphne/missionlogs/2019/20190520_20190524/20190523T195841/syslog
        num_dict = defaultdict(lambda:0)
        for filtering, stopping, summary in zip(filterings, stoppings, summaries):
            try:
                fi_num = filtering.text.split(']')[0].split('#')[1]
                st_num = stopping.text.split(']')[0].split('#')[1]
                su_num = summary.text.split(']')[0].split('#')[1]
                if fi_num == st_num == su_num:
                    num_dict[fi_num] += 1
            except IndexError:
                self.logger.warning(f"Likely ESP state messages without 'sample #' text")
                self.logger.info(f"filtering.text = {filtering.text}")
                self.logger.info(f"stopping.text = {stopping.text}")
                self.logger.info(f"summary.text = {summary.text}")

        to_del = []
        for num, count in num_dict.items():
            if count > 1:
                self.logger.warning(f"[sample #{num}] found more that once ({count}) in syslog")
                # Find maximum length summary text
                max_summ_len = 0
                for index, summary in enumerate(summaries):
                    lsr_seq_num = re.search(lsr_seq_num_re, summary.text, re.MULTILINE)
                    if lsr_seq_num.groupdict().get('seq_num') == num:
                        if len(summary.text) > max_summ_len:
                            max_summ_len = len(summary.text)

                for index, summary in enumerate(summaries):
                    lsr_seq_num = re.search(lsr_seq_num_re, summary.text, re.MULTILINE)
                    if lsr_seq_num.groupdict().get('seq_num') == num:
                        self.logger.info(f"index {index:3}: summary.text = {summary.text}")
                        if len(summary.text) < max_summ_len:
                            self.logger.info(f"Will delete shorter summary.text with index = {index}")
                            to_del.append(index)

        for index in reversed(to_del):
            self.logger.info(f"Deleting index {index} from filtering, stoppings, and summaries lists")
            del filterings[index]
            del stoppings[index]
            del summaries[index]

        for summary in summaries:
            try:
                lsr_cartridge_number = re.search(lsr_cartridge_number_re, summary.text, re.MULTILINE).groupdict().get('cartridge_number')
            except AttributeError:
                self.logger.debug(f"Cannot parse Cartridge number from {summary.text}")
                continue
            lsr_seq_num = re.search(lsr_seq_num_re, summary.text, re.MULTILINE)
            try:
                self.logger.info(f"Disposition of {platform_name} Cartridge {lsr_cartridge_number}: Passed validation, marked for saving"
                                 f" [sample #{lsr_seq_num.groupdict().get('seq_num')}]")
            except AttributeError:
                self.logger.warn(f"Likely lsr_seq_num ({lsr_seq_num}) is None and this log is before 'sample #' was implemented completely")
                self.logger.info(f"Disposition of {platform_name} Cartridge {lsr_cartridge_number}: Passed validation, marked for saving")

        return filterings, stoppings, summaries

    def _match_seq_to_cartridge(self, filterings, stoppings, summaries, before_seq_num_implemented=False):
        '''Take lists from parsing TethysDash log and build Sample names list with start and end times
        '''
        # Loop through extractions from syslog to build dictionary
        sample_names = defaultdict(SampleInfo)
        for filtering, stopping, summary in zip(filterings, stoppings, summaries):
            self.logger.debug(f"summary = {summary}")
            ms = (re.match(sampling_start_re, filtering.text) or 
                  re.match(no_num_sampling_start_re, filtering.text))
            me = (re.match(sampling_end_re, stopping.text) or
                  re.match(no_num_sampling_end_re, stopping.text))

            lsr_seq_num = re.search(lsr_seq_num_re, summary.text, re.MULTILINE)
            lsr_lsr_num_messages = re.search(lsr_num_messages_re, summary.text, re.MULTILINE)
            lsr_cartridge_number = re.search(lsr_cartridge_number_re, summary.text, re.MULTILINE)
            lsr_volume = re.search(lsr_volume_re, summary.text, re.MULTILINE)
            if not lsr_volume:
                self.logger.debug(f"Could not parse lsr_volume from '{summary.text}'")
                self.logger.debug(f"Attempting with lsr_volume_re_paused regex: {lsr_volume_re_paused}")
                lsr_volume = re.search(lsr_volume_re_paused, summary.text, re.MULTILINE)
            lsr_esp_error_msg = re.search(lsr_esp_error_msg_re, summary.text, re.MULTILINE)

            # Ensure that sample # (seq) numbers match
            try:
                if before_seq_num_implemented:
                    self.logger.info(f"This log is before seq_num was implemented - not checking for match")
                elif not (ms.groupdict().get('seq_num') == me.groupdict().get('seq_num') == lsr_seq_num.groupdict().get('seq_num')):
                    self.logger.warn(f"Sample numbers do not match for '{filtering.text}', '{stopping.text}', and '{summary.text}'")
            except AttributeError:
                if filtering and stopping and not lsr_seq_num:
                    sample_name = summary.text
                    self.logger.info(f"No ESP log summary report: Assigning sample_name = {sample_name}")
                else:
                    self.logger.warn(f"Sample numbers do not match for '{filtering.text}', '{stopping.text}', and '{summary.text}'")
            else:
                try:
                    sample_name = f"Cartridge {lsr_cartridge_number.groupdict().get('cartridge_number')}"
                    if lsr_seq_num:
                        self.logger.info(f"sample # = {lsr_seq_num.groupdict().get('seq_num')}, sample_name = {sample_name}")
                    else:
                        self.logger.info(f"(No 'sample #' match) sample_name = {sample_name}")
                except AttributeError:
                    # This should not happen. ESP log summary report should have a number of messages separated by newlines.
                    # - the TethysDash should deliver these messages in summary.text
                    # Remove ' ESP log summary report (2 messages)' text for sample_name
                    sample_name = summary.text.split('ESP')[0].strip()
                    self.logger.info(f"No ESP Cartridge number found: Assigning sample_name = {sample_name}")

            if not sample_name:
                self.logger.warn(f"Skipping this sample because of previous warning.")
                continue

            # Convert volumes to ml and check for error in optional 3rd line of messages from ESP
            volume = None
            if lsr_volume:
                if lsr_volume.groupdict().get('volume_units') == 'ml':
                    volume = float(lsr_volume.groupdict().get('volume_num'))
            if lsr_esp_error_msg:
                if lsr_esp_error_msg.groupdict().get('esp_error_message'):
                    # Instance of 'Slide::Error in PROCESSING -- Archive Syringe positionErr at 54ul (actually 72ul)' in:
                    # http://dods.mbari.org/data/lrauv/tethys/missionlogs/2018/20180906_20180917/20180908T084424/syslog
                    merr = re.match('.+actually (\d+)([a-z]+)', lsr_esp_error_msg.groupdict().get('esp_error_message'))
                    if merr:
                        if merr.group(2) == 'ul':
                            self.logger.info(f"Saving 'actually' volume following from {lsr_esp_error_msg.groupdict().get('esp_error_message')}")
                            volume = float(merr.group(1)) * 1.e-3
                    else:
                        # Instance of 'Syringe::PressureError in PROCESSING -- 24.5psi is out of 11.0..22.5 range -- Skipping SPR' in:
                        # http://dods.mbari.org/data/lrauv/makai/missionlogs/2019/20190822_20190827/20190822T194106/syslog
                        self.logger.info(f"Error encountered: {lsr_esp_error_msg.groupdict().get('esp_error_message')}")

                
            sample_names[sample_name] = SampleInfo(filtering.esec, stopping.esec, volume, summary.text)

        return sample_names

    def _sippers_from_json(self, platform_name, url, use_syslog=True):
        '''Retrieve Sipper (CANONSampler) information that's available in the syslogurl from the TethysDash REST API
        url looks like     'http://dods.mbari.org/opendap/data/lrauv/daphne/missionlogs/2018/20180220_20180221/20180221T074336/201802210743_201802211832_2S_scieng.nc',
        syslog_url is like 'http://dods.mbari.org/opendap/data/lrauv/daphne/missionlogs/2018/20180220_20180221/20180221T074336/syslog'
        Construct a TethysDash REST URL that looks like:
        https://okeanids.mbari.org/TethysDash/api/events?vehicles=daphne&from=2018-02-21T07:43&to=2018-02-21T18:32&eventTypes=logImportant&limit=100000
        Query it to build information on each Sipper sample in the url.
        '''
        samplings_at = []
        sample_num_errs = []
        
        # MBTS Missions in feb and mar 2022 need to subrtact 7 hours (GMT offset?) to get the right time slice from https://okeanids.mbari.org/TethysDash/api/events
        # - Turns out that unless 'Z' is appended then local time is assumed
        ##subtract_7_hours = True
        ##if subtract_7_hours:
        ##    from_dt = datetime.strptime(from_time, "%Y-%m-%dT%H:%M") - timedelta(hours=7)
        ##    to_dt = datetime.strptime(to_time, "%Y-%m-%dT%H:%M") - timedelta(hours=7)
        ##    from_time = datetime.strftime(from_dt, "%Y-%m-%dT%H:%M")
        ##    to_time = datetime.strftime(to_dt, "%Y-%m-%dT%H:%M")
        # Assuming that when use_syslog use began in December 2022 the above code is no longer needed

        SIPPERING = 'CANONSampler sampling at'
        if use_syslog:
            log_important, _ = self._read_syslog(url, components=('CANONSampler',))
            log_critical, _ = self._read_syslog(url, components=('CANONSampler',), levels=('CRITICAL',))
        else:
            log_important = self._read_tethysdash(platform_name, url)

        Log = namedtuple('Log', 'esec text')
        try:
            samplings_at = [Log(d['unixTime']/1000.0, d['text']) for d in log_important if SIPPERING in d['text']]
        except KeyError:
            self.logger.debug(f"No '{SIPPERING}' messages found {url}'s syslog")
        try:
            sample_num_errs = [Log(d['unixTime']/1000.0, d['text']) for d in log_important if re.match(SIPPER_NUM_ERR, d['text'])]
        except KeyError:
            self.logger.debug(f"No '{SIPPERING}' messages found in {url}'s syslog")

        if samplings_at and sample_num_errs:
            self.logger.info(f"Parsed {len(samplings_at)} '{SIPPERING}' strings and {len(sample_num_errs)} Sample numbers from {url}'s syslog")
        else:
            self.logger.info(f"No Sippers (CANONSampler) parsed from {url}'s syslog")
      
        return samplings_at, sample_num_errs

    def _match_sippers(self, samplings_at, sample_num_errs):
        '''Take lists from parsing TethysDash log and build Sipper names list with start and end times
        '''
        if len(samplings_at) != len(sample_num_errs):
            self.logger.warn(f"len(samplings_at) [{len(samplings_at)}] != len(sample_num_errs) [{len(sample_num_errs)}]")
            self.logger.warn("A Sipper logging error might have occurred -- check syslog")

        # Loop through exctractions from syslog to build dictionary
        sipper_names = defaultdict(SampleInfo)
        for sample_at, sample_num_err in zip(samplings_at, sample_num_errs):
            self.logger.debug(f"sample_at = {sample_at}")
            sne = re.match(SIPPER_NUM_ERR, sample_num_err.text)
            sample_name = f"Sipper {sne.groupdict().get('sipper_num')}"

            # Sipper does not report volume
            volume = None
            duration = sample_num_err.esec - sample_at.esec
            summary = f"{sample_at.text} Then {duration:.2f} seconds later: {sample_num_err.text}"
            sipper_names[sample_name] = SampleInfo(sample_at.esec, sample_num_err.esec, volume, summary)

        return sipper_names

    def _save_samples(self, db_alias, platform_name, activity_name, sampletype, samples, url, log_text, esp_device=None):
        # Load Samples and sample.text as a Resource associated with the Sample
        for sample_name, sample in samples.items():
            self.logger.info(f"Calling _create_activity_instantpoint_platform() for sample_name={sample_name}")
            try:
                act, ip, point, depth, maptrack = self._create_activity_instantpoint_platform(
                                                db_alias, platform_name, 
                                                activity_name, sampletype, url,
                                                sample.start, sample.end, sample_name, esp_device)
            except IntegrityError as e:
                self.logger.warn(f"Sample {sample_name} already loaded")
                continue
            if not act:
                continue

            try:
                samp, _ = (Sample.objects.using(db_alias).get_or_create( 
                            name = sample_name,
                            instantpoint = ip,
                            geom = point,
                            depth = depth,
                            sampletype = sampletype,
                            volume = sample.volume))
            except DataError as e:
                self.logger.error(f"{e}")
                self.logger.info(f"It's possible that the sample_name is too long: {sample_name}")
                raise

            # Update Activity with point and track of the Sampling event
            act.mappoint = point
            act.maptrack = maptrack
            self.logger.info(f"Saving {sampletype.name} Sample '{sample_name}': {sample.summary}, volume = {sample.volume} ml")
            act.save(using=db_alias)
            self.logger.debug(f"Updated Activity with point={point} and maptrack={maptrack}")

            # Associate Resource (log summary report text) with Sample
            res, _ = Resource.objects.using(db_alias).get_or_create(name=log_text, value=sample.summary)
            SampleResource.objects.using(db_alias).get_or_create(sample=samp, resource=res)
            self.logger.debug(f"Saved Resource {res}")

            # Associate Resource (ESP device name) with Sample and warn if device name not found in syslog
            if sampletype.name.startswith('ESP'):
                if esp_device:
                    res, _ = Resource.objects.using(db_alias).get_or_create(name='ESP_device_name', value=esp_device)
                    SampleResource.objects.using(db_alias).get_or_create(sample=samp, resource=res)
                    self.logger.debug(f"Saved Resource {res}")
                else:
                    # Likely an ESP Sample before Fall 2018 when "console:ESP... login" messages started appearing in the syslog
                    self.logger.warn(f"SampleType is {sampletype.name}, but no ESP device name found in syslog for {platform_name} {samp}")


    def load_lrauv_samples(self, platform_name, activity_name, url, db_alias):
        '''
        url looks like 'http://dods.mbari.org/opendap/data/lrauv/tethys/missionlogs/2018/20180906_20180917/20180908T084424/201809080844_201809112341_2S_scieng.nc'
        '''

        filterings, stoppings, summaries, criticals, esp_device = self._esps_from_json(platform_name, url, db_alias)
        filterings, stoppings, summaries = self._validate_summaries(platform_name, filterings, stoppings, summaries, criticals)

        # After 14 August 2018 a 'sample #<num>' is included in the log message:
        # https://bitbucket.org/mbari/lrauv-application/pull-requests/76/add-sample-to-all-logimportant-entries/diff
        # Before then don't require a seq_num match
        before_seq_num_implemented = False
        if datetime.strptime(url.split('/')[-1][:8], '%Y%m%d') < datetime(2018, 8, 14):
            before_seq_num_implemented = True
        esp_names = None
        if filterings and stoppings and summaries:
            esp_names = self._match_seq_to_cartridge(filterings, stoppings, summaries, 
                                                     before_seq_num_implemented=before_seq_num_implemented)

        samplings_at, sample_num_errs = self._sippers_from_json(platform_name, url)
        sipper_names = self._match_sippers(samplings_at, sample_num_errs)

        if esp_names:
            (esp_archive_type, created) = SampleType.objects.using(db_alias).get_or_create(name=ESP_FILTERING)
            self.logger.debug('sampletype %s, created = %s', esp_archive_type, created)
            self._save_samples(db_alias, platform_name, activity_name, esp_archive_type, esp_names, url,
                               log_text='ESP log summary report', esp_device=esp_device)

        if sipper_names:
            (sipper_type, created) = SampleType.objects.using(db_alias).get_or_create(name=SIPPER)
            self.logger.debug('sampletype %s, created = %s', sipper_type, created)
            self._save_samples(db_alias, platform_name, activity_name, sipper_type, sipper_names, url,
                               log_text='CANONSampler Sampled at message')

class SeabirdLoader(STOQS_Loader):
    '''
    Inherit database loading functions from STOQS_Loader and use its constructor
    '''
    def __init__(self, activityName, platformName, dbAlias='default', campaignName=None,
                activitytypeName=None, platformColor=None, platformTypeName='CTD', stride=1, dodsBase=None):
        self.pctdDir = dodsBase.split('dodsC')[1]
        'Just use the STOQS_Loader constructor'
        super(SeabirdLoader, self).__init__(activityName, platformName, dbAlias, campaignName,
                activitytypeName, platformColor, platformTypeName, stride)

    def buildParmDict(self):
        '''
        Build parameter dictionary akin to that returned by pydap.  The parameters from the .btl file must
        match the parameters read from the .nc file.  See comments for mapping copied from pctdToNetCDF.py.
        '''

        # Match the mapping done in pctdToNetCDF.py:

        # self.pr_list.append(float(r['PrDM']))
        # self.depth = self.ncFile.createVariable('depth', 'float64', ('time',))
        # self.depth.long_name = 'DEPTH'
        # self.depth.standard_name = 'depth'
        # self.depth.units = 'm'
        # self.depth[:] = csiro.depth(self.pr_list, self.lat_list)      # Convert pressure to depth

        # self.t1_list.append(r['T190C'])
        # temp = self.ncFile.createVariable('TEMP', 'float64', ('time',))
        # temp.long_name = 'Temperature, 2 [ITS-90, deg C]'
        # temp.standard_name = 'sea_water_temperature'
        # temp.units = 'Celsius'

        # self.sal_list.append(r['Sal00'])
        # sal = self.ncFile.createVariable('PSAL', 'float64', ('time',))
        # sal.long_name = 'Salinity, Practical [PSU]'
        # sal.standard_name = 'sea_water_salinity'

        # self.xmiss_list.append(r['Xmiss'])
        # xmiss = self.ncFile.createVariable('xmiss', 'float64', ('time',))
        # xmiss.long_name = 'Beam Transmission, Chelsea/Seatech'
        # xmiss.units = '%'

        # self.ecofl_list.append(r['FlECO-AFL'])
        # ecofl = self.ncFile.createVariable('ecofl', 'float64', ('time',))
        # ecofl.long_name = 'Fluorescence, WET Labs ECO-AFL/FL'
        # ecofl.units = 'mg/m^3'

        # self.oxygen_list.append(r['Sbeox0ML/L'])
        # oxygen = self.ncFile.createVariable('oxygen', 'float64', ('time',))
        # oxygen.long_name = 'Oxygen, SBE 43'
        # oxygen.units = 'ml/l'

        # Fake up a Pydap-like dataset
        self.ds = DatasetType('nameless')

        # The colname attribute must be the keys that DictReader returns - the keys of this dictionary will be the Parameter names in stoqs
        pr = BaseType('pressure')
        pr.attributes = {'colname': 'PrDM', 'units': 'm' , 'long_name': 'DEPTH', 'standard_name': 'depth'}
        self.ds['pressure'] = pr

        temp = BaseType('TEMP')
        temp.attributes = {'colname': 'T190C', 'units': 'ITS-90, deg C', 'long_name': 'temperature', 'standard_name': 'sea_water_temperature'}
        self.ds['TEMP'] = temp

        sal = BaseType('PSAL')
        sal.attributes = {'colname': 'Sal00', 'long_name': 'salinity', 'standard_name': 'sea_water_salinity'} 
        self.ds['PSAL'] = sal

        xmiss = BaseType('xmiss')
        xmiss.attributes = {'colname': 'Xmiss', 'units': '%', 'long_name': 'Beam Transmission, Chelsea/Seatech'}
        self.ds['xmiss'] = xmiss

        ecofl = BaseType('ecofl')
        ecofl.attributes = {'colname': 'FlECO-AFL', 'units': 'mg/m^3', 'long_name': 'Fluorescence, WET Labs ECO-AFL/FL'}
        self.ds['ecofl'] = ecofl

        wetstar = BaseType('wetstar')
        wetstar.attributes = {'colname': 'WetStar', 'units': 'mg/m^3', 'long_name': 'Fluorescence, WET Labs WETstar'}
        self.ds['wetstar'] = wetstar

        oxygen = BaseType('oxygen')
        oxygen.attributes = {'colname': 'Sbeox0ML/L', 'units': 'ml/l', 'long_name': 'Oxygen, SBE 43'}
        self.ds['oxygen'] = oxygen
        
        # Append ' (units)' to Parameter name
        parmDict = {}
        for name, var in self.ds.items():
            parameter_name, _ = self.parameter_name(var.name)
            parmDict[parameter_name] = var

        return parmDict

    def load_data(self, lat, lon, depth, mtime, parmNameValues):
        '''
        Load the data values recorded at the bottle trips so that we have some InstantPoints to 
        hang off for our Samples.  This is necessary as typically data are continuously acquired on the 
        down cast and bottles are tripped on the upcast with data collected just at the time of the bottle trip.  
        @parmNameValues is a list of 2-tuples of (ParameterName, Value) measured at the time and location specified by
        @lat decimal degrees
        @lon decimal degrees
        @mtime Python datetime.datetime object
        @depth in meters
        '''

        # Sanity check to prevent accidental switching of lat & lon
        if lat < -90 or lat > 90:
            self.logger.exception("lat = %f.  Can't load this!", lat)
            sys.exit(-1)

        try:
            measurement = self.createMeasurement(mtime=mtime, depth=depth, lat=lat, lon=lon)
        except SkipRecord as e:
            self.logger.info(e)
        except Exception as e:
            self.logger.error(e)
            sys.exit(-1)
        else:
            self.logger.debug("longitude = %s, latitude = %s, mtime = %s, depth = %s", lon, lat, mtime, depth)

        loaded = 0
        for pn,value in parmNameValues:
            self.logger.debug("pn = %s", pn)
            try:
                mp, _ = MeasuredParameter.objects.using(self.dbAlias).get_or_create(measurement = measurement,
                                                  parameter = self.getParameterByName(pn), datavalue = value)
            except Exception as e:
                self.logger.error(e)
                self.logger.exception("Bad value (id=%(id)s) for %(pn)s = %(value)s", {'pn': pn, 'value': value, 'id': mp.pk})
            else:
                loaded += 1
                self.logger.debug("Inserted value (id=%(id)s) for %(pn)s = %(value)s", {'pn': pn, 'value': value, 'id': mp.pk})

    def load_btl(self, lat, lon, depth, timevalue, bottleName):
        '''
        Load a single Niskin Bottle sample
        '''

        # Get the Activity from the Database
        try:
            activity = Activity.objects.using(self.dbAlias).get(name__contains=self.activityName)
            self.logger.debug('Got activity = %s', activity)
        except ObjectDoesNotExist:
            self.logger.warn('Failed to find Activity with name like %s.  Skipping GulperLoad.', self.activityName)
            return
        except MultipleObjectsReturned:
            self.logger.warn('Multiple objects returned for name__contains = %s.  Selecting one by random and continuing...', self.activityName)
            activity = Activity.objects.using(self.dbAlias).filter(name__contains=self.activityName)[0]
        
        # Get or create SampleType for Niskin
        (sample_type, created) = SampleType.objects.using(self.dbAlias).get_or_create(name=NISKIN)
        self.logger.debug('sampletype %s, created = %s', sample_type, created)
        # Get or create SamplePurpose for Niskin
        (sample_purpose, created) = SamplePurpose.objects.using(self.dbAlias).get_or_create(name = 'StandardDepth')
        self.logger.debug('samplepurpose %s, created = %s', sample_purpose, created)
        try:
            ip, _ = get_closest_instantpoint(self.activityName, timevalue, self.dbAlias)
            point = Point(lon, lat)
            Sample.objects.using(self.dbAlias).get_or_create( name = bottleName,
                                                                    depth = str(depth),     # Must be str to convert to Decimal
                                                                    geom = point,
                                                                    instantpoint = ip,
                                                                    sampletype = sample_type,
                                                                    samplepurpose = sample_purpose,
                                                                    volume = 20000.0
                                                                )
        except ClosestTimeNotFoundException:
            self.logger.warn('ClosestTimeNotFoundException: A match for %s not found for %s', timevalue, activity)
        else:
            self.logger.info('Loaded Bottle name = %s', bottleName)

    def process_btl_file(self, fh, year, lat, lon, btlUrl):
        '''
        Iterate through lines of iterator to Seabird .btl file and pull out data for loading into STOQS
        '''
        _debug = False
        tmpFile = NamedTemporaryFile(dir='/dev/shm', suffix='.btl').name
        self.logger.debug('tmpFile = %s', tmpFile)
        tmpFH = open(tmpFile, 'w')
        lastLine = ''
        for line in fh:
            # Write to tempfile all lines that don't begin with '*' nor '#' then open that with csv.DictReader
            # Concatenate broken lines that begin with 'Position...' and with HH:MM:SS, remove (avg|sdev)
            line = line.decode('latin-1')
            if not line.startswith('#') and not line.startswith('*'):
                m = re.match('.+(Sbeox0PS)(Sbeox0Mm)', line.strip())
                if m:
                    line = re.sub('(?<=)(Sbeox0PS)(Sbeox0Mm)(?=)', lambda m: "%s %s" % (m.group(1), m.group(2)), line)
                    if _debug: self.logger.debug('Fixed header: line = %s', line)
                if line.strip() == 'Position        Time':
                    # Append 2nd line of header to first line & write to tmpFile
                    if _debug: self.logger.debug('Writing ' + lastLine + line)
                    tmpFH.write(lastLine + line + '\n')
                m = re.match('\d\d:\d\d:\d\d', line.strip())
                if m:
                    # Append Time string to last line & write to tmpFile
                    if _debug: self.logger.debug('m.group(0) = %s', m.group(0))
                    if _debug: self.logger.debug('Writing ' + lastLine + m.group(0) + '\n')
                    tmpFH.write(lastLine + ' ' + m.group(0) + '\n')
                m = re.match('.+[A-Z][a-z][a-z] \d\d \d\d\d\d', line.strip())
                if m:
                    # Replace spaces with dashes in the date field
                    line = re.sub('(?<= )([A-Z][a-z][a-z]) (\d\d) (\d\d\d\d)(?= )', lambda m: "%s-%s-%s" % (m.group(1), m.group(2), m.group(3)), line)
                    if _debug: self.logger.debug('Spaces to dashes: line = %s', line)

                lastLine = line.rstrip()      # Save line without terminating linefeed

        tmpFH.close()
        try:
            fh.close()
        except AttributeError:
            pass    # fh is likely a list read in from a URL, ignore AttributeError

        # Create activity for this cast
        self.startDatetime = None
        self.endDatetime = None
        # Bottle records:
        # {'': None, 'Par': '1.0000e-12', 'PrDM': '201.442', 'Sbeox0Mm/Kg': '85.099', 'Potemp190C': '8.4225', 'Xmiss': '76.5307', 'Sigma-\xe911': '26.3792', 'DepSM': '199.859', 'Sbeox0PS': '29.72432', 'Sal11': '33.9416', 'V2': '1.0162', 'V1': '3.8616', 'C1S/m': '3.571764', 'T090C': '8.4430', 'V4': '0.0000', 'V5': '0.1305', 'V6': '2.6264', 'Date': 'Feb-04-2012', 'C0S/m': '3.571260', 'Bat': '1.0699', 'FlECO-AFL': '0.4249', 'Bottle': '1', 'Time': '09:20:05', 'Position': '(avg)', 'Sigma-\xe900': '26.3752', 'Sbeox0ML/L': '1.95575', 'Sal00': '33.9365', 'AltM': '52.53', 'Upoly0': '0.0002000', 'Scan': '14341', 'Sbeox0V': '1.0159', 'Potemp090C': '8.4223', 'V3': '0.0370', 'TimeJ': '35.722228', 'T190C': '8.4432'}

        for r in csv.DictReader(open(tmpFile), delimiter=' ', skipinitialspace=True):
            dt = datetime(year, 1, 1, 0, 0, 0) + timedelta(days=float(r['TimeJ'])) - timedelta(days=1)
            if not self.startDatetime:
                self.startDatetime = dt
        try:
            self.endDatetime = dt
        except UnboundLocalError:
            self.logger.warn(f'Not able to read time from bottle file for {self.activityName}')
            return

        self.platform = self.getPlatform(self.platformName, self.platformTypeName)
        self.activitytypeName = 'CTD upcast'

        # Bottle samples are to be loaded after downcast data are loaded so that we can use the same activity
        try:
            activity = Activity.objects.using(self.dbAlias).get(name__contains=self.activityName)
            self.logger.debug('Got activity = %s', activity)
            self.activity = activity
        except ObjectDoesNotExist:
            self.logger.warn('Failed to find Activity with name like %s.  Expected that downcast was data before loading bottles.', self.activityName)
            self.logger.info('Creating Activity for these bottles')
            self.createActivity()
            ##raise SingleActivityNotFound('Failed to find Activity with name like %s' % self.activityName)
        except MultipleObjectsReturned:
            self.logger.error('Multiple objects returned for name__contains = %s.'
                         'This should not happen.  Fix the database and the reason for this.',
                         self.activityName)
            raise SingleActivityNotFound('Multiple objects returned for name__contains = %s' % self.activityName)

        parmDict = self.buildParmDict()
        self.logger.debug('Calling add_parameters for parmDict = %s', parmDict)
        self.include_names = list(self.ds.keys())
        # add_parameters() from the base class expects a 'ds' parameter dictionary
        self.url = btlUrl
        self.add_parameters(self.ds)

        for r in csv.DictReader(open(tmpFile), delimiter=' ', skipinitialspace=True):
            dt = datetime(year, 1, 1, 0, 0, 0) + timedelta(days=float(r['TimeJ'])) - timedelta(days=1)
            ##esDiff = dt - datetime(1970, 1, 1, 0, 0, 0)
            ##es = 86400 * esDiff.days + esDiff.seconds
            bName = r['Bottle']

            self.logger.debug('r = %s', r)
            # Load data 
            parmNameValues = []
            for name in list(parmDict.keys()):
                self.logger.debug('name = %s, parmDict[name].attributes = %s', name, parmDict[name].attributes)
                try:
                    parmNameValues.append((name, float(r[parmDict[name].attributes['colname']])))
                except KeyError as e:
                    # Accomodations for sub compact CTD
                    if parmDict[name].attributes['colname'] == 'T190C':
                        parmNameValues.append((name, float(r['Tv290C'])))
                    elif parmDict[name].attributes['colname'] == 'PrDM':
                        parmNameValues.append((name, float(r['PrdM'])))
                    elif parmDict[name].attributes['colname'] == 'FlECO-AFL':
                        continue
                    elif parmDict[name].attributes['colname'] == 'WetStar':
                        continue
                    else:
                        raise KeyError(e)

            self.load_data(lat, lon, float(r['DepSM']), dt, parmNameValues)

            # Load Bottle sample
            if _debug:
                self.logger.info('Calling load_btl(%s,%s,%s,%s,%s)', lat, lon, float(r['DepSM']), dt, bName)
            self.load_btl(lat, lon, float(r['DepSM']), dt, bName)

        os.remove(tmpFile)

    def process_btl_files(self, seabirdFileList=()):
        '''
        Loop through all .btl files and insert a Sample record to the database for each bottle trip.  Assumes that c*.btl files 
        are available in a local pctd directory, if not then they are read from a THREDDS server.

        Processed c*.btl files look like (after xml header):

    Bottle        Date      Sal00      Sal11  Sigma-00  Sigma-11 Sbeox0ML/L   Sbeox0PSSbeox0Mm/Kg Potemp090C Potemp190C      TimeJ       PrDM      DepSM      C0S/m      C1S/m      T090C      T190C        Bat      Xmiss         V1    Sbeox0V         V2  FlECO-AFL         V3     Upoly0         V4        Par         V5       AltM         V6       Scan
  Position        Time                                                                                                                                                                                                                                                                                                                                          
      2    Sep 10 2012    34.0050    34.0045    26.3491    26.3486    1.63257   25.10932     71.039     8.9360     8.9366 255.145990    202.002    200.414   3.624756   3.624763     8.9575     8.9582     0.5715    86.6855     4.3660     0.9883     0.9888     0.3746     0.0350  0.0002000     0.0000 1.0000e-12     0.1303     100.00     5.0000      11246 (avg)
              20:30:15                                                                                                    1.7398e-05      0.071      0.071   0.000030   0.000058     0.0003     0.0008     0.0082     0.1775     0.0088     0.0004     0.0004     0.0146     0.0006  0.0000000     0.0000 0.0000e+00     0.0005       0.00     0.0000         35 (sdev)
      3    Sep 10 2012    33.9433    33.9424    26.2372    26.2363    1.91904   29.75985     83.513     9.3330     9.3342 255.147702    150.644    149.478   3.652452   3.652470     9.3495     9.3507     0.4231    89.9630     4.5288     1.0855     1.0858     0.3890     0.0355  0.0002000     0.0000 1.0000e-12     0.1293     100.00     5.0000      14795 (avg)
              20:32:43

        If seabirdFileList is given then process through those files in the list, otherwise process all .btl files in 
        self.parentInDir.  This is handy for debugging in that only the files in the list are processed.
        '''
        try:
            fileList = glob(os.path.join(self.parentInDir, 'pctd/*c*.btl'))
        except AttributeError:
            fileList = []
        if fileList:
            # Read files from local pctd directory
            fileList.sort()
            for bfile in fileList:
                self.activityName = bfile.split('/')[-1].split('.')[-2] 
                year, lat, lon = get_year_lat_lon(bfile)
                fh = open(bfile)
                try:
                    self.process_btl_file(fh, year, lat, lon)
                except SingleActivityNotFound:
                    continue

        else:
            # Read files from the network - use BeautifulSoup to parse TDS's html response
            webBtlDir = self.tdsBase + 'catalog/' + self.pctdDir + 'catalog.html'
            self.logger.debug('Opening url to %s', webBtlDir)
            soup = BeautifulSoup(urlopen(webBtlDir).read(), 'lxml')
            linkList = soup.find_all('a')
            sorted(linkList, key=lambda elem: elem.text)
            for link in linkList:
                bfile = link.get('href')
                if bfile.endswith('.btl'):
                    self.logger.debug("bfile = %s", bfile)
                    if bfile.split('/')[-1].split('.')[0] + '.nc' not in seabirdFileList:
                        self.logger.warn('Skipping %s as it is in not in seabirdFileList = %s', bfile, seabirdFileList)
                        continue

                    # btlUrl looks something like: http://odss.mbari.org/thredds/fileServer/CANON_september2012/wf/pctd/c0912c53.btl
                    btlUrl = self.tdsBase + 'fileServer/' +  self.pctdDir + bfile.split('/')[-1]
                    hdrUrl = self.tdsBase + 'fileServer/' +  self.pctdDir + ''.join(bfile.split('/')[-1].split('.')[:-1]) + '.hdr'
                    self.logger.info('btlUrl = %s', btlUrl)
    
                    self.activityName = bfile.split('/')[-1].split('.')[-2] 
                    year, lat, lon = get_year_lat_lon(hdrUrl = hdrUrl)
                    btlFH = urlopen(btlUrl).read().splitlines()
                    try:
                        self.process_btl_file(btlFH, year, lat, lon, btlUrl)
                    except SingleActivityNotFound:
                        continue

        # TODO: Adjust Activity downcast + upcast(bottle trips) times to include all data


class SubSamplesLoader(STOQS_Loader):
    '''
    Inherit database loading functions from STOQS_Loader and use its constructor.
    This class is designed to load subsample information for Samples that have already
    been loaded into a STOQS database.  The input data will have a key field that will
    match to an existing Sample and SampledParameter data that will need to be loaded
    in.
    '''

    def load_subsample(self, parentSample, row):
        '''
        Populate the Sample, SampledParameter, SampleRelationship, and associated lookup tables 
        (SampleType, SamplePurpose, AnalysisMethod) with data in the row from the spreadsheet.
        '''
        parameter_value = row.get('Parameter Value')
        if not parameter_value:
            raise SubSampleLoadError("Must have a row['Parameter Value'] to load subsample")

        (sampleType, created) = SampleType.objects.using(self.dbAlias).get_or_create(name='subsample')
        (samplePurpose, created) = SamplePurpose.objects.using(self.dbAlias).get_or_create(name=row['Sample Type'])

        fd = None
        if row.get('Filter Diameter [mm]'):
            fd = float(row['Filter Diameter [mm]'])
        fps = None
        try:
            if row.get('Filter Pore Size [uM]'):
                fps = float(row['Filter Pore Size [uM]'])
        except KeyError:
            try:
                if row.get('Filter Pore Size [um]'):
                    fps = float(row['Filter Pore Size [um]'])
            except ValueError as e:
                # Likely a strange character present in a units string
                if row.get('Filter Pore Size [um]'):
                    fps = float(row.get('Filter Pore Size [um]').split()[0])
        except ValueError as e:
            # Likely a strange character present in a units string
            if row.get('Filter Pore Size [uM]'):
                fps = float(row.get('Filter Pore Size [uM]').split()[0])
            
        vol = row.get('Sample Volume [mL]')
        if not vol:
            if row.get('Sample Volume [m^3]'):
                vol = float(row.get('Sample Volume [m^3]')) * 1.e6     # A million ml per cubic meter
        if not vol:
            self.logger.warn('Sample Volume [mL] or Sample Volume [m^3] is not specified.'
                        ' Assigning default value of 280.'
                        ' PLEASE SPECIFY THE VOLUME IN THE SPREADSHEET.')
            vol = 280           # Default volume is 280 ml - this is a required field so display a warning

        sample = Sample(  instantpoint=parentSample.instantpoint,
                            depth=parentSample.depth,
                            geom=parentSample.geom,
                            name=parentSample.name,
                            volume=float(vol),
                            filterdiameter=fd,
                            filterporesize=fps,
                            laboratory=row['Laboratory'],
                            researcher=row['Researcher'],
                            sampletype=sampleType,
                            samplepurpose=samplePurpose)
        sample.save(using=self.dbAlias)

        samplerelationship = SampleRelationship(child=sample, parent=parentSample)
        samplerelationship.save(using=self.dbAlias)
                  
        parameter_name = row.get('Parameter Name')
        spaceRemoveMsg = ''
        if parameter_name.find(' ') != -1:
            spaceRemoveMsg = ("row['Parameter Name'] = %s contains a space. Replacing"
                              " with '_' before adding to STOQS." % parameter_name)
            self.logger.debug(spaceRemoveMsg)
            parameter_name = parameter_name.replace(' ', '_')

        if '(' in parameter_name or ')' in parameter_name:
            parenRemoveMsg = ("row['Parameter Name'] = %s contains ( or ). Removing"
                              " them before adding to STOQS." % parameter_name)
            self.logger.debug(parenRemoveMsg)
            parameter_name = parameter_name.replace('(', '').replace(')', '')

        parameter_units = row.get('Parameter Units')
        (parameter, created) = Parameter.objects.using(self.dbAlias).get_or_create(name=parameter_name, units=parameter_units)
        self.logger.debug('parameter, created = %s, %s', parameter, created)
        if created and spaceRemoveMsg:
            self.logger.info(spaceRemoveMsg)
    
        analysisMethod = None
        if row['Analysis Method']:
            (analysisMethod, created) = AnalysisMethod.objects.using(self.dbAlias
                    ).get_or_create(name=removeNonAscii(row['Analysis Method']))

        sp = SampledParameter(sample=sample, parameter=parameter, 
                datavalue=parameter_value, analysismethod=analysisMethod)
        try:
            sp.save(using=self.dbAlias)
        except ValidationError as e:
            self.logger.warn(str(e))

        return parameter
                                
    def delete_subsample(self, parentSample, row):
        '''
        Delete the subsample represented by the data in @row from the database
        '''
        parameter_value = row.get('Parameter Value')
        if not parameter_value:                 # Must have a value to proceed
            return

        fd = None
        if row['Filter Diameter [mm]']:
            fd = float(row['Filter Diameter [mm]'])
        fps = None
        if row['Filter Pore Size [uM]']:
            fps = float(row['Filter Pore Size [uM]'])

        samples = Sample.objects.using(self.dbAlias).filter(
                            instantpoint=parentSample.instantpoint,
                            depth=parentSample.depth,
                            geom=parentSample.geom,
                            volume=float(row['Sample Volume [mL]']),
                            filterdiameter=fd,
                            filterporesize=fps,
                            laboratory=row['Laboratory'],
                            researcher=row['Researcher'],
                            )
        if not samples:
            self.logger.debug('No samples returned from query of parentSample = %s and row = %s', parentSample, row)
            return

        if len(samples) == 1:
            self.logger.debug('Deleting subsample %s from database %s', samples[0], self.dbAlais)
            samples[0].delete(using=self.dbAlias)
        else:
            self.logger.warn('More than one subsample returned for query of parentSample = %s and row = %s', parentSample, row)
            self.logger.debug('samples.query = %s', str(samples.query))
            self.logger.warn('Removing them all...')
            for s in samples:
                self.logger.debug('s.id = %s', s.id)
                s.delete(using=self.dbAlias)

    def process_subsample_file(self, fileName, unloadFlag=False):
        '''
        Open .csv file and load the data, matching to existing Sample.
        The format of the file is as defined by Julio's work.  The first few records look like:

            Cruise,Bottle Number,Sample Type,Sample Volume [mL],Filter Diameter [mm],Filter Pore Size [uM],Parameter Name,Parameter Value,Parameter Units,MBARI BOG Taxon Code,Laboratory,Researcher,Analysis Method,Comment Name,Comment Value
            2011_074_02_074_02,0,random,1500,25,30,B1006 barnacles,0.218,OD A450 nm,,Vrijenhoek,Harvey,Sandwich Hybridization Assay,,
            2011_074_02_074_02,0,random,1500,25,30,M2B mussels,0.118,OD A450 nm,,Vrijenhoek,Harvey,Sandwich Hybridization Assay,,

        If @unloadFlag is True then delete the subsamples from @fileName from the database.  This is useful for testing.
        '''
        subCount = 0
        parameter = None
        loadedParentSamples = []
        self.parameter_counts = {}
        for r in csv.DictReader(open(fileName, encoding='latin-1')):
            self.logger.debug(r)
            aName = r['Cruise']

            if aName == '2011_257_00_257_01':
                aName = '2011_257_00_257_00'      # Correct a typo in Julio's spreadsheet

            try:
                # Try first with %.1f formatted bottle number for Gulper - TODO: Deprecate this!
                sample_name = '%.1f' % float(r['Bottle Number'])
                parentSample = Sample.objects.using(self.dbAlias).filter( 
                        instantpoint__activity__name__icontains=aName, 
                        name=sample_name)[0]
            except IndexError:
                try:
                    # Try without formatted %.1 for bottle number
                    sample_name = r['Bottle Number']
                    parentSample = Sample.objects.using(self.dbAlias).filter(
                            instantpoint__activity__name__icontains=aName, 
                            name=sample_name)[0]
                except IndexError:
                    self.logger.error('Parent Sample not found for Cruise (Activity Name) = %s, Bottle Number = %s', aName, r['Bottle Number'])
                    continue
                    ##sys.exit(-1)
            except KeyError:
                # Special for Plankton Pump, Comment Value is 'Relative Depth'
                sample_name = r.get('Comment Value')
                self.logger.debug('aName=%s, name=%s', aName, sample_name)
                try:
                    parentSample = Sample.objects.using(self.dbAlias).get(
                        sampletype__name=PLANKTONPUMP,
                        instantpoint__activity__name__icontains=aName, 
                        name=sample_name)
                except ObjectDoesNotExist:
                    self.logger.warn('Parent Sample not found for Activity %s, name %s. Skipping.', 
                            aName, sample_name)

            except ValueError as e:
                # Likely a 'NetTow' string in the Bottle Number column
                if r['Bottle Number'] == 'NetTow':
                    try:
                        # Convention is one NetTow per cast, given them all a name of '1'
                        sample_name = '1'
                        parentSample = Sample.objects.using(self.dbAlias).select_related(
                                'instantpoint__activity').filter(
                                instantpoint__activity__name__icontains=aName + '_NetTow1', )[0]
                    except IndexError as e:
                        self.logger.warn('Parent Sample not found for Activity %s. Skipping.', aName)
                        continue
                else:
                    raise e

            if unloadFlag:
                # Unload subsample
                self.delete_subsample(parentSample, r)
            else:
                if parameter and subCount and parentSample not in loadedParentSamples:
                    # Useful logger output when parentSample changes - more useful when spreadsheet is sorted by parentSample
                    self.logger.info('%d subsamples loaded of %s from %s', subCount, parameter.name, os.path.basename(fileName))

                    self.logger.info('Loading subsamples of parentSample (activity, bottle/name) = (%s, %s)', aName, sample_name)
                    subCount = 0

                try:
                    # Load subsample
                    parameter = self.load_subsample(parentSample, r)
                except SubSampleLoadError as e:
                    self.logger.warn(e)
                    continue
                else:
                    subCount = subCount + 1
                    try:
                        self.parameter_counts[parameter] += 1
                    except KeyError:
                        self.parameter_counts[parameter] = 0

                    loadedParentSamples.append(parentSample)
   
        if not unloadFlag and parameter: 
            # Last logger info message and finish up the loading for this file
            self.logger.info('%d subsamples loaded of %s from %s', subCount, parameter.name, os.path.basename(fileName))

            self.assignParameterGroup(groupName=SAMPLED)
            self.postProcess()

    def postProcess(self):
        '''
        Perform step(s) following subsample loads, namely inserting/updating records in the ActivityParameter
        table.  The updateActivityParameterStats() method in STOQS_Loader expects a hash of parameters
        that are unique to an activity that is an attribute of self.
        '''
        for row in SampledParameter.objects.using(self.dbAlias).values('sample__instantpoint__activity__pk').distinct():
            a_id = row['sample__instantpoint__activity__pk']
            self.logger.debug('a_id = %d', a_id)
            self.activity = Activity.objects.using(self.dbAlias).get(pk=a_id)
            self.updateActivityParameterStats(sampledFlag=True)


if __name__ == '__main__':

    # Accept optional arguments of dbAlias, input data directory name, and output directory name
    # If not specified then 'default' and the current directory is used
    try:
        dbAlias = sys.argv[1]
    except IndexError:
        dbAlias = 'stoqs_dorado2011_s100'

    try:
        unload = sys.argv[2]
    except IndexError:
        pass
    else:
        ssl = SubSamplesLoader('', '', dbAlias=dbAlias)
        ssl.process_subsample_file('2011_AUVdorado_Samples_Database.csv', True)
        sys.exit(0)
        

    # Test SubSamplesLoader
    ssl = SubSamplesLoader('', '', dbAlias=dbAlias)
    ssl.process_subsample_file('2011_AUVdorado_Samples_Database.csv')

    sys.exit(0)

    # Test SeabirdLoader
    sl = SeabirdLoader('activity name', 'wf_pctd', dbAlias=dbAlias)
    ##sl.parentInDir = '.'  # Set if reading data from a directory rather than a TDS URL
    # Catalog to .btl files is formed with sl.tdsBase + 'catalog/' + sl.pctdDir + 'catalog.html'
    sl.tdsBase= 'http://odss.mbari.org/thredds/' 
    sl.pctdDir = 'CANON_september2012/wf/pctd/'
    sl.campaignName = 'CANON - September 2012'
    sl.process_btl_files()


    # Test load_gulps: A nice test data load for a northern Monterey Bay survey  
    ##file = 'Dorado389_2010_300_00_300_00_decim.nc'
    ##dbAlias = 'default'
    auv_file = 'Dorado389_2010_277_01_277_01_decim.nc'
    dbAlias = 'stoqs_oct2010'

    aName = file

    load_gulps(aName, auv_file, dbAlias)

