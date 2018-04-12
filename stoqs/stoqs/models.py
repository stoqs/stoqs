'''
This is the STOQS database model. The database schema derives from this module.
To evolve the schema you may make changes here then run syncdb and the unit tests.
To preserve data in existing databases you will need to make corresponding changes
in those databases, either by hand, or with a tool such as South.  Otherwise, you
may simply drop your databases and reload the data.

Mike McCann
MBARI 17 March 2012
'''


from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils.encoding import python_2_unicode_compatible

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
        if add:
            value=getattr(model_instance,self.attname)
            if not value:
                value = str(uuid.uuid4()).replace('-','')
            setattr(model_instance, self.attname, value)
            return value
        else:
            return super(UUIDField, self).pre_save(model_instance, add)


@python_2_unicode_compatible
class ResourceType(models.Model):
    '''
    Type of Resource. Example names: nc_global, quick-look-plot.
    '''
    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128, db_index=True, unique=True)
    description = models.CharField(max_length=256, blank=True, null=True)
    class Meta(object):
        app_label = 'stoqs'
    def __str__(self):
        return "%s" % (self.name,)


@python_2_unicode_compatible
class Resource(models.Model):
    '''
    A catchall class for saving any bit of information that may be associated with an Activity, or other STOQS model class.
    This is useful for collecting web resources that may be shown in a popup window for an activity.  Examples include: NC_GLOBAL data set
    attributes or quick-look plots.  The ResoureType class may be used to help categorize the display of resources.
    '''
    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128, null=True)
    value = models.TextField(null=True)
    uristring = models.CharField(max_length=256, null=True)
    resourcetype = models.ForeignKey(ResourceType, on_delete=models.CASCADE, blank=True, null=True)
    class Meta(object):
        verbose_name = 'Resource'
        verbose_name_plural = 'Resources'
        app_label = 'stoqs'
    def __str__(self):
        return "(%s=%s)" % (self.name, self.value,)


@python_2_unicode_compatible
class Campaign(models.Model):
    '''
    A Campaign holds a collection of Activities and can have a name, description and start and end time.  
    An example name is "CANON October 2010".
    '''
    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128, db_index=True, unique_for_date='startdate')
    startdate = models.DateTimeField(null=True)
    enddate = models.DateTimeField(null=True)
    description = models.CharField(max_length=4096, blank=True, null=True)
    class Meta(object):
        app_label = 'stoqs'
        verbose_name='Campaign'
        verbose_name_plural='Campaigns'
    def __str__(self):
        return "%s" % (self.name,)
        

@python_2_unicode_compatible
class CampaignLog(models.Model):
    '''
    Placeholder for potential integration of various logging systems into STOQS.  The
    idea is that salient messages would be mined from other sources and loaded into the
    stoqs database the same way measurements are loaded.
    '''
    uuid = UUIDField(editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    timevalue = models.DateTimeField(db_index=True)
    message = models.CharField(max_length=2048)
    geom = models.PointField(srid=4326, spatial_index=True, dim=2, blank=True, null=True)
    depth = models.FloatField(blank=True, null=True)
    username = models.CharField(max_length=128, blank=True, null=True)
    class Meta(object):
        app_label = 'stoqs'
        verbose_name='Campaign Log'
        verbose_name_plural='Campaign Logs'
    def __str__(self):
        return "%s at %s" % (self.message, self.timevalue)


@python_2_unicode_compatible
class ActivityType(models.Model):
    '''
    Type of Activity.  Example names: AUV Survey, Mooring Deployment, Ship Cruse, GLider Mission.
    '''
    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128, db_index=True, unique=True)
    class Meta(object):
        verbose_name='Activity Type'
        verbose_name_plural='Activity Types'
        app_label = 'stoqs'
    def __str__(self):
        return "%s" % (self.name,)


@python_2_unicode_compatible
class PlatformType(models.Model):
    '''
    Type of platform. Example names: auv, mooring, drifter, ship.  The color field is RGB(A) in hex.
    '''
    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128, db_index=True, unique=True)
    color = models.CharField(max_length=8, blank=True, null=True)
    class Meta(object):
        app_label = 'stoqs'
    def __str__(self):
        return "%s" % (self.name,)


@python_2_unicode_compatible
class Platform(models.Model):
    '''
    Platform.  Example names (use lower case): dorado, tethys, martin.  The color field is RGB(A) in hex.
    '''
    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128)
    platformtype = models.ForeignKey(PlatformType, on_delete=models.CASCADE) 
    color = models.CharField(max_length=8, blank=True, null=True)
    class Meta(object):
        verbose_name = 'Platform'
        verbose_name_plural = 'Platforms'
        app_label = 'stoqs'
    def __str__(self):
        return "%s" % (self.name,)


@python_2_unicode_compatible
class Activity(models.Model):
    '''
    An Activity is anything that may produce data.  Example Activity names include:  
    Dorado389_2011_117_01_117_01_decim.nc (stride=10), 
    20110415_20110418/20110418T192351/slate.nc (stride=10), 27710_jhmudas_v1.nc (stride=1).
    '''
    uuid = UUIDField(editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, blank=True, null=True) 
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE) 
    name = models.CharField(max_length=256)
    comment = models.TextField(max_length=2048)
    startdate = models.DateTimeField()
    plannedstartdate = models.DateTimeField(null=True)
    enddate = models.DateTimeField(null=True)
    plannedenddate = models.DateTimeField(null=True)
    num_measuredparameters = models.IntegerField(null=True)
    loaded_date = models.DateTimeField(null=True)
    maptrack = models.LineStringField(null=True)
    plannedtrack = models.LineStringField(null=True)
    mappoint = models.PointField(srid=4326, spatial_index=True, dim=2, blank=True, null=True)
    mindepth = models.FloatField(null=True)
    maxdepth = models.FloatField(null=True)
    activitytype = models.ForeignKey(ActivityType, on_delete=models.CASCADE, blank=True, null=True, default=None) 
    class Meta(object):
        verbose_name='Activity'
        verbose_name_plural='Activities'
        app_label = 'stoqs'
    def __str__(self):
        return "%s" % (self.name,)


@python_2_unicode_compatible
class InstantPoint(models.Model):
    '''
    An instance in time for an Activity.  This InstantPoint may have a measurement or sample associated with it.
    An InstantPoint may be used to record the start time for an integrative measurement or sample. An example
    is a plankton net tow which integrates over space and time. As implemented in the STOQS UI, NetTow data have
    exactly one InstantPoint per Activity, with the ActivityType name containing 'NetTow'. The start and end 
    times and depths can then be retrieved from fields of the Activity record. If the integrative measurement 
    or sample is from a non-linear longitude/latitude path then that can be stored in the maptrack field.
    '''
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE) 
    timevalue = models.DateTimeField(db_index=True)
    class Meta(object):
        app_label = 'stoqs'
        unique_together = ('activity', 'timevalue')
    def __str__(self):
        return "%s" % (self.timevalue,)


@python_2_unicode_compatible
class NominalLocation(models.Model):
    '''
    A NominalLocation has depth and geom fields for storing a Nominal horizontal position and depth of a
    measurement.  This is useful for representing CF discrete geometry data of featureType timeSeriesProfile;
    for example, a mooring time series with nominal latitude, longitude and nominal depths of subsurface
    instruments.  It has a many to one relationship with Activity.
    '''
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE) 
    depth= models.FloatField(db_index=True)
    geom = models.PointField(srid=4326, spatial_index=True, dim=2)
    class Meta(object):
        verbose_name = 'NominalLocation'
        verbose_name_plural = 'NominalLocations'
        app_label = 'stoqs'
    def __str__(self):
        return "Nominal Location at %s %s %s" % (self.geom.x, self.geom.y, self.depth)


class SimpleDepthTime(models.Model):
    '''
    A simplified time series of depth values for an Activity useful for plotting in the UI
    '''
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE) 
    nominallocation = models.ForeignKey(NominalLocation, on_delete=models.CASCADE, null=True) 
    instantpoint = models.ForeignKey(InstantPoint, on_delete=models.CASCADE)
    epochmilliseconds = models.FloatField()
    depth= models.FloatField()
    class Meta(object):
        verbose_name='Simple depth time series'
        verbose_name_plural='Simple depth time series'
        app_label = 'stoqs'


class SimpleBottomDepthTime(models.Model):
    '''
    A simplified time series of bottom depth values for an Activity useful for plotting in the UI
    '''
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE) 
    nominallocation = models.ForeignKey(NominalLocation, on_delete=models.CASCADE, null=True) 
    instantpoint = models.ForeignKey(InstantPoint, on_delete=models.CASCADE)
    epochmilliseconds = models.FloatField()
    bottomdepth= models.FloatField()
    class Meta(object):
        verbose_name='Simple bottom depth time series'
        verbose_name_plural='Simple bottom depth time series'
        app_label = 'stoqs'


class PlannedDepthTime(models.Model):
    '''
    A simplified time series of depth values for an Activity useful for plotting in the UI
    '''
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE) 
    epochmilliseconds = models.FloatField()
    depth= models.FloatField()
    class Meta(object):
        verbose_name='Planned depth time series'
        verbose_name_plural='Planned depth time series'
        app_label = 'stoqs'


@python_2_unicode_compatible
class Parameter(models.Model):
    '''
    A Parameter is something that can be measured producing a numeric value or
    a array of numeric values. If a parameter is related to an array of values
    then the domain field contains the domain values corresponding to the 
    dataarray values in MeasuredParameter.  Example names include temperature, 
    salinity, fluoresence, plankton counts by size class.
    '''
    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128, unique=True)
    type = models.CharField(max_length=128, blank=True, null=True)
    description= models.CharField(max_length=512, blank=True, null=True)
    standard_name = models.CharField(max_length=128, null=True)
    long_name = models.CharField(max_length=128, blank=True, null=True)
    units = models.CharField(max_length=128, blank=True, null=True)
    origin = models.CharField(max_length=256, blank=True, null=True)
    domain = ArrayField(models.FloatField(), null=True)
    class Meta(object):
        verbose_name = 'Parameter'
        verbose_name_plural = 'Parameters'
        app_label = 'stoqs'
    def __str__(self):
        return "%s" % (self.name,)


@python_2_unicode_compatible
class ParameterGroup(models.Model):
    '''
    A grouping of parameters with a many-to-many relationship to the Paramter table.  Useful for showing checkboxes
    in the User Interface for which kinds of Parameters to show, e.g.: Electronic measured, bottle samples, bio-optical,
    physical.  Mapping to other ontologies to a ParamterGroup (e.g. GCMD) is also possible.
    '''
    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128, unique=True)
    description= models.CharField(max_length=128, blank=True, null=True)
    class Meta(object):
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
    parametergroup = models.ForeignKey(ParameterGroup, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    class Meta(object):
        verbose_name = 'ParameterGroup Parameter'
        verbose_name_plural = 'ParameterGroup Parameter'
        app_label = 'stoqs'
        unique_together = ['parametergroup', 'parameter']


class CampaignResource(models.Model):
    '''
    Association class pairing Campaigns and Resources.  Must use explicit many-to-many.
    '''
    uuid = UUIDField(editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    class Meta(object):
        verbose_name = 'Campaign Resource'
        verbose_name_plural = 'Campaign Resource'
        app_label = 'stoqs'
        unique_together = ['campaign', 'resource']
    def __repr__(self):
        return "CampaignResource(%s=%s)" % (self.resource.name, self.resource.value)


class ActivityResource(models.Model):
    '''
    Association class pairing Activities and Resources.  Must use explicit many-to-many.
    '''
    uuid = UUIDField(editable=False)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    class Meta(object):
        verbose_name = 'Activity Resource'
        verbose_name_plural = 'Activity Resource'
        app_label = 'stoqs'
        unique_together = ['activity', 'resource']


class ParameterResource(models.Model):
    '''
    Association class pairing Parameters and Resources.  Must use explicit many-to-many.
    '''
    uuid = UUIDField(editable=False)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    class Meta(object):
        verbose_name = 'Parameter Resource'
        verbose_name_plural = 'Parameter Resource'
        app_label = 'stoqs'
        unique_together = ['parameter', 'resource']


@python_2_unicode_compatible
class Measurement(models.Model):
    '''
    A Measurement may have a @depth value (this is an Oceanographic Query System) and a horizontal location 
    (represented by the @geom field), it may also have a nominal location with is represented in a related table.
    It is  associated with an InstantPoint and and a MeasuredParameter (where the measured datavalue is stored).
    '''
    instantpoint = models.ForeignKey(InstantPoint, on_delete=models.CASCADE)
    nominallocation = models.ForeignKey(NominalLocation, on_delete=models.CASCADE, null=True)
    depth= models.FloatField(db_index=True)
    bottomdepth= models.FloatField(db_index=True, null=True)
    geom = models.PointField(srid=4326, spatial_index=True, dim=2)
    class Meta(object):
        verbose_name = 'Measurement'
        verbose_name_plural = 'Measurements'
        unique_together = ('instantpoint', 'depth', 'geom')
        app_label = 'stoqs'
    def __str__(self):
        return "Measurement at %s, %s" % (self.geom, self.depth)


@python_2_unicode_compatible
class SampleType(models.Model):
    '''
    Type of Sample.  Example names: Gulper, Niskin, Bucket
    '''
    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128, db_index=True, unique=True)
    class Meta(object):
        verbose_name='Sample Type'
        verbose_name_plural='Sample Types'
        app_label = 'stoqs'
    def __str__(self):
        return "%s" % (self.name,)


@python_2_unicode_compatible
class SamplePurpose(models.Model):
    '''
    Purpose of Sample.  Example names: random, control, peak
    '''
    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=128, unique=True)
    description = models.CharField(max_length=1024)
    class Meta(object):
        verbose_name='Sample Purpose'
        verbose_name_plural='Sample Purposes'
        app_label = 'stoqs'
    def __str__(self):
        return "%s" % (self.name,)


@python_2_unicode_compatible
class AnalysisMethod(models.Model):
    '''
    The method used for producing a ParamaterSample.datavlue from a Sample
    '''
    uuid = UUIDField(editable=False)
    name = models.CharField(max_length=256, db_index=True, unique=True)
    uristring = models.CharField(max_length=256, null=True)
    class Meta(object):
        verbose_name='Analysis Method'
        verbose_name_plural='Analysis Methods'
        app_label = 'stoqs'
    def __str__(self):
        return "%s" % (self.name,)


@python_2_unicode_compatible
class Sample(models.Model):
    '''
    A Sample may have a depth value (this is an Oceanographic Query System) and a location (represented by the geom field), 
    be associated with an InstantPoint and and a SampledParameter (where the measured datavalue is stored).  A Sample
    differs from a Measurement in that it represents an actual physical sample from which analyses may be made producing
    digital values which may be stored in the SampleParameter table.  Some of the fields have units.  The canonical unit
    values are:
        volume: ml
        filterdiameter: mm
        filterporesize: microns
    '''
    uuid = UUIDField(editable=False)
    instantpoint = models.ForeignKey(InstantPoint, on_delete=models.CASCADE)
    depth= models.DecimalField(max_digits=100, db_index=True, decimal_places=30)
    geom = models.PointField(srid=4326, spatial_index=True, dim=2)
    name = models.CharField(max_length=128, db_index=True)
    sampletype = models.ForeignKey(SampleType, on_delete=models.CASCADE, blank=True, null=True, default=None) 
    samplepurpose = models.ForeignKey(SamplePurpose, on_delete=models.CASCADE, blank=True, null=True, default=None) 
    volume = models.FloatField(blank=True, null=True)
    filterdiameter = models.FloatField(blank=True, null=True)
    filterporesize = models.FloatField(blank=True, null=True)
    laboratory = models.CharField(max_length=128, blank=True, null=True)
    researcher = models.CharField(max_length=128, blank=True, null=True)
    class Meta(object):
        verbose_name = 'Sample'
        verbose_name_plural = 'Samples'
        app_label = 'stoqs'
    def __str__(self):
        return "%s" % (self.name,)


class SampleRelationship(models.Model):
    '''
    Association class pairing Samples and Samples for many-to-many parent/child relationships.
    '''
    uuid = UUIDField(editable=False)
    parent = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name='child')
    child = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name='parent')
    class Meta(object):
        verbose_name = 'Sample Relationship'
        verbose_name_plural = 'Sample Relationships'
        app_label = 'stoqs'
        unique_together = ['parent', 'child']


class SampleResource(models.Model):
    '''
    Association class pairing Samples and Resources.  Must use explicit many-to-many.
    '''
    uuid = UUIDField(editable=False)
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    class Meta(object):
        verbose_name = 'Sample Resource'
        verbose_name_plural = 'Sample Resource'
        app_label = 'stoqs'
        unique_together = ['sample', 'resource']


class PlatformResource(models.Model):
    '''
    Association class pairing Platforms and Resources.  Must use explicit many-to-many.
    '''
    uuid = UUIDField(editable=False)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    class Meta(object):
        verbose_name = 'Platform Resource'
        verbose_name_plural = 'Platform Resource'
        app_label = 'stoqs'
        unique_together = ['platform', 'resource']


class ResourceResource(models.Model):
    '''
    Association class pairing Resources and Resources for many-to-many from/to relationships.
    '''
    uuid = UUIDField(editable=False)
    fromresource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='toresource')
    toresource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='fromresource')
    class Meta(object):
        verbose_name = 'Resource Resource'
        verbose_name_plural = 'Resource Resource'
        app_label = 'stoqs'
        unique_together = ['fromresource', 'toresource']


class ActivityParameter(models.Model):
    '''
    Association class pairing Parameters that have been loaded for an Activity
    '''
    uuid = UUIDField(editable=False)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    # Parameter statistics for the Activity
    number = models.IntegerField(null=True)
    min = models.FloatField(null=True)
    max = models.FloatField(null=True)
    mean = models.FloatField(null=True)
    median = models.FloatField(null=True)
    mode = models.FloatField(null=True)
    # Useful for visualiztion, ignoring min & max outliers - 2.5% & 97.5% percentiles of the parameter
    p025 = models.FloatField(null=True)
    p975 = models.FloatField(null=True)
    # Useful for visualiztion, ignoring fewer min & max outliers - 1% & 99% percentiles of the parameter
    p010 = models.FloatField(null=True)
    p990 = models.FloatField(null=True)
    class Meta(object):
        verbose_name = 'Activity Parameter'
        verbose_name_plural = 'Activity Parameter'
        app_label = 'stoqs'
        unique_together = ['activity', 'parameter']
        

class ActivityParameterHistogram(models.Model):
    '''
    Association class pairing Parameters that have been loaded for an Activity
    '''
    uuid = UUIDField(editable=False)
    activityparameter =  models.ForeignKey(ActivityParameter, on_delete=models.CASCADE)
    binlo = models.FloatField()
    binhi = models.FloatField()
    bincount = models.IntegerField()


class MeasuredParameter(models.Model):
    '''
    Association class pairing Measurements with Parameters.  This is where the measured values are stored -- in the datavalue field.
    '''
    measurement = models.ForeignKey(Measurement, on_delete=models.CASCADE) 
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE) 
    datavalue = models.FloatField(db_index=True, null=True)
    dataarray = ArrayField(models.FloatField(), null=True)
    class Meta(object):
        verbose_name = 'Measured Parameter'
        verbose_name_plural = 'Measured Parameter'
        app_label = 'stoqs'
        unique_together = ['measurement','parameter']


class SampledParameter(models.Model):
    '''
    Association class pairing Samples with Parameters.  This is where any digital sampled data values are stored -- in the datavalue field.
    '''
    uuid = UUIDField(editable=False)
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE) 
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE) 
    datavalue = models.DecimalField(max_digits=100, db_index=True, decimal_places=30)
    analysismethod = models.ForeignKey(AnalysisMethod, on_delete=models.CASCADE, null=True)
    class Meta(object):
        verbose_name = 'Sampled Parameter'
        verbose_name_plural = 'Sampled Parameter'
        app_label = 'stoqs'
        unique_together = ['sample','parameter']


class MeasuredParameterResource(models.Model):
    '''
    Association class pairing MeasuredParameters and Resources.  Must use explicit many-to-many.
    Class contains activity field for ease of association in the filter set of the UI.
    '''
    uuid = UUIDField(editable=False)
    measuredparameter = models.ForeignKey(MeasuredParameter, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    class Meta(object):
        verbose_name = 'MeasuredParameter Resource'
        verbose_name_plural = 'MeasuredParameter Resource'
        app_label = 'stoqs'
        unique_together = ['measuredparameter', 'resource']


class SampledParameterResource(models.Model):
    '''
    Association class pairing SampledParameters and Resources.  Must use explicit many-to-many.
    Class contains activity field for ease of association in the filter set of the UI.
    '''
    uuid = UUIDField(editable=False)
    sampledparameter = models.ForeignKey(SampledParameter, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    class Meta(object):
        verbose_name = 'SampledParameter Resource'
        verbose_name_plural = 'SampledParameter Resource'
        app_label = 'stoqs'
        unique_together = ['sampledparameter', 'resource']


class PermaLink(models.Model):
    '''
    A simple model for storing permalinks created by users.
    '''
    uuid=UUIDField(editable=False, primary_key=True)
    parameters=models.TextField(null=False, blank=False)
    create_date=models.DateTimeField(auto_now_add=True)
    usage_count=models.IntegerField(default=0)
    last_usage=models.DateTimeField(auto_now=True)
