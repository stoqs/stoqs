# -*- coding: utf-8 -*-


from django.conf import settings
from django.urls import re_path
from django.conf.urls.static import static
from stoqs.views.wms import showActivityWMS, showActivitiesWMS, showParametersWMS, showPlatformsWMS
from stoqs.views import (showActivityResource, showActivityParameter, showActivityType,
                         showActivity, showAnalysisMethod, showCampaignResource, 
                         showCampaign, showInstantPoint, showMeasuredParameterResource,
                         showMeasurement, showParameterGroupParameter, showParameterGroup,
                         showParameterResource, showParameter, showPlatformResource,
                         showPlatformType, showPlatform, showResourceResource,
                         showResourceType, showResource, showSampleType, showSamplePurpose,
                         showSampleResource, showSample, showSimpleDepthTime, showNominalLocation)
from stoqs.views.app import (showMeasuredParameter, showSampledParameter, 
                             showActivityParameterHistogram, showResourceActivity,
                             showSampleDT, showQuickLookPlots)
from stoqs.views.query import queryData, queryMap, queryUI
from stoqs.views.management import showCampaigns, showDatabase, showActivitiesMBARICustom
from stoqs.views.permalinks import generate_permalink, load_permalink
from stoqs.views.parameterinfo import parameterinfo

app_name = 'stoqs'                         

# The database alias (the key of the DATABASES dictionary) will prefix all of our requests
pre = r'^(?P<dbAlias>[^/]+)/'  

# format is one of: 'html', 'csv', 'kml', 'json', 'parquet', 'estimate'
formatPat = r'(?P<fmt>[^/]{0,8})'

urlpatterns = [
    # New Map interfaces with inheritence of bootstrap template
    re_path(pre + r'activityWMS$', showActivityWMS, {}, name='show-activity-wms'),

    # Map interfaces
    re_path(pre + r'activitiesWMS$', showActivitiesWMS, {}, name='show-activities-wms'),
    re_path(pre + r'parametersWMS$', showParametersWMS, {}, name='show-parameters-wms'),
    re_path(pre + r'platformsWMS$', showPlatformsWMS, {}, name='show-platforms-wms'),

    # All STOQS objects - full object queries with .json, .xml, .html, and .csv responses
    # Could be replaced with a REST API app, 
    re_path(pre + r'api/activityresource.?'  + formatPat, showActivityResource,  {}, name='show-activityresource'),
    re_path(pre + r'api/activityparameter.?' + formatPat, showActivityParameter, {}, name='show-activityparameter'),
    re_path(pre + r'api/activitytype.?'      + formatPat, showActivityType,      {}, name='show-activitytype'),
    re_path(pre + r'api/activity.?'          + formatPat, showActivity,          {}, name='show-activity'),
    re_path(pre + r'api/analysismethod.?'    + formatPat, showAnalysisMethod,    {}, name='show-analysismethod'),
    re_path(pre + r'api/campaignresource.?'          + formatPat, showCampaignResource,          {}, name='show-campaignresource'),
    re_path(pre + r'api/campaign.?'          + formatPat, showCampaign,          {}, name='show-campaign'),
    re_path(pre + r'api/instantpoint.?'      + formatPat, showInstantPoint,      {}, name='show-instantpoint'),
    re_path(pre + r'api/measuredparameterresource.?'  + formatPat, showMeasuredParameterResource,  {}, name='show-measuredparameterresource'),
    re_path(pre + r'api/measurement.?'       + formatPat, showMeasurement,       {}, name='show-measurement'),
    re_path(pre + r'api/parametergroupparameter.?'    + formatPat, showParameterGroupParameter,    {}, name='show-parametergroupparameter'),
    re_path(pre + r'api/parametergroup.?'    + formatPat, showParameterGroup,    {}, name='show-parametergroup'),
    re_path(pre + r'api/parameterresource.?' + formatPat, showParameterResource, {}, name='show-parameterresource'),
    re_path(pre + r'api/parameter.?'         + formatPat, showParameter,         {}, name='show-parameter'),
    re_path(pre + r'api/platformresource.?'  + formatPat, showPlatformResource,  {}, name='show-platformresource'),
    re_path(pre + r'api/platformtype.?'      + formatPat, showPlatformType,      {}, name='show-platformtype'),
    re_path(pre + r'api/platform.?'          + formatPat, showPlatform,          {}, name='show-platform'),
    re_path(pre + r'api/resourceresource.?'  + formatPat, showResourceResource,  {}, name='show-resourceresource'),
    re_path(pre + r'api/resourcetype.?'      + formatPat, showResourceType,      {}, name='show-resourcetype'),
    re_path(pre + r'api/resource.?'          + formatPat, showResource,          {}, name='show-resource'),
    re_path(pre + r'api/sampletype.?'        + formatPat, showSampleType,        {}, name='show-sampletype'),
    re_path(pre + r'api/samplepurpose.?'     + formatPat, showSamplePurpose,     {}, name='show-samplepuspose'),
    re_path(pre + r'api/sampleresource.?'    + formatPat, showSampleResource,    {}, name='show-sampleresource'),
    re_path(pre + r'api/sample.?'            + formatPat, showSample,            {}, name='show-sample'),
    re_path(pre + r'api/simpledepthtime.?'   + formatPat, showSimpleDepthTime,   {}, name='show-simpledepthtime'),
    re_path(pre + r'api/nominallocation.?'   + formatPat, showNominalLocation,   {}, name='show-nominallocation'),

    # Requests that override BaseOutputer
    re_path(pre + r'api/measuredparameter.?' + formatPat, showMeasuredParameter,  {}, name='show-measuredparmeter'),
    re_path(pre + r'api/sampledparameter.?' + formatPat, showSampledParameter,  {}, name='show-sampledparmeter'),
    re_path(pre + r'api/activityparameterhistogram.?' + formatPat, 
                                                        showActivityParameterHistogram,  {}, name='show-aph'),
    re_path(pre + r'api/resourceactivity.?' + formatPat, showResourceActivity,  {}, name='show-resourceactivity'),

    re_path(pre + r'sampledatatable.?'   + formatPat, showSampleDT,      {}, name='show-sample-datatable'),
    re_path(pre + r'quicklookplots', showQuickLookPlots,  {}, name='show-quicklookplots'),

    # URL For Chander's STOQSQManager related views
    re_path(pre + r'query/summary/$', queryData, {}, name='stoqs-query-summary'),
    re_path(pre + r'query/map/$', queryMap, {}, name='stoqs-query-map'),
    re_path(pre + r'query/', queryUI, {}, name='stoqs-query-ui'),

    # Management, base of campaign, etc.
    re_path(r'campaigns.(?P<fmt>[^/]{3,5})$', showCampaigns, {}, name='show-campaigns'),
    re_path(pre + r'mgmt$', showDatabase, {}, name='show-database'),
    re_path(pre + r'activitiesMBARICustom$', showActivitiesMBARICustom, {}, name='show-activities'),

    # WFS - Tesing for exposing Sample data to the OpenLayers map
    # Prerequisites:
    #   su -y 'yum install libxml2-devel libxml2 libxslt-devel libxslt'
    #   pip install lxml
    #   pip install -e git+https://github.com/JeffHeard/ga_ows.git#egg=ga_ows
    #   export LD_LIBRARY_PATH='/usr/local/lib:$LD_LIBRARY_PATH' && python manage.py runserver 0.0.0.0:8000
    ##re_path(pre + r'wfs/?', WFS.as_view(
    ##    models=[m.Sample],          # everything but this is optional.
    ##    title='STOQS Sample WFS',
    ##    provider_name='MBARI',
    ##)),

    # If nothing above matches show the query interface if a dbalias is specified, otherwise show the campaigns
    re_path(pre + '$', queryUI, {}, name='base-campaign'),
    
    # Views related to generating permalinks for later use.
    re_path(pre + 'generate_permalink/', generate_permalink, {}, name='generate_permalink'),
    re_path(pre + 'permalink/(?P<pid>[^/]*)/', load_permalink, {}, name='load_permalink'),

    # Feed data for parameterinfo-popup
    re_path(pre + 'parameterinfo/(?P<pid>[^/]*)/', parameterinfo, {}, name='parameterinfo'),

    re_path('^$', showCampaigns, {}, name='show-default'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# See http://django-debug-toolbar.readthedocs.io/en/1.0/installation.html#explicit-setup
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ]
