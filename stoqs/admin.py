#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__credits__ = ["Chander Ganesan, Open Technology Group"]
__license__ = "GPL"
__version__ = "$Revision: 12197 $".split()[1]
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

<replace with short module description>

Mike McCann
MBARI Jan 3, 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''


from stoqs import custom_admin as admin
from stoqs import models

class CampaignAdmin(admin.OSMGeoAdmin):
    list_display=('name', 'description', 'startdate', 'enddate')

class CampaignLogAdmin(admin.OSMGeoAdmin):
    list_display=('message', 'timevalue', 'campaign')

class ActivityAdmin(admin.OSMGeoAdmin):
    list_display=('name', 'comment', 'activitytype')

class ActivityTypeAdmin(admin.OSMGeoAdmin):
    list_display=('name',)

class PlatformTypeAdmin(admin.OSMGeoAdmin):
    list_display=('name',)

class PlatformAdmin(admin.OSMGeoAdmin):
    list_display=('name', 'platformtype')

class InstantPointAdmin(admin.OSMGeoAdmin):
    list_display=('activity', 'timevalue')

class MeasurementAdmin(admin.OSMGeoAdmin):
    list_display=('depth', 'geom', 'instantpoint')

class MeasuredParameterAdmin(admin.OSMGeoAdmin):
    list_display=('datavalue', 'measurement', 'parameter')

class ParameterAdmin(admin.OSMGeoAdmin):
    list_display=('name', 'standard_name', 'units')

class ActivityParameterAdmin(admin.OSMGeoAdmin):
    list_display=('activity', 'parameter', 'number')



admin.site.register(models.Campaign, CampaignAdmin)
admin.site.register(models.CampaignLog, CampaignLogAdmin)
admin.site.register(models.Activity, ActivityAdmin)
admin.site.register(models.ActivityType, ActivityTypeAdmin)
admin.site.register(models.Platform, PlatformAdmin)
admin.site.register(models.InstantPoint, InstantPointAdmin)
admin.site.register(models.PlatformType, PlatformTypeAdmin)
admin.site.register(models.Measurement, MeasurementAdmin)
admin.site.register(models.MeasuredParameter, MeasuredParameterAdmin)
admin.site.register(models.Parameter, ParameterAdmin)
admin.site.register(models.ActivityParameter, ActivityParameterAdmin)


