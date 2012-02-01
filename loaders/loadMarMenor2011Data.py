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

def runLoader(url, cName, aName, pName, pTypeName, aTypeName, parmList, dbName, stride):
	'''Run the DAPloader for AUVCTD trajectory data and update the Activity with attributes resulting from the load into dbName'''

	print "Instantiating Auvctd_Loader for url = %s" % url
	loader = DAPloaders.Auvctd_Loader(
			url = url,
			campaignName = cName,
			dbName = dbName,
			activityName = aName,
			activitytypeName = aTypeName,
			platformName = pName,
			platformTypeName = pTypeName,
			stride = stride)

	print "runLoader(): Setting include_names to %s" % parmList
	loader.include_names = parmList
	(nMP, path) = loader.process_data()
	print "runLoader(): Loaded Activity with name = %s" % aName

	# Careful with the structure of this comment.  It is parsed in views.py to give some useful links in showActivities()
	newComment = "%d MeasuredParameters loaded: %s. Loaded on %sZ" % (nMP, ' '.join(loader.varsLoaded), datetime.utcnow())
	print "runLoader(): Updating its comment with newComment = %s" % newComment

	num_updated = mod.Activity.objects.using(dbName).filter(name = aName).update(comment = newComment,
						maptrack = path,
						num_measuredparameters = nMP,
						loaded_date = datetime.utcnow())

	print "runLoader(): %d activities updated with new attributes." % num_updated
	raw_input('paused')


def loadMissions(baseUrl, fileList, activityName, campaignName, pName, pTypeName, aTypeName, parmList, dbName, stride = 1):
	'''Load missions from OPeNDAP url from either a list of files from a base or a single URL with a given activityName '''

	if fileList: 
		for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in files], fileList):
			url = baseUrl + file
			print "loadMissions(): Calling runLoader() with parmList = %s" % parmList
			runLoader(url, campaignName, aName, pName, pTypeName, aTypeName, parmList, dbName, stride)
	elif activityName:
		url = baseUrl
		runLoader(url, campaignName, activityName, pName, pTypeName, aTypeName, parmList, dbName, stride)
	else:
		print "loadMissions(): Must specify either a fileList or an activityName"


# Specific locations of data to be loaded - ideally the only thing that needs to be changed for another campaign
if __name__ == '__main__':
	'''Mar Menor In Situ (AUV and Castaway) data loads '''

	dbName = 'stoqs_nov2011'
	campaignName = 'Mar Menor - November 2011'

	# Sparus, e.g.: http://odss.mbari.org:8080/thredds/dodsC/marmenor/insitu/UniversityOfGirona/exp4_5Nov2011_data.nc.html
	baseUrl = 'http://odss.mbari.org:8080/thredds/dodsC/marmenor/insitu/'
	files =      [  'UniversityOfGirona/exp1_3Nov2011_data.nc',
			'UniversityOfGirona/exp2_3Nov2011_data.nc',
			'UniversityOfGirona/exp3_5Nov2011_data.nc',
			'UniversityOfGirona/exp4_5Nov2011_data.nc',
			]
	parms = ['temperature', 'conductivity']
	loadMissions(baseUrl, files, '', campaignName, 'sparus', 'auv', 'AUV Mission', parms, dbName)

	# University of Villanova
	baseUrl = 'http://odss.mbari.org:8080/thredds/dodsC/marmenor/insitu/'
	files =      [  'UniversityOfVillanova/GuanayII_2011-11-3_Salinity_v2.nc',
			'UniversityOfVillanova/GuanayII-4nov.nc',
			]
	parms = ['temperature', 'conductivity', 'salinity']
	loadMissions(baseUrl, files, '', campaignName, 'guanayii', 'auv', 'AUV Mission', parms, dbName)

	# University of Porto
	baseUrl = 'http://odss.mbari.org:8080/thredds/dodsC/marmenor/insitu/'
	files =      [  'UniversityOfPorto/092152_quad_1m.nc',
			'UniversityOfPorto/085825_rect_6_8.nc',
			'UniversityOfPorto/085422_quad_surface.nc',
			'UniversityOfPorto/083743_rect_1m.nc',
			'UniversityOfPorto/081952_quad_100m_superficie.nc',
			]
	parms = ['temperature', 'conductivity', 'salinity']
	loadMissions(baseUrl, files, '', campaignName, 'seacon-2', 'auv', 'AUV Mission', parms, dbName)

	# Castaway: http://odss.mbari.org:8080/thredds/dodsC/agg/Castaway.html
	baseUrl = 'http://odss.mbari.org:8080/thredds/dodsC/agg/Castaway'
	aName = 'All Castaway CTD casts done from the Sorell on 5 November 2011'
	parms = ['temperature', 'conductivity', 'salinity']
	loadMissions(baseUrl, '', aName, campaignName, 'Castaway', 'ship', 'CTD Casts', parms, dbName)

