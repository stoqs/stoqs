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


def loadDoradoMissions(baseUrl, fileList, activityName, campaignName, pName, pTypeName, aTypeName, dbName, stride = 1):
	'''Load missions from OPeNDAP url from either a list of files from a base or a single URL with a given activityName '''

	if fileList: 
		for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in files], fileList):
			url = baseUrl + file
			DAPloaders.runDoradoLoader(url, campaignName, aName, pName, pTypeName, aTypeName, dbName, stride)

def loadTethysMissions(baseUrl, fileList, activityName, campaignName, pName, pTypeName, aTypeName, dbName, stride = 1):
	'''Load missions from OPeNDAP url from either a list of files from a base or a single URL with a given activityName '''

	parmList = ['mass_concentration_of_chlorophyll_in_sea_water']
	if fileList: 
		for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in files], fileList):
			url = baseUrl + file
			DAPloaders.runLrauvLoader(url, campaignName, aName, pName, pTypeName, aTypeName, parmList, dbName, stride)

def loadMartinActivities(baseUrl, fileList, activityName, campaignName, pName, pTypeName, aTypeName, dbName, stride = 1):
	'''Load missions from OPeNDAP url from either a list of files from a base or a single URL with a given activityName '''

	parmList = ['conductivity', 'temperature', 'salinity', 'fluorescence', 'turbidity']
	if fileList: 
		for (aName, file) in zip([ a + ' (stride=%d)' % stride for a in files], fileList):
			url = baseUrl + file
			DAPloaders.runAuvctdLoader(url, campaignName, aName, pName, pTypeName, aTypeName, parmList, dbName, stride)
	else:
		print "loadMartinActivities(): Must specify a fileList"


if __name__ == '__main__':
	'''load full resolution Dorado and ESP data from October 2010 Biospace patch tracking experiment into the stoqs_oct2010 database
	'''

	# Specific locations of data to be loaded - ideally the only thing that needs to be changed for another campaign
	dbName = 'stoqs_oct2010'
	stride = 1000
	campaignName = 'CANON/Biospace/Latmix - October 2010'

	# --------------------------------- Dorado loads -------------------------------
	##baseUrl = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/'	# salinity.units = "", pydap can't handle
	baseUrl = 'http://odss.mbari.org/thredds/dodsC/dorado/'				# NCML to make salinity.units = "1"
	files =      [  'Dorado389_2010_277_01_277_01_decim.nc',
			'Dorado389_2010_278_01_278_01_decim.nc',
			'Dorado389_2010_279_02_279_02_decim.nc',
			'Dorado389_2010_280_01_280_01_decim.nc',
			'Dorado389_2010_284_00_284_00_decim.nc',
			'Dorado389_2010_285_00_285_00_decim.nc',
			'Dorado389_2010_286_01_286_02_decim.nc',
			'Dorado389_2010_287_00_287_00_decim.nc',
			'Dorado389_2010_291_00_291_00_decim.nc',
			'Dorado389_2010_292_01_292_01_decim.nc',
			'Dorado389_2010_293_00_293_00_decim.nc',
			'Dorado389_2010_294_01_294_01_decim.nc',
			'Dorado389_2010_298_01_298_01_decim.nc',
			'Dorado389_2010_299_00_299_00_decim.nc',
			'Dorado389_2010_300_00_300_00_decim.nc',
			'Dorado389_2010_301_00_301_00_decim.nc',
		]
	loadDoradoMissions(baseUrl, files, '', campaignName, 'dorado', 'auv', 'AUV Mission', dbName, stride)

	# --------------------------- Martin Underway loads ----------------------------
	baseUrl = 'http://odss.mbari.org/thredds/dodsC/jhm_underway'
	files =      [  '27710_jhmudas_v1.nc',
			'27810_jhmudas_v1.nc',
			'27910_jhmudas_v1.nc',
			'28010_jhmudas_v1.nc',
			'28110_jhmudas_v1.nc',
			'28410_jhmudas_v1.nc',
			'28510_jhmudas_v1.nc',
			'28610_jhmudas_v1.nc',
			'28710_jhmudas_v1.nc',
			'29010_jhmudas_v1.nc',
			'29110_jhmudas_v1.nc',
			'29210_jhmudas_v1.nc',
			'29310_jhmudas_v1.nc',
			'29410_jhmudas_v1.nc',
			'29810_jhmudas_v1.nc',
			'29910_jhmudas_v1.nc',
			'30010_jhmudas_v1.nc',
			'30110_jhmudas_v1.nc',
		]
	loadMartinActivities(baseUrl, files, '', campaignName, 'martin', 'ship', 'cruise', dbName, stride)

	# ----------------------------- Tethys LR AUV loads ----------------------------
	baseUrl = 'http://dods.mbari.org/opendap/data/auvctd/tethys/2010/netcdf/'
	files =      [  '20101018T143308_Chl_.nc',
			'20101019T001815_Chl_.nc',
			'20101019T155117_Chl_.nc',
			'20101020T113957_Chl_.nc',
		]
	loadTethysMissions(baseUrl, files, '', campaignName, 'tethys', 'auv', 'AUV Mission', dbName, stride)

	# ------------------------- Water sample analyses loads ------------------------

