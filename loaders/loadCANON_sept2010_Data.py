#!/usr/bin/env python
__author__    = 'Mike McCann'
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


def loadMissions(baseUrl, fileList, activityName, campaignName, pName, pTypeName, aTypeName, dbName, stride = 1):
	'''Load missions from OPeNDAP url from either a list of files from a base or a single URL with a given activityName '''

	if fileList: 
		for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in files], fileList):
			url = baseUrl + file
			DAPloaders.runDoradoLoader(url, campaignName, aName, pName, pTypeName, aTypeName, dbName, stride)
	elif activityName:
		url = baseUrl
		DAPloaders.runCSVLoader(url, campaignName, activityName, pName, pTypeName, aTypeName, dbName, stride)
	else:
		print "loadMissions(): Must specify either a fileList or an activityName"


if __name__ == '__main__':
	'''load full resolution Dorado and ESP data from September 2010 drifter following experiment into the stoqs_sept2010 database
	'''

	# Specific locations of data to be loaded - ideally the only thing that needs to be changed for another campaign
	dbName = 'stoqs_sept2010'
	stride = 1
	campaignName = 'ESP Drifter Tracking - September 2010'


	# ------------------------- Dorado loads -------------------------
	baseUrl = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
	files =      [  'Dorado389_2010_257_01_258_04_decim.nc',
			'Dorado389_2010_258_05_258_08_decim.nc',
			'Dorado389_2010_259_00_259_03_decim.nc',
			'Dorado389_2010_260_00_260_00_decim.nc',
			'Dorado389_2010_261_00_261_00_decim.nc'
			]
	loadMissions(baseUrl, files, '', campaignName, 'dorado', 'auv', 'AUV Mission', dbName, stride)



	# ------------------------- Julio analyses loads -------------------------

