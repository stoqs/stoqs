#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2015, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

Master load script that is driven by a dictionary of campaigns and the 
commands that load them. This dictionary also drives the campaigns
served by a deployment of stoqs via the stoqs/campaigns.py file.

Mike McCann
MBARI 5 September 2015
'''

import os
import sys
app_dir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, app_dir)
os.environ['DJANGO_SETTINGS_MODULE']='config.settings.local'
import django
django.setup()

import time
import logging
import datetime
import importlib
import platform
from git import Repo
from django.conf import settings
from django.core.management import call_command
from django.core.exceptions import ObjectDoesNotExist
from stoqs.models import ResourceType, Resource, Campaign, CampaignResource

def tail(f, n):
    stdin,stdout = os.popen2("tail -" + str(n) + " " + f)
    stdin.close()
    lines = stdout.readlines()
    stdout.close()

    return lines

class DatabaseCreationError(Exception):
    pass


class DatabaseLoadError(Exception):
    pass


class Loader():

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    def _create_db(self, db):
        '''Create database. Invoking user should have priveleges to connect to 
        the database server as user postgres. A password may be required.
        '''

        commands = ' && '.join((
            'psql -p {port} -c \"CREATE DATABASE {db} owner=stoqsadm template=template_postgis;\" -U postgres',
            'psql -p {port} -c \"ALTER DATABASE {db} set timezone=\'GMT\';\" -U postgres',
            'psql -p {port} -c \"GRANT ALL ON ALL TABLES IN SCHEMA public TO stoqsadm;\" -d {db} -U postgres'))

        createdb = commands.format(**{'port': settings.DATABASES[db]['PORT'], 'db': db})
        if self.args.clobber:
            createdb = ('psql -p {port} -c \"DROP DATABASE {db};\" -U postgres && '
                    ).format(**{'port': settings.DATABASES[db]['PORT'], 'db': db}) + createdb

        self.logger.info('Creating database %s', db)
        self.logger.debug('createdb = %s', createdb)
        ret = os.system(createdb)
        self.logger.debug('ret = %s', ret)

        if ret != 0:
            # Try again without DROP command if --clobber is specified
            if self.args.clobber:
                createdb = commands.format(**{'port': settings.DATABASES[db]['PORT'], 'db': db})
                self.logger.debug('createdb = %s', createdb)
                ret = os.system(createdb)
                self.logger.debug('ret = %s', ret)
                if ret != 0:
                    raise DatabaseCreationError((
                        'Failed to create {} even after trying without DROP command').format(db))
                else:
                    return

            raise DatabaseCreationError(('Failed to create {}').format(db))

    def provenance_dict(self, load_command, log_file):
        '''Return a dictionary of provenance Resource items
        '''
        repo = Repo(app_dir, search_parent_directories=True)

        prov = {'load_command': load_command,
                'gitorigin': repo.remotes.origin.url,
                'gitcommit': repo.head.commit.hexsha,
                'environment': platform.platform() + " python " + sys.version.split('\n')[0],
                'load_date_gmt': datetime.datetime.utcnow(),
                'real_exection_time': tail(log_file, 3)[0].split()[1],
                'user_exection_time': tail(log_file, 3)[1].split()[1],
                'sys_exection_time': tail(log_file, 3)[2].split()[1],
               }

        return prov

    def record_provenance(self, db, load_command, log_file):
        '''Add Resources to the Campaign that describe what loaded it
        '''
        rt,created = ResourceType.objects.using(db).get_or_create(
                        name='provenance', description='Information about the source of data')
        i = 0
        c = None
        while not c:
            try:
                self.logger.debug('Looking in database %s for first Campaign record', db)
                c = Campaign.objects.using(db).get(id=1)
            except ObjectDoesNotExist:
                # Sleep a bit for jobs running with --background option
                sec_wait = 2
                time.sleep(sec_wait)
                i += 1
                max_iter = 10
                if i > max_iter:
                    raise DatabaseLoadError(('No campaign created after {:d} seconds. '
                            'Check log_file for errors: {}').format(sec_wait * max_iter, log_file))

        for name,value in self.provenance_dict(load_command, log_file).iteritems():
            r,created = Resource.objects.using(db).get_or_create(
                            uristring='', name=name, value=value, resourcetype=rt)
            cr,created = CampaignResource.objects.using(db).get_or_create(
                            campaign=c, resource=r)
            self.logger.info('Resource uristring=%s, name=%s, value=%s', '', name, value)

    def remove_test(self):
        campaigns = importlib.import_module(self.args.campaigns)
        for db,load_command in campaigns.campaigns.iteritems():
            if self.args.db:
                if db not in self.args.db:
                    continue

            db += '_t'
            dropdb = ('psql -c \"DROP DATABASE {};\" -U postgres').format(db)

            self.logger.info('Dropping database %s', db)
            self.logger.debug('dropdb = %s', dropdb)
            ret = os.system(dropdb)
            self.logger.debug('ret = %s', ret)
            if ret != 0:
                self.logger.warn(('Failed to drop {}').format(db))

    def list(self):
        stoqs_campaigns = []
        campaigns = importlib.import_module(self.args.campaigns)
        for db,load_command in campaigns.campaigns.iteritems():
            if self.args.db:
                if db not in self.args.db:
                    continue

            if self.args.test:
                if ((db.endswith('_o') and '-o' in load_command) or 'ROVCTD' in load_command
                       or load_command.endswith('.sh') or '&&' in load_command):
                    continue
                else:
                    db += '_t'

            stoqs_campaigns.append(db)

        print '\n'.join(stoqs_campaigns)
        print 'export STOQS_CAMPAIGNS="' + ','.join(stoqs_campaigns) + '"'
                
    def load(self):
        campaigns = importlib.import_module(self.args.campaigns)
        for db,load_command in campaigns.campaigns.iteritems():
            if self.args.db:
                if db not in self.args.db:
                    continue

            if self.args.test:
                # Do not load test database for optimal stride, ROVCTD or ones 
                # loaded with bash scripts or multiple load executions
                if ((db.endswith('_o') and '-o' in load_command) or 'ROVCTD' in load_command
                       or load_command.endswith('.sh') or '&&' in load_command):
                    continue
                else:
                    load_command += ' -t'
                    db += '_t'
                    self.logger.debug(('Adding {} to STOQS_CAMPAIGNS').format(db))
                    os.environ['STOQS_CAMPAIGNS'] = db + ',' + os.environ.get('STOQS_CAMPAIGNS', '')

                    # Django docs say not to do this, but I can't seem to force a settings reload
                    settings.DATABASES[db] = settings.DATABASES.get('default').copy()
                    settings.DATABASES[db]['NAME'] = db

            try:
                self._create_db(db)
            except DatabaseCreationError as e:
                self.logger.warn(str(e) + ' Perhaps you should use the --clobber option.')
                continue

            call_command('makemigrations', 'stoqs', settings='config.settings.local', noinput=True)

            # Need to execute migrate using manage.py so that config.settings.local 
            # loads the updated STOQS_CAMPAIGNS env variable for test databases
            cmd = ('./manage.py migrate --settings=config.settings.local --noinput '
                   ' --database={}').format(db)
            os.system(cmd)

            # Execute the load
            script = 'loaders/' + load_command
            if self.args.test:
                log_file = script.split()[0].replace('.py', '_t.out')
            else:
                log_file = script.split()[0].replace('.py', '.out')
            cmd = '(time ' + script + ') > ' + log_file + ' 2>&1'
            if self.args.background:
                cmd += ' &'
            self.logger.info('Executing: %s', cmd)
            os.system(cmd)

            try:
                self.record_provenance(db, load_command, log_file)
            except DatabaseLoadError as e:
                self.logger.warn(str(e))

    def process_command_line(self):
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n\n' 
        examples += "  Load all databases:\n"
        examples += "    " + sys.argv[0] + " --all \n"
        examples += "  Reload all databases (dropping all existing databases):\n"
        examples += "    " + sys.argv[0] + " --all --clobber\n"
        examples += "  Reload specific databases from as background jobs with verbose output:\n"
        examples += "    " + sys.argv[0] + " --db stoqs_september2013 stoqs_may2015 --clobber --background -v 1\n"
        examples += "  Drop specific test databases:\n"
        examples += "    " + sys.argv[0] + " --db stoqs_september2010 stoqs_october2010 --removetest -v 1\n"
        examples += "\n"
        examples += '\nIf running from cde-package replace ".py" with ".py.cde".'
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Script to load or reload STOQS databases using the dictionary in stoqs/campaigns.py',
                                         epilog=examples)
                                             
        parser.add_argument('--campaigns', action='store', help='Module containing campaigns dictionary (must also be in campaigns.py)', default='campaigns')

        parser.add_argument('--db', action='store', help='Specify databases from CAMPAIGNS to load', nargs='*')
        parser.add_argument('--all', action='store_true', help='Load all databases referenced in campaigns')
        parser.add_argument('--test', action='store_true', help='Load test databases using -t option of loaders.LoadScript')
        parser.add_argument('--clobber', action='store_true', help='Drop databases before creating and loading them')
        parser.add_argument('--background', action='store_true', help='Execute each load in the background to parallel process multiple loads')
        parser.add_argument('--removetest', action='store_true', help='Drop all test databases; the --db option limits the dropping to those in the list')
        parser.add_argument('--list', action='store_true', help='List the databases that are in --campaigns')

        parser.add_argument('-v', '--verbose', nargs='?', choices=[1,2,3], type=int, help='Turn on verbose output. Higher number = more output.', const=1)
    
        self.args = parser.parse_args()
        self.commandline = ' '.join(sys.argv)

        if self.args.verbose > 1:
            self.logger.setLevel(logging.DEBUG)
        elif self.args.verbose > 0:
            self.logger.setLevel(logging.INFO)
   
 
if __name__ == '__main__':
    l = Loader()
    l.process_command_line()
    if l.args.removetest:
        l.remove_test()
    elif l.args.list:
        l.list()
    else:
        l.load()


