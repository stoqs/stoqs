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

Unit tests for the STOQS project.  Test with:
    python -Wall manage.py test stoqs -v 2


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

from django.utils import unittest
from django.test.client import Client
from django.test import TestCase
from django.core.urlresolvers import reverse

from stoqs.models import Activity
import logging
import time

logger = logging.getLogger(__name__)


class BaseAndMeasurementViewsTestCase(TestCase):
    fixtures = ['stoqs_test_data.json']
    format_types = ['.html', '.json', '.xml', '.csv']
    multi_db = False
    
    def setup(self):
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
            req = reverse('show-campaign', kwargs={'format': fmt,
                                                   'dbAlias': 'default'})
            response = self.client.get(req)
            self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
    
    def test_parameter(self):
       for fmt in self.format_types:
           req = reverse('show-parameter', kwargs={'format': fmt,
                                                   'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
   
    def test_platform(self):
       for fmt in self.format_types:
           req = reverse('show-platform', kwargs={'format': fmt,
                                                  'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_platformType(self):
       for fmt in self.format_types:
           req = reverse('show-platformtype', kwargs={'format': fmt,
                                                      'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
   
    def test_activity(self):
       for fmt in self.format_types:
           req = reverse('show-activity', kwargs={'format': fmt,
                                                  'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_activityType(self):
       for fmt in self.format_types:
           req = reverse('show-activitytype', kwargs={'format': fmt,
                                                      'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
    
    def test_activity_parameter(self):
       for fmt in self.format_types:
           req = reverse('show-activityparameter', kwargs={'format': fmt,
                                                           'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
   
    def test_resource(self):
       for fmt in self.format_types:
           req = reverse('show-resource', kwargs={'format': fmt,
                                                  'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
    
    def test_resourceType(self):
       for fmt in self.format_types:
           req = reverse('show-resourcetype', kwargs={'format': fmt,
                                                      'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
   
    def test_activity_resource(self):
       for fmt in self.format_types:
           req = reverse('show-activityresource', kwargs={'format': fmt,
                                                          'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_parameter_resource(self):
       for fmt in self.format_types:
           req = reverse('show-parameterresource', kwargs={'format': fmt,
                                                          'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_platform_resource(self):
       for fmt in self.format_types:
           req = reverse('show-platformresource', kwargs={'format': fmt,
                                                          'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_instantpoint_resource(self):
       for fmt in self.format_types:
           req = reverse('show-instantpointresource', kwargs={'format': fmt,
                                                          'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_measurement_resource(self):
       for fmt in self.format_types:
           req = reverse('show-measurementresource', kwargs={'format': fmt,
                                                          'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_sample(self):
       for fmt in self.format_types:
           req = reverse('show-sample', kwargs={'format': fmt,
                                                          'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_sample_type(self):
       for fmt in self.format_types:
           req = reverse('show-sampletype', kwargs={'format': fmt,
                                                          'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_analysis_method(self):
       for fmt in self.format_types:
           req = reverse('show-analysismethod', kwargs={'format': fmt,
                                                          'dbAlias': 'default'})
           response = self.client.get(req)
           self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
   
    def test_measuredparameter(self):
        for fmt in  ['.html', '.json', '.csv', '.tsv', '.kml', '.count']:
            logger.debug('fmt = %s', fmt)
            base = reverse('show-measuredparmeter', kwargs={ 'format': fmt,
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
            base = reverse('show-measuredparmeter', kwargs={ 'format': fmt,
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
                self.assertEqual(response.content, '30', 'Response should be "50" for %s' % req)

    def test_query_jsonencoded(self):
        req = reverse('stoqs-query-results', kwargs={'format': 'json',
                                                     'dbAlias': 'default'})
        response = self.client.get(req)
        json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)

    def test_query_summary(self):
        req = reverse('stoqs-query-summary', kwargs={'dbAlias': 'default'})
        response = self.client.get(req)
        json.loads(response.content) # Verify we don't get an exception when we load the data.
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
   
    def test_query_ui(self):
        req = reverse('stoqs-query-ui', kwargs={'dbAlias': 'default'})
        response = self.client.get(req)
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
   

    # Management tests 
    def test_manage(self):
        req = '/test_stoqs/mgmt'
        response = self.client.get(req)
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
        
        req = '/test_stoqs/activitiesMBARICustom'
        response = self.client.get(req)
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
        loadedText = '498 MeasuredParameters'
        self.assertTrue(response.content.find(loadedText) != -1, 'Should find "%s" string at %s' % (loadedText, req))
        
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
        
