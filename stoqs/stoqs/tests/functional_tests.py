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

Functional tests for the stoqs application

Mike McCann

@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

from django.test import TestCase
from selenium import webdriver

import logging

logger = logging.getLogger(__name__)

class BrowserTestCase(TestCase):
    '''Use selenium to test things in the browser'''

    def setUp(self):
        self.browser = webdriver.Firefox()

    def tearDown(self):
        self.browser.quit()

    def test_campaign_page(self):
        self.browser.get('http://localhost:8000/')
        self.assertIn('Campaign List', self.browser.title)

    def test_query_page(self):
        self.browser.get('http://localhost:8000/default/query/')
        self.assertIn('default', self.browser.title)

