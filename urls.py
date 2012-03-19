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

# The database alias (the key of the DATABASES dictionary) will prefix all of our requests
pre = r'^(?P<dbAlias>[^/]+)/'  

# Repeated between clause for measurement queries
btwnCl = r'(?P<pName>[^/]+)/between/(?P<startDate>\w+)/(?P<endDate>\w+)/depth/(?P<dmin>[0-9\.]+)/(?P<dmax>[0-9\.]+)'

# type is one of: 'data', 'perf'; format is one of: 'html', 'csv', 'kml'
typePat = r'/(?P<type>[^/]{4,5})'
formatPat = r'(?P<format>[^/]{0,4})$'
formatCl = typePat + r'\.' + formatPat


urlpatterns = patterns('',
            
    # Admin interface
    url(pre + r'admin/', include(admin.site.urls)),

    # Map interfaces
    url(pre + r'activitiesWMS$', 'stoqs.views.wms.showActivitiesWMS', {}, name='show-activities-wms'),
    url(pre + r'parametersWMS$', 'stoqs.views.wms.showParametersWMS', {}, name='show-parameters-wms'),
    url(pre + r'platformsWMS$', 'stoqs.views.wms.showPlatformsWMS', {}, name='show-platforms-wms'),

    # Type and name queries
    url(pre + r'platformTypes.?' + formatPat, 'stoqs.views.showPlatformTypes', {}, name='show-platform-types'),
    url(pre + r'platformNames.?' + formatPat, 'stoqs.views.showPlatformNames', {}, name='show-platform-names'),
    url(pre + r'platformNamesOfType/(?P<ptn>[^/]+).?' + formatPat, 'stoqs.views.showPlatformNamesOfType', {}, name='show-platform-names-of-type'),
    url(pre + r'platformAssociations.?' + formatPat, 'stoqs.views.showPlatformAssociations', {}, name='show-platform-associations'),

    # All STOQS objects - full object queries with .json, .xml, .html, and .csv responses
    url(pre + r'platform.?' + formatPat, 'stoqs.views.showPlatform', {}, name='show-platform'),
    url(pre + r'platformType.?' + formatPat, 'stoqs.views.showPlatformType', {}, name='show-platformtype'),
    url(pre + r'parameter.?' + formatPat, 'stoqs.views.showParameter', {}, name='show-parameter'),
    url(pre + r'activity.?' + formatPat, 'stoqs.views.showActivity', {}, name='show-activity'),
    url(pre + r'activityType.?' + formatPat, 'stoqs.views.showActivityType', {}, name='show-activitytype'),
    url(pre + r'campaign.?' + formatPat, 'stoqs.views.showCampaign', {}, name='show-campaign'),
    url(pre + r'resource.?' + formatPat, 'stoqs.views.showResource', {}, name='show-resource'),
    url(pre + r'resourceType.?' + formatPat, 'stoqs.views.showResourceType', {}, name='show-resourcetype'),
    url(pre + r'activity_resource.?' + formatPat, 'stoqs.views.showActivityResource', {}, name='show-activityresource'),
    url(pre + r'activity_parameter.?' + formatPat, 'stoqs.views.showActivityParameter', {}, name='show-activityparameter'),

    url(pre + r'parameters.?' + formatPat, 'stoqs.views.showParameters', {}, name='show-parameters'),
    url(pre + r'platforms.?' + formatPat, 'stoqs.views.showPlatforms', {}, name='show-platforms'),
    url(pre + r'platformtypes.?' + formatPat, 'stoqs.views.showPlatformTypes', {}, name='show-platformtypes'),
    url(pre + r'activities.?' + formatPat, 'stoqs.views.showActivities', {}, name='show-activities'),
    url(pre + r'activitytypes.?' + formatPat, 'stoqs.views.showActivityTypes', {}, name='show-activitytypes'),

    # Position queries (last, since, between)
    url(pre + r'position/(?P<name>[^/]+)/last/(?P<number>\d{1,10})(?P<unit>[smhdw]?)/data.' + formatPat, 'stoqs.views.showLastPositions', {}, name='show-last-positions'),
    url(pre + r'position/([^/]+)/last/(\d{1,10})([smhdw]?)/stride/(\d+)/data.' + formatPat, 'stoqs.views.showLastPositions', {}, name='show-last-positions'),
    url(pre + r'position/([^/]+)/last/(\d{1,10})([smhdw]?)/count$', 'stoqs.views.showLastPositions', {'countFlag': True}, name='show-last-positions'),

    url(pre + r'position/(?P<name>\w+)/since/(?P<startDate>\w+)/data.' + formatPat, 'stoqs.views.showSincePositions', {}, name='show-since-positions'),
    url(pre + r'position/([^/]+)/since/([^/]+)/stride/(\d+)/data.' + formatPat, 'stoqs.views.showSincePositions', {}, name='show-since-positions'),
    url(pre + r'position/([^/]+)/since/([^/]+)/count$', 'stoqs.views.showSincePositions', {'countFlag': True}, name='show-since-positions'),

    url(pre + r'position/(?P<name>\w+)/between/(?P<startDate>[^/]+)/(?P<endDate>[^/]+)/data.' + formatPat, 'stoqs.views.showBetweenPositions', {}, name='show-between-positions'),
    url(pre + r'position/([^/]+)/between/([^/]+)/([^/]+)/stride/(\d+)/data.' + formatPat, 'stoqs.views.showBetweenPositions', {}, name='show-between-positions'),
    url(pre + r'position/([^/]+)/between/([^/]+)/([^/]+)/count$', 'stoqs.views.showBetweenPositions', {'countFlag': True}, name='show-between-positions'),

    # Repeat last position queries, but for 'OfType'
    url(pre + r'positionOfType/(?P<name>\w+)/last/(?P<number>\d{1,10})(?P<unit>[smhdw]?)/data.' + formatPat, 
	   'stoqs.views.showLastPositions', {'ofType': True}, name='show-last-positions'),
    url(pre + r'positionOfType/(\w+)/last/(\d{1,10})([smhdw]?)/stride/(\d+)/data.' + formatPat, 
	   'stoqs.views.showLastPositions', {'ofType': True}, name='show-last-positions'),
    url(pre + r'positionOfType/([^/]+)/last/(\d{1,10})([smhdw]?)/count$', 
       'stoqs.views.showLastPositions', {'ofType': True, 'countFlag': True}, name='show-last-positions'),

    url(pre + r'positionOfType/(?P<name>[^/]+)/since/(?P<startDate>\w+)/data.' + formatPat, 
	   'stoqs.views.showSincePositions', {'ofType': True}, name='show-since-positions'),
    url(pre + r'positionOfType/(\w+)/since/([^/]+)/stride/(\d+)/data.' + formatPat, 
	   'stoqs.views.showSincePositions', {'ofType': True}, name='show-since-positions'),
    url(pre + r'positionOfType/([^/]+)/since/(\w+)/count$', 
       'stoqs.views.showSincePositions', {'ofType': True, 'countFlag': True}, name='show-since-positions'),

    url(pre + r'positionOfType/(?P<name>[^/]+)/between/(?P<startDate>\w+)/(?P<endDate>\w+)/data.' + formatPat, 
	   'stoqs.views.showBetweenPositions', {'ofType': True}, name='show-between-positions'),
    url(pre + r'positionOfType/([^/]+)/between/([^/]+)/([^/]+)/stride/(\d+)/data.' + formatPat, 
	    'stoqs.views.showBetweenPositions', {'ofType': True}, name='show-between-positions'),
    url(pre + r'positionOfType/([^/]+)/between/([^/]+)/([^/]+)/count$', 
        'stoqs.views.showBetweenPositions', {'ofType': True, 'countFlag': True}, name='show-between-positions'),

    # Position 'OfActivity' queries
    url(pre + r'positionOfActivity/name/(?P<aName>[^/]+)/type/(?P<aType>[^/]+)/data.' + formatPat, 
	   'stoqs.views.showPositionsOfActivity', {}, name='show-positions-of-activity'),
    url(pre + r'positionOfActivity/name/([^/]+)/type/([^/]+)/stride/(\d+)/data.' + formatPat, 
	   'stoqs.views.showPositionsOfActivity', {}, name='show-positions-of-activity'),

    # Measurements  
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
    url(pre + r'activitiesMBARICustom$', 'stoqs.views.management.showActivitiesMBARICustom', {}, name='show-activities'),

)

