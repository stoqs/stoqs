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

# CACHING
# ------------------------------------------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        ##'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'LOCATION': ''
    }
}

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=default_allowed_hosts)

# django-debug-toolbar
# See: http://django-debug-toolbar.readthedocs.io/en/1.0/installation.html#explicit-setup
# ------------------------------------------------------------------------------
DEBUG_TOOLBAR_PATCH_SETTINGS = False
##MIDDLEWARE += ('debug_toolbar.middleware.DebugToolbarMiddleware',)
##INSTALLED_APPS += ('debug_toolbar', )

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

# See: https://stackoverflow.com/questions/62193187/django-shell-plus-how-to-access-jupyter-notebook-in-docker-container
NOTEBOOK_ARGUMENTS = [
    "--ip",
    "0.0.0.0",
    "--port",
    "8888",
    "--allow-root",
    "--no-browser",
]

# Home page link, logo and alt text - HOME_PAGE_LOGO must be in STATIC_URL/images
HOME_PAGE_LINK = env('HOME_PAGE_LINK', default='http://www.mbari.org')
HOME_PAGE_LOGO = env('HOME_PAGE_LOGO', default='new_mbari_logo.png')
HOME_PAGE_ALT = env('HOME_PAGE_LOGO', default='MBARI')

# For additional campaigns import a campaigns dictionary from stoqs/campaigns.py
# which can be a symbolic link to a file configured for a specific installation.
try:
    from campaigns import campaigns
    for campaign in list(campaigns.keys()):
        DATABASES[campaign] = DATABASES.get('default').copy()
        DATABASES[campaign]['NAME'] = campaign
        MAPSERVER_DATABASES[campaign] = MAPSERVER_DATABASES.get('default').copy()
        MAPSERVER_DATABASES[campaign]['NAME'] = campaign
except Exception:
    pass

