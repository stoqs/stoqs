#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2011, MBARI"
__credits__ = ["Chander Ganesan, Open Technology Group"]
__license__ = "GPL"
__version__ = "$Revision: 12153 $".split()[1]
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

Load small sample of data from OPeNDAP data sources at MBARI
for testing purposes.  The collection should be sufficient to
provide decent test coverage for the STOQS application.

Mike McCann
MBARI Dec 28, 2011

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE']='settings'
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import DAPloaders
from datetime import datetime
from stoqs import models as mod


baseUrl = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
files = [ 'Dorado389_2010_257_01_258_04_decim.nc']
stride = 1000
dbName = 'stoqs_june2011'
              
for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in files], files):
##while False:
    print "Instantiating Auvctd_Loader for url = %s" % baseUrl + file
    loader = DAPloaders.Auvctd_Loader(aName,
                url = baseUrl + file,
                platformName = 'dorado',
                activitytypeName = 'AUV Mission',
                dbName = dbName,
                stride = stride)

    nMP = loader.process_data()

    # Careful with the structure of this comment.  It is parsed in views.py to give some useful links in showActivities()
    newComment = "%d MeasuredParameters loaded for Parameters: %s. Loaded on %sZ" % (nMP, ' '.join(loader.varsLoaded), datetime.utcnow())
    print "Updating comment with newComment = %s" % newComment
    mod.Activity.objects.using(dbName).filter(name = aName).update(comment = newComment)
