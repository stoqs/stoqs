#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__credits__ = ["Chander Ganesan, Open Technology Group"]
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

This is the STOQS database model. The database schema derives from this module.
To evolve the schema you may make changes here then run syncdb and the unit tests.
To preserve data in existing databases you will need to make corresponding changes
in those databases, either by hand, or with a tool such as South.  Otherwise, you
may simply drop your databases and reload the data.

Mike McCann
MBARI 17 March 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

from django.contrib.gis.db import models

try:
    import uuid
except ImportError:
    from django.utils import uuid


class UUIDField(models.CharField) :
    '''
    Major classes in the model have been given a uuid field, which may prove helpful as web accessible resource identifiers.
    '''
    
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 32 )
        models.CharField.__init__(self, *args, **kwargs)
    
    def pre_save(self, model_instance, add):
        if add :
            value=getattr(model_instance,self.attname)
            if not value:
                value = unicode(uuid.uuid4()).replace('-','')
            setattr(model_instance, self.attname, value)
            return value
        else:
            return super(models.CharField, self).pre_save(model_instance, add)


class Campaign(models.Model):
    '''
    A Campaign holds a collection of Activities and can have a name, description and start and end time.  
    An example name is "CANON October 2010".
    '''

    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128, db_index=True, unique_for_date='startdate')
    description = models.CharField(max_length=4096, blank=True, null=True)
    startdate = models.DateTimeField(null=True)
    enddate = models.DateTimeField(null=True)
    objects = models.GeoManager()
    class Meta:
        app_label = 'stoqs'
        verbose_name='Campaign'
        verbose_name_plural='Campaigns'
        def __str__(self):
                return "%s" % (self.name,)
        
class CampaignLog(models.Model):
    '''
    Placeholder for potential integration of various logging systems into STOQS.  The
    idea is that salient messages would be mined from other sources and loaded into the
    stoqs database the same way measurements are loaded.
    '''
    uuid = UUIDField(editable=False)
    campaign = models.ForeignKey(Campaign)
    timevalue = models.DateTimeField(db_index=True)
    message = models.CharField(max_length=2048)
    objects = models.GeoManager()
    class Meta:
        app_label = 'stoqs'
        verbose_name='Campaign Log'
        verbose_name_plural='Campaign Logs'

class ActivityType(models.Model):
    '''
    Type of Activity.  Example names: AUV Survey, Mooring Deployment, Ship Cruse, GLider Mission.
    '''

    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128, db_index=True, unique=True)
    objects = models.GeoManager()
    class Meta:
        verbose_name='Activity Type'
        verbose_name_plural='Activity Types'
        app_label = 'stoqs'
        def __str__(self):
                return "%s" % (self.name,)

class PlatformType(models.Model):
    '''
    Type of platform. Example names: auv, mooring, drifter, ship.
    '''

    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128, db_index=True, unique=True)
    objects = models.GeoManager()
    class Meta:
        app_label = 'stoqs'
        def __str__(self):
                return "%s" % (self.name,)

class Platform(models.Model):
    '''
    Platform.  Example names (use lower case): dorado, tethys, martin.
    '''

    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128)
    platformtype = models.ForeignKey(PlatformType) 
    objects = models.GeoManager()
    class Meta:
        verbose_name = 'Platform'
        verbose_name_plural = 'Platforms'
        app_label = 'stoqs'
        def __str__(self):
                return "%s" % (self.name,)

class Activity(models.Model):
    '''
    An Activity is anything that may produce data.  Example Activity names include:  
    Dorado389_2011_117_01_117_01_decim.nc (stride=10), 
    20110415_20110418/20110418T192351/slate.nc (stride=10), 27710_jhmudas_v1.nc (stride=1).
    '''

    uuid = UUIDField(editable=False)
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
    mindepth = models.FloatField(null=True)
    maxdepth = models.FloatField(null=True)
    objects = models.GeoManager()
    class Meta:
        verbose_name='Activity'
        verbose_name_plural='Activities'
        app_label = 'stoqs'
    def __str__(self):
        return "%s" % (self.name,)

class SimpleDepthTime(models.Model):
    '''
    A simplified time series of depth values for an Activity
    '''
    activity = models.ForeignKey(Activity) 
    timevalue = models.DateTimeField(db_index=True)
    depth= models.FloatField()
    objects = models.GeoManager()
    class Meta:
        verbose_name='Simple depth time series'
        verbose_name_plural='Simple depth time series'
        app_label = 'stoqs'

class InstantPoint(models.Model):
    '''
    An instance in time for an Activity.  This InstantPoint may have a measurement or sample associated with it.
    '''
    activity = models.ForeignKey(Activity) 
    timevalue = models.DateTimeField(db_index=True)
    objects = models.GeoManager()
    class Meta:
        app_label = 'stoqs'

class Parameter(models.Model):
    '''
    A Parameter is something that can be measured producing a numeric value.  Example names include: 
    temperature, salinity, fluoresence.
    '''

    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128, unique=True)
    type = models.CharField(max_length=128, blank=True, null=True)
    description= models.CharField(max_length=128, blank=True, null=True)
    standard_name = models.CharField(max_length=128, null=True)
    long_name = models.CharField(max_length=128, blank=True, null=True)
    units = models.CharField(max_length=128, blank=True, null=True)
    origin = models.CharField(max_length=128, blank=True, null=True)
    objects = models.GeoManager()
    class Meta:
        verbose_name = 'Parameter'
        verbose_name_plural = 'Parameters'
        app_label = 'stoqs'
        def __str__(self):
                return "%s" % (self.name,)

class ParameterGroup(models.Model):
    '''
    A grouping of parameters with a many-to-many relationship to the Paramter table.  Useful for showing checkboxes
    in the User Interface for which kinds of Parameters to show, e.g.: Electronic measured, bottle samples, bio-optical,
    physical.  Mapping to other ontologies to a ParamterGroup (e.g. GCMD) is also possible.
    '''
    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128, unique=True)
    objects = models.GeoManager()
    class Meta:
        verbose_name = 'ParameterGroup'
        verbose_name_plural = 'ParameterGroups'
        app_label = 'stoqs'
        def __str__(self):
                return "%s" % (self.name,)

class ParameterGroupParameter(models.Model):
    '''
    Association table pairing ParamterGroup and Parameter
    '''
    uuid = UUIDField(editable=False)
    parametergroup = models.ForeignKey(ParameterGroup)
    parameter = models.ForeignKey(Parameter)
    class Meta:
        verbose_name = 'ParameterGroup Parameter'
        verbose_name_plural = 'ParameterGroup Parameter'
        app_label = 'stoqs'
        unique_together = ['parametergroup', 'parameter']

class ResourceType(models.Model):
    '''
    Type of Resource. Example names: nc_global, quick-look-plot.
    '''

    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128, db_index=True, unique=True)
    description = models.CharField(max_length=256, blank=True, null=True)
    objects = models.GeoManager()
    class Meta:
        app_label = 'stoqs'
        def __str__(self):
                return "%s" % (self.name,)

class Resource(models.Model):
    '''
    A catchall class for saving any bit of information that may be associated with an Activity, or other STOQS model class.
    This is useful for collecting web resources that may be shown in a popup window for an activity.  Examples include: NC_GLOBAL data set
    attributes or quick-look plots.  The ResoureType class may be used to help categorize the display of resources.
    '''
    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128, null=True)
    value = models.TextField(null=True)
    resourcetype = models.ForeignKey(ResourceType, blank=True, null=True, default=None)
    uristring = models.CharField(max_length=256, null=True)
    objects = models.GeoManager()
    class Meta:
        verbose_name = 'Resource'
        verbose_name_plural = 'Resources'
        app_label = 'stoqs'
        def __str__(self):
                return "%s" % (self.name,)

class ActivityResource(models.Model):
    '''
    Association class pairing Activities and Resources.
    '''
    uuid = UUIDField(editable=False)
    activity = models.ForeignKey(Activity)
    resource = models.ForeignKey(Resource)
    class Meta:
        verbose_name = 'Activity Resource'
        verbose_name_plural = 'Activity Resource'
        app_label = 'stoqs'
        unique_together = ['activity', 'resource']

class Measurement(models.Model):
    '''
    A Measurement may have a depth value (this is an Oceanographic Query System) and a location (represented by the geom field), 
    be associated with an InstantPoint and and a MeasuredParameter (where the measured datavalue is stored).
    '''

    instantpoint = models.ForeignKey(InstantPoint)
    depth= models.DecimalField(max_digits=100, db_index=True, decimal_places=30)
    geom = models.PointField(srid=4326, spatial_index=True, dim=2)
    objects = models.GeoManager()
    class Meta:
        verbose_name = 'Measurement'
        verbose_name_plural = 'Measurements'
        app_label = 'stoqs'
        def __str__(self):
                return "Measurement at %s" % (self.geom,)

class Sample(models.Model):
    '''
    A Sample may have a depth value (this is an Oceanographic Query System) and a location (represented by the geom field), 
    be associated with an InstantPoint and and a SampledParameter (where the measured datavalue is stored).  A Sample
    differs from a Measurement in that it represents an actual physical sample from which analyses may be made producing
    digital values which may be stored in the SampleParameter table.
    '''

    instantpoint = models.ForeignKey(InstantPoint)
    depth= models.DecimalField(max_digits=100, db_index=True, decimal_places=30)
    geom = models.PointField(srid=4326, spatial_index=True, dim=2)
    name = models.CharField(max_length=128, db_index=True)
    objects = models.GeoManager()
    class Meta:
        verbose_name = 'Sample'
        verbose_name_plural = 'Samples'
        app_label = 'stoqs'
        def __str__(self):
                return "Sample at %s" % (self.geom,)

class ActivityParameter(models.Model):
    '''
    Association class pairing Parameters that have been loaded for an Activity
    '''
    uuid = UUIDField(editable=False)
    activity = models.ForeignKey(Activity)
    parameter = models.ForeignKey(Parameter)
    # Parameter statistics for the Activity
    number = models.IntegerField(null=True)
    min = models.FloatField(null=True)
    max = models.FloatField(null=True)
    mean = models.FloatField(null=True)
    median = models.FloatField(null=True)
    mode = models.FloatField(null=True)
    # Useful for ignoring min & max outliers - 2.5% & 97.5% qualtiles of the parameter
    p025 = models.FloatField(null=True)
    p975 = models.FloatField(null=True)
    class Meta:
        verbose_name = 'Activity Parameter'
        verbose_name_plural = 'Activity Parameter'
        app_label = 'stoqs'
        unique_together = ['activity', 'parameter']
        
class MeasuredParameter(models.Model):
    '''
    Association class pairing Measurements with Parameters.  This is where the measured values are stored -- in the datavalue field.
    '''
    measurement = models.ForeignKey(Measurement) 
    parameter = models.ForeignKey(Parameter) 
    datavalue = models.DecimalField(max_digits=100, db_index=True, decimal_places=30)
    objects = models.GeoManager()
    class Meta:
        verbose_name = 'Measured Parameter'
        verbose_name_plural = 'Measured Parameter'
        app_label = 'stoqs'
        unique_together = ['measurement','parameter']

class SampledParameter(models.Model):
    '''
    Association class pairing Samples with Parameters.  This is where any digital sampled data values are stored -- in the datavalue field.
    '''
    sample = models.ForeignKey(Sample) 
    parameter = models.ForeignKey(Parameter) 
    datavalue = models.DecimalField(max_digits=100, db_index=True, decimal_places=30)
    objects = models.GeoManager()
    class Meta:
        verbose_name = 'Sampled Parameter'
        verbose_name_plural = 'Sampled Parameter'
        app_label = 'stoqs'
        unique_together = ['sample','parameter']

