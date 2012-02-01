#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__credits__ = ["Chander Ganesan, Open Technology Group"]
__license__ = "GPL"
__version__ = "$Revision: 1234$".split()[1]
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

STOQS database model.  The STOQS database schema derives from this module.
To evolve the schema make changes here then syncdb and run unit tests.
Note that data in existing databases will be lost following this methodology.
You will need to reload data if following this brute force approach.


Mike McCann
MBARI Jan 10, 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

from django.contrib.gis.db import models

class Campaign(models.Model):
	name = models.CharField(max_length=30, db_index=True, unique_for_date='startdate')
	description = models.CharField(max_length=4096, blank=True, null=True)
	startdate = models.DateTimeField(null=True)
	enddate = models.DateTimeField(null=True)
	objects = models.GeoManager()
	class Meta:
		app_label = 'stoqs'
		verbose_name='Campaign'
		verbose_name_plural='Campaigns'
		
class CampaignLog(models.Model):
	'''Placeholder for potential integration of various logging systems into STOQS.  The
	idea is that salient messages would be mined from other sources and loaded into the
	stoqs database the same way measurements are loaded.
	'''
	campaign = models.ForeignKey(Campaign)
	timevalue = models.DateTimeField(db_index=True)
	message = models.CharField(max_length=2048)
	objects = models.GeoManager()
	class Meta:
		app_label = 'stoqs'
		verbose_name='Campaign Log'
		verbose_name_plural='Campaign Logs'

class ActivityType(models.Model):
	name = models.CharField(max_length=128, db_index=True, unique=True)
	objects = models.GeoManager()
	class Meta:
		verbose_name='Activity Type'
		verbose_name_plural='Activity Types'
		app_label = 'stoqs'

class PlatformType(models.Model):
	name = models.CharField(max_length=128, db_index=True, unique=True)
	objects = models.GeoManager()
	class Meta:
		app_label = 'stoqs'

#   Does not work with db_routing
#	def save(self, **kwds):
#		'''
#		Force the name to be lower case when creating a new platform type.
#		'''
#		self.name=self.name.lower()
#		super(PlatformType, self).save(kwds) # Call the "real" save() method.

class Platform(models.Model):
	name = models.CharField(max_length=30)
	platformtype = models.ForeignKey(PlatformType) 
	objects = models.GeoManager()
	class Meta:
		app_label = 'stoqs'

class Activity(models.Model):
	campaign = models.ForeignKey(Campaign, blank=True, null=True, default=None) 
	platform = models.ForeignKey(Platform) 
	activitytype = models.ForeignKey(ActivityType, blank=True, null=True, default=None) 
	name = models.CharField(max_length=128)
	comment = models.TextField(max_length=2048)
	startdate = models.DateTimeField()
	enddate = models.DateTimeField(null=True)
	num_measuredparameters = models.IntegerField(null=True)
	loaded_date = models.DateTimeField(null=True)
	maptrack = models.LineStringField(null=True)
	objects = models.GeoManager()
	class Meta:
		verbose_name='Activity'
		verbose_name_plural='Activities'
		app_label = 'stoqs'
	def __str__(self):
		return "Experiment of %s" % (self.platform.name,)

class InstantPoint(models.Model):
	activity = models.ForeignKey(Activity) 
	timevalue = models.DateTimeField(db_index=True)
	objects = models.GeoManager()
	class Meta:
		app_label = 'stoqs'

class Parameter(models.Model):
	name = models.CharField(max_length=128, unique=True)
	type = models.CharField(max_length=128, blank=True, null=True)
	description= models.CharField(max_length=128, blank=True, null=True)
	standard_name = models.CharField(max_length=128, null=True)
	long_name = models.CharField(max_length=128, blank=True, null=True)
	units = models.CharField(max_length=128, blank=True, null=True)
	origin = models.CharField(max_length=128, blank=True, null=True)
 
	objects = models.GeoManager()
	class Meta:
		app_label = 'stoqs'

class Measurement(models.Model):
	instantpoint = models.ForeignKey(InstantPoint)
	depth= models.DecimalField(max_digits=100, db_index=True, decimal_places=30)
	geom = models.PointField(srid=4326, spatial_index=True, dim=2)
	objects = models.GeoManager()
	class Meta:
		app_label = 'stoqs'

#class ActivityParameter(models.Model):
#	'''Association class pairing Parameters that have been loaded for an Activity'''
#	activity = models.ForeignKey(Activity)
#	parameter = models.ForeignKey(Parameter)
#	number = models.IntegerField(null=True)
#	class Meta:
#			app_label = 'stoqs'
#			unique_together = ['activity', 'parameter']
			
class MeasuredParameter(models.Model):
	measurement = models.ForeignKey(Measurement) 
	parameter = models.ForeignKey(Parameter) 
	datavalue = models.DecimalField(max_digits=100, db_index=True, decimal_places=30)
	objects = models.GeoManager()
	class Meta:
		app_label = 'stoqs'
		unique_together = ['measurement','parameter']

