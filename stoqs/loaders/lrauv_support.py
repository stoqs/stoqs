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
                          MeasuredParameterResource, ResourceResource, Campaign,
                          SimpleDepthTime, ActivityType)
from utils.STOQSQManager import LABEL, DESCRIPTION, LRAUV_MISSION

import numpy as np
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
        '''Make start and end datetimes for each mission name.  TethysDash API response delivers most
        recent first, so need to reverse the response.
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
            names.append(mission_starts[mc].text.replace(STARTED_MISSION, '').strip())

        return reversed(starts), reversed(ends), reversed(names)

    def _update_mission_activity(self):
        '''Update maptrack, num_measuredparameters, ...
        '''
        pass

    def load_missions(self, platform_name, activity_name, url, db_alias):
        '''Parse the syslog looking for messages that identify the starts of missions.
        There's always a mission running on an LRAUV.
        url looks like 'http://dods.mbari.org/opendap/data/lrauv/tethys/missionlogs/2018/20180906_20180917/20180908T084424/201809080844_201809112341_2S_scieng.nc'
        '''
        syslog_url = "{}/syslog".format('/'.join(url.replace('opendap/', '').split('/')[:-1]))
        self.logger.info(f"Getting Sample information from the TethysDash API that's also in {syslog_url}")
        mission_starts = self._missions_from_json(platform_name, url)
        campaign = Campaign.objects.using(db_alias).get()
        activity = Activity.objects.using(db_alias).get(name=activity_name)
        starts, ends, names = self._make_starts_ends_names(mission_starts, activity, db_alias)

        rt, _ = (ResourceType.objects.using(db_alias)
                             .get_or_create(name=LRAUV_MISSION, 
                                            description='LRAUV Mission name as retrieved from TethysDash api'))
        activity_type, _ = (ActivityType.objects.using(db_alias)
                                        .get_or_create(name=LRAUV_MISSION))

        # We can use the machinery of Labeled data to label the mission's Measured Parameters -- describe the source of it
        rdt, _ = ResourceType.objects.using(db_alias).get_or_create(name=LABEL, description='metadata')
        lrauv_mission_res, _ = (Resource.objects.using(db_alias)
                                        .get_or_create(name=LRAUV_MISSION, 
                                                       value=f"{STARTED_MISSION} parsed from syslog", 
                                                       uristring=syslog_url, 
                                                       resourcetype=rdt))

        # Create the new Activities with the start and end times encompassing all the nemes in the set
        MissionActivity = namedtuple('MissionActivity', 'start end count')
        ma = {}
        ma_count = defaultdict(int)
        for start, end, name in zip(starts, ends, names):
            ma_count[name] += 1
            if name not in ma:
                ma[name] = MissionActivity(start, end, ma_count[name])
            else:
                # Update the end value and count, retaining the initial start
                ma[name] = MissionActivity(ma[name].start, end, ma_count[name])

        activity_by_mission = {}
        for name, mission_activity in ma.items():
            self.logger.info(f"Creating {LRAUV_MISSION} Activity for mission: {name} ")
            # LRAUV_MISSION Activity may exist from an earlier activity, try and get
            # it from the DB by just its name, type, and platform in the campaign
            try:
                act = Activity.objects.using(db_alias).get(name=name, 
                                                           activitytype=activity_type, 
                                                           campaign=campaign, 
                                                           platform=activity.platform)
            except Activity.DoesNotExist:
                comment = f"Created by stoqs/loaders/{__name__}.py load_missions():"
                act = Activity(name=name, 
                               activitytype=activity_type,
                               campaign=campaign, 
                               platform=activity.platform, 
                               startdate=mission_activity.start,
                               comment=comment)

            # Always update the enddate and comment - save the Activity for use below
            act.enddate = mission_activity.end
            act.comment += f" {mission_activity.count} missions from {syslog_url}"
            act.save(using=db_alias)
            activity_by_mission[name] = act            

        last_name = ''
        for start, end, name in zip(starts, ends, names):
            self.logger.info(f"LRAUV mission '{name}' in Activity {activity}: start={start}, end={end}")
            self.logger.info(f"Associating with MeasuredParameters for Attribute selection in the UI")
            # This Resource name appears in the STOQS UI in blue text of the Attributes -> Measurement tab
            res, _ = Resource.objects.using(db_alias).get_or_create(name=LRAUV_MISSION, value=name, resourcetype=rt)
            # Associate with Resource that describes the source
            ResourceResource.objects.using(db_alias).get_or_create(fromresource=res, 
                                                                   toresource=lrauv_mission_res)
            # Create collections of MeasuredParameterResources for each Measurement in the Mission
            for count, meas in enumerate(Measurement.objects.using(db_alias)
                                    .filter(instantpoint__activity__name=activity_name, 
                                            instantpoint__timevalue__gte=start, 
                                            instantpoint__timevalue__lt=end)):
                if not count % 100:
                    self.logger.debug(f"{count:5d}: timevalue = {meas.instantpoint.timevalue}")
                for mp in MeasuredParameter.objects.using(db_alias).filter(measurement=meas):
                    mpr, _ = (MeasuredParameterResource.objects.using(db_alias)
                                                       .get_or_create(measuredparameter=mp,
                                                                      resource=res,
                                                                      activity=activity))

            # Associate copies of SimpleDepthTime with the mission Activity for overview data viz
            self.logger.info(f"Associating with SimpleDepthTime copies with Activity {name}")
            last_sdt = None
            for count, sdt in enumerate(SimpleDepthTime.objects.using(db_alias)
                                   .filter(instantpoint__timevalue__gte=start,
                                           instantpoint__timevalue__lt=end)):
                # Copy the object with a new foreign key reference to the additional activity
                # See: https://docs.djangoproject.com/en/2.2/topics/db/queries/#copying-model-instances
                if not count % 100:
                    self.logger.debug(f"{count:5d}: timevalue = {sdt.instantpoint.timevalue}")
                sdt.pk = None
                sdt.activity = activity_by_mission[name]
                sdt.save(using=db_alias)
                last_sdt = sdt

            if last_sdt:
                if name != last_name:
                    # Add a NaN value to the previous simpledepth time series to cause a break in the Flot plot
                    sdt_break = SimpleDepthTime(instantpoint=last_sdt.instantpoint, 
                                                depth=np.nan, 
                                                activity=activity_by_mission[name],
                                                epochmilliseconds=last_sdt.epochmilliseconds+1)
                    sdt_break.save(using=db_alias)

            last_name = name

