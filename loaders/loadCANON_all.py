#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Script to load all of the CANON campaign data.  Edit individual load script to adjust what gets loaded.
This could probably be made OO with a loadCANON class to ease the places where things get edited.  For
example, in the future I'd like to change the database names to be more consistent.  Right now I need to
edit the individual loadCANON_* files to make this change.

Mike McCann
MBARI 20 April 2012

@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import loadCANON_sept2010_Data
import loadCANON_oct2010_Data
import loadCANON_april2011_Data
import loadCANON_june2011_Data

stride = 10
loadCANON_sept2010_Data.loadAll(stride)
loadCANON_oct2010_Data.loadAll(stride)
loadCANON_april2011_Data.loadAll(stride)
loadCANON_june2011_Data.loadAll(stride)

