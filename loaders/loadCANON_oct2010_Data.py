#!/usr/bin/env python
__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Use DAPloaders.py to load full resolution Dorado and ESP data from October 2010
Biospace patch tracking experiment into the stoqs_oct2010 database.

Mike McCann
MBARI 24 Jan 2012

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
	'''load full resolution Dorado and ESP data from October 2010 Biospace patch tracking experiment into the stoqs_oct2010 database
	'''

	# Specific locations of data to be loaded - ideally the only thing that needs to be changed for another campaign
	dbName = 'stoqs_oct2010'
	stride = 1
	campaignName = 'CANON/Biospace/Latmix - October 2010'

	# ------------------------- Dorado loads -------------------------
	baseUrl = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'
	##files =      [  'Dorado389_2010_277_01_277_01_decim.nc',
	##		'Dorado389_2010_278_01_278_01_decim.nc',
	##		'Dorado389_2010_279_02_279_02_decim.nc',
	##files = [		'Dorado389_2010_280_01_280_01_decim.nc',
	##		'Dorado389_2010_284_00_284_00_decim.nc',
	##		'Dorado389_2010_285_00_285_00_decim.nc',
	##		'Dorado389_2010_286_01_286_02_decim.nc',
	files = [	'Dorado389_2010_287_00_287_00_decim.nc',
			'Dorado389_2010_291_00_291_00_decim.nc',
			'Dorado389_2010_292_01_292_01_decim.nc',
			'Dorado389_2010_293_00_293_00_decim.nc',
			'Dorado389_2010_294_01_294_01_decim.nc',
			'Dorado389_2010_298_01_298_01_decim.nc',
			'Dorado389_2010_299_00_299_00_decim.nc',
			'Dorado389_2010_300_00_300_00_decim.nc',
			'Dorado389_2010_301_00_301_00_decim.nc',
		]
	loadMissions(baseUrl, files, '', campaignName, 'dorado', 'auv', 'AUV Mission', dbName, stride)


	# ------------------------- Water sample analyses loads -------------------------

