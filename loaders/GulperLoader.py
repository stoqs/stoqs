#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

The GulperLoader module had a load_gulps() method that parses an odv _gulper.txt
file and saves the gulp events as parent Samples in the STOQS database.

Mike McCann
MBARI 18 April 2012

@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

# Force lookup of models to THE specific stoqs module.
import os
import sys
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # settings.py is one dir up
from django.conf import settings

from stoqs import models as m
from datetime import datetime, timedelta
import numpy
import csv
import urllib2
import logging

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# When settings.DEBUG is True Django will fill up a hash with stats on every insert done to the database.
# "Monkey patch" the CursorWrapper to prevent this.  Otherwise we can't load large amounts of data.
# See http://stackoverflow.com/questions/7768027/turn-off-sql-logging-while-keeping-settings-debug
from django.db.backends import BaseDatabaseWrapper
from django.db.backends.util import CursorWrapper

if settings.DEBUG:
    BaseDatabaseWrapper.make_debug_cursor = lambda self, cursor: CursorWrapper(cursor, self)

class ClosestTimeNotFoundException(Exception):
    pass

def get_closest_instantpoint(aName, tv, dbAlias):
        '''
        Start with a tolerance of 1 second and double it until we get a non-zero count,
        get the values and find the closest one by finding the one with minimum absolute difference.
        '''
        tol = 1
        num_timevalues = 0
        logger.debug('Looking for tv = %s', tv)
        while tol < 86400:                                      # Fail if not found within 24 hours
            qs = m.InstantPoint.objects.using(dbAlias).filter(  activity__name = aName,
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

def load_gulps(activityName, file, dbAlias):
    '''
    file looks like 'Dorado389_2011_111_00_111_00_decim.nc'.  From hard-coded knowledge of MBARI's filesystem
    read the associated _gulper.txt file for the survey and load the gulps as samples in the dbAlias database.
    '''

    # Get the Activity from the Database
    activity = m.Activity.objects.using(dbAlias).get(name=activityName)
    logger.debug('Got activity = %s', activity)

    # Use the dods server to read over http - works from outside of MABRI's Intranet
    baseUrl = 'http://dods.mbari.org/data/auvctd/surveys/'
    yyyy = file.split('_')[1].split('_')[0]
    survey = file.split(r'_decim')[0]
    # E.g.: http://dods.mbari.org/data/auvctd/surveys/2010/odv/Dorado389_2010_300_00_300_00_Gulper.txt
    gulperFile = baseUrl + yyyy + '/odv/' + survey + '_Gulper.txt'

    logger.debug('Reading gulps from %s', gulperFile)
    reader = csv.DictReader(urllib2.urlopen(gulperFile), dialect='excel-tab')

    # Get or create SampleType for Gulper
    (gulper_type, created) = m.SampleType.objects.using(dbAlias).get_or_create(name = 'Gulper')
    logger.debug('sampletype %s, created = %s', gulper_type, created)
    for row in reader:
        # Need to subtract 1 day from odv file as 1.0 == midnight on 1 January
        timevalue = datetime(int(yyyy), 1, 1) + timedelta(days = (float(row[r'YearDay [day]']) - 1))
        ip, seconds_diff = get_closest_instantpoint(activityName, timevalue, dbAlias)
        point = 'POINT(%s %s)' % (row[r'Lon (degrees_east)'], row[r'Lat (degrees_north)'])
        stuple = m.Sample.objects.using(dbAlias).get_or_create( name = row[r'Bottle Number [count]'],
                                                                depth = row[r'DEPTH [m]'],
                                                                geom = point,
                                                                instantpoint = ip,
                                                                sampletype = gulper_type,
                                                                volume = 2000
                                                              )
        rtuple = m.Resource.objects.using(dbAlias).get_or_create( name = 'Seconds away from InstantPoint',
                                                                  value = seconds_diff
                                                                )
        # 2nd item of tuples will be True or False dependending on whether the object was created or gotten
        logger.info('Loaded Sample %s with Resource: %s', stuple, rtuple)


if __name__ == '__main__':

    # A nice test data load for a northern Monterey Bay survey  
    file = 'Dorado389_2010_300_00_300_00_decim.nc'
    aName = file
    dbAlias = 'default'

    load_gulps(aName, file, dbAlias)

