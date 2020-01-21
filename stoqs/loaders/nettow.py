#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2015, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

Script to load Sampling events for Net Tow data
- Produce a .csv file from subsample information file and db info
- Load Samples from that .csv file into specified database

Mike McCann
MBARI 3 February 2015

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

import os
import sys
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, project_dir)

import csv
import logging
from datetime import timedelta, datetime
from datadiff.tools import assert_equal
from django.contrib.gis.geos import Point
from collections import defaultdict, OrderedDict
from loaders.SampleLoaders import NETTOW, VERTICALNETTOW
from stoqs.models import Activity, Sample, InstantPoint, ActivityType, Campaign, Platform, SampleType, SamplePurpose, PlatformType

class NetTow():
    '''Data and methods to support Net Tow Sample data loading
    '''

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    def _collect_samples(self, file):
        '''Read records into a hash keyed on 'Cruise', typically the CTD cast 
        name. The values of the hash are a list of sample_metadata (sm) hashes
        which are then checked for consistency. For SIMZ cruises the convention
        has been to conduct one net tow per CTD cast. If data differences 
        indicate that more than one tow has been done then raise an
        exception.
        '''
        cast_hash = defaultdict(lambda: [])
        with open(self.args.subsampleFile, encoding='latin-1') as f:
            for r in csv.DictReader(f):
                sm = OrderedDict()
                sm['name'] = r.get('Name', '')
                sm['depth'] = r.get('Depth [m]', '')
                sm['sampletype'] = r.get('Sample Type', '')
                sm['volume'] = r.get('Sample Volume [mL]', '')
                if not sm['volume']:
                    sm['volume'] = r.get('Sample Volume [m^3]', '')
                sm['filterdiameter'] = r.get('Filter Diameter [mm]', '')
                try:
                    sm['filterporesize'] = float(r.get('Filter Pore Size [um]'))
                except ValueError:
                    sm['filterporesize'] = float(r.get('Filter Pore Size [um]').split()[0])
                cast_hash[r.get('Cruise')].append(sm)

        # Ensure consistency of sample metadata following SIMZ convention
        cast_hash_consistent = OrderedDict()
        for cast,sm_list in sorted(cast_hash.items()):
            for sm_hash in sm_list[1:]:
                self.logger.debug('Checking consistency of record %s', sm_hash)
                assert_equal(sm_list[0], sm_hash)

            cast_hash_consistent[cast] = sm_list[0]
                    
        return cast_hash_consistent

    def _db_join(self, sm_hash):
        '''Join Sample data with data already in the database for the CTD cast.
        Use Cruise/Cast/Activity name as the key to get time, geom, and 
        environmental information.
        '''
        self.logger.info('Joining subsample information with cast data from the database using subtractMinutes = %d', self.args.subtractMinutes)
        new_hash = OrderedDict()
        for a_name,v in list(sm_hash.items()):
            try:
                a = Activity.objects.using(self.args.database).get(name__contains=a_name)
                v['longitude'] = a.mappoint.x
                v['latitude'] = a.mappoint.y
                v['datetime_gmt'] = (a.startdate - timedelta(minutes=self.args.subtractMinutes)).isoformat()
                new_hash[a_name] = v
            except Activity.DoesNotExist as e:
                self.logger.warn('Activity matching "%s" does not exist in database %s', a_name, self.args.database)
                continue
            except Activity.MultipleObjectsReturned as e:
                self.logger.warn(e)
                acts = Activity.objects.using(self.args.database).filter(name__contains=a_name).order_by('name')
                self.logger.warn('Names found:')
                for a in acts:
                    self.logger.warn(a.name)
                self.logger.warn('Creating a load record for the first one, but make sure that this is what you want!')
                v['longitude'] = acts[0].mappoint.x
                v['latitude'] = acts[0].mappoint.y
                v['datetime_gmt'] = (acts[0].startdate - timedelta(minutes=self.args.subtractMinutes)).isoformat()
                new_hash[a_name] = v
                continue

        return new_hash

    def make_csv(self):
        '''Construct and write parent Sample csv file
        '''
        try:
            s = self._collect_samples(self.args.subsampleFile)
        except AssertionError as e:
            # TODO: Apply logic to allow multiple net tows at a CTD cast station
            self.logger.error('Sample metadata differs for net tow within a CTD cast.')
            self.logger.error('Are there more than one net tows per cast or is this an error in file %s?', self.args.subsampleFile)
            self.logger.exception(e)
            sys.exit(-2)

        # Get spatial-temporal and campaign information from the database
        s = self._db_join(s)

        with open(self.args.csvFile, 'w') as f:
            f.write('Cast,')
            f.write(','.join(list(next(iter(list(s.values()))).keys())))
            f.write('\n')
            for k,v in list(s.items()):
                f.write('%s,' % k)
                f.write(','.join([str(dv) for dv in list(v.values())]))
                f.write('\n')

    def _get_net_tow_platform(self, cast_platform):
        '''Use name of profile CTD platform to construct a new Platform for connecting to a NetTow Activity.
        Return existing Platform if it's already been created.
        '''
        pt, created = PlatformType.objects.using(self.args.database).get_or_create(name='ship')

        # Expects name like "RachelCarson_UCTD" with an underscore to split on
        name = cast_platform.name.split('_')[0] + '_NetTow'
        platform, created = Platform.objects.using(self.args.database).get_or_create(
                                name = name, 
                                platformtype = pt,    
                                color = cast_platform.color
                            )
        return platform

    def _create_activity_instantpoint_platform(self, r, duration_minutes, nettow_number, point):
        '''Create an Activity and an InstantPoint from which to hang the Sample. Return the InstantPoint.
        '''
        if r.get('sampletype').lower().find('vertical') != -1:
            mindepth = 0
        else:
            mindepth = r.get('depth')

        campaign = Campaign.objects.using(self.args.database).filter(activity__name__contains=r.get('Cast'))[0]
        cast_plt = Platform.objects.using(self.args.database).filter(activity__name__contains=r.get('Cast'))[0]
        platform = self._get_net_tow_platform(cast_plt)
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
                            mindepth = mindepth,
                            maxdepth = r.get('depth'),
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
                point = Point(float(r.get('longitude')), float(r.get('latitude')))
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
        examples += " --csvFile 2013_SIMZ_TowNet_ParentSamples.csv\n"
        examples += "\n"
        examples += "  Step 2 - Load parent Sample information:\n"
        examples += "    " + sys.argv[0] + " --database stoqs_simz_aug2013_t"
        examples += " --loadFile 2013_SIMZ_TowNet_ParentSamples.csv\n"
        examples += '\nIf running from cde-package replace ".py" with ".py.cde".'
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Script to load parent Samples for Tow Net data',
                                         epilog=examples)
                                             
        parser.add_argument('-d', '--database', action='store', help='Database alias', required=True)

        parser.add_argument('-s', '--subsampleFile', action='store', help='File name containing analysis data from net tows in STOQS subsample format')
        parser.add_argument('-c', '--csvFile', action='store', help='Output comma separated value file containing parent Sample data')
        parser.add_argument('-m', '--subtractMinutes', action='store', help='Subtract these number of minutes from start of CTD cast for net tow time', 
                                    type=int, default=30)
        parser.add_argument('--laboratory', action='store', help='Laboratory responsible for the Samples')
        parser.add_argument('--researcher', action='store', help='Researcher responsible for the Samples')
        parser.add_argument('--purpose', action='store', help='Purpose of the Sample')

        parser.add_argument('-l', '--loadFile', action='store', help='Load parent Sample data into database')

        parser.add_argument('-v', '--verbose', nargs='?', choices=[1,2,3], type=int, help='Turn on verbose output. Higher number = more output.', const=1, default=0)
    
        self.args = parser.parse_args()
        self.commandline = ' '.join(sys.argv)

        if self.args.subsampleFile:
            if not self.args.csvFile:
                parser.error('Must include --csvFile argument with --subsampleFile option')
                
        elif self.args.loadFile:
            pass

        else:
            parser.error('Must provide either --subsampleFile or --loadFile option')

        if self.args.verbose > 1:
            self.logger.setLevel(logging.DEBUG)
        elif self.args.verbose >0:
            self.logger.setLevel(logging.INFO)
    
if __name__ == '__main__':

    nt = NetTow()
    nt.process_command_line()

    if nt.args.subsampleFile and nt.args.csvFile:
        nt.make_csv()

    elif nt.args.loadFile:
        nt.load_samples()

