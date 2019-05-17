import os
import sys
# Add parent dir to pythonpath so that we can see the loaders and stoqs modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../") )
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
from django.conf import settings

from collections import defaultdict, namedtuple
from datetime import datetime
from loaders import STOQS_Loader
from stoqs.models import (Activity, ResourceType, Resource, Measurement, MeasuredParameter,
                          MeasuredParameterResource, ResourceResource)
from utils.STOQSQManager import LABEL, DESCRIPTION, LRAUV_MISSION

import requests

STARTED_MISSION = 'Started mission'

class MissionLoader(STOQS_Loader):
    '''Holds methods customized for reading information from MBARI's LRAUVs
    '''
    def _missions_from_json(self, platform_name, url):
        '''Retrieve Start mission information that's available in the syslogurl from the TethysDash REST API
        url looks like 'http://dods.mbari.org/opendap/data/lrauv/tethys/missionlogs/2018/20180906_20180917/20180908T084424/201809080844_201809112341_2S_scieng.nc'
        Construct a TethysDash REST URL that looks like:
        https://okeanids.mbari.org/TethysDash/api/events?vehicles=tethys&from=2018-09-08T00:00&to=2018-09-08T06:00&eventTypes=logImportant&limit=1000
        Query it to build information on each mission in the url.
        '''
        mission_starts = []

        st = url.split('/')[-1].split('_')[0]
        et = url.split('/')[-1].split('_')[1]
        from_time = f"{st[0:4]}-{st[4:6]}-{st[6:8]}T{st[8:10]}:{st[10:12]}"
        to_time = f"{et[0:4]}-{et[4:6]}-{et[6:8]}T{et[8:10]}:{et[10:12]}"

        # Sanity check the ending year
        try:
            if int(et[0:4]) > datetime.now().year:
                self.logger.warn(f"Not looking for Samples for url = {url} as the to date is > {datetime.now().year}")
                return mission_starts
        except ValueError:
            # Likely an old slate.nc4 file that got converted to a .nc file
            self.logger.warn(f"Could not parse end date year from url = {url}")
            return mission_starts

        td_url = f"https://okeanids.mbari.org/TethysDash/api/events?vehicles={platform_name}&from={from_time}&to={to_time}&eventTypes=logImportant&limit=100000"

        self.logger.debug(f"Opening td_url = {td_url}")
        with requests.get(td_url) as resp:
            if resp.status_code != 200:
                self.logger.error('Cannot read %s, resp.status_code = %s', syslog_url, resp.status_code)
                return
            td_log_important = resp.json()['result']

        Mission = namedtuple('Mission', 'esec text')
        try:
            mission_starts = [Mission(d['unixTime']/1000.0, d['text']) for d in td_log_important if STARTED_MISSION in d['text']]
        except KeyError:
            self.logger.debug(f"No '{STARTED_MISSION}' messages found in {td_url}")

        if mission_starts:
            self.logger.info(f"Parsed {len(mission_starts)} Missions from {td_url}")
        else:
            self.logger.info(f"No Missions parsed from {td_url}")

        return mission_starts

    def _make_starts_ends_names(self, mission_starts, activity, db_alias):
        '''Make start and end datetimes for each mission name
        '''
        starts = []
        ends = []
        names = []
        for mc in range(len(mission_starts)):
            starts.append(datetime.utcfromtimestamp(mission_starts[mc].esec))
            try:
                ends.append(datetime.utcfromtimestamp(mission_starts[mc+1].esec))
            except IndexError:
                ends.append(activity.enddate)
            names.append(mission_starts[mc].text.replace(STARTED_MISSION, ''))

        return starts, ends, names

    def load_missions(self, platform_name, activity_name, url, db_alias):
        '''Parse the syslog looking for messages that identify the starts of missions.
        There's always a mission running on an LRAUV.
        url looks like 'http://dods.mbari.org/opendap/data/lrauv/tethys/missionlogs/2018/20180906_20180917/20180908T084424/201809080844_201809112341_2S_scieng.nc'
        '''
        syslog_url = "{}/syslog".format('/'.join(url.replace('opendap/', '').split('/')[:-1]))
        self.logger.info(f"Getting Sample information from the TethysDash API that's also in {syslog_url}")
        mission_starts = self._missions_from_json(platform_name, url)
        activity = Activity.objects.using(db_alias).get(name=activity_name)
        starts, ends, names = self._make_starts_ends_names(mission_starts, activity, db_alias)

        rt, _ = ResourceType.objects.using(db_alias).get_or_create(name=LRAUV_MISSION, description='LRAUV Mission name as retrieved from TethysDash api')

        # We can use the machinery of Labeled data to label the mission's Measured Parameters -- describe the source of it
        rdt, _ = ResourceType.objects.using(db_alias).get_or_create(name=LABEL, description='metadata')
        lrauv_mission_res, _ = (Resource.objects.using(db_alias)
                                        .get_or_create(name=LRAUV_MISSION, 
                                                       value=f"{STARTED_MISSION} parsed from syslog", 
                                                       uristring=syslog_url, 
                                                       resourcetype=rdt))

        for start, end, name in zip(starts, ends, names):
            self.logger.info(f"Associating with MeasuredParameters LRAUV mission '{name}' in Activity {activity}")
            # This Resource name appears in the STOQS UI in blue text of the Attributes -> Measurement tab
            res, _ = Resource.objects.using(db_alias).get_or_create(name=LRAUV_MISSION, value=name, resourcetype=rt)
            # Associate with Resource that describes the source
            ResourceResource.objects.using(db_alias).get_or_create(fromresource=res, 
                                                                   toresource=lrauv_mission_res)
            # Create collections of MeasuredParameterResources for each Measurement in the Mission
            for meas in (Measurement.objects.using(db_alias)
                                    .filter(instantpoint__activity__name=activity_name, 
                                            instantpoint__timevalue__gte=start, 
                                            instantpoint__timevalue__lt=end)):
                for mp in MeasuredParameter.objects.using(db_alias).filter(measurement=meas):
                    mpr, _ = (MeasuredParameterResource.objects.using(db_alias)
                                                       .get_or_create(measuredparameter=mp,
                                                                      resource=res,
                                                                      activity=activity))

