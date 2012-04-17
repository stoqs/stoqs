#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Script to load all of the CANON campaign data.  Edit individual load script to adjust what gets loaded.

Mike McCann
MBARI 16 April 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
project_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))  # settings.py is one dir up

import loadCANON_sept2010_Data
import loadCANON_oct2010_Data
import loadCANON_april2011_Data
import loadCANON_june2011_Data


stride = 1000
loadCANON_sept2010_Data.loadAll(stride)
loadCANON_oct2010_Data.loadAll(stride)
loadCANON_april2011_Data.loadAll(stride)
loadCANON_june2011_Data.loadAll(stride)

