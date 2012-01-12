#!/usr/bin/env python
__author__    = 'Mike McCann'
__version__ = '$Revision: 12155 $'.split()[1]
__date__ = '$Date: 2011-12-29 16:51:47 -0800 (Thu, 29 Dec 2011) $'.split()[1]
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Use DAPloaders.py to load full resolution Dorado and Tethys data from April 2011
into the stoqs_april2011 database.

Mike McCann
MBARI 3 May 2011

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

import sys
sys.path.insert(0, "../loaders")

import DAPloaders
from datetime import datetime
from stoqs import models as mod

# Dorado loads
baseUrl = 'http://dods.mbari.org/opendap/data/auvctd/surveys/2011/netcdf/'
files =      [  'Dorado389_2011_110_12_110_12_decim.nc',
		'Dorado389_2011_111_00_111_00_decim.nc',
		'Dorado389_2011_115_10_115_10_decim.nc',
		'Dorado389_2011_116_00_116_00_decim.nc',
		'Dorado389_2011_117_01_117_01_decim.nc',
		'Dorado389_2011_118_00_118_00_decim.nc'
		]
for (aName, file) in zip([ a + ' (stride=1)' for a in files], files):
	print "Instantiating Auvctd_Loader for url = %s" % baseUrl + file
	loader = DAPloaders.Auvctd_Loader(aName,
				url = baseUrl + file,
				platformName = 'dorado',
				activitytypeName = 'AUV Mission',
				stride = 1)

	nMP = loader.process_data()

	# Careful with the structure of this comment.  It is parsed in views.py to give some useful links in showActivities()
	newComment = "%d MeasuredParameters loaded for Parameters: %s. Loaded on %sZ" % (nMP, ' '.join(loader.varsLoaded), datetime.utcnow())
	print "Updating comment with newComment = %s" % newComment
	mod.Activity.objects.filter(name = aName).update(comment = newComment)


# Tethys loads
# The Hyrax server seems to deliver data from variables with '.' in the name from the DODS access form, but pydap throws an exception
##baseUrl = 'http://dods.mbari.org/opendap/data/lrauv/Tethys/missionlogs/2011/'
# Must use the TDS server as is has the NCML which removes the variables with '.' in the name
baseUrl = 'http://elvis.shore.mbari.org:8080/thredds/dodsC/lrauv/tethys/2011/'
files =	     [	'20110415_20110418/20110415T163108/slate.nc',
		'20110415_20110418/20110416T074851/slate.nc',
		'20110415_20110418/20110417T064753/slate.nc',
		'20110415_20110418/20110418T060227/slate.nc',
		'20110415_20110418/20110418T192351/slate.nc',
		'20110421_20110424/20110421T170430/slate.nc',
		'20110421_20110424/20110422T001932/slate.nc',
		'20110421_20110424/20110423T223119/slate.nc',
		'20110421_20110424/20110424T214938/slate.nc',
		'20110426_20110502/20110426T171129/slate.nc',
		'20110426_20110502/20110427T191236/slate.nc',
		'20110426_20110502/20110429T222225/slate.nc',
		'20110426_20110502/20110430T132028/slate.nc',
		'20110426_20110502/20110502T040031/slate.nc'
		]

for (aName, file) in zip(['Tethys ' +  a + ' (stride=4)' for a in files], files):
	print "Instantiating Lrauv_Loader for url = %s" % baseUrl + file
	loader = DAPloaders.Lrauv_Loader(aName,
				url = baseUrl + file,
				platformName = 'tethys',
				activitytypeName = 'AUV Mission',
				stride = 4)

	nMP = loader.process_data()

	# Careful with the structure of this comment.  It is parsed in views.py to give some useful links in showActivities()
	newComment = "%d MeasuredParameters loaded for Parameters: %s. Loaded on %sZ" % (nMP, ' '.join(loader.varsLoaded), datetime.utcnow())
	print "Updating comment with newComment = %s" % newComment
	mod.Activity.objects.filter(name = aName).update(comment = newComment)

