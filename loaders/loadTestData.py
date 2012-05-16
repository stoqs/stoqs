#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2011, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

Load small sample of data from OPeNDAP and other data sources at MBARI
for testing purposes.  The collection should be sufficient to
provide decent test coverage for the STOQS application.

Mike McCann
MBARI Dec 28, 2011

@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # settings.py is one dir up

import DAPloaders
import GulperLoader

baseUrl = 'http://odss.mbari.org/thredds/dodsC/dorado/'             # NCML to make salinity.units = "1"
file = 'Dorado389_2010_300_00_300_00_decim.nc'                      # file name is same as activity name
stride = 1000                                                       # Make large for quicker runs, smaller for denser data
dbAlias = 'default'

DAPloaders.runDoradoLoader(baseUrl + file, 'Test Load', '%s (stride=%d)' % (file, stride,), 'dorado', 'auv', 'AUV Mission', dbAlias, stride)
GulperLoader.load_gulps(file, file, dbAlias)


