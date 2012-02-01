#!/usr/bin/env python
__author__    = 'Mike McCann'
__version__ = '$Revision: 12300 $'.split()[1]
__date__ = '$Date: 2012-01-11 15:07:03 -0800 (Wed, 11 Jan 2012) $'.split()[1]
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Use DAPloaders.py to load full resolution Dorado and ESP data from September 2010
drifter following experiment into the stoqs_sept2010 database.

Mike McCann
MBARI 29 June 2011

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
files =      [  'Dorado389_2010_257_01_258_04_decim.nc',
		'Dorado389_2010_258_05_258_08_decim.nc',
		'Dorado389_2010_259_00_259_03_decim.nc',
		'Dorado389_2010_260_00_260_00_decim.nc',
		'Dorado389_2010_261_00_261_00_decim.nc'
		]
dbName = 'stoqs_sept2010'
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

	(nMP, path) = loader.process_data()

	# Careful with the structure of this comment.  It is parsed in views.py to give some useful links in showActivities()
	# The ':' is important, this is where the string is split.
	# Making this dependency is bad -- we really need to put this kind of information in the model as attributes of Activity
	newComment = "%d MeasuredParameters loaded: %s. Loaded on %sZ" % (nMP, ' '.join(loader.varsLoaded), datetime.utcnow())
	print "Updating comment with newComment = %s" % newComment
	mod.Activity.objects.using(dbName).filter(name = aName).update(comment = newComment, 
									maptrack = path,
									num_measuredparameters = nMP,
									loaded_date = datetime.utcnow())


sys.exit(11)
# ------------------------- Julio analyses loads -------------------------
##baseUrl = 'http://elvis.shore.mbari.org:8080/thredds/dodsC/agg/'
##		'OS_MBARI-M1_R_TS',
for (aName, file) in zip(['Mooring ' +  a + ' (stride=1)' for a in files], files):
	print "Instantiating Mooring_Loader for url = %s" % baseUrl + file
	loader = CSVloaders.ESP_Loader(aName,
				url = baseUrl + file,
				platformName = 'ESP',
				activitytypeName = 'Drifter deployment',
				startDatetime = datetime(2010, 9, 14),
				dataStartDatetime = datetime(2010, 9, 14),
				endDatetime = datetime(2010, 9, 18),
				stride = 1)

	try:
		nMP = loader.process_data()
	except DAPloaders.NoValidData:
		print "*** No valid data from url = %s" % baseUrl + file
		continue

	# Careful with the structure of this comment.  It is parsed in views.py to give some useful links in showActivities()
	newComment = "%d MeasuredParameters loaded for Parameters: %s. Loaded on %sZ" % (nMP, ' '.join(loader.varsLoaded), datetime.utcnow())
	print "Updating comment with newComment = %s" % newComment
	mod.Activity.objects.using(dbName).filter(name = aName).update(comment = newComment)

