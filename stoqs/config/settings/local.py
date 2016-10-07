# -*- coding: utf-8 -*-
'''
Local settings

- Run in Debug mode
- Use console backend for emails
- Add Django Debug Toolbar
- Add django-extensions as app
- Set home page logo and link to address
'''

from .common import *  # noqa

# DEBUG
# ------------------------------------------------------------------------------
DEBUG = env.bool('DJANGO_DEBUG', default=True)
TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key only used for development and testing.
SECRET_KEY = env("DJANGO_SECRET_KEY", default='KJAHKHDADHSDKHA_JASDKHASKJH_CHANGEME!!!')

# Mail settings
# ------------------------------------------------------------------------------
EMAIL_HOST = 'localhost'
EMAIL_PORT = 1025
EMAIL_BACKEND = env('DJANGO_EMAIL_BACKEND',
                    default='django.core.mail.backends.console.EmailBackend')

# CACHING
# ------------------------------------------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': ''
    }
}

# django-debug-toolbar
# See: http://django-debug-toolbar.readthedocs.io/en/1.0/installation.html#explicit-setup
# ------------------------------------------------------------------------------
DEBUG_TOOLBAR_PATCH_SETTINGS = False
MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware',)
INSTALLED_APPS += ('debug_toolbar', )

INTERNAL_IPS = ('127.0.0.1', '10.0.2.2',)

DEBUG_TOOLBAR_CONFIG = {
    'DISABLE_PANELS': [
        'debug_toolbar.panels.redirects.RedirectsPanel',
    ],
    'SHOW_TEMPLATE_CONTEXT': True,
}

# django-extensions
# ------------------------------------------------------------------------------
INSTALLED_APPS += ('django_extensions', )

# TESTING
# ------------------------------------------------------------------------------
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Your local stuff: Below this line define 3rd party library settings

# Home page link, logo and alt text - HOME_PAGE_LOGO must be in STATIC_URL/images
HOME_PAGE_LINK = env('HOME_PAGE_LINK', default='http://www.mbari.org')
HOME_PAGE_LOGO = env('HOME_PAGE_LOGO', default='new_mbari_logo.png')
HOME_PAGE_ALT = env('HOME_PAGE_LOGO', default='MBARI')

# For additional campaigns import a campaigns dictionary from stoqs/campaigns.py
# which can be a symbolic link to a file configured for a specific installation.
try:
    from campaigns import campaigns
    for campaign in campaigns.keys():
        DATABASES[campaign] = DATABASES.get('default').copy()
        DATABASES[campaign]['NAME'] = campaign
except Exception:
    pass

