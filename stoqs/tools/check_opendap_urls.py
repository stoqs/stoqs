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
# http://mahugh.com/2017/05/23/http-requests-asyncio-aiohttp-vs-requests/

import asyncio
import concurrent
import django
import os
import psycopg2
import sys

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectorError
from timeit import default_timer

# Insert Django App directory (parent of config) into python path
sys.path.insert(0, os.path.abspath(os.path.join(
                    os.path.dirname(__file__), "../")))
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
django.setup()

try:
    from campaigns import campaigns
except ModuleNotFoundError:
    print('ERROR: campaigns module not found. Did you "cd stoqs && ln -s mbari_campaigns.py campaigns.py"?')
    sys.exit(-1)

from stoqs.models import Campaign, Resource


all_bad_urls = []

def iter_db_campaigns():
    for db, load_script in campaigns.items():
        try:
            c = Campaign.objects.using(db).get(id=1)
            yield db, c, load_script
        except (django.db.utils.ConnectionDoesNotExist, 
                django.db.utils.OperationalError,
                psycopg2.OperationalError, 
                Campaign.DoesNotExist, 
                django.db.utils.ProgrammingError) as e:
            print(f'{db:25s}: *** {str(e).strip()} ***')

def iter_opendap_urls_batch(db, batch=4):
    '''Iterator to return a batch of urls in a list each time it's called
    '''
    count = Resource.objects.using(db).filter(name='opendap_url', 
                                              uristring__startswith='http').count()
    for i in range(0, count, batch):
        yield (Resource.objects.using(db).filter(name='opendap_url')
                .order_by('name').values_list('uristring', flat=True)[i:i + batch])

async def check_opendap(url, session):
    check_opendap.start_time[url] = default_timer()

    try:
        async with session.get(url, timeout=5) as response:
            if response.status == 404:
                symb = 'x'
            elif response.status == 301:
                symb = ','
            else:
                symb = '.'
            elapsed = default_timer() - check_opendap.start_time[url]
            ##print('{0:30}{1:5.2f} {2}'.format(url, elapsed, asterisks(elapsed)))
            print(symb, end='', flush=True)
            if symb == 'x':
                return url

    except (ClientConnectorError, concurrent.futures._base.TimeoutError):
        symb = 'x'
        print(symb, end='', flush=True)
        return url


async def check_urls(urls):
    tasks = []
    async with ClientSession() as session:
        for url in urls:
            check_opendap.start_time = dict()
            task = asyncio.ensure_future(check_opendap(url, session))
            tasks.append(task)

        bad_urls = await asyncio.gather(*tasks)
        bad_urls = [x for x in bad_urls if x is not None]

    all_bad_urls.extend(x for x in bad_urls if x is not None)

def asterisks(num):
    """Returns a string of asterisks reflecting the magnitude of a number."""
    return int(num*10)*'*'


if __name__ == '__main__':
    print('Checking OPeNDAP URLs in campaigns... (key: . good(200)  , redirect(301)  x bad(404)')
    for db, c, load_script in iter_db_campaigns():
        print(f'{db:25s}: {c.description}')
        print(f'{load_script}\n  ', end='')
        all_bad_urls = []
        loop = asyncio.get_event_loop()
        for urls in iter_opendap_urls_batch(db, batch=30):
            future = asyncio.ensure_future(check_urls(urls))
            loop.run_until_complete(future)

        if all_bad_urls:
            bad_urls_str = '\n             '.join(all_bad_urls)
            print(f'\n  bad_urls = {bad_urls_str}\n')
        else:
            print('\n')

