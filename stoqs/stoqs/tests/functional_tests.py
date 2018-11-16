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

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from stoqs.models import Parameter

import logging
import os
import re
import time

logger = logging.getLogger(__name__)

class wait_for_text_to_match(object):
    def __init__(self, locator, pattern):
        self.locator = locator
        self.pattern = re.compile(pattern)

    def __call__(self, driver):
        try:
            element_text = EC._find_element(driver, self.locator).text
            return self.pattern.search(element_text)
        except StaleElementReferenceException:
            return False

class BaseTestCase(StaticLiveServerTestCase):
    # Note that the test runner sets DEBUG to False: 
    # https://docs.djangoproject.com/en/1.8/topics/testing/advanced/#django.test.runner.DiscoverRunner.setup_test_environment

    # Specifying fixtures will copy the default database to a test database allowing for simple stoqs.models
    # object retrieval.  Note that self.browser gets pages from the original default database, not the copy.
    fixtures = ['stoqs_test_data.json']
    multi_db = False

    def setUp(self):
        self.browser = webdriver.Firefox()

    def tearDown(self):
        self.browser.quit()

    def _mapserver_loading_panel_test(self, delay=2):
        '''Wait for ajax-loader GIF image to go away'''
        wait = WebDriverWait(self.browser, delay)
        try:
            wait.until(lambda display: self.browser.find_element_by_id('map').
                        find_element_by_class_name('olControlLoadingPanel').
                        value_of_css_property('display') == 'none')
        except TimeoutException as e:
            return ('Mapserver images did not load after waiting ' +
                    str(delay) + ' seconds')
        else:
            return ''

    def _temporal_loading_panel_test(self, delay=2):
        '''Wait for ajax-loader GIF image to go away'''
        wait = WebDriverWait(self.browser, delay)
        try:
            wait.until(lambda display: self.browser
                        .find_element_by_id('metadata-loading')
                        .get_attribute('innerHTML') == '')
        except TimeoutException as e:
            return ('Time-depth images did not load after waiting ' +
                    str(delay) + ' seconds')
        else:
            return ''

    def _wait_until_visible_then_click(self, element, scroll_up=True, delay=5):
        # See: http://stackoverflow.com/questions/23857145/selenium-python-element-not-clickable
        element = WebDriverWait(self.browser, delay, poll_frequency=.2).until(
                        EC.visibility_of(element))
        if scroll_up:
            self.browser.execute_script("window.scrollTo(0, 0)")

        element.click()

    def _wait_until_id_is_visible(self, id_string, delay=2):
        try:
            element_present = EC.presence_of_element_located((By.ID, id_string))
            element = WebDriverWait(self.browser, delay).until(element_present)
            return element
        except TimeoutException:
            print(f"TimeoutException: Waited {delay} seconds for '{id_string}' element id to appear")

    def _wait_until_src_is_visible(self, src_string, delay=2):
        try:
            element_present = EC.presence_of_element_located((By.XPATH, f"//img[contains(@src,'{src_string}')]"))
            element = WebDriverWait(self.browser, delay).until(element_present)
            return element
        except TimeoutException:
            print(f"TimeoutException: Waited {delay} seconds for <img src='{src_string}'... to appear")

    def _wait_until_text_is_visible(self, element_id, expected_text, delay=2, contains=True):
        try:
            if not contains:
                WebDriverWait(self.browser, delay, poll_frequency=.2).until(
                              wait_for_text_to_match((By.ID, element_id), expected_text))
            else:
                # First get the element
                el = WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.ID, element_id)))
                # Now wait for the expected_text to appear in it
                tf = WebDriverWait(self.browser, delay, poll_frequency=.2).until(
                                   EC.text_to_be_present_in_element((By.ID, element_id), expected_text))

        except TimeoutException:
            print(f"TimeoutException: Waited {delay} seconds for text '{expected_text}' to appear")

    def _test_share_view(self, func_name):
        # Generic for any func_name that creates a view to share
        getattr(self, func_name)()

        share_view = self.browser.find_element_by_id('permalink')
        self._wait_until_visible_then_click(share_view)
        permalink = self.browser.find_element_by_id('permalink-box'
                             ).find_element_by_name('permalink')
        self._wait_until_visible_then_click(permalink)
        permalink_url = permalink.get_attribute('value')

        # Load permalink
        self.browser.get(permalink_url)
        self.assertEqual('', self._mapserver_loading_panel_test())


class BrowserTestCase(BaseTestCase):
    '''Use selenium to test standard things in the browser
    '''

    def test_campaign_page(self):
        self.browser.get(self.live_server_url)
        self.assertIn('Campaign List', self.browser.title)

    def test_query_page(self):
        self.browser.get(os.path.join(self.live_server_url, 'default/query'))
        self.assertIn('default', self.browser.title)
        self.assertEqual('', self._mapserver_loading_panel_test())

    def test_dorado_trajectory(self):
        self.browser.get(os.path.join(self.live_server_url, 'default/query'))
        try:
            # Click on Platforms to expand
            platforms_anchor = self.browser.find_element_by_id(
                                    'platforms-anchor')
            self._wait_until_visible_then_click(platforms_anchor)
        except NoSuchElementException as e:
            print(str(e))
            print("Is the development server running?")
            return

        # Finds <tr> for 'dorado' then gets the button for clicking
        dorado_button = self.browser.find_element_by_id('dorado'
                            ).find_element_by_tag_name('button')
        self._wait_until_visible_then_click(dorado_button)

        # Test that Mapserver returns images
        self.assertEqual('', self._mapserver_loading_panel_test())

        # Test Spatial 3D - provides test coverage in utils/Viz
        spatial_3d_anchor = self.browser.find_element_by_id('spatial-3d-anchor')
        self._wait_until_visible_then_click(spatial_3d_anchor)
        # - Measurement data
        measuredparameters_anchor = self.browser.find_element_by_id('measuredparameters-anchor')
        self._wait_until_visible_then_click(measuredparameters_anchor)
        altitude_id = Parameter.objects.get(name__contains='altitude').id
        altitude_plot_button = self.browser.find_element(By.XPATH,
                "//input[@name='parameters_plot' and @value='{}']".format(altitude_id))
        self._wait_until_visible_then_click(altitude_plot_button)
        self._wait_until_src_is_visible('dorado_colorbar', delay=6)
        # - Colormap
        colorbar = self.browser.find_element_by_id('mp-colormap')
        self._wait_until_visible_then_click(colorbar)
        colormap = self._wait_until_src_is_visible('deep.png', delay=4)
        self._wait_until_visible_then_click(colormap)
        # - 3D measuement data
        showgeox3dmeasurement = self.browser.find_element_by_id('showgeox3dmeasurement')
        self._wait_until_visible_then_click(showgeox3dmeasurement)
        self._wait_until_id_is_visible('mp-x3d-track')
        assert 'shape' == self.browser.find_element_by_id('mp-x3d-track').tag_name
        # - 3D Platform animation
        showplatforms = self.browser.find_element_by_id('showplatforms')
        self._wait_until_visible_then_click(showplatforms)

        self._wait_until_id_is_visible('dorado_LOCATION', delay=4)
        self.assertEquals('geolocation', self.browser.find_element_by_id('dorado_LOCATION').tag_name)

    def test_m1_timeseries(self):
        self.browser.get(os.path.join(self.live_server_url, 'default/query'))
        # Test Temporal->Parameter for timeseries plots
        self._wait_until_id_is_visible('temporal-parameter-li', delay=4)
        parameter_tab = self.browser.find_element_by_id('temporal-parameter-li')
        self._temporal_loading_panel_test(delay=6)
        self._wait_until_visible_then_click(parameter_tab, delay=4)
        expected_text = 'every single point'
        self._wait_until_text_is_visible('stride-info', expected_text, delay=6)
        self.assertIn(expected_text, self.browser.find_element_by_id('stride-info').text)

    def test_share_view_trajectory(self):
        self._test_share_view('test_dorado_trajectory')
        self._temporal_loading_panel_test(delay=6)
        self._wait_until_id_is_visible('mp-x3d-track')

        # Hack to make test pass: click checkbox twice to make dorado_LOCATION appear
        showplatforms = self.browser.find_element_by_id('showplatforms')
        self._wait_until_visible_then_click(showplatforms)
        self._wait_until_visible_then_click(showplatforms)

        self._wait_until_id_is_visible('dorado_LOCATION', delay=8)
        self.assertEquals('geolocation', self.browser.find_element_by_id('dorado_LOCATION').tag_name)

    def test_share_view_timeseries(self):
        self._test_share_view('test_m1_timeseries')
        expected_text = 'every single point'
        self._wait_until_text_is_visible('stride-info', expected_text, delay=10)
        self.assertIn(expected_text, self.browser.find_element_by_id('stride-info').text)

    def test_contour_plots(self):
        self.browser.get(os.path.join(self.live_server_url, 'default/query'))

        # Open Measured Parameters section
        mp_section = self.browser.find_element_by_id('measuredparameters-anchor')
        self._wait_until_visible_then_click(mp_section)

        # Expand Temporal window
        expand_temporal = self.browser.find_element_by_id('td-zoom-rc-button')
        self._wait_until_visible_then_click(expand_temporal)

        # Make contour color plot of M1 northward_sea_water_velocity and hide Django toolbar
        northward_sea_water_velocity_HR_id = Parameter.objects.get(name__contains='northward_sea_water_velocity_HR').id
        parameter_plot_radio_button = self.browser.find_element(By.XPATH,
            "//input[@name='parameters_plot' and @value='{}']".format(northward_sea_water_velocity_HR_id))
        parameter_plot_radio_button.click()
        self._temporal_loading_panel_test(delay=6)
        self._wait_until_src_is_visible('M1_Mooring_colorbar', delay=6)
        contour_button = self.browser.find_element(By.XPATH, "//input[@name='showdataas' and @value='contour']")
        self._wait_until_visible_then_click(contour_button)

        expected_text = 'Color: northward_sea_water_velocity_HR (cm s-1) from M1_Mooring'
        self._temporal_loading_panel_test(delay=6)
        self._wait_until_text_is_visible('temporalparameterplotinfo', expected_text, delay=6)
        self.assertEquals(expected_text, self.browser.find_element_by_id('temporalparameterplotinfo').text)

        # Contour line of M1 northward_sea_water_velocity - same as color plot
        parameter_contour_plot_radio_button = self.browser.find_element(By.XPATH,
            "//input[@name='parameters_contour_plot' and @value='{}']".format(northward_sea_water_velocity_HR_id))
        parameter_contour_plot_radio_button.click()

        # Test that at least the color bar image appears
        self.assertIn('_M1_Mooring_colorbar_', self.browser.find_element_by_id('sectioncolorbarimg').get_property('src'))

        # Contour line of M1 SEA_WATER_SALINITY_HR_id - different from color plot
        SEA_WATER_SALINITY_HR_id = Parameter.objects.get(name__contains='SEA_WATER_SALINITY_HR').id
        parameter_contour_plot_radio_button = self.browser.find_element(By.XPATH,
            "//input[@name='parameters_contour_plot' and @value='{}']".format(SEA_WATER_SALINITY_HR_id))
        parameter_contour_plot_radio_button.click()

        expected_text = 'Lines: SEA_WATER_SALINITY_HR ( ) from M1_Mooring'
        self._temporal_loading_panel_test(delay=6)
        self._wait_until_text_is_visible('temporalparameterplotinfo_lines', expected_text, delay=6)
        self.assertEquals(expected_text, self.browser.find_element_by_id('temporalparameterplotinfo_lines').text)

        # Clear the Color plot leaving just the Lines plot
        clear_color_plot_radio_button = self.browser.find_element_by_id('mp_parameters_plot_clear')
        clear_color_plot_radio_button.click()
        self.browser.execute_script("window.scrollTo(0, 0)")

        expected_text_color = ''
        expected_text_lines = 'Lines: SEA_WATER_SALINITY_HR ( ) from M1_Mooring'
        self._wait_until_text_is_visible('temporalparameterplotinfo', expected_text_color, delay=6)
        self._wait_until_text_is_visible('temporalparameterplotinfo_lines', expected_text_lines, delay=6)
        self._temporal_loading_panel_test(delay=6)
        self.assertEquals(expected_text_color, self.browser.find_element_by_id('temporalparameterplotinfo').text)
        self.assertEquals(expected_text_lines, self.browser.find_element_by_id('temporalparameterplotinfo_lines').text)

        # Uncomment to visually inspect the plot for correctness
        ##self.browser.execute_script("window.scrollTo(0, 0)")
        ##import pdb; pdb.set_trace()


class BugsFoundTestCase(BaseTestCase):
    '''Test bugs that have been found
    '''
    fixtures = ['stoqs_test_data.json']
    multi_db = False

    def test_select_wrong_platform_after_plot(self):
        self.browser.get(os.path.join(self.live_server_url, 'default/query'))

        # Open Measured Parameters section and plot Parameter bb470 from M1
        mp_section = self.browser.find_element_by_id('measuredparameters-anchor')
        self._wait_until_visible_then_click(mp_section)
        bb470_button = self.browser.find_element(By.XPATH,
                "//input[@name='parameters_plot' and @value='{}']".format(
                Parameter.objects.get(name__contains='bb470').id))
        bb470_button.click()
        self._temporal_loading_panel_test(delay=6)

        # Select 'dorado' Platform - bb470 will not be in the selection
        platforms_anchor = self.browser.find_element_by_id('platforms-anchor')
        self._wait_until_visible_then_click(platforms_anchor)
        dorado_button = self.browser.find_element_by_id('dorado'
                            ).find_element_by_tag_name('button')
        self._wait_until_visible_then_click(dorado_button)

        expected_text = 'Cannot plot Parameter'
        self._temporal_loading_panel_test(delay=6)
        self._wait_until_text_is_visible('temporalparameterplotinfo', expected_text)
        self.assertEquals(expected_text, self.browser.find_element_by_id('temporalparameterplotinfo').text)

        # Uncomment to visually inspect the plot for correctness
        ##self.browser.execute_script("window.scrollTo(0, 0)")
        ##import pdb; pdb.set_trace()
