#!/usr/bin/env python

'''
Examine all campaigns on server for OPeNDAP URLs that are broken.
To use:
    1. Symlink the campaigns.py file to mbari_campaigns.py (e.g.)
    2. Set your DATABASE_URL to the correct server/credentials
    3. ./check_opendap_urls.py
'''

# Borrowed some techniques from:
# https://jakevdp.github.io/blog/2017/11/09/exploring-line-lengths-in-python-packages/
# http://nbviewer.jupyter.org/github/stoqs/stoqs/blob/master/stoqs/contrib/notebooks/pull_from_all_databases.ipynb

import django
import os
import psycopg2
import requests
import sys

# Insert Django App directory (parent of config) into python path
sys.path.insert(0, os.path.abspath(os.path.join(
                    os.path.dirname(__file__), "../")))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
django.setup()

try:
    from campaigns import campaigns
except ModuleNotFoundError:
    print('ERROR: campaigns module not found. Did you "cd stoqs && ln -s mbari_campaigns.py campaigns.py"?')
    sys.exit(-1)

from stoqs.models import Campaign, Resource


def iter_db_campaigns():
    for db in campaigns:
        try:
            c = Campaign.objects.using(db).get(id=1)
            yield db, c
        except (django.db.utils.ConnectionDoesNotExist, django.db.utils.OperationalError,
                psycopg2.OperationalError, Campaign.DoesNotExist) as e:
            print(f'{db:25s}: *** {str(e).strip()} ***')

def iter_opendap_urls(db):
    for r in Resource.objects.using(db).filter(name='opendap_url'):
        yield r.uristring

def check_opendap_dds(url):
    try:
        req = requests.head(url + '.dds', timeout=5)
    except requests.exceptions.ConnectionError as e:
        return url

    if req.status_code == 200:
        symb = '.'
    elif req.status_code == 301:
        symb = ','
    else:
        symb = 'x'

    print(symb, end='', flush=True)

    if symb == 'x':
        return url
    else:
        return None


if __name__ == '__main__':
    print('Checking OPeNDAP URLs in campaigns... (key: . good(200)  , redirect(301)  x bad(404)')
    for db, c in iter_db_campaigns():
        print(f'{db:25s}: {c.description}\n  ', end='')
        bad_urls = []
        for url in iter_opendap_urls(db):
            ##print(f'  {url}')
            bad_url = check_opendap_dds(url)
            if bad_url:
                bad_urls.append(bad_url)

        if bad_urls:
            bad_urls_str = '\n             '.join(bad_urls)
            print(f'\n  bad_urls = {bad_urls_str}')
        else:
            print('')

