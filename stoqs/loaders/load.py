#!/usr/bin/env python

'''
Master load script that is driven by a dictionary of campaigns and the 
commands that load them. This dictionary also drives the campaigns
served by a deployment of stoqs via the stoqs/campaigns.py file.

Mike McCann
MBARI 5 September 2015
'''

import os
import sys
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.insert(0, app_dir)
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE']='config.settings.local'
import django
django.setup()

import time
import logging
import datetime
import fileinput
import glob
import importlib
import platform
import socket
import subprocess
from git import Repo
from shutil import copyfile
from django.conf import settings
from django.core.management import call_command
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import ConnectionDoesNotExist, OperationalError, ProgrammingError
from django.db import transaction, connections, close_old_connections
from slacker import Slacker
from stoqs.models import ResourceType, Resource, Campaign, CampaignResource, MeasuredParameter, \
                         SampledParameter, Activity, Parameter, Platform
from loaders.timing import MINUTES

def tail(f, n):
    return subprocess.getoutput(f"tail -{n} {f}")


class DatabaseCreationError(Exception):
    pass


class DatabaseLoadError(Exception):
    pass


class Loader(object):

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    prov = {}

    def _db_exists(self, db):
        '''Return true is the database db exists on the server
        '''

        command = '''psql -p {port} -U postgres -c \"SELECT datname FROM pg_catalog.pg_database WHERE lower(datname) = lower('{db}');\"'''.format(
                        **{'port': settings.DATABASES[db]['PORT'], 'db': db})
        self.logger.debug('command = %s', command)
        output = subprocess.getoutput(command)
        self.logger.debug('output = %s', output)
        if db in output:
            return True
        else:
            return False

    def _show_activity(self, db):
        command = r'''echo "\x \\\\ SELECT * from pg_stat_activity where datname = '{db}';" | psql -p {port} -U postgres'''.format(
                        **{'port': settings.DATABASES[db]['PORT'], 'db': db})
        self.logger.info('command = %s', command)
        output = subprocess.getoutput(command)
        self.logger.info('output = %s', output)

    def _create_db(self, db):
        '''Create database. Invoking user should have privileges to connect to 
        the database server as user postgres. Only the port number from the 
        DATABASE_URL is extracted to pass to the psql commands, we use the 
        local Unix domain socket to connect to the database.
        '''

        commands = ' && '.join((
            'psql -p {port} -c \"CREATE DATABASE {db} owner=stoqsadm;\" -U postgres',
            'psql -p {port} -c \"ALTER DATABASE {db} set timezone=\'GMT\';\" -U postgres',
            'psql -p {port} -c \"GRANT ALL ON ALL TABLES IN SCHEMA public TO stoqsadm;\" -d {db} -U postgres'))

        createdb = commands.format(**{'port': settings.DATABASES[db]['PORT'], 'db': db})
        self.logger.info('Creating database %s', db)
        self.logger.debug('createdb = %s', createdb)
        ret = os.system(createdb)
        self.logger.debug('ret = %s', ret)

        if ret != 0:
            if self.args.clobber:
                createdb = commands.format(**{'port': settings.DATABASES[db]['PORT'], 'db': db})
                self.logger.debug('createdb = %s', createdb)
                ret = os.system(createdb)
                self.logger.debug('ret = %s', ret)
                if ret != 0:
                    raise DatabaseCreationError(('Failed to create {}').format(db))
                else:
                    return

            raise DatabaseCreationError(('Failed to create {}').format(db))

        # Create postgis extensions as superuser
        create_ext = ('psql -p {port} -c \"CREATE EXTENSION postgis;\" -d {db} -U postgres && '
                    ).format(**{'port': settings.DATABASES[db]['PORT'], 'db': db})
        create_ext += ('psql -p {port} -c \"CREATE EXTENSION postgis_topology;\" -d {db} -U postgres'
                    ).format(**{'port': settings.DATABASES[db]['PORT'], 'db': db})

        self.logger.info('Creating postgis extensions for database %s', db)
        self.logger.debug('create_ext = %s', create_ext)
        ret = os.system(create_ext)
        self.logger.debug('ret = %s', ret)

    def _copy_log_file(self, log_file):
        loadlogs_dir = os.path.join(settings.MEDIA_ROOT, 'loadlogs')
        try: 
            os.makedirs(loadlogs_dir)
        except OSError:
            if not os.path.isdir(loadlogs_dir):
                raise
        log_file_url = os.path.basename(log_file) + '.txt'
        try:
            copyfile(log_file , os.path.join(loadlogs_dir, log_file_url))
            self.prov['load_logfile'] = os.path.join(settings.MEDIA_URL, 'loadlogs', log_file_url)
        except IOError as e:
            self.logger.warning(e)

    def _create_pg_dump(self, db):
        pg_dumps_dir = os.path.join(settings.MEDIA_ROOT, 'pg_dumps')
        try: 
            os.makedirs(pg_dumps_dir)
        except OSError:
            if not os.path.isdir(pg_dumps_dir):
                raise

        port = settings.DATABASES[db]['PORT']
        pg_fq_dump_file = os.path.join(pg_dumps_dir, db + '.pg_dump')
        # File location relative to server root
        pg_dump_file = os.path.join(settings.MEDIA_URL, 'pg_dumps', db + '.pg_dump')
        # Rely on system path to find the correct version of pg_dump
        pg_dump_cmd = f"pg_dump -p {port} -U postgres -Fc {db} > {pg_fq_dump_file}"

        self.logger.info(f"Creating pg_dump of {db} in {pg_fq_dump_file}")
        self.logger.debug(f"pg_dump_cmd = {pg_dump_cmd}")
        os.system(pg_dump_cmd)

        return pg_fq_dump_file, pg_dump_file, os.path.getsize(pg_fq_dump_file)

    def _provenance_dict(self, db, load_command, log_file):
        '''Return a dictionary of provenance Resource items. Special handling 
        for --background operation: don't tail log file, instead add those
        items when run with the --updateprovenance flag.
        '''
        repo = Repo(app_dir, search_parent_directories=True)

        if not self.args.updateprovenance:
            # Inserted when load executed with or without --background
            self.prov['load_command'] = load_command
            self.prov['gitorigin'] = repo.remotes.origin.url
            try:
                self.prov['gitcommit'] = repo.head.commit.hexsha
            except (ValueError, BrokenPipeError) as e:
                self.logger.warning('could not get head commit sha for %s: %s', repo.remotes.origin.url, e)
                self.prov['gitcommit'] = ""
            self.prov['environment'] = platform.platform() + " python " + sys.version.split('\n')[0]
            self.prov['load_date_gmt'] = datetime.datetime.utcnow()

        if not self.args.background:
            if os.path.isfile(log_file):
                # Look for line printed by timing module
                for line in tail(log_file, 50).split('\n'):
                    if line.startswith(MINUTES):
                        self.prov['minutes_to_load'] =line.split(':')[1]
                if 'minutes_to_load' not in self.prov:
                    self.logger.warning(f"Did not find line starting with {MINUTES} in {log_file}")
                try:
                    # Inserted after the log_file has been written with --updateprovenance
                    self.prov['real_exection_time'] = tail(log_file, 3).split('\n')[0].split('\t')[1]
                    self.prov['user_exection_time'] = tail(log_file, 3).split('\n')[1].split('\t')[1]
                    self.prov['sys_exection_time'] = tail(log_file, 3).split('\n')[2].split('\t')[1]
                except IndexError:
                    self.logger.debug('No execution_time information in %s', log_file)
            else:
                self.logger.warning('Load log file not found: %s', log_file)

            # Counts
            self.prov['MeasuredParameter_count'] = MeasuredParameter.objects.using(db).count()
            self.prov['SampledParameter_count'] = SampledParameter.objects.using(db).count()
            self.prov['Parameter_count'] = Parameter.objects.using(db).count()
            self.prov['Activity_count'] = Activity.objects.using(db).count()
            self.prov['Platform_count'] = Platform.objects.using(db).count()

    def _log_file(self, script, db, load_command):
        if self._has_no_t_option(db, load_command):
            log_file = os.path.join(os.path.dirname(script.split()[0]), db + '.out')
        else:
            if self.args.test:
                log_file = script.split()[0].replace('.py', '_t.out')
            else:
                log_file = script.split()[0].replace('.py', '.out')

        return log_file

    def _has_no_t_option(self, db, load_command):
        return ((db.endswith('_o') and '-o' in load_command) or 
                'ROVCTD' in load_command or
                load_command.endswith('.sh') or 
                '&&' in load_command)

    def _drop_indexes(self):
        # As of 2017 the STOQS project does not commit migration files.
        # If significant schema changes are made the SOP is to reload databases;
        # this also helps ensure that the archived NetCDF files are still accessible.
        # To try loading data with more efficiency in the database this method
        # removes migrations and modifies the models.py file to remove indexes.
        # The migration files need to be removed because of this Django patch:
        # https://code.djangoproject.com/ticket/28052
        migration_files = glob.glob(os.path.join(app_dir, 'stoqs/migrations', '00*.py'))
        for m_f in migration_files:
            if '0001_initial.py' not in m_f:
                self.logger.info('Removing migration file: %s', m_f)
                os.remove(m_f)

        model_files = (os.path.join(app_dir, 'stoqs/migrations/0001_initial.py'),
                       os.path.join(app_dir, 'stoqs/models.py'))
        with fileinput.input(files=model_files, inplace=True, backup='.bak') as f:
            for line in f:
                if '_index=True' in line:
                    print(line.replace('_index=True', '_index=False'), end='')
                else:
                    print(line, end='')

    def _create_indexes(self):
        # Add indexes back to models.py
        ##migration_files = glob.glob(os.path.join(app_dir, 'stoqs/migrations', '00*.py'))
        ##for m_f in migration_files:
        ##    if '0001_initial.py' not in m_f:
        ##        self.logger.info('Removing migration file: %s', m_f)
        ##        os.remove(m_f)

        model_file = os.path.join(app_dir, 'stoqs/models.py')
        ##model_file = os.path.join(app_dir, 'stoqs/migrations/0001_initial.py')
        with fileinput.input(files=(model_file,), inplace=True) as f:
            for line in f:
                if '_index=False' in line:
                    print(line.replace('_index=False', '_index=True'), end='')
                else:
                    print(line, end='')

    def checks(self):
        if self.args.verbose >= 1:
            self.logger.setLevel(logging.DEBUG)
        elif self.args.verbose > 0:
            self.logger.setLevel(logging.INFO)

        # That stoqs/campaigns.py file can be loaded
        try:
            campaigns = importlib.import_module(self.args.campaigns)
        except ImportError:
            print('The stoqs/campaigns.py could not be loaded. '
                              'Create a symbolic link named "campaigns.py" '
                              'pointing to the file for your site.')
            print('Use stoqs/mbari_campaigns.py or stoqs/mbari_lrauv_campaigns.py as'
                  ' the source file or as a model for your own.')
            sys.exit()

        if self.args.db:
            for d in self.args.db:
                if d not in list(campaigns.campaigns.keys()):
                    self.logger.warning('%s not in %s', d, self.args.campaigns)

        # That can connect as user postgres for creating and dropping databases
        cmd = ('psql -p {} -c "\q" -U postgres').format(settings.DATABASES['default']['PORT'])
        self.logger.debug('cmd = %s', cmd)
        ret = os.system(cmd)
        self.logger.debug('ret = %s', ret)
        if ret != 0:
            self.logger.warning('Cannot connect to the database server as user postgres. Either run as user postgres or alter your pg_hba.conf file.')
            suggestion = '''

To permit simpler loading of your databases you may want to temporarilry open
up your server to allow any local acccount to connect as user postgres without
a password. WARNING: this opens up your server to potential attack, you should
undo this change when done with your loads.

In the "local" section of your /var/lib/pgsql/<version>/data/pg_hba.conf file
add a 'trust' entry for all local accounts above the other entries, e.g.:

# "local" is for Unix domain socket connections only
local   all             all                                     trust
local   all             all                                     peer
'''
            self.logger.info(suggestion)

        # That the user really wants to reload all production databases
        if self.args.clobber and not self.args.test and not self.args.restore:
            print(("On the server running on port =", settings.DATABASES['default']['PORT']))
            print("You are about to drop all database(s) in the list below and reload them:")
            print((('{:30s} {:>15s}').format('Database', 'Last Load time (min)')))
            print((('{:30s} {:>15s}').format('-'*25, '-'*20)))
            nothing_printed = True
            dbs_to_drop = []
            for db,load_command in list(campaigns.campaigns.items()):
                if self.args.db:
                    if db not in self.args.db:
                        continue
                    else:
                        dbs_to_drop.append(db)

                script = os.path.join(app_dir, 'loaders', load_command)
                try:
                    with transaction.atomic(using=db):
                        minutes_to_load = CampaignResource.objects.using(db).get(
                                            resource__name='minutes_to_load').resource.value
                    print(f"{db:30s} {minutes_to_load:>20}")
                    nothing_printed = False
                except (CampaignResource.DoesNotExist, CampaignResource.MultipleObjectsReturned,
                        OperationalError, ProgrammingError) as e:
                    self.logger.debug(str(e))
                    self.logger.debug('Closing all connections:')
                    for conn in connections.all():
                        if conn.settings_dict['NAME'] not in self.args.db:
                            continue
                        self.logger.debug(f"    {conn.settings_dict['NAME']}")
                        conn.close()

                if nothing_printed:
                    print(f"{db:30s} {'--- ':>20}")

            if not self.args.noinput:
                ans = input('\nAre you sure you want to drop these database(s) and reload them? [y/N] ')
                if ans.lower() == 'y':
                    for db_to_drop in dbs_to_drop:
                        if self._db_exists(db_to_drop):
                            self._dropdb(db_to_drop)
                else:
                    print('Exiting')
                    sys.exit()

        # That user wants to load all the production databases (no --db argument)
        if not self.args.db and not self.args.list and not self.args.updateprovenance:
            print(("On the server running on port =", settings.DATABASES['default']['PORT']))
            print("You are about to operate on all of these databases:")
            print((' '.join(list(campaigns.campaigns.keys()))))
            if self.args.restore:
                ans = input('\nAre you sure you want restore all these databases? [y/N] ') or 'N'
            else:
                ans = input('\nAre you sure you want load all these databases? [y/N] ') or 'N'
            if ans.lower() != 'y':
                print('Exiting')
                sys.exit()

        # That script support the --test option
        if self.args.db and self.args.test:
            for db in self.args.db:
                if self._has_no_t_option(db, campaigns.campaigns[db]):
                    print(f'{campaigns.campaigns[db]} does not support the --test argument')
                    sys.exit(-1)

    def _assign_rt_campaign(self, db, rt_name='provenance'):
        '''Set resourcetype and campaign items for provenance and pg_dump metadata
        '''
        try:
            self.rt, _ = ResourceType.objects.using(db).get_or_create(name=rt_name, 
                    description='Information about the source of data')
        except (ConnectionDoesNotExist, OperationalError, ProgrammingError) as e:
            self.logger.warning('Could not open database "%s" for updating provenance.', db)
            self.logger.warning(e)
            raise ObjectDoesNotExist(e)

        i = 0
        self.campaign = None
        while not self.campaign:
            try:
                self.logger.debug('Looking in database %s for first Campaign record', db)
                self.campaign = Campaign.objects.using(db).get(id=1)
            except ObjectDoesNotExist:
                if self.args.background:
                    # Sleep a bit for background jobs to create the Campaign
                    sec_wait = 5
                    time.sleep(sec_wait)
                    i += 1
                    max_iter = 24
                    if i > max_iter:
                        raise DatabaseLoadError(('No campaign created after {:d} seconds. '
                            'Check log_file for errors: {}').format(sec_wait * max_iter, log_file))
                else:
                    self.logger.error(f'Could not find Campaign record for {db} in the database.')
                    raise DatabaseLoadError()

    def recordprovenance(self, db, load_command, log_file):
        '''Add Resources to the Campaign that describe what loaded it
        '''
        self.logger.debug('Recording provenance for %s using log_file = %s', db, log_file)
        self._assign_rt_campaign(db)

        self.logger.info('Database %s', db)
        self._provenance_dict(db, load_command, log_file)
        for name,value in list(self.prov.items()):
            r, _ = Resource.objects.using(db).get_or_create(
                            uristring='', name=name, value=value, resourcetype=self.rt)
            cr, loaded_flag = CampaignResource.objects.using(db).get_or_create(campaign=self.campaign, resource=r)
            self.logger.info('Resource uristring="%s", name="%s", value="%s"', '', name, value)

    def updateprovenance(self):
        campaigns = importlib.import_module(self.args.campaigns)
        for db,load_command in list(campaigns.campaigns.items()):
            if self.args.db:
                if db not in self.args.db:
                    continue

            if self.args.test:
                if self._has_no_t_option(db, load_command):
                    continue

                db += '_t'

            script = os.path.join(app_dir, 'loaders', load_command)
            log_file = self._log_file(script, db, load_command)

            try:
                self.recordprovenance(db, load_command, log_file)
            except (ObjectDoesNotExist, DatabaseLoadError) as e:
                self.logger.warning('Could not record provenance in database %s', db)
                self.logger.warning(e)

    def grant_everyone_select(self):
        campaigns = importlib.import_module(self.args.campaigns)
        for db,load_command in list(campaigns.campaigns.items()):
            if self.args.db:
                if db not in self.args.db:
                    continue

            if self.args.test:
                if self._has_no_t_option(db, load_command):
                    continue
                
                db += '_t'

            command = 'psql -p {port} -c \"GRANT SELECT ON ALL TABLES IN SCHEMA public TO everyone;\" -d {db} -U postgres'
            grant = command.format(**{'port': settings.DATABASES[db]['PORT'], 'db': db})

            self.logger.info('Granting SELECT to everyone on database %s', db)
            self.logger.debug('grant = %s', grant)
            ret = os.system(grant)
            self.logger.debug('ret = %s', ret)

    def add_resource(self):
        '''Customize the Resources to be added here in the source code
        '''
        campaigns = importlib.import_module(self.args.campaigns)
        for db,load_command in list(campaigns.campaigns.items()):
            if self.args.db:
                if db not in self.args.db:
                    continue

            if self.args.test:
                if self._has_no_t_option(db, load_command):
                    continue
                
                db += '_t'

            resourceType, _ = ResourceType.objects.using(db).get_or_create(
                                           name='x3dterrain', 
                                           description='X3D Terrain information for Spatial 3D visualization')
            campaign = Campaign.objects.using(db).get()
            self.logger.info(f'Adding Resources to {db}')
            for url in (Resource.objects.using(db).filter(resourcetype__name='x3dterrain')
                                        .values_list('uristring', flat=True).distinct()):
                self.logger.info(f'{url}: Adding default clipping plane zNear, zFar values: 100.0, 300000.0')
                resource, rid1 = Resource.objects.using(db).get_or_create(
                              uristring=url, name='zNear', value=100.0, resourcetype=resourceType)
                CampaignResource.objects.using(db).get_or_create(
                              campaign=campaign, resource=resource)
                resource, rid2 = Resource.objects.using(db).get_or_create(
                              uristring=url, name='zFar', value=300000.0, resourcetype=resourceType)
                CampaignResource.objects.using(db).get_or_create(
                              campaign=campaign, resource=resource)

    def pg_dump(self):
        campaigns = importlib.import_module(self.args.campaigns)
        for db,load_command in list(campaigns.campaigns.items()):
            if self.args.db:
                if db not in self.args.db:
                    continue

            if self.args.test:
                if self._has_no_t_option(db, load_command):
                    continue

                db += '_t'

            pg_fq_dump_file, pg_dump_file, pg_dump_size = self._create_pg_dump(db)

            try:
                self._assign_rt_campaign(db)
            except (ObjectDoesNotExist, DatabaseLoadError):
                self.logger.warning('Skipping')
                continue

            self.logger.debug(f'Recording pg_dump_size = {pg_dump_size} in provenance')
            for name,value in {'pg_dump_file': pg_dump_file, 
                               'pg_fq_dump_file': pg_fq_dump_file,
                               'pg_dump_size': pg_dump_size,
                               'pg_dump_date_gmt': datetime.datetime.utcnow()}.items():
                r, _ = Resource.objects.using(db).get_or_create(
                                uristring='', name=name, resourcetype=self.rt)
                r.value = value
                r.save(using=db)
                    
                CampaignResource.objects.using(db).get_or_create(
                                campaign=self.campaign, resource=r)
                self.logger.info('Resource uristring="%s", name="%s", value="%s"', '', name, value)

    def _dropdb(self, db):
        dropdb = '''psql -p {port} -U postgres -c \"DROP DATABASE {db};\"'''.format(
                    **{'port': settings.DATABASES['default']['PORT'], 'db': db})

        self.logger.info('Dropping database %s', db)
        self.logger.debug('dropdb = %s', dropdb)
        close_old_connections()
        ret = os.system(dropdb)
        self.logger.debug('ret = %s', ret)
        if ret != 0:
            self.logger.warning('Failed to drop %s', db)
            self._show_activity(db)

    def _restore_db(self , db):
        if self._db_exists(db) and self.args.clobber:
            self._dropdb(db)
        self.logger.info('Creating database: %s', db)
        ret = os.system(f'createdb -U postgres {db}')
        self.logger.debug(f'ret = {ret}')
        if ret != 0:
            raise DatabaseCreationError(f'Could not create database: {db}. Perhaps use the --clobber option?')

        # Note that pg_dump(1)s should be done with the same version of Postgresql 
        # to avoid spurious error messages upon restore.  This can be done with
        # 'docker-compose run stoqs stoqs/loaders/load.py --pg_dump' on the source server.
        self.logger.info('Restoring database: %s', db)
        cmd = (f'wget --no-check-certificate -qO- http://{self.args.restore}/media/pg_dumps/{db}.pg_dump | pg_restore -Fc -U postgres -d {db}')
        t1 = time.time()
        self.logger.info(f'Executing: {cmd}')
        ret = os.system(cmd)
        self.logger.debug(f'ret = {ret}')
        if ret != 0:
            raise DatabaseCreationError(f'Could not create database: {db}. Perhaps use the --clobber option?')
        self.logger.info(f"Time to restore: {(time.time() - t1) / 60:.2f} minutes")

    def removetest(self):
        self.logger.info('Removing test databases from sever running on port %s', 
                settings.DATABASES['default']['PORT'])
        campaigns = importlib.import_module(self.args.campaigns)
        for db,load_command in list(campaigns.campaigns.items()):
            if self.args.db:
                if db not in self.args.db:
                    continue

                if self._has_no_t_option(db, load_command):
                    continue

            db += '_t'
            self._dropdb(db)

    def print_list(self):
        stoqs_campaigns = []
        campaigns = importlib.import_module(self.args.campaigns)
        for db,load_command in list(campaigns.campaigns.items()):
            if self.args.db:
                if db not in self.args.db:
                    continue

            if self.args.test:
                if self._has_no_t_option(db, load_command):
                    continue

                db += '_t'

            stoqs_campaigns.append(db)

        print(('\n'.join(stoqs_campaigns)))
        print(('export STOQS_CAMPAIGNS="' + ','.join(stoqs_campaigns) + '"'))
        print()
        print(' '.join(stoqs_campaigns))

    def lines_with_string(self, file_name, string, max_lines=10):
        matching_lines = ''
        with open(file_name) as f:
            i = 0
            for line in f:
                if string in line:
                    i += 1
                    matching_lines += line
                if i > max_lines:
                    break

        if i >= max_lines:
            matching_lines += f'\n(... truncated after {string} seen {max_lines} times ...)'

        if not matching_lines:
            matching_lines = f'No lines containing string {string}.'

        return matching_lines

    def load(self, campaigns=None, create_only=False, cl_args=None):
        if not campaigns:
            campaigns = importlib.import_module(self.args.campaigns)

        for db,load_command in list(campaigns.campaigns.items()):
            if self.args.db:
                if db not in self.args.db:
                    continue

            if self.args.test:
                if self._has_no_t_option(db, load_command):
                    continue

                load_command += ' -t'
                db += '_t'

                # Borrowed from stoqs/config/settings/common.py
                campaign = db
                settings.DATABASES[campaign] = settings.DATABASES.get('default').copy()
                settings.DATABASES[campaign]['NAME'] = campaign
                settings.MAPSERVER_DATABASES[campaign] = settings.MAPSERVER_DATABASES.get('default').copy()
                settings.MAPSERVER_DATABASES[campaign]['NAME'] = campaign

            if db not in settings.DATABASES:
                # Django docs say not to do this, but I can't seem to force a settings reload.
                # Note that databases in campaigns.py are put in settings by settings.local.
                settings.DATABASES[db] = settings.DATABASES.get('default').copy()
                settings.DATABASES[db]['NAME'] = db

            appending = False
            if cl_args:
                if cl_args.realtime:
                    load_command += ' --realtime'
                if cl_args.missionlogs:
                    load_command += ' --missionlogs'
                if cl_args.remove_appended_activities:
                    load_command += ' --remove_appended_activities'
                if cl_args.append:
                    appending = True
            if hasattr(self.args, 'append'):
                if self.args.append:
                    appending = True

            if appending:
                load_command += ' --append'
                if cl_args:
                    if cl_args.startdate:
                       load_command += f' --startdate {cl_args.startdate}' 
                if '--startdate' not in load_command:
                    if self.args.startdate:
                       load_command += f' --startdate {self.args.startdate}' 
                    elif self.args.current_day:
                       load_command += f" --startdate {datetime.datetime.utcnow().strftime('%Y%m%d')}"

            if not appending and not self.args.restore:
                if self._db_exists(db) and self.args.clobber and (self.args.noinput or self.args.test):
                    self._dropdb(db)

                try:
                    self._create_db(db)
                except DatabaseCreationError as e:
                    self.logger.warning(e)
                    self.logger.warning('Use the --clobber option, or fix the problem indicated.')
                    if self.args.db and not self.args.test:
                        raise Exception('Maybe use the --clobber option to recreate the database...')
                    else:
                        # If running test for all databases just go on to next database
                        continue

                if self.args.drop_indexes:
                    self.logger.info('Dropping indexes...')
                    self._drop_indexes()
                else:
                    try:
                        call_command('makemigrations', 'stoqs', settings='config.settings.local', noinput=True)
                    except TypeError:
                        call_command('makemigrations', 'stoqs', settings='config.settings.local', interactive=False)

                try:
                    call_command('migrate', settings='config.settings.local', noinput=True, database=db)
                except TypeError:
                    call_command('migrate', settings='config.settings.local', interactive=False, database=db)

                if create_only:
                    return

            if hasattr(self.args, 'verbose') and not load_command.endswith('.sh'):
                if self.args.verbose > 2:
                    load_command += ' -v'

            if self.args.restore:
                try:
                    self._restore_db(db)
                except DatabaseCreationError as e:
                    self.logger.warning(f'{e}')
                continue
            else:
                # === Execute the load
                script = os.path.join(app_dir, 'loaders', load_command)
                log_file = self._log_file(script, db, load_command)
                if script.endswith('.sh'):
                    cmd = (f'cd {os.path.dirname(script)} && (STOQS_CAMPAIGNS={db} time {script}) > {log_file} 2>&1;')
                else:
                    if appending:
                        cmd = (f'(STOQS_CAMPAIGNS={db} time {script}) >> {log_file} 2>&1;')
                    else:
                        cmd = (f'(STOQS_CAMPAIGNS={db} time {script}) > {log_file} 2>&1;')

            if self.args.email:
                # Send email on success or failure
                cmd += ('''
if [ $? -eq 0 ]
then
    (echo Any ERROR mesages and last 10 lines of: {log};
    grep ERROR {log}; 
    tail {log}) | mail -s "{db} load finished" {email}
else
    (echo Any ERROR mesages and last 20 lines of: {log};
    grep ERROR {log}; 
    tail -20 {log}) | mail -s "{db} load FAILED" {email}
fi''').format(**{'log':log_file, 'db': db, 'email': self.args.email})

            if self.args.background:
                cmd = '({}) &'.format(cmd)

            if self.args.create_only:
                return

            # Execute as system call - Allows for repeatable loading and output capture by executing the load script in cmd
            self.logger.info('Executing: %s', cmd)
            ret = os.system(cmd)
            self.logger.debug(f'ret = {ret}')

            self._copy_log_file(log_file)

            if self.args.slack:
                server = os.environ.get('NGINX_SERVER_NAME', socket.gethostname())
                message = f"{db} load into {settings.DATABASES[db]['HOST']} on {server}"
                if ret == 0:
                    message += ' *succeded*.\n'
                else:
                    message += ' *failed*.\n'

                stoqs_icon_url = 'http://www.stoqs.org/wp-content/uploads/2017/07/STOQS_favicon_logo3_512.png'
                self.slack.chat.post_message('#stoqs-loads', text=message, username='stoqsadm', icon_url=stoqs_icon_url)

                message = f'All WARNING messages from {log_file}:'
                message += f"```{self.lines_with_string(log_file, 'WARNING')}```"
                self.slack.chat.post_message('#stoqs-loads', text=message, username='stoqsadm', icon_url=stoqs_icon_url)

                message = f'All ERROR messages from {log_file}:'
                message += f"```{self.lines_with_string(log_file, 'ERROR')}```"
                self.slack.chat.post_message('#stoqs-loads', text=message, username='stoqsadm', icon_url=stoqs_icon_url)

                num_lines = 20
                message = f'Last {num_lines} lines of {log_file}:'
                message += f"```{tail(log_file, num_lines)}```"
                log_url = 'http://localhost:8008/media/loadlogs/' + os.path.basename(log_file) + '.txt'
                self.slack.chat.post_message('#stoqs-loads', text=message, username='stoqsadm', icon_url=stoqs_icon_url, attachments=log_url)

                self.logger.info('Message sent to Slack channel #stoqs-loads')
                
            if ret != 0:
                self.logger.error(f'Non-zero return code from load script. Check {log_file}')
                if self._db_exists(db) and self.args.drop_if_fail:
                    self._dropdb(db)
                raise DatabaseLoadError(f'Non-zero return code from load script. Check {log_file}')

            if self.args.drop_indexes:
                self.logger.info('Creating indexes...')
                self._create_indexes()
                call_command('makemigrations', 'stoqs', settings='config.settings.local', noinput=True)
                call_command('migrate', settings='config.settings.local', noinput=True, database=db)

            if not appending:
                # Record details of the database load to the database
                try:
                    self.recordprovenance(db, load_command, log_file)
                except DatabaseLoadError as e:
                    self.logger.warning(str(e))

    def process_command_line(self):
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n\n' 
        examples += "  Load all databases:\n"
        examples += "    " + sys.argv[0] + "\n"
        examples += "  Reload all databases (dropping all existing databases):\n"
        examples += "    " + sys.argv[0] + " --clobber\n"
        examples += "  Reload specific databases from as background jobs with verbose output:\n"
        examples += "    " + sys.argv[0] + " --db stoqs_september2013 stoqs_may2015 --clobber --background --email mccann@mbari.org -v 1\n"
        examples += "  Drop specific test databases:\n"
        examples += "    " + sys.argv[0] + " --db stoqs_september2010 stoqs_october2010 --removetest -v 1\n"
        examples += "  Drop all test databases:\n"
        examples += "    " + sys.argv[0] + "--removetest -v 1\n"
        examples += "  List test databases to get STOQS_CAMPAIGNS string:\n"
        examples += "    " + sys.argv[0] + " --list --test"
        examples += "\n"
        examples += '\nIf running from cde-package replace ".py" with ".py.cde".'
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                 description=('''
Script to load or reload STOQS databases using the dictionary in stoqs/campaigns.py
                              
A typical workflow to build up a production server is:
1. Construct a stoqs/campaigns.py file (use mbari_campaigns.py as model)
2. Make *ex situ* Sampled Parameter data available:
   a. Uncompress Sample data files included in the stoqs repository:
      find stoqs/loaders -name "*.gz" | xargs gunzip
   b. Copy BOG database extraction files to CANON/BOG_Data
   c. (A Big TODO: Change these loads to a web-accessable method...)
3. Copy terrain data files that are not included or copied during test.sh execution:
    cd stoqs/loaders
    wget https://stoqs.mbari.org/terrain/Monterey25.grd  
    wget https://stoqs.mbari.org/terrain/Globe_1m_bath.grd
    wget https://stoqs.mbari.org/terrain/MontereyCanyonBeds_1m+5m.grd
    wget https://stoqs.mbari.org/terrain/SanPedroBasin50.grd
    wget https://stoqs.mbari.org/terrain/michigan_lld.grd
4. Get the STOQS_CAMPAIGNS setting for running your server:
    {load} --test --list
5. Load test (_t) databases to test all your load scripts:
    {load} --test --clobber --background --email {user} -v > load.out 2>&1
    (Check your email for load finished messages)
    Email is not configured for a Docker installation, instead use Slack:
    cd docker
    docker exec -e SLACKTOKEN=<your_private_token> -e STOQS_CAMPAIGNS=<results_from_previous_step> stoqs {load} --test --slack
    (The --clobber, --db <database>, and --verbose <num> options can be used to reload and debug problems.)
6. Add metadata to the database with links to the log files and create a pg_dump of the database:
    {load} --test --updateprovenance
    {load} --test --pg_dump
7. Set your environment variables and run your server:
    export DATABASE_URL=postgis://<dbuser>:<pw>@<host>:<port>/stoqs
    export STOQS_CAMPAIGNS=<output_from_previous_step>
    export MAPSERVER_HOST=<mapserver_ip_address>
    stoqs/manage.py runserver 0.0.0.0:8000 --settings=config.settings.local
    - or, however you start your uWSGI app, e.g.:
    uwsgi --socket :8001 --module wsgi:application
8. Visit your server and see that your test databases are indeed loaded
9. Check all your output files for ERROR and WARNING messages
10. Fix any problems so that ALL the test database loads succeed
11. Remove the test databases:
    {load} --removetest -v
12. Load your production databases:
    {load} --background --email {user} -v > load.out 2>&1
13. Add provenance information to the database, with setting for non-default MEDIA_ROOT:
    export MEDIA_ROOT=/usr/share/nginx/media
    {load} --updateprovenance -v 
14. Create a pg_dump of the database that can be used for backups and quicker loading of a development database:
    {load} --pg_dump
15. Give the 'everyone' role SELECT privileges on all databases:
    {load} --grant_everyone_select -v 
16. After a final check announce the availability of these databases
17. To restore from a backup on Docker (with stoqs_simz_aug2013 as an example):
    docker-compose run stoqs createdb -U postgres stoqs_simz_aug2013_restored
    docker-compose run stoqs pg_restore -Fc -U postgres -d stoqs_simz_aug2013_restored /srv/media-files/pg_dumps/stoqs_simz_aug2013.pg_dump
    (If the server hosts the original database as well, then the Campaign name must be changed for it to show on the campaign list.)
18. To restore all databases from a source server, e.g.:
    a. docker-compose run stoqs stoqs/loaders/load.py --restore stoqs.shore.mbari.org
    b. Then copy the loadlog files over, preserving file modification times:
        On the source server:
            docker-compose exec nginx /bin/bash
            cp -a /srv/media-files/loadlogs /srv/html           # Copy files from container to host
        On the destination server:
            (using an account with sudo privs, e.g. mccann):
                sudo chown stoqsadm /opt/docker_stoqs_vols/html
            (logged in as stoqsadm, e.g. use mccann account on source server)
                scp -rp mccann@stoqs.shore.mbari.org:/opt/docker_stoqs_vols/html/loadlogs /opt/docker_stoqs_vols/html
                docker-compose exec nginx /bin/bash
                cp -a /srv/html/loadlogs /srv/media-files/      # Copy files from host to container
    c. Check that loadlogs are web accessible, e.g.:
        https://kraken2.shore.mbari.org/media/loadlogs/loadCANON_october2020.out.txt
    d. Copy .out files to the new server:
        cd stoqs/loaders && tar cvf outfiles.tar */*.out
        copy to new server and untar in stoqs/loaders
    e. If another server is using the database then update any firewall rules to new server's IP 


To get any stdout/stderr output you must use -v, the default is no output.
''').format(**{'load': sys.argv[0], 'user': os.environ['USER']}),
                 epilog=examples)
                                             
        parser.add_argument('--campaigns', action='store', help='Module containing campaigns dictionary (must also be in campaigns.py)', default='campaigns')

        parser.add_argument('--db', action='store', help=('Specify databases from CAMPAIGNS to load'
                                                          ' (do not append "_t", instead use --test'
                                                          ' for test databases)'), nargs='*')
        parser.add_argument('--test', action='store_true', help='Load test databases using -t option of loaders.LoadScript')
        parser.add_argument('--clobber', action='store_true', help=('Drop databases before creating and loading them.'
                                                                   ' Need to confirm dropping production databases.'))
        parser.add_argument('--background', action='store_true', help='Execute each load in the background to parallel process multiple loads')
        parser.add_argument('--removetest', action='store_true', help='Drop all test databases; the --db option limits the dropping to those in the list')
        parser.add_argument('--list', action='store_true', help='List the databases that are in --campaigns')
        parser.add_argument('--email', action='store', help='Address to send mail to when the load finishes. Does not work from Docker, use --slack instead.')
        parser.add_argument('--slack', action='store_true', help='Post message to stoqs-loads channel on Slack using SLACKTOKEN env variable')
        parser.add_argument('--updateprovenance', action='store_true', help=('Use after background jobs finish to copy'
                                                                            ' loadlogs and update provenance information'))
        parser.add_argument('--grant_everyone_select', action='store_true', help='Grant everyone role select privileges on all relations')
        parser.add_argument('--add_resource', action='store_true', help='Add a Resource to all databases: e.g. for zNear & zFar')
        parser.add_argument('--drop_indexes', action='store_true', help='Before load drop indexes and create them following the load')
        parser.add_argument('--pg_dump', action='store_true', help='Store a pg_dump(1) with "-Fc" option file on the server')
        parser.add_argument('--noinput', action='store_true', help='Execute without asking for a response, e.g. for --clobber')
        parser.add_argument('--drop_if_fail', action='store_true', help='Drop database if fail to load data')
        parser.add_argument('--append', action='store_true', help='Append data to existing database')
        parser.add_argument('--startdate', help='Startdate in YYYYMMDD format for appending data')
        parser.add_argument('--current_day', action='store_true', help='Set startdate to current UTC day - useful for running directly from cron')
        parser.add_argument('--create_only', action='store_true', help='Just create the database and do not load the data')
        parser.add_argument('--restore', action='store', help='Restore databases from specified server, e.g.: stoqs.shore.mbari.org')

        parser.add_argument('-v', '--verbose', nargs='?', choices=[1,2,3], type=int, help='Turn on verbose output. If > 2 load is verbose too.', const=1, default=0)
    
        self.args = parser.parse_args()
        self.commandline = ' '.join(sys.argv)

        if self.args.slack:
            try:
                self.slack = Slacker(os.environ['SLACKTOKEN'])
            except KeyError:
                print('If using --slack must set SLACKTOKEN environment variable. [Never share your token!]')
                sys.exit(-1)


if __name__ == '__main__':
    l = Loader()

    l.process_command_line()
    l.checks()

    if l.args.removetest:
        l.removetest()
    elif l.args.list:
        l.print_list()
    elif l.args.updateprovenance:
        l.updateprovenance()
    elif l.args.pg_dump and l.args.grant_everyone_select:
        l.pg_dump()
        l.grant_everyone_select()
    elif l.args.grant_everyone_select:
        l.grant_everyone_select()
    elif l.args.add_resource:
        l.add_resource()
    elif l.args.pg_dump:
        l.pg_dump()
    else:
        l.load()
        l.grant_everyone_select()

