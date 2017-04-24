#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2011, MBARI"
__credits__ = ["Chander Ganesan, Open Technology Group"]
__license__ = "GPL"
__version__ = "$Revision: 12276 $".split()[1]
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

Tests for the stoqs application

Mike McCann
MBARI Dec 29, 2011

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

import os
import sys
import time
import json
import time
import logging

from django.conf import settings
from django.test import TestCase
from django.core.urlresolvers import reverse
from stoqs.models import Activity, Parameter, Resource

logger = logging.getLogger(__name__)

class BaseAndMeasurementViewsTestCase(TestCase):
    fixtures = ['stoqs_test_data.json']
    format_types = ['.html', '.json', '.xml', '.csv']
    multi_db = False
    
    def setUp(self):
        ##call_setup_methods()
        pass

    # Animation tests
    ##def test_animate(self):
    ##    req = '/animatepoint/between/20101027T220000/20101028T005100/deltaminutes/30/format/url/?&width=400&height=400&rows=1&cols=1&tiles=%5B%7B%22url%22%3A%22http%3A%2F%2Flocalhost%2Fcgi-bin%2Fmapserv%3FMAP%3D%252Fdev%252Fshm%252Factivitypoint_hGjfPF.map%26LAYERS%3DDorado389_2010_300_00_300_00_decim.nc%26TIME%3D2010-10-27T22%253A00%253A00Z%252F2010-10-28T00%253A51%253A00Z%26TIMEFORMAT%3D%2525Y-%2525m-%2525dT%2525H%253A%2525M%253A%2525SZ%26TRANSPARENT%3DTRUE%26SERVICE%3DWMS%26VERSION%3D1.1.1%26REQUEST%3DGetMap%26STYLES%3D%26FORMAT%3Dimage%252Fpng%26SRS%3DEPSG%253A900913%26BBOX%3D-13686202.73393%2C4320220.8660706%2C-13502753.86607%2C4503669.7339294%26WIDTH%3D600%26HEIGHT%3D600%22%2C%22x%22%3A-100%2C%22y%22%3A-100%2C%22tileSizeW%22%3A600%2C%22tileSizeH%22%3A600%2C%22opacity%22%3A100%7D%5D'
    ##    response = self.client.get(req)
    ##    self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    # Base class view tests
    def test_campaign(self):
        for fmt in self.format_types:
            req = reverse('stoqs:show-campaign', kwargs={'fmt': fmt,
                                                   'dbAlias': 'default'})
            response = self.client.get(req)
            self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_base_campaign(self):
        req = reverse('stoqs:base-campaign', kwargs={'dbAlias': 'default'})
        response = self.client.get(req)
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_parameter(self):
       for fmt in self.format_types:
           req = reverse('stoqs:show-parameter', kwargs={'fmt': fmt,
                                                   'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
   
    def test_platform(self):
       for fmt in self.format_types:
           req = reverse('stoqs:show-platform', kwargs={'fmt': fmt,
                                                  'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_platformType(self):
       for fmt in self.format_types:
           req = reverse('stoqs:show-platformtype', kwargs={'fmt': fmt,
                                                      'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
   
    def test_activity(self):
       for fmt in self.format_types:
           req = reverse('stoqs:show-activity', kwargs={'fmt': fmt,
                                                  'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_activityType(self):
       for fmt in self.format_types:
           req = reverse('stoqs:show-activitytype', kwargs={'fmt': fmt,
                                                      'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
    
    def test_activity_parameter(self):
       for fmt in self.format_types:
           req = reverse('stoqs:show-activityparameter', kwargs={'fmt': fmt,
                                                           'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
   
    def test_resource(self):
       for fmt in self.format_types:
           req = reverse('stoqs:show-resource', kwargs={'fmt': fmt,
                                                  'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
    
    def test_resourceType(self):
       for fmt in self.format_types:
           req = reverse('stoqs:show-resourcetype', kwargs={'fmt': fmt,
                                                      'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
   
    def test_activity_resource(self):
       for fmt in self.format_types:
           req = reverse('stoqs:show-activityresource', kwargs={'fmt': fmt,
                                                          'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_parameter_resource(self):
       for fmt in self.format_types:
           req = reverse('stoqs:show-parameterresource', kwargs={'fmt': fmt,
                                                          'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_platform_resource(self):
       for fmt in self.format_types:
           req = reverse('stoqs:show-platformresource', kwargs={'fmt': fmt,
                                                          'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_sample(self):
       for fmt in self.format_types:
           req = reverse('stoqs:show-sample', kwargs={'fmt': fmt,
                                                          'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_sample_type(self):
       for fmt in self.format_types:
           req = reverse('stoqs:show-sampletype', kwargs={'fmt': fmt,
                                                          'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_analysis_method(self):
       for fmt in self.format_types:
           req = reverse('stoqs:show-analysismethod', kwargs={'fmt': fmt,
                                                          'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
   
    def test_measuredparameter(self):
        for fmt in  ['.html', '.json', '.csv', '.tsv', '.kml', '.count']:
            logger.debug('fmt = %s', fmt)
            base = reverse('stoqs:show-measuredparmeter', kwargs={ 'fmt': fmt,
                                                            'dbAlias': 'default'})
            params = {  'parameter__name': 'temperature',
                        'cmin': 11.5,
                        'cmax': 14.1 }
            qstring = ''
            for k,v in params.iteritems():
                qstring = qstring + k + '=' + str(v) + '&'

            req = base + '?' + qstring
            logger.debug('req = %s', req)
            response = self.client.get(req)
            self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
            if fmt == '.count':
                logger.debug(response.content)
                self.assertEqual(response.content, '50', 'Response should be "50" for %s' % req)
    
   
    def test_measuredparameter_with_parametervalues(self):
        for fmt in  ['.html', '.json', '.csv', '.tsv', '.kml', '.count']:
            logger.debug('fmt = %s', fmt)
            base = reverse('stoqs:show-measuredparmeter', kwargs={'fmt': fmt,
                                                            'dbAlias': 'default'})
            params = {  'parameter__name': 'temperature',
                        'cmin': 11.5,
                        'cmax': 14.1,
                        'sea_water_sigma_t_MIN': 25.0,
                        'sea_water_sigma_t_MAX': 25.33 }
            qstring = ''
            for k,v in params.iteritems():
                qstring = qstring + k + '=' + str(v) + '&'

            req = base + '?' + qstring
            logger.debug('req = %s', req)
            response = self.client.get(req)
            self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
            if fmt == '.count':
                logger.debug(response.content)
                self.assertEqual(response.content, '50', 'Response should be "50" for %s' % req)

    def test_query_summary(self):
        req = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})
        response = self.client.get(req)
        json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
   
    def test_query_ui(self):
        req = reverse('stoqs:stoqs-query-ui', kwargs={'dbAlias': 'default'})
        response = self.client.get(req)
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
   

    # Management tests 
    def test_manage(self):
        req = '/test_stoqs/mgmt'
        response = self.client.get(req)
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s, instead got %s' % (req, response.status_code))
        
        req = '/test_stoqs/activitiesMBARICustom'
        response = self.client.get(req)
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
        # Number of Dorado MeasuredParameters will be on a line in the content
        loadedText = 'Loaded variables'
        self.assertTrue(response.content.find(loadedText) != -1, 
                'Should find "%s" in string at %s, instead got: %s' % (
                    loadedText, req, response.content))
        
        req = '/test_stoqs/deleteActivity/1'
        response = self.client.get(req)
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
        
        # Now test that the activity was deleted, after sleeping for a bit.  Need to see if Celery can provide notification
        # This should work, but as of 10 Jan 2010 it does not.  Commented out for now.
#        logger.info('Sleeping after delete')
#        time.sleep(20)
#        req = '/test_stoqs/activities'
#        response = self.client.get(req)
#        logger.debug(response.content)
#        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
#        self.assertTrue(response.content.find(loadedText) == -1, 'Should not find "%s" string at %s' % (loadedText, req))

    
#    def test_admin_stoqs_that_should_be_there(self):
#	'''Need to pass login credentials, and create the login...'''
#        req='http://localhost:8000/test_stoqs/admin/stoqs'
#        response = self.client.get(req)
#        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
#        logger.debug(response.content)
        
class SummaryDataTestCase(TestCase):
    fixtures = ['stoqs_test_data.json']
    multi_db = False

    # Many of these tests use a shortcut of building a qstring from the AJAX 
    # request. They use Parameter IDs that may change if a different fixture 
    # with different IDs is used. 
    
    def test_empty(self):
        base = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})

        # Empty request with no kwargs
        qstring = ''

        req = base + '?' + qstring
        response = self.client.get(req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_timedepth(self):
        base = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})

        # time and depth constraint with get_actual_count
        qstring = ('except=spsql&except=mpsql&'
                   'start_time=2010-10-27+22%3A13%3A33&'
                   'end_time=2010-10-28+06%3A06%3A31&min_depth=-41.48&'
                   'max_depth=100.32&pplr=1&ppsl=1&get_actual_count=1')

        req = base + '?' + qstring
        response = self.client.get(req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_timedepth2(self):
        base = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})

        # time and depth constraint with get_actual_count
        qstring = ('except=spsql&except=mpsql&start_time=2010-10-28+00%3A45%3A57&'
                   'end_time=2010-10-28+12%3A17%3A20&min_depth=100.32&'
                   'max_depth=395.18&pplr=1&ppsl=1')

        req = base + '?' + qstring
        response = self.client.get(req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.
        # Perform the same check the UI does to confirm that data are in the selection
        self.assertIsNotNone(data.get('counts').get('approximate_count'), 
                'Should have a not None approximate_count')
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_measuredparameter_select(self):
        base = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})

        # Select temperature for data access
        qstring = ('except=spsql&except=mpsql&'
                   'measuredparametersgroup=temperature&'
                   'xaxis_min=1288214585000&xaxis_max=1288309759000&'
                   'yaxis_min=-100&yaxis_max=600&pplr=1&ppsl=1')

        req = base + '?' + qstring
        response = self.client.get(req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_sampledparameter_select(self):
        base = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})

        CAL1939_calanoida_id = Parameter.objects.get(name='CAL1939_calanoida').id
        qstring = ('except=spsql&except=mpsql&sampledparametersgroup={:d}&'
                   'xaxis_min=1288214585000&xaxis_max=1288309759000&'
                   'yaxis_min=-100&yaxis_max=600&pplr=1&ppsl=1').format(
                           CAL1939_calanoida_id)

        req = base + '?' + qstring
        response = self.client.get(req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_parameterplot_scatter(self):
        base = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})

        qstring = ('only=parameterplatformdatavaluepng'
                   '&only=measuredparameterx3d&only=parameterminmax'
                   '&except=spsql&except=mpsql&xaxis_min=1288216319000'
                   '&xaxis_max=1288279374000&yaxis_min=-10&yaxis_max=50'
                   '&parameterplotid=4&platformplotname=dorado&'
                   'showdataas=scatter&pplr=1&ppsl=1')

        req = base + '?' + qstring
        response = self.client.get(req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
        # Test that image file was created
        img_path = os.path.join(settings.MEDIA_ROOT, 'sections/', data.get('parameterplatformdatavaluepng')[0])
        self.assertTrue(os.path.isfile(img_path), 'File %s was not created' % img_path)
        # Assert image was created and is accesible via http - returns 404 after module updates on 7 October 2016
        ##img_url = os.path.join(settings.MEDIA_URL, 'sections', data.get('parameterplatformdatavaluepng')[0])
        ##img_resp = self.client.get(img_url)
        ##self.assertEqual(img_resp.status_code, 200, 'Status code for image should be 200 for %s' % img_url)

    def test_parameterparameterplot1(self):
        base = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})

        qstring = ('only=parameterparameterpng&only=parameterparameterx3d'
                   '&except=spsql&except=mpsql&xaxis_min=1288216319000'
                   '&xaxis_max=1288279374000&yaxis_min=-10&yaxis_max=50'
                   '&px=4&py=5&showstandardnameparametervalues=1&pplr=1&ppsl=1')

        req = base + '?' + qstring
        response = self.client.get(req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
        # Test that image file was created
        img_path = os.path.join(settings.MEDIA_ROOT, 'parameterparameter', data.get('parameterparameterpng')[0])
        self.assertTrue(os.path.isfile(img_path), 'File %s was not created' % img_path)
        # Assert image was created and is accesible via http - returns 404 after module updates on 7 October 2016
        ##img_url = os.path.join(settings.MEDIA_URL, 'parameterparameter', data.get('parameterparameterpng')[0])
        ##img_resp = self.client.get(img_url)
        ##self.assertEqual(img_resp.status_code, 200, 'Status code for image should be 200 for %s' % img_url)

    def test_parameterparameterplot2(self):
        base = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})

        # SampledParameter (B1006_barnacles) vs. MeasuredParameter (fl700_uncoor)
        fl700_uncorr_id = Parameter.objects.get(name='fl700_uncorr').id
        B1006_barnacles_id = Parameter.objects.get(name='B1006_barnacles').id
        qstring = ('only=parameterparameterpng&only=parameterparameterx3d&'
                   'except=spsql&except=mpsql&xaxis_min=1288214585000&'
                   'xaxis_max=1288309759000&yaxis_min=-100&yaxis_max=600&px={:d}&'
                   'py={:d}&pplr=1&ppsl=1').format(fl700_uncorr_id, B1006_barnacles_id)

        req = base + '?' + qstring
        response = self.client.get(req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
        # Test that image file was created
        img_path = os.path.join(settings.MEDIA_ROOT, 'parameterparameter', data.get('parameterparameterpng')[0])
        self.assertTrue(os.path.isfile(img_path), 'File %s was not created' % img_path)
        # Assert image was created and is accesible via http - returns 404 after module updates on 7 October 2016
        ##img_url = os.path.join(settings.MEDIA_URL, 'parameterparameter', data.get('parameterparameterpng')[0])
        ##img_resp = self.client.get(img_url)
        ##self.assertEqual(img_resp.status_code, 200, 'Status code for image should be 200 for %s' % img_url)

    def test_parameterparameterplot3(self):
        base = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})

        # SampledParameter vs. MeasuredParameter and 3D with color
        fl700_uncorr_id = Parameter.objects.get(name='fl700_uncorr').id
        B1006_barnacles_id = Parameter.objects.get(name='B1006_barnacles').id
        qstring = ('only=parameterparameterpng&only=parameterparameterx3d&'
                   'except=spsql&except=mpsql&xaxis_min=1288216319000&'
                   'xaxis_max=1288279374000&yaxis_min=-10&yaxis_max=50&'
                   'platforms=dorado&px=6&py=1&pz={:d}&pc={:d}&pplr=1&ppsl=1'
                   ).format(fl700_uncorr_id, B1006_barnacles_id)

        req = base + '?' + qstring
        response = self.client.get(req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
        # Test that image file was created
        img_path = os.path.join(settings.MEDIA_ROOT, 'parameterparameter', data.get('parameterparameterpng')[0])
        self.assertTrue(os.path.isfile(img_path), 'File %s was not created' % img_path)
        # Assert image was created and is accesible via http - returns 404 after module updates on 7 October 2016
        ##img_url = os.path.join(settings.MEDIA_URL, 'parameterparameter', data.get('parameterparameterpng')[0])
        ##img_resp = self.client.get(img_url)
        ##self.assertEqual(img_resp.status_code, 200, 'Status code for image should be 200 for %s' % img_url)

    def test_simpledepthtime_timeseries(self):
        base = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})

        # Plot SEA_WATER_SALINITY_HR from M1_Mooring 
        SEA_WATER_SALINITY_HR_id = Parameter.objects.get(name='SEA_WATER_SALINITY_HR').id
        qstring = ('only=parametertime&except=spsql&except=mpsql&'
                   'xaxis_min=1288214585000&xaxis_max=1288309759000&'
                   'yaxis_min=-200&yaxis_max=600&parametertab=1&'
                   'secondsperpixel=216&parametertimeplotid={:d}&pplr=1&ppsl=1'
                   ).format(SEA_WATER_SALINITY_HR_id)

        req = base + '?' + qstring
        response = self.client.get(req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_simpledepthtime_timeseriesprofile1(self):
        base = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})

        # Plot SEA_WATER_SALINITY_HR from M1_Mooring 
        SEA_WATER_SALINITY_HR_id = Parameter.objects.get(name='SEA_WATER_SALINITY_HR').id
        qstring = ('except=spsql&except=mpsql&xaxis_min=1288214585000&'
                   'xaxis_max=1288309759000&yaxis_min=-100&yaxis_max=600&'
                   'platforms=M1_Mooring&parameterplotid={:d}&'
                   'platformplotname=M1_Mooring&showdataas=scatter&pplr=1&'
                   'ppsl=1').format(SEA_WATER_SALINITY_HR_id)

        req = base + '?' + qstring
        response = self.client.get(req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_simpledepthtime_timeseriesprofile2(self):
        base = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})

        qstring = ('only=parametertime&except=spsql&except=mpsql&'
                   'xaxis_min=1288214585000&xaxis_max=1288309759000&'
                   'yaxis_min=-200&yaxis_max=600&platforms=M1_Mooring&'
                   'parametertab=1&secondsperpixel=216&'
                   'parametertimeplotid=11&pplr=1&ppsl=1')

        req = base + '?' + qstring
        response = self.client.get(req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_histograms(self):
        base = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})

        qstring = ('only=activityparameterhistograms&except=spsql&except=mpsql&'
                   'xaxis_min=1288214585000&xaxis_max=1288309759000&'
                   'yaxis_min=-100&yaxis_max=600&'
                   'showstandardnameparametervalues=1&showallparametervalues=1&'
                   'pplr=1&ppsl=1')

        req = base + '?' + qstring
        response = self.client.get(req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_standardname_select(self):
        base = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})

        # Standardname sea_water_temperature selected for data access
        qstring = ('except=spsql&except=mpsql&'
                   'parameterstandardname=sea_water_temperature&'
                   'xaxis_min=1288214585000&xaxis_max=1288309759000&'
                   'yaxis_min=-100&yaxis_max=600&pplr=1&ppsl=1')

        req = base + '?' + qstring
        response = self.client.get(req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_labeled(self):
        base = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})

        diatom_id = Resource.objects.get(name='label', value='diatom').id
        sediment_id = Resource.objects.get(name='label', value='sediment').id
        qstring = ('except=spsql&except=mpsql&'
                   'measuredparametersgroup=fl700_uncorr&'
                   'xaxis_min=1288216319000&xaxis_max=1288279374000&'
                   'yaxis_min=-10&yaxis_max=50&mplabels={:d}&mplabels={:d}&'
                   'pplr=1&ppsl=1').format(diatom_id, sediment_id)

        req = base + '?' + qstring
        response = self.client.get(req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_platform_animations(self):
        base = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})

        qstring = ('except=spsql&except=mpsql&xaxis_min=1288214585000&'
                   'xaxis_max=1288309759000&yaxis_min=-100&yaxis_max=600&'
                   'showplatforms=1&ve=10&pplr=1&ppsl=1')

        req = base + '?' + qstring
        response = self.client.get(req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_parametervalue_min_max1(self):
        base = reverse('stoqs:stoqs-query-summary', kwargs={'dbAlias': 'default'})

        qstring = ('except=spsql&except=mpsql&xaxis_min=1288214585000&'
                   'xaxis_max=1288309759000&yaxis_min=-100&yaxis_max=600&'
                   'temperature_MIN=11.22&temperature_MAX=13.19&'
                   'showstandardnameparametervalues=1&parameterplotid=1&'
                   'platformplotname=dorado&showdataas=scatter&pplr=1&ppsl=1')

        req = base + '?' + qstring
        response = self.client.get(req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)


class RegressionTestCase(TestCase):
    fixtures = ['stoqs_test_data.json']
    multi_db = False

    # As bugs are discovered this class is a place to put tests

    def test_jetplus_kmln_generation(self):
        base = reverse('stoqs:show-measuredparmeter', kwargs={'fmt': '.kmln', 'dbAlias': 'default'})

        # Discovered that jetplus.txt was just 128 points when the KML colormap generation code
        # assumed 256 colors in the color lookup table. This test confirms that the correct color
        # is generated from the jetplus color lookup table.
        qstring = ('parameter__name=temperature&measurement__instantpoint__activity__platform__name'
                   '=dorado&measurement__instantpoint__timevalue__gt=2010-10-28%2002:10:19&'
                   'measurement__instantpoint__timevalue__lt=2010-10-28%2003:43:39&'
                   'measurement__depth__gte=20.1&measurement__depth__lte=35.72&cmin=11.53&'
                   'cmax=14.06&cm=jetplus&num_colors=256')

        req = base + '?' + qstring
        response = self.client.get(req)
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
        kml_data = response.content
        required_string = ('<coordinates>\n-121.934521, 36.868014,-29.8\n</coordinates>\n'
                           '</Point>\n</Placemark> \n<Placemark>\n<styleUrl>#ffd10000') 
        self.assertTrue(required_string in response.content, 'required_string not found in response.content')

