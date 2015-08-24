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
from django.conf import settings
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import selenium.webdriver.support.ui as ui

import logging

logger = logging.getLogger(__name__)

class BrowserTestCase(TestCase):
    '''Use selenium to test things in the browser'''

    def setUp(self):
        self.browser = webdriver.Firefox()

    def tearDown(self):
        self.browser.quit()

    def _mapserver_loading_panel_test(self):
        '''Wait for ajax-loader GIF image to go away'''
        seconds = 2
        wait = ui.WebDriverWait(self.browser, seconds)
        try:
            wait.until(lambda display: self.browser.find_element_by_id('map').
                        find_element_by_class_name('olControlLoadingPanel').
                        value_of_css_property('display') == 'none')
        except TimeoutException as e:
            return ('Mapserver images did not load after waiting ' +
                    str(seconds) + ' seconds')
        else:
            return ''

    def test_campaign_page(self):
        self.browser.get('http://localhost:8000/')
        self.assertIn('Campaign List', self.browser.title)

    def test_query_page(self):
        self.browser.get('http://localhost:8000/default/query/')
        self.assertIn('default', self.browser.title)
        self.assertEquals('', self._mapserver_loading_panel_test())

    def test_dorado_trajectory(self):
        self.browser.get('http://localhost:8000/default/query/')
        try:
            # Click on Platforms to expand
            platforms_anchor = self.browser.find_element_by_id(
                                    'platforms-anchor')
            platforms_anchor.click()
        except NoSuchElementException as e:
            print e
            print "Is the development server running?"
            return

        # Finds <tr> for 'dorado' then gets the button for clicking
        dorado_button = self.browser.find_element_by_id('dorado'
                            ).find_element_by_tag_name('button')
        dorado_button.click()

        # Test that Mapserver returns images
        self.assertEquals('', self._mapserver_loading_panel_test())

        # Test Spatial 3D
        self.browser.implicitly_wait(10)
        spatial_3d_anchor = self.browser.find_element_by_id('spatial-3d-anchor')
        spatial_3d_anchor.click()
        showplatforms = self.browser.find_element_by_id('showplatforms')
        showplatforms.click()
        
        dl = self.browser.find_element_by_id('dorado_LOCATION')
        assert dl.tag_name == 'geolocation'

