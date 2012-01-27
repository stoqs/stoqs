#!/usr/bin/env python
__author__    = 'Mike McCann'
__version__ = '$Revision: 12300 $'.split()[1]
__date__ = '$Date: 2012-01-11 15:07:03 -0800 (Wed, 11 Jan 2012) $'.split()[1]
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Use DAPloaders.py to load full resolution Dorado and ESP data from October 2010
patch tracking experiment into the stoqs_oct2010 database.

Mike McCann
MBARI 24 Jan 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))	# settings.py is one dir up


import DAPloaders
from datetime import datetime
from stoqs import models as mod

# ------------------------- Dorado loads -------------------------
baseUrl = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
##files =      [  'Dorado389_2010_277_01_277_01_decim.nc',
##		'Dorado389_2010_278_01_278_01_decim.nc',
##		'Dorado389_2010_279_02_279_02_decim.nc',
##		'Dorado389_2010_280_01_280_01_decim.nc',
##		'Dorado389_2010_284_00_284_00_decim.nc',
##files = [	'Dorado389_2010_285_00_285_00_decim.nc',
##		'Dorado389_2010_286_01_286_02_decim.nc',
##		'Dorado389_2010_287_00_287_00_decim.nc',
files = [	'Dorado389_2010_291_00_291_00_decim.nc',
		'Dorado389_2010_292_01_292_01_decim.nc',
		'Dorado389_2010_293_00_293_00_decim.nc',
		'Dorado389_2010_294_01_294_01_decim.nc',
		'Dorado389_2010_298_01_298_01_decim.nc',
		'Dorado389_2010_299_00_299_00_decim.nc',
		'Dorado389_2010_300_00_300_00_decim.nc',
		'Dorado389_2010_301_00_301_00_decim.nc',
		]
dbName = 'stoqs_oct2010'
stride = 1
for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in files], files):
##while False:
	print "Instantiating Auvctd_Loader for url = %s" % baseUrl + file
	loader = DAPloaders.Auvctd_Loader(
				url = baseUrl + file,
				campaignName = dbName,
				dbName = dbName,
				activityName = aName,
				activitytypeName = 'AUV Mission',
				platformName = 'dorado',
				platformTypeName = 'auv',
				stride = stride)

	nMP = loader.process_data()

	# Careful with the structure of this comment.  It is parsed in views.py to give some useful links in showActivities()
	# The ':' is important, this is where the string is split.
	# Making this dependency is bad -- we really need to put this kind of information in the model as attributes of Activity
	newComment = "%d MeasuredParameters loaded: %s. Loaded on %sZ" % (nMP, ' '.join(loader.varsLoaded), datetime.utcnow())
	print "Updating comment with newComment = %s" % newComment
	mod.Activity.objects.using(dbName).filter(name = aName).update(comment = newComment, 
												num_measuredparameters = nMP,
												loaded_date = datetime.utcnow())


