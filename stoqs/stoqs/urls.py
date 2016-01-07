# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import patterns, url
from django.conf.urls.static import static

# The database alias (the key of the DATABASES dictionary) will prefix all of our requests
pre = r'^(?P<dbAlias>[^/]+)/'  

# format is one of: 'html', 'csv', 'kml', 'json'
formatPat = r'(?P<fmt>[^/]{0,5})'

urlpatterns = patterns('',
            
    # New Map interfaces with inheritence of bootstrap template
    url(pre + r'activityWMS$', 'stoqs.views.wms.showActivityWMS', {}, name='show-activity-wms'),

    # Map interfaces
    url(pre + r'activitiesWMS$', 'stoqs.views.wms.showActivitiesWMS', {}, name='show-activities-wms'),
    url(pre + r'parametersWMS$', 'stoqs.views.wms.showParametersWMS', {}, name='show-parameters-wms'),
    url(pre + r'platformsWMS$', 'stoqs.views.wms.showPlatformsWMS', {}, name='show-platforms-wms'),

    # All STOQS objects - full object queries with .json, .xml, .html, and .csv responses
    # Could be replaced with a REST API app, 
    url(pre + r'api/activityresource.?'  + formatPat, 'stoqs.views.showActivityResource',  {}, name='show-activityresource'),
    url(pre + r'api/activityparameter.?' + formatPat, 'stoqs.views.showActivityParameter', {}, name='show-activityparameter'),
    url(pre + r'api/activitytype.?'      + formatPat, 'stoqs.views.showActivityType',      {}, name='show-activitytype'),
    url(pre + r'api/activity.?'          + formatPat, 'stoqs.views.showActivity',          {}, name='show-activity'),
    url(pre + r'api/analysismethod.?'    + formatPat, 'stoqs.views.showAnalysisMethod',    {}, name='show-analysismethod'),
    url(pre + r'api/campaignresource.?'          + formatPat, 'stoqs.views.showCampaignResource',          {}, name='show-campaignresource'),
    url(pre + r'api/campaign.?'          + formatPat, 'stoqs.views.showCampaign',          {}, name='show-campaign'),
    url(pre + r'api/instantpoint.?'      + formatPat, 'stoqs.views.showInstantPoint',      {}, name='show-instantpoint'),
    url(pre + r'api/measuredparameterresource.?'  + formatPat, 'stoqs.views.showMeasuredParameterResource',  {}, name='show-measuredparameterresource'),
    url(pre + r'api/measurement.?'       + formatPat, 'stoqs.views.showMeasurement',       {}, name='show-measurement'),
    url(pre + r'api/parametergroupparameter.?'    + formatPat, 'stoqs.views.showParameterGroupParameter',    {}, name='show-parametergroupparameter'),
    url(pre + r'api/parametergroup.?'    + formatPat, 'stoqs.views.showParameterGroup',    {}, name='show-parametergroup'),
    url(pre + r'api/parameterresource.?' + formatPat, 'stoqs.views.showParameterResource', {}, name='show-parameterresource'),
    url(pre + r'api/parameter.?'         + formatPat, 'stoqs.views.showParameter',         {}, name='show-parameter'),
    url(pre + r'api/platformresource.?'  + formatPat, 'stoqs.views.showPlatformResource',  {}, name='show-platformresource'),
    url(pre + r'api/platformtype.?'      + formatPat, 'stoqs.views.showPlatformType',      {}, name='show-platformtype'),
    url(pre + r'api/platform.?'          + formatPat, 'stoqs.views.showPlatform',          {}, name='show-platform'),
    url(pre + r'api/resourceresource.?'  + formatPat, 'stoqs.views.showResourceResource',  {}, name='show-resourceresource'),
    url(pre + r'api/resourcetype.?'      + formatPat, 'stoqs.views.showResourceType',      {}, name='show-resourcetype'),
    url(pre + r'api/resource.?'          + formatPat, 'stoqs.views.showResource',          {}, name='show-resource'),
    url(pre + r'api/sampletype.?'        + formatPat, 'stoqs.views.showSampleType',        {}, name='show-sampletype'),
    url(pre + r'api/samplepurpose.?'     + formatPat, 'stoqs.views.showSamplePurpose',     {}, name='show-samplepuspose'),
    url(pre + r'api/sample.?'            + formatPat, 'stoqs.views.showSample',            {}, name='show-sample'),
    url(pre + r'api/simpledepthtime.?'   + formatPat, 'stoqs.views.showSimpleDepthTime',   {}, name='show-simpledepthtime'),

    # Requests that override BaseOutputer
    url(pre + r'api/measuredparameter.?' + formatPat, 'stoqs.views.app.showMeasuredParameter',  {}, name='show-measuredparmeter'),
    url(pre + r'api/sampledparameter.?' + formatPat, 'stoqs.views.app.showSampledParameter',  {}, name='show-sampledparmeter'),
    url(pre + r'api/activityparameterhistogram.?'      
                                     + formatPat, 'stoqs.views.app.showActivityParameterHistogram',  {}, name='show-aph'),
    url(pre + r'api/resourceactivity.?' + formatPat, 'stoqs.views.app.showResourceActivity',  {}, name='show-resourceactivity'),

    url(pre + r'sampledatatable.?'   + formatPat, 'stoqs.views.app.showSampleDT',      {}, name='show-sample-datatable'),
    url(pre + r'quicklookplots', 'stoqs.views.app.showQuickLookPlots',  {}, name='show-quicklookplots'),

    # URL For Chander's STOQQManager related views
    url(pre + r'query/summary/$', 'stoqs.views.query.queryData', {}, name='stoqs-query-summary'),
    url(pre + r'query/map/$', 'stoqs.views.query.queryMap', {}, name='stoqs-query-map'),
    url(pre + r'query/(?P<fmt>[^/]+)/?$', 'stoqs.views.query.queryData', {}, name='stoqs-query-results'),
    url(pre + r'query/', 'stoqs.views.query.queryUI', {}, name='stoqs-query-ui'),

    # Management, base of campaign, etc.
    url(r'campaigns.(?P<fmt>[^/]{3,5})$', 'stoqs.views.management.showCampaigns', {}, name='show-campaigns'),
    url(pre + r'mgmt$', 'stoqs.views.management.showDatabase', {}, name='show-database'),
    url(pre + r'deleteActivity/(?P<activityId>[0-9]+)$', 'stoqs.views.management.deleteActivity', {}, name='delete-activity'),
    url(pre + r'activitiesMBARICustom$', 'stoqs.views.management.showActivitiesMBARICustom', {}, name='show-activities'),

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

    # If nothing above matches show the quey interface is a dbalias is specified, otherwise show the campaigns
    url(pre + '$', 'stoqs.views.query.queryUI', {}, name='base-campaign'),
    
    # Views related to generating permalinks for later use.
    url(pre + 'generate_permalink/', 'stoqs.views.permalinks.generate_permalink', {}, name='generate_permalink'),
    url(pre + 'permalink/(?P<id>[^/]*)/', 'stoqs.views.permalinks.load_permalink', {}, name='load_permalink'),

    url('^$', 'stoqs.views.management.showCampaigns', {}, name='show-default'),

) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
