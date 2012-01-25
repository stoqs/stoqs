#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__credits__ = ["Chander Ganesan, Open Technology Group"]
__license__ = "GPL"
__version__ = "$Revision: 12295 $".split()[1]
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

The URL patterns for the stoqs database web application.  The first field specifies the
database that is automatically routed to the associated database defined in settings.py,
e.g.:

  http://localhost:8000/stoqs_sept2010/platformTypes
  http://localhost:8000/stoqs_june2011/platformNames
  http://localhost:8000/stoqs_nov2011/platformAssociations.csv


Mike McCann
MBARI Jan 3, 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

from django.conf.urls.defaults import *
from django.contrib.gis import admin
##import views

admin.autodiscover()

pre = r'^(?P<dbName>[^/]+)/'    # The database name will prefix all of our requests

# Repeated between clause for measurement queries
btwnCl = r'(?P<pName>[^/]+)/between/(?P<startDate>\w+)/(?P<endDate>\w+)/depth/(?P<dmin>[0-9\.]+)/(?P<dmax>[0-9\.]+)'

# type is one of: 'data', 'perf'; format is one of: 'html', 'csv', 'kml'
formatCl = r'/(?P<type>\w{4,5})\.(?P<format>\w{0,4})$'


urlpatterns = patterns('',
            
    # Admin interface
    url(pre + r'admin/', include(admin.site.urls)),

    # Type and name queries
    url(pre + r'platformTypes.?(\w{0,4})$', 'stoqs.views.showPlatformTypes', {}, name='show-platform-types'),
    url(pre + r'platformNames.?(\w{0,4})$', 'stoqs.views.showPlatformNames', {}, name='show-platform-names'),
    url(pre + r'platformNamesOfType/(\w+).?(\w{0,4})$', 'stoqs.views.showPlatformNamesOfType', {}, name='show-platform-names-of-type'),
    url(pre + r'platformAssociations.?(\w{0,4})$', 'stoqs.views.showPlatformAssociations', {}, name='show-platform-associations'),

    # Parameters
    url(pre + r'parameters.?(\w{0,4})$', 'stoqs.views.showParameters', {}, name='show-parameters'),

    # Position queries (last, since, between)
    url(pre + r'position/(?P<name>\w+)/last/(?P<number>\d{1,10})(?P<unit>[smhdw]?)/data.?(?P<format>\w{0,4})$', 'stoqs.views.showLastPositions', {}, name='show-last-positions'),
    url(pre + r'position/(\w+)/last/(\d{1,10})([smhdw]?)/stride/(\d+)/data.(\w{0,4})$', 'stoqs.views.showLastPositions', {}, name='show-last-positions'),
    url(pre + r'position/(\w+)/last/(\d{1,10})([smhdw]?)/count$', 'stoqs.views.showLastPositions', {'countFlag': True}, name='show-last-positions'),

    url(pre + r'position/(?P<name>\w+)/since/(?P<startDate>\w+)/data.(?P<format>\w{0,4})$', 'stoqs.views.showSincePositions', {}, name='show-since-positions'),
    url(pre + r'position/(\w+)/since/(\w+)/stride/(\d+)/data.(\w{0,4})$', 'stoqs.views.showSincePositions', {}, name='show-since-positions'),
    url(pre + r'position/(\w+)/since/(\w+)/count$', 'stoqs.views.showSincePositions', {'countFlag': True}, name='show-since-positions'),

    url(pre + r'position/(?P<name>\w+)/between/(?P<startDate>\w+)/(?P<endDate>\w+)/data.(?P<format>\w{0,4})$', 'stoqs.views.showBetweenPositions', {}, name='show-between-positions'),
    url(pre + r'position/(\w+)/between/(\w+)/(\w+)/stride/(\d+)/data.(\w{0,4})$', 'stoqs.views.showBetweenPositions', {}, name='show-between-positions'),
    url(pre + r'position/(\w+)/between/(\w+)/(\w+)/count$', 'stoqs.views.showBetweenPositions', {'countFlag': True}, name='show-between-positions'),

    # Repeat last position queries, but for 'OfType'
    url(pre + r'positionOfType/(?P<name>\w+)/last/(?P<number>\d{1,10})(?P<unit>[smhdw]?)/data.?(?P<format>\w{0,4})$', 
	   'stoqs.views.showLastPositions', {'ofType': True}, name='show-last-positions'),
    url(pre + r'positionOfType/(\w+)/last/(\d{1,10})([smhdw]?)/stride/(\d+)/data.(\w{0,4})$', 
	   'stoqs.views.showLastPositions', {'ofType': True}, name='show-last-positions'),
    url(pre + r'positionOfType/(\w+)/last/(\d{1,10})([smhdw]?)/count$', 
       'stoqs.views.showLastPositions', {'ofType': True, 'countFlag': True}, name='show-last-positions'),

    url(pre + r'positionOfType/(?P<name>\w+)/since/(?P<startDate>\w+)/data.(?P<format>\w{0,4})$', 
	   'stoqs.views.showSincePositions', {'ofType': True}, name='show-since-positions'),
    url(pre + r'positionOfType/(\w+)/since/(\w+)/stride/(\d+)/data.(\w{0,4})$', 
	   'stoqs.views.showSincePositions', {'ofType': True}, name='show-since-positions'),
    url(pre + r'positionOfType/(\w+)/since/(\w+)/count$', 
       'stoqs.views.showSincePositions', {'ofType': True, 'countFlag': True}, name='show-since-positions'),

    url(pre + r'positionOfType/(?P<name>\w+)/between/(?P<startDate>\w+)/(?P<endDate>\w+)/data.(?P<format>\w{0,4})$', 
	   'stoqs.views.showBetweenPositions', {'ofType': True}, name='show-between-positions'),
    url(pre + r'positionOfType/(\w+)/between/(\w+)/(\w+)/stride/(\d+)/data.(\w{0,4})$', 
	    'stoqs.views.showBetweenPositions', {'ofType': True}, name='show-between-positions'),
    url(pre + r'positionOfType/(\w+)/between/(\w+)/(\w+)/count$', 
        'stoqs.views.showBetweenPositions', {'ofType': True, 'countFlag': True}, name='show-between-positions'),

    # Position 'OfActivity' queries
    url(pre + r'positionOfActivity/name/(?P<aName>\w+)/type/(?P<aType>\w+)/data.?(?P<format>\w{0,4})$', 
	   'stoqs.views.showPositionsOfActivity', {}, name='show-positions-of-activity'),
    url(pre + r'positionOfActivity/name/(\w+)/type/(\w+)/stride/(\d+)/data.(\w{0,4})$', 
	   'stoqs.views.showPositionsOfActivity', {}, name='show-positions-of-activity'),

    # Measurements  
    url(pre + r'parameterNames.?(\w{0,4})$', 'stoqs.views.measurement.showParameterNames', {}, name='show-parameter-names'),
    
    url(pre + 'measurement/' + btwnCl + formatCl, 
        'stoqs.views.measurement.showBetweenMeasurements', {}, name='show-between-meas'),
    url(pre + r'measurement/' + btwnCl + '/stride/(?P<stride>\d+)' + formatCl, 
        'stoqs.views.measurement.showBetweenMeasurements', {}, name='show-between-meas-stride'),
                       
    url(pre + 'measurement/sn/' + btwnCl + formatCl, 
        'stoqs.views.measurement.showBetweenMeasurements', {'snFlag': True}, name='show-between-sn-meas'),
    url(pre + r'measurement/sn/' + btwnCl + '/stride/(?P<stride>\d+)' + formatCl, 
        'stoqs.views.measurement.showBetweenMeasurements', {'snFlag': True}, name='show-between-sn-meas-stride'),
                       
    url(pre + r'measurement/' + btwnCl + '/count$', 
        'stoqs.views.measurement.showBetweenMeasurements', {'countFlag': True}, name='show-between-meas-count'),
    url(pre + r'measurement/sn/' + btwnCl + '/count$', 
        'stoqs.views.measurement.showBetweenMeasurements', {'countFlag': True, 'snFlag': True}, name='show-between-sn-meas-count'),
    ##(r'^measurementOfActivity/name/(?P<aName>\w+)/type/(?P<aType>\w+)/data.(?P<format>\w{0,4})$', views.showMeasurementsOfActivity),
    ##(r'^measurementOfActivity/name/(\w+)/type/(\w+)/stride/(\d+)/data.(\w{0,4})$', views.showMeasurementsOfActivity),

    # Management
    url(r'campaigns', 'stoqs.views.management.showCampaigns', {}, name='show-campaigns'),
    url(pre + r'mgmt$', 'stoqs.views.management.showDatabase', {}, name='show-database'),
    url(pre + r'deleteActivity/(?P<activityId>[0-9]+)$', 'stoqs.views.management.deleteActivity', {}, name='delete-activity'),
    url(pre + r'activities$', 'stoqs.views.management.showActivities', {}, name='show-activities'),

)

