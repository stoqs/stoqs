import unittest
from selenium import webdriver

class HomePageTestCase(unittest.TestCase):
    def setUp(self):
        self.browser = webdriver.Firefox()

    def tearDown(self):
        self.browser.quit()

    def test_home_page(self):
        self.browser.get('http://localhost:8000')
        self.assertIn('Campaign List', self.browser.title)

if __name__ == '__main__':
    unittest.main()
