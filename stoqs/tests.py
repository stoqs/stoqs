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
os.environ['DJANGO_SETTINGS_MODULE']='settings'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../loaders'))

import DAPloaders

from django.utils import unittest
from django.test.client import Client
from django.test import TestCase

from stoqs.models import Activity
from loaders import DAPloaders
import logging
import time

logger = logging.getLogger('__name__')

class MeasurementViewsTestCase(TestCase):
    fixtures = ['stoqs_test_data.json']
    
    def setup(self):
        ##call_setup_methods()
        pass
        
    def test_campaigns(self):
        req = '/test_stoqs/campaigns'
        response = self.client.get(req)
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
    
    def test_parameters(self):
	for fmt in ('html', 'json', 'xml'):
            req = '/test_stoqs/parameters.%s' % fmt
            response = self.client.get(req)
            self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
   
    def test_platforms(self):
	for fmt in ('html', 'json', 'xml'):
            req = '/test_stoqs/platforms.%s' % fmt
            response = self.client.get(req)
            self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
    
    def test_measurementStandardNameBetween(self):
        # For the load of:
        #   http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/Dorado389_2010_300_00_300_00_decim.nc
        #   with stride = 1000    
        # there are 31 measurements for each parameter
        for parm in ('sea_water_salinity', 'sea_water_temperature', 'sea_water_sigma_t', 
                     'mass_concentration_of_chlorophyll_in_sea_water',
                    ):
            req = '/test_stoqs/measurement/sn/%s/between/20101028T075155/20101029T015157/depth/0/300/count' % parm
            response = self.client.get(req)
            self.assertEqual(response.content, '36', 'Measurement between count for %s' % req)  # ?
            
        # Make sure all the formats return 200
        for fmt in ('html', 'csv', 'kml'):
            req = '/test_stoqs/measurement/sn/sea_water_salinity/between/20101028T075155/20101029T015157/depth/0/300/data.%s' % fmt
            response = self.client.get(req)
            self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
        
        # Now with a stride
        for fmt in ('html', 'csv', 'kml'):
            req = '/test_stoqs/measurement/sn/sea_water_salinity/between/20101028T075155/20101029T015157/depth/0/300/stride/10/data.%s' % fmt
            response = self.client.get(req)
            self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
  
    def test_measurementBetween(self):
        
        # For the load of:
        #   http://dods.mbari.org/opendap/data/auvctd/surveys/2010/netcdf/Dorado389_2010_300_00_300_00_decim.nc
        #   with stride = 1000    
        # there are 31 measurements for each parameter
        for parm in ('bbp420', 'bbp700', 'biolume', 'fl700_uncorr', 'mass_concentration_of_chlorophyll_in_sea_water',
                    'nitrate', 'oxygen', 'salinity', 'sea_water_sigma_t', 'temperature'):
            req = '/test_stoqs/measurement/%s/between/20101028T075155/20101029T015157/depth/0/300/count' % parm
            response = self.client.get(req)
            self.assertEqual(response.content, '36', 'Measurement between count for %s' % req)  # ?
           
        # Make sure all the formats return 200
        for fmt in ('html', 'csv', 'kml'):
            req = '/test_stoqs/measurement/temperature/between/20101028T075155/20101029T015157/depth/0/300/data.%s' % fmt
            response = self.client.get(req)
            self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
        
        # Now with a stride
        for fmt in ('html', 'csv', 'kml'):
            req = '/test_stoqs/measurement/temperature/between/20101028T075155/20101029T015157/depth/0/300/stride/10/data.%s' % fmt
            response = self.client.get(req)
            self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
    
    def test_manage(self):
        req = '/test_stoqs/mgmt'
        response = self.client.get(req)
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
        
        req = '/test_stoqs/activities'
        response = self.client.get(req)
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
        loadedText = '498 MeasuredParameters'
        self.assertTrue(response.content.find(loadedText) != -1, 'Should find "%s" string at %s' % (loadedText, req))
        
        req = '/test_stoqs/deleteActivity/1'
        response = self.client.get(req)
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
        
        # Now test that the activity was deleted, after sleeping for a bit.  Need to see if Celery can provide notification
        # This should work, but as of 10 Jan 2010 it does not.  COmmented out for now.
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
        
