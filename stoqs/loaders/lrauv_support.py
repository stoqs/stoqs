import os
import sys
# Add parent dir to pythonpath so that we can see the loaders and stoqs modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../") )
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
from django.conf import settings
from django.db.models import Max, Min

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

    def _make_starts_ends_names(self, mission_starts, orig_activity, db_alias):
        '''Make start and end datetimes for each mission name.
        '''
        starts = []
        ends = []
        names = []
        # TethysDash API response delivers most recent first, so need to reverse the order.
        for mc in range(len(mission_starts)-1, -1, -1):
            starts.append(datetime.utcfromtimestamp(mission_starts[mc].esec))
            try:
                ends.append(datetime.utcfromtimestamp(mission_starts[mc-1].esec))
            except IndexError:
                ends.append(orig_activity.enddate)

            name = mission_starts[mc].text.replace(STARTED_MISSION, '').strip()

            # Prevent bad (too long with line feeds) name
            if len(name) > 255:
                self.logger.warn(f"Mission named parsed from TethysDash is too big with length of {len(name)}")
                self.logger.warn(f"{name}")
                name = name.split('\n')[0]
                self.logger.info(f"Truncated at newline; name = {name}")

            names.append(name)

        return starts, ends, names

    def _create_mission_activities(self, db_alias, orig_activity, starts, ends, names, syslog_url):
        '''Go through mission information extracted from TethysDash and create an
        Activity for each named mission
        '''
        campaign = Campaign.objects.using(db_alias).get()
        activitytype, _ = (ActivityType.objects.using(db_alias)
                                       .get_or_create(name=LRAUV_MISSION))

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
                                                           activitytype=activitytype, 
                                                           campaign=campaign, 
                                                           platform=orig_activity.platform)
            except Activity.DoesNotExist:
                comment = f"Created by stoqs/loaders/{__name__}.py load_missions():"
                act = Activity(name=name, 
                               activitytype=activitytype,
                               campaign=campaign, 
                               platform=orig_activity.platform, 
                               startdate=mission_activity.start,
                               comment=comment)

            # Always update the enddate and comment - save the Activity for use below
            act.enddate = mission_activity.end
            if mission_activity.count == 1:
                act.comment += f" {mission_activity.count} mission from {syslog_url}"
            else:
                act.comment += f" {mission_activity.count} missions from {syslog_url}"
            act.save(using=db_alias)
            activity_by_mission[name] = act

        return ma, activity_by_mission

    def _update_mission_activity(self, db_alias, orig_activity, activity_by_mission, 
                                 mindepths, maxdepths, num_measuredparameters):
        '''Update Activity attributes in the database to represent all the missions of all the logs
        '''
        activitytype, _ = (ActivityType.objects.using(db_alias)
                                       .get_or_create(name=LRAUV_MISSION))
        for name in set(activity_by_mission.keys()):
            self.logger.info(f"Updating mission Activity {name}")
            self.logger.info(f"mindepth = {mindepths[name]}, maxdepth = {maxdepths[name]}, num_measuredparameters = {num_measuredparameters[name]}")

            act = Activity.objects.using(db_alias).get(name=name, 
                                                       activitytype=activitytype, 
                                                       platform=orig_activity.platform)
            try:
                if mindepths[name] < act.mindepth:
                    act.mindepth = mindepths[name]
            except TypeError:
                act.mindepth = mindepths[name]
            try:
                if maxdepths[name] > act.maxdepth:
                    act.maxdepth = maxdepths[name]
            except TypeError:
                act.maxdepth = maxdepths[name]

            try:
                act.num_measuredparameters += num_measuredparameters[name]
            except TypeError:
                act.num_measuredparameters = num_measuredparameters[name]

            act.save(using=db_alias)

    def load_missions(self, platform_name, activity_name, url, db_alias, save_attributes=False):
        '''Parse the syslog looking for messages that identify the starts of missions.
        There's always a mission running on an LRAUV.  This method is rather big and could use some refactoring for readability sake.
        url looks like 'http://dods.mbari.org/opendap/data/lrauv/tethys/missionlogs/2018/20180906_20180917/20180908T084424/201809080844_201809112341_2S_scieng.nc'
        '''
        syslog_url = "{}/syslog".format('/'.join(url.replace('opendap/', '').split('/')[:-1]))
        self.logger.info(f"Getting mission start information from the TethysDash API that's also in {syslog_url}")
        mission_starts = self._missions_from_json(platform_name, url)
        orig_activity = Activity.objects.using(db_alias).get(name=activity_name)
        starts, ends, names = self._make_starts_ends_names(mission_starts, orig_activity, db_alias)

        rt, _ = (ResourceType.objects.using(db_alias)
                             .get_or_create(name=LRAUV_MISSION, 
                                            description='LRAUV Mission name as retrieved from TethysDash api'))

        if save_attributes:
            # We can use the machinery of Labeled data to label the mission's Measured Parameters for Attribute display in the UI
            rdt, _ = ResourceType.objects.using(db_alias).get_or_create(name=LABEL, description='metadata')
            lrauv_mission_res, _ = (Resource.objects.using(db_alias)
                                            .get_or_create(name=LRAUV_MISSION, 
                                                           value=f"{STARTED_MISSION} parsed from syslog", 
                                                           uristring=syslog_url, 
                                                           resourcetype=rdt))

        ma, activity_by_mission = self._create_mission_activities(
                                       db_alias, orig_activity, starts, ends, names, syslog_url)

        # Initialize Activity attributes that are collected across all mission activities
        mindepths = {}
        maxdepths = {}
        num_measuredparameters = {}
        for name in set(names):
            mindepths[name] = 12000
            maxdepths[name] = -1000
            num_measuredparameters[name] = 0

        last_name = ''
        for start, end, name in zip(starts, ends, names):
            # Need to find min and max depth across all Missions, collect them in hashes
            meas_qs = (Measurement.objects.using(db_alias)
                                         .filter(instantpoint__activity=orig_activity,
                                                 instantpoint__timevalue__gte=start,
                                                 instantpoint__timevalue__lt=end))
            mm = meas_qs.aggregate(Min('depth'), Max('depth'))
            if mm['depth__min']:
                if mm['depth__min'] < mindepths[name]:
                    mindepths[name] = mm['depth__min']
            if mm['depth__max']:
                if mm['depth__max'] > maxdepths[name]:
                    maxdepths[name] = mm['depth__max']

            if save_attributes:
                self.logger.info(f"LRAUV mission '{name}' in Activity {orig_activity}: start={start}, end={end}, duration={end-start}")
                self.logger.info(f"Associating with MeasuredParameters for Attribute selection in the UI")
                # This Resource name appears in the STOQS UI in blue text of the Attributes -> Measurement tab
                res, _ = Resource.objects.using(db_alias).get_or_create(name=LRAUV_MISSION, value=name, resourcetype=rt)
                # Associate with Resource that describes the source
                ResourceResource.objects.using(db_alias).get_or_create(fromresource=res, 
                                                                       toresource=lrauv_mission_res)
                # Create collections of MeasuredParameterResources for each Measurement in the Mission
                for count, meas in enumerate(meas_qs):
                    if not count % 100:
                        self.logger.debug(f"{count:5d}: timevalue = {meas.instantpoint.timevalue}")
                    for mp in MeasuredParameter.objects.using(db_alias).filter(measurement=meas):
                        num_measuredparameters[name] += 1
                        mpr, _ = (MeasuredParameterResource.objects.using(db_alias)
                                                           .get_or_create(measuredparameter=mp,
                                                                          resource=res,
                                                                          activity=orig_activity))

            # Associate copies of SimpleDepthTime with the mission Activity for overview data viz
            self.logger.info(f"Associating with SimpleDepthTime copies with Activity {name}")
            last_sdt = None
            for count, sdt in enumerate(SimpleDepthTime.objects.using(db_alias)
                                   .filter(activity=orig_activity,
                                           instantpoint__timevalue__gte=start,
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

        self._update_mission_activity(db_alias, orig_activity, activity_by_mission, 
                                      mindepths, maxdepths, num_measuredparameters)

