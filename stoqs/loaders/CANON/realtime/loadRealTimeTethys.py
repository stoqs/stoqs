#!/usr/bin/env python
__author__    = 'Mike McCann'
__version__ = '$Revision: $'.split()[1]
__date__ = '$Date: $'.split()[1]
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Use DAPloaders.py to load data from realtime Tethys shore.nc files into the
stoqs_realtime database.

Mike McCann
MBARI 17 May 2011

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import sys
sys.path.insert(0, "/home/stoqsadm/dev/stoqs/src/loaders")

import DAPloaders
from datetime import datetime

# Tethys loads from TDS on beach
lrauvLoad = DAPloaders.Lrauv_Loader('Tethys realtime - May 2011 (testing 1)',
                url = 'http://beach.mbari.org:8080/thredds/dodsC/agg/tethys_ctd',
                startDatetime = datetime(2011, 5, 8),
                endDatetime = datetime(2011,5, 16),
                platformName = 'tethys',
                stride = 1)

lrauvLoad.process_data()


