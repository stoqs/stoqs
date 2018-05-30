#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Master loader for all CANON activities

Mike McCann
MBARI 22 April 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # settings.py is one dir up

from MarMenor import MarMenorLoader
import timing

try:
    stride = int(sys.argv[1])
except IndexError:
    stride = 100
try:
    dbAlias = sys.argv[2]
except IndexError:
    dbAlias = 'stoqs_marmenor_nov2011_s100'


# ----------------------------------------------------------------------------------
mml = MarMenorLoader(dbAlias, 'MarMenor - October 2011')

##mml.sparus_base='http://odss.mbari.org/thredds/dodsC/'
##mml.sparus_files='marmenor/insitu/UniversityOfGirona/'
##mml.sparus_parms=['

mml.castaway_base='http://odss.mbari.org/thredds/dodsC/'
mml.castaway_files=['agg/Castaway/20111110']
mml.castaway_parms=['temperature', 'salinity']

mml.stride = stride
mml.loadAll()

