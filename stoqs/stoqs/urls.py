# -*- coding: utf-8 -*-


from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from stoqs.views.wms import showActivityWMS, showActivitiesWMS, showParametersWMS, showPlatformsWMS
from stoqs.views import (showActivityResource, showActivityParameter, showActivityType,
                         showActivity, showAnalysisMethod, showCampaignResource, 
                         showCampaign, showInstantPoint, showMeasuredParameterResource,
                         showMeasurement, showParameterGroupParameter, showParameterGroup,
                         showParameterResource, showParameter, showPlatformResource,
                         showPlatformType, showPlatform, showResourceResource,
                         showResourceType, showResource, showSampleType, showSamplePurpose,
                         showSample, showSimpleDepthTime)
from stoqs.views.app import (showMeasuredParameter, showSampledParameter, 
                             showActivityParameterHistogram, showResourceActivity,
                             showSampleDT, showQuickLookPlots)
from stoqs.views.query import queryData, queryMap, queryUI
from stoqs.views.management import showCampaigns, showDatabase, deleteActivity, showActivitiesMBARICustom
from stoqs.views.permalinks import generate_permalink, load_permalink
from stoqs.views.parameterinfo import parameterinfo

app_name = 'stoqs'                         

# The database alias (the key of the DATABASES dictionary) will prefix all of our requests
pre = r'^(?P<dbAlias>[^/]+)/'  

# format is one of: 'html', 'csv', 'kml', 'json'
formatPat = r'(?P<fmt>[^/]{0,5})'

urlpatterns = [
    # New Map interfaces with inheritence of bootstrap template
    url(pre + r'activityWMS$', showActivityWMS, {}, name='show-activity-wms'),

    # Map interfaces
    url(pre + r'activitiesWMS$', showActivitiesWMS, {}, name='show-activities-wms'),
    url(pre + r'parametersWMS$', showParametersWMS, {}, name='show-parameters-wms'),
    url(pre + r'platformsWMS$', showPlatformsWMS, {}, name='show-platforms-wms'),

    # All STOQS objects - full object queries with .json, .xml, .html, and .csv responses
    # Could be replaced with a REST API app, 
    url(pre + r'api/activityresource.?'  + formatPat, showActivityResource,  {}, name='show-activityresource'),
    url(pre + r'api/activityparameter.?' + formatPat, showActivityParameter, {}, name='show-activityparameter'),
    url(pre + r'api/activitytype.?'      + formatPat, showActivityType,      {}, name='show-activitytype'),
    url(pre + r'api/activity.?'          + formatPat, showActivity,          {}, name='show-activity'),
    url(pre + r'api/analysismethod.?'    + formatPat, showAnalysisMethod,    {}, name='show-analysismethod'),
    url(pre + r'api/campaignresource.?'          + formatPat, showCampaignResource,          {}, name='show-campaignresource'),
    url(pre + r'api/campaign.?'          + formatPat, showCampaign,          {}, name='show-campaign'),
    url(pre + r'api/instantpoint.?'      + formatPat, showInstantPoint,      {}, name='show-instantpoint'),
    url(pre + r'api/measuredparameterresource.?'  + formatPat, showMeasuredParameterResource,  {}, name='show-measuredparameterresource'),
    url(pre + r'api/measurement.?'       + formatPat, showMeasurement,       {}, name='show-measurement'),
    url(pre + r'api/parametergroupparameter.?'    + formatPat, showParameterGroupParameter,    {}, name='show-parametergroupparameter'),
    url(pre + r'api/parametergroup.?'    + formatPat, showParameterGroup,    {}, name='show-parametergroup'),
    url(pre + r'api/parameterresource.?' + formatPat, showParameterResource, {}, name='show-parameterresource'),
    url(pre + r'api/parameter.?'         + formatPat, showParameter,         {}, name='show-parameter'),
    url(pre + r'api/platformresource.?'  + formatPat, showPlatformResource,  {}, name='show-platformresource'),
    url(pre + r'api/platformtype.?'      + formatPat, showPlatformType,      {}, name='show-platformtype'),
    url(pre + r'api/platform.?'          + formatPat, showPlatform,          {}, name='show-platform'),
    url(pre + r'api/resourceresource.?'  + formatPat, showResourceResource,  {}, name='show-resourceresource'),
    url(pre + r'api/resourcetype.?'      + formatPat, showResourceType,      {}, name='show-resourcetype'),
    url(pre + r'api/resource.?'          + formatPat, showResource,          {}, name='show-resource'),
    url(pre + r'api/sampletype.?'        + formatPat, showSampleType,        {}, name='show-sampletype'),
    url(pre + r'api/samplepurpose.?'     + formatPat, showSamplePurpose,     {}, name='show-samplepuspose'),
    url(pre + r'api/sample.?'            + formatPat, showSample,            {}, name='show-sample'),
    url(pre + r'api/simpledepthtime.?'   + formatPat, showSimpleDepthTime,   {}, name='show-simpledepthtime'),

    # Requests that override BaseOutputer
    url(pre + r'api/measuredparameter.?' + formatPat, showMeasuredParameter,  {}, name='show-measuredparmeter'),
    url(pre + r'api/sampledparameter.?' + formatPat, showSampledParameter,  {}, name='show-sampledparmeter'),
    url(pre + r'api/activityparameterhistogram.?' + formatPat, 
                                                        showActivityParameterHistogram,  {}, name='show-aph'),
    url(pre + r'api/resourceactivity.?' + formatPat, showResourceActivity,  {}, name='show-resourceactivity'),

    url(pre + r'sampledatatable.?'   + formatPat, showSampleDT,      {}, name='show-sample-datatable'),
    url(pre + r'quicklookplots', showQuickLookPlots,  {}, name='show-quicklookplots'),

    # URL For Chander's STOQSQManager related views
    url(pre + r'query/summary/$', queryData, {}, name='stoqs-query-summary'),
    url(pre + r'query/map/$', queryMap, {}, name='stoqs-query-map'),
    url(pre + r'query/', queryUI, {}, name='stoqs-query-ui'),

    # Management, base of campaign, etc.
    url(r'campaigns.(?P<fmt>[^/]{3,5})$', showCampaigns, {}, name='show-campaigns'),
    url(pre + r'mgmt$', showDatabase, {}, name='show-database'),
    url(pre + r'deleteActivity/(?P<activityId>[0-9]+)$', deleteActivity, {}, name='delete-activity'),
    url(pre + r'activitiesMBARICustom$', showActivitiesMBARICustom, {}, name='show-activities'),

    # WFS - Tesing for exposing Sample data to the OpenLayers map
    # Prerequisites:
    #   su -y 'yum install libxml2-devel libxml2 libxslt-devel libxslt'
    #   pip install lxml
    #   pip install -e git+https://github.com/JeffHeard/ga_ows.git#egg=ga_ows
    #   export LD_LIBRARY_PATH='/usr/local/lib:$LD_LIBRARY_PATH' && python manage.py runserver 0.0.0.0:8000
    ##url(pre + r'wfs/?', WFS.as_view(
    ##    models=[m.Sample],          # everything but this is optional.
    ##    title='STOQS Sample WFS',
    ##    provider_name='MBARI',
    ##)),

    # If nothing above matches show the query interface if a dbalias is specified, otherwise show the campaigns
    url(pre + '$', queryUI, {}, name='base-campaign'),
    
    # Views related to generating permalinks for later use.
    url(pre + 'generate_permalink/', generate_permalink, {}, name='generate_permalink'),
    url(pre + 'permalink/(?P<pid>[^/]*)/', load_permalink, {}, name='load_permalink'),

    # Feed data for parameterinfo-popup
    url(pre + 'parameterinfo/(?P<pid>[^/]*)/', parameterinfo, {}, name='parameterinfo'),

    url('^$', showCampaigns, {}, name='show-default'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
