#!/opt/python/bin/python

__author__    = 'Mike McCann'
__version__ = '$Revision: 12143 $'.split()[1]
__date__ = '$Date: 2011-12-28 15:24:31 -0800 (Wed, 28 Dec 2011) $'.split()[1]
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''
Program for loading Mooring data from THREDDS Data Server to STOQS.

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@status: production
@license: GPL
'''

from loaders import dataloaders as dl
from stoqs import models as m
import datetime

base_url = 'http://elvis.shore.mbari.org/thredds/dodsC/agg/OS_MBARI-%(mooring)s_R_TS'
startDate = datetime.date(2010, 9, 14)
endDate = datetime.date(2010, 9, 18)
for mooring in ('M0', 'M1', 'M2'):
	url = base_url % {'mooring': mooring}
	print "url = %s" % url
	print "Importing mooring data %s from url = %s" % (survey_name, url)
	raw_input('pause')
	activity_name = 'OS_MBARI-%s' % mooring
	ml = dl.Base_Loader(activity_name, 
		platform = m.Platform.objects.get(code = mooring),
		url=url,
		stride=1)
	print "Calling process_data()..."
	ml.process_data()


