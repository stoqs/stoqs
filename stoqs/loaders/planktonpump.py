#!/usr/bin/env python
#
# From: Julio Harvey <jharvey@mbari.org>
# Subject: Erin's plankton pump data for STOQS
# Date: December 1, 2015 at 5:04:43 PM PST
# To: Mike McCann <mccann@mbari.org>
# 
# Hi Mike,
# 
# I've attached the plankton pump data in tidy format, thanks in advance 
# for your help getting it into stoqs.
# 
# I heard back from Erin and the temporal story is that plankton pump 
# sample uptake durations were for 10 minutes each time.  Shall we call 
# the sampling start time as 1 minute after the last of the four Niskins 
# were fired at each depth? If you have a better call, I'll defer to your 
# judgement.
# 
# Feel free to raise issues with column headings or anything else as needed.
# 
# Thanks again!
# 
# Julio

'''
Script to load Sampling events for Plankton Pump data
- Produce a .csv file from subsample information file and db info
- Load Samples from that .csv file into specified database

Mike McCann
MBARI 2 December 2015
'''

import os
import sys
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.insert(0, app_dir)
os.environ['DJANGO_SETTINGS_MODULE']='config.settings.local'
import django
django.setup()

import csv
import logging
from datetime import timedelta, datetime
from datadiff.tools import assert_equal
from django.db.models import Avg
from collections import defaultdict, OrderedDict
from loaders.SampleLoaders import NETTOW, VERTICALNETTOW
from stoqs.models import Activity, Sample, InstantPoint, ActivityType, Campaign, Platform, SampleType, SamplePurpose, PlatformType

class PlanktonPump():
    '''Data and methods to support Plankton Pump Sample data loading
    '''

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    def _collect_samples(self, file):
        '''Read records into a hash keyed on ('Cruise', 'Relative Depth').
        The values of the hash are a list of sample_metadata (sm) hashes.
        For SIMZ cruises the convention has been to conduct one plankton pump 
        per group of 4 Niskin bottle trips, 3 pumps per cast. 
        '''
        sm_hash = OrderedDict()
        with open(self.args.subsampleFile) as f:
            for r in csv.DictReader(f):
                sm = OrderedDict()
                sm['name'] = r.get('Name', '')
                sm['depth'] = r.get('Depth [m]', '')
                sm['sampletype'] = r.get('Sample Type', '')
                sm[r.get('Comment Name')] = r.get('Comment Value', '')
                key = (r.get('Cruise'), sm.get('Relative Depth'))

                try:
                    sm_hash[key].append(sm)
                except KeyError:
                    sm_hash[key] = []
                    sm_hash[key].append(sm)

        return sm_hash

    def _pumping_depth(self, a_name, v):
        '''Compare with cluster of Niskin bottles and return depth of the
        Plankton Pump.
        '''
        bottles = dict(Bottom_Upper_Bottom = (1,2,3,4),
                       Mid_Mid = (5,6,7,8),
                       Surface_Below_Surface = (9,10,11,12),
                       Bottom_Bottom = (1,2,3,4),
                       Surface_Surface = (9,10,11,12),
                       Mid_Upper_Bottom = (1,2,3,4),
                       Surface_Mid = (9,10,11,12),
                       )
        samples = Sample.objects.using(self.args.database).filter(
                       sampletype__name='Niskin',
                       instantpoint__activity__name=a_name, 
                       name__in=bottles[v['Relative Depth']])

        self.logger.info('Bottle depths for cast %s, %s: %s', a_name, v['Relative Depth'], 
                          [float(d) for d in samples.values_list('depth', flat=True)])
        depth = samples.aggregate(Avg('depth')).values()[0]
        self.logger.info('Average depth = %s', depth)

        return depth

    def _add_db_values(self, activity, sample):
        '''Add information from the STOQS Activity object to the sample dictionary
        '''
        sample['longitude'] = activity.mappoint.x
        sample['latitude'] = activity.mappoint.y
        sample['datetime_gmt'] = (activity.startdate - timedelta(minutes=self.args.add_minutes)).isoformat()
        sample['depth'] = self._pumping_depth(activity.name, sample)

        return sample

    def _db_join(self, sm_hash):
        '''Join Sample data with data already in the database for the CTD cast.
        Use Cruise/Cast/Activity name as the key to get time, geom, and 
        environmental information.
        '''
        self.logger.info('Joining subsample information with cast data from the'
                         ' database using add_minutes = %d', self.args.add_minutes)
        new_hash = OrderedDict()
        for (a_name, rdepth), samples in sm_hash.iteritems():
            for sample in samples:
                key = (a_name, rdepth)
                try:
                    a = Activity.objects.using(self.args.database).get(name__contains=a_name)
                    sample = self._add_db_values(a, sample)
                    new_hash[key] = sample
                except Activity.DoesNotExist as e:
                    self.logger.warn('Activity matching "%s" does not exist in database %s', a_name, self.args.database)
                except Activity.MultipleObjectsReturned as e:
                    self.logger.warn(e)
                    acts = Activity.objects.using(self.args.database).filter(name__contains=a_name).order_by('name')
                    self.logger.warn('Names found:')
                    for a in acts:
                        self.logger.warn(a.name)
                    self.logger.warn('Creating a load record for the first one, but make sure that this is what you want!')
                    sample = self._add_db_values(acts[0], sample)
                    new_hash[key] = sample

        return new_hash

    def make_parent_csv(self):
        '''Construct and write parent Sample csv file
        '''
        s = self._collect_samples(self.args.subsampleFile)

        # Get spatial-temporal and campaign information from the database
        s = self._db_join(s)

        with open(self.args.csv_file, 'w') as f:
            f.write('Cast,')
            import pdb; pdb.set_trace()
            f.write(','.join(s.itervalues().next().keys()))
            f.write('\n')
            for k,v in s.iteritems():
                f.write('%s,' % k)
                f.write(','.join([str(dv) for dv in v.values()]))
                f.write('\n')

    def _get_plankton_pump_platform(self, cast_platform):
        '''Use name of profile CTD platform to construct a new Platform for connecting to a PlanktonPump Activity.
        Return existing Platform if it's already been created.
        '''
        pt, created = PlatformType.objects.using(self.args.database).get_or_create(name='ship')

        # Expects name like "RachelCarson_UCTD" with an underscore to split on
        name = cast_platform.name.split('_')[0] + '_PlanktonPump'
        platform, created = Platform.objects.using(self.args.database).get_or_create(
                                name = name, 
                                platformtype = pt,    
                                color = cast_platform.color
                            )
        return platform

    def _create_activity_instantpoint_platform(self, r, duration_minutes, nettow_number, point):
        '''Create an Activity and an InstantPoint from which to hang the Sample. Return the InstantPoint.
        '''
        campaign = Campaign.objects.using(self.args.database).filter(activity__name__contains=r.get('Cast'))[0]
        cast_plt = Platform.objects.using(self.args.database).filter(activity__name__contains=r.get('Cast'))[0]
        platform = self._get_plankton_pump_platform(cast_plt)
        at, created = ActivityType.objects.using(self.args.database).get_or_create(name=VERTICALNETTOW)

        timevalue = datetime.strptime(r.get('datetime_gmt'), '%Y-%m-%dT%H:%M:%S')
        act, created = Activity.objects.using(self.args.database).get_or_create(
                            campaign = campaign,
                            activitytype = at,
                            name = r.get('Cast') + '_%s%d' % (NETTOW, nettow_number),
                            comment = 'Plankton net tow done in conjunction with CTD cast %s' % r.get('Cast'),
                            platform = platform,
                            startdate = timevalue,
                            enddate = timevalue + timedelta(minutes=duration_minutes),
                       )
        # Update loaded_date after get_or_create() so that we can get the old record if script is re-executed
        act.loaded_date = datetime.utcnow()
        act.save(using=self.args.database)

        ip, created = InstantPoint.objects.using(self.args.database).get_or_create(
                            activity = act,
                            timevalue = timevalue
                      )

        return act, ip

    def load_samples(self):
        '''Load parent Samples into the database.
        '''
        # As of February 2015 the convention is one net tow per CTD cast, number the name of the
        # Samples in preparation in case we will have more than one. This will be over-ridden by name in the .csv file.
        nettow_number = 1
        with open(self.args.loadFile) as f:
            for r in csv.DictReader(f):
                point = 'POINT(%s %s)' % (r.get('longitude'), r.get('latitude'))
                # TODO: If net tow numbers are in the .csv file then they will need to be paresed for nettow_number here
                act, ip = self._create_activity_instantpoint_platform(r, duration_minutes=2, nettow_number=nettow_number, point=point)

                if r.get('sampletype').lower().find('vertical') != -1:
                    sampletype_name = VERTICALNETTOW
                sampletype, created = SampleType.objects.using(self.args.database).get_or_create(name=sampletype_name)

                samplepurpose = None
                if self.args.purpose:
                    samplepurpose, created = SamplePurpose.objects.using(self.args.database).get_or_create(name=self.args.purpose)
                
                v = None
                if r.get('volume'):
                    v = float(r.get('volume'))
                fd = None
                if r.get('filterdiameter'):
                    fd = float(r.get('filterdiameter'))
                fps = None
                if r.get('filterporesize'):
                    fps = float(r.get('filterporesize'))
                name = str(nettow_number)
                if r.get('name'):
                    name = r.get('name')

                samp, created = Sample.objects.using(self.args.database).get_or_create( 
                                    name = name,
                                    depth = r.get('depth'),
                                    geom = point,
                                    instantpoint = ip,
                                    sampletype = sampletype,
                                    volume = v,
                                    filterdiameter = fd,
                                    filterporesize = fps,
                                    laboratory = self.args.laboratory,
                                    researcher = self.args.researcher,
                                    samplepurpose = samplepurpose
                                )

                self.logger.info('Loaded Sample %s for Activity %s', samp, act)
                                    

    def process_command_line(self):
        '''The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Example:' + '\n\n' 
        examples += "  Step 1 - Create .csv file of parent Sample information:\n"
        examples += "    " + sys.argv[0] + " --database stoqs_simz_aug2013_t"
        examples += " --subsampleFile 2013_SIMZ_TowNets_STOQS.csv"
        examples += " --csv_file 2013_SIMZ_TowNet_ParentSamples.csv\n"
        examples += "\n"
        examples += "  Step 2 - Load parent Sample information:\n"
        examples += "    " + sys.argv[0] + " --database stoqs_simz_aug2013_t"
        examples += " --loadFile 2013_SIMZ_TowNet_ParentSamples.csv\n"
        examples += '\nIf running from cde-package replace ".py" with ".py.cde".'
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Script to load parent Samples for Tow Net data',
                                         epilog=examples)
                                             
        parser.add_argument('-d', '--database', action='store', help='Database alias', required=True)

        parser.add_argument('--subsampleFile', action='store', 
                            help='File name containing analysis data from net tows in STOQS subsample format')
        parser.add_argument('--csv_file', action='store', 
                            help='Output comma separated value file containing parent Sample data')
        parser.add_argument('--add_minutes', action='store', type=int, default=1,
                            help='Add these number of minutes to last Niskin bottle trip in cluster')
        parser.add_argument('--duration', action='store', type=int, default=10,
                            help='Duration in minutes of the pumping')
        parser.add_argument('--laboratory', action='store', 
                            help='Laboratory responsible for the Samples')
        parser.add_argument('--researcher', action='store', 
                            help='Researcher responsible for the Samples')
        parser.add_argument('--purpose', action='store', 
                            help='Purpose of the Sample')

        parser.add_argument('-l', '--loadFile', action='store', 
                            help='Load parent Sample data into database')

        parser.add_argument('-v', '--verbose', nargs='?', choices=[1,2,3], type=int, 
                            help='Turn on verbose output. Higher number = more output.', const=1)
    
        self.args = parser.parse_args()
        self.commandline = ' '.join(sys.argv)

        if self.args.subsampleFile:
            if not self.args.csv_file:
                parser.error('Must include --csv_file argument with --subsampleFile option')
                
        elif self.args.loadFile:
            pass

        else:
            parser.error('Must provide either --subsampleFile or --loadFile option')

        if self.args.verbose > 1:
            self.logger.setLevel(logging.DEBUG)
        elif self.args.verbose >0:
            self.logger.setLevel(logging.INFO)
    
if __name__ == '__main__':

    pp = PlanktonPump()
    pp.process_command_line()

    if pp.args.subsampleFile and pp.args.csv_file:
        pp.make_parent_csv()

    elif pp.args.loadFile:
        pp.load_samples()

