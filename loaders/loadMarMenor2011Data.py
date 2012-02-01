#!/usr/bin/env python
__author__    = 'Mike McCann'
__version__ = '$Revision: 12152 $'.split()[1]
__date__ = '$Date: 2011-12-29 16:35:55 -0800 (Thu, 29 Dec 2011) $'.split()[1]
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Use DAPloaders.py to load full resolution AUV and shipboard CTD (Castaway) 
data from the Mar Menor AUV Experiment - November 2011 into the stoqs_nov2011
database.

Mike McCann
MBARI 9 November 2011

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE']='settings'
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import DAPloaders
from datetime import datetime
from stoqs import models as mod

# ------------------------- Mar Menor In Situ (AUV and Castaway) data loads -------------------------
# E.g.:
#   http://odss.mbari.org:8080/thredds/dodsC/marmenor/insitu/UniversityOfGirona/exp4_5Nov2011_data.nc.html
# This could be smarter with a directory scan...
baseUrl = 'http://odss.mbari.org:8080/thredds/dodsC/marmenor/insitu/'
files =      [  'UniversityOfGirona/exp1_3Nov2011_data.nc',
		'UniversityOfGirona/exp2_3Nov2011_data.nc',
		'UniversityOfGirona/exp3_5Nov2011_data.nc',
		'UniversityOfGirona/exp4_5Nov2011_data.nc',
		]
for (aName, file) in zip([ a + ' (stride=1)' for a in files], files):
##while False:
	print "Instantiating Auvctd_Loader for url = %s" % baseUrl + file
	loader = DAPloaders.Auvctd_Loader(aName,
				url = baseUrl + file,
				platformName = 'sparus',
				platformTypeName = 'auv',
				activitytypeName = 'AUV Mission',
				stride = 1)

	loader.include_names = ['temperature', 'conductivity']
	(nMP, path) = loader.process_data()

	# Careful with the structure of this comment.  It is parsed in views.py to give some useful links in showActivities()
	newComment = "%d MeasuredParameters loaded for Parameters: %s. Loaded on %sZ" % (nMP, ' '.join(loader.varsLoaded), datetime.utcnow())
	print "Updating comment with newComment = %s" % newComment
	mod.Activity.objects.filter(name = aName).update(comment = newComment,
								maptrack = path,
								num_measuredparameters = nMP,
								loaded_date = datetime.utcnow())


# http://odss.mbari.org:8080/thredds/dodsC/agg/Castaway.html
baseUrl = 'http://odss.mbari.org:8080/thredds/dodsC/agg/Castaway'
aName = 'All Castaway CTD casts done from the Sorell on 5 November 2011'
file = ''
if True:	# Do just once
##if False:
	print "Instantiating Auvctd_Loader for url = %s" % baseUrl + file
	loader = DAPloaders.Auvctd_Loader(aName,
				url = baseUrl + file,
				platformName = 'Castaway',
				platformTypeName = 'ship',
				activitytypeName = 'CTD Casts',
				stride = 1)

	loader.include_names = ['temperature', 'conductivity', 'salinity']
	(nMP, path) = loader.process_data()

	# Careful with the structure of this comment.  It is parsed in views.py to give some useful links in showActivities()
	newComment = "%d MeasuredParameters loaded for Parameters: %s. Loaded on %sZ" % (nMP, ' '.join(loader.varsLoaded), datetime.utcnow())
	print "Updating comment with newComment = %s" % newComment
	mod.Activity.objects.filter(name = aName).update(comment = newComment,
								maptrack = path,
								num_measuredparameters = nMP,
								loaded_date = datetime.utcnow())


# University of Villanova
baseUrl = 'http://odss.mbari.org:8080/thredds/dodsC/marmenor/insitu/'
files =      [  'UniversityOfVillanova/GuanayII_2011-11-3_Salinity_v2.nc',
		'UniversityOfVillanova/GuanayII-4nov.nc',
		]
for (aName, file) in zip([ a + ' (stride=1)' for a in files], files):
##while False:
	print "Instantiating Auvctd_Loader for url = %s" % baseUrl + file
	loader = DAPloaders.Auvctd_Loader(aName,
				url = baseUrl + file,
				platformName = 'guanayii',
				platformTypeName = 'auv',
				activitytypeName = 'AUV Mission',
				stride = 1)

	loader.include_names = ['temperature', 'conductivity', 'salinity']
	(nMP, path) = loader.process_data()

	# Careful with the structure of this comment.  It is parsed in views.py to give some useful links in showActivities()
	newComment = "%d MeasuredParameters loaded for Parameters: %s. Loaded on %sZ" % (nMP, ' '.join(loader.varsLoaded), datetime.utcnow())
	print "Updating comment with newComment = %s" % newComment
	mod.Activity.objects.filter(name = aName).update(comment = newComment,
								maptrack = path,
								num_measuredparameters = nMP,
								loaded_date = datetime.utcnow())


# University of Porto
baseUrl = 'http://odss.mbari.org:8080/thredds/dodsC/marmenor/insitu/'
files =      [  'UniversityOfPorto/092152_quad_1m.nc',
		'UniversityOfPorto/085825_rect_6_8.nc',
		'UniversityOfPorto/085422_quad_surface.nc',
		'UniversityOfPorto/083743_rect_1m.nc',
		'UniversityOfPorto/081952_quad_100m_superficie.nc',
		]
for (aName, file) in zip([ a + ' (stride=1)' for a in files], files):
##while False:
	print "Instantiating Auvctd_Loader for url = %s" % baseUrl + file
	loader = DAPloaders.Auvctd_Loader(aName,
				url = baseUrl + file,
				platformName = 'seacon-2',
				platformTypeName = 'auv',
				activitytypeName = 'AUV Mission',
				stride = 1)

	loader.include_names = ['temperature', 'conductivity', 'salinity']
	(nMP, path) = loader.process_data()

	# Careful with the structure of this comment.  It is parsed in views.py to give some useful links in showActivities()
	newComment = "%d MeasuredParameters loaded for Parameters: %s. Loaded on %sZ" % (nMP, ' '.join(loader.varsLoaded), datetime.utcnow())
	print "Updating comment with newComment = %s" % newComment
	mod.Activity.objects.filter(name = aName).update(comment = newComment,
								maptrack = path,
								num_measuredparameters = nMP,
								loaded_date = datetime.utcnow())

