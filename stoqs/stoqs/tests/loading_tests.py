#!/usr/bin/env python

'''
Tests special case data loaders, e.g.:
- Non-GridType Trajectory data
- EPIC data from CCE Campaign

Mike McCann
MBARI 24 October 2017
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

        
class MeasuredParameterTestCase(TestCase):
    fixtures = ['stoqs_load_test.json']
    multi_db = False

    # Many of these tests use a shortcut of building a qstring from the AJAX 
    # request. 
    

    def test_epic_timeseries1(self):
        base = reverse('stoqs:show-measuredparmeter', kwargs={'dbAlias': 'stoqs_load_test', 'fmt': '.json'})

        # TODO: use a time value from the stoqs/stoqs/tests/load_data.py script
        qstring = ('parameter__name=D_3&measurement__instantpoint__timevalue__gt=2016-03-08T00:00:00')

        req = base + '?' + qstring
        response = self.client.get(req)
        import pdb; pdb.set_trace()
        self.assertEqual(response.status_code, 200, 'Status code should be 200 for %s' % req)
        data = json.loads(response.content) # Verify we don't get an exception when we load the data.

        # Test that we have the correct number of rows


