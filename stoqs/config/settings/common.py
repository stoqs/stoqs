# -*- coding: utf-8 -*-
"""
Django settings for stoqs project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""
from __future__ import absolute_import, unicode_literals

import environ
import dj_database_url

ROOT_DIR = environ.Path(__file__) - 3  # (/a/b/myfile.py - 3 = /)
APPS_DIR = ROOT_DIR.path('stoqs')
SITE_ID = 1

env = environ.Env()

# APP CONFIGURATION
# ------------------------------------------------------------------------------
DJANGO_APPS = (
    # Default Django apps:
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',

    # Useful template tags:
    # 'django.contrib.humanize',

    # Admin
    'django.contrib.admin',
)
THIRD_PARTY_APPS = (
    'crispy_forms',  # Form layouts
    'allauth',  # registration
    'allauth.account',  # registration
    # See: https://github.com/pennersr/django-allauth/blob/master/docs/installation.rst
    # and https://github.com/pennersr/django-allauth/commit/b1bce45012a808aef233e7f7b60a956d8a2524ee
    # Expect allauth.socialaccount to work when 0.22 is in pypi
    ##'allauth.socialaccount',  # registration
    ##'allauth.socialaccount.providers.dropbox',
    ##'allauth.socialaccount.providers.facebook',
    ##'allauth.socialaccount.providers.github',
    ##'allauth.socialaccount.providers.google',
    ##'allauth.socialaccount.providers.openid',
    ##'allauth.socialaccount.providers.twitter',
)

# Apps specific for this project go here.
LOCAL_APPS = (
    # Your stuff: custom apps go here
    'stoqs',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIDDLEWARE CONFIGURATION
# ------------------------------------------------------------------------------
MIDDLEWARE_CLASSES = (
    # Make sure djangosecure.middleware.SecurityMiddleware is listed first
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'stoqs.db_router.RouterMiddleware',
)

# MIGRATIONS CONFIGURATION
# ------------------------------------------------------------------------------
MIGRATION_MODULES = {
    'sites': 'stoqs.contrib.sites.migrations'
}

# DEBUG
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)

# FIXTURE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    # The app's fixtures directory is automatically included
)

# EMAIL CONFIGURATION
# ------------------------------------------------------------------------------
EMAIL_BACKEND = env('DJANGO_EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')

# MANAGER CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
    ("""Mike McCann""", 'MBARIMike@gmail.com'),
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
# Need to set environment variable DATABASE_URL containing DB login/password
# e.g.: export DATABASE_URL="postgis://stoqsadm:CHANGEME@127.0.0.1:5432/stoqs"
DATABASES = {
    # Raises ImproperlyConfigured exception if DATABASE_URL not in os.environ
    'default': env.db("DATABASE_URL")
}
DATABASES['default']['ATOMIC_REQUESTS'] = True

# For running additional databases append entries from STOQS_CAMPAIGNS environment
# Example: export STOQS_CAMPAIGNS='stoqs_beds_canyon_events_t,stoqs_os2015_t'
for campaign in env.list('STOQS_CAMPAIGNS', default=[]):
    DATABASES[campaign] = DATABASES.get('default').copy()
    DATABASES[campaign]['NAME'] = campaign

# GENERAL CONFIGURATION
# ------------------------------------------------------------------------------
# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'UTC'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = 'en-us'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
# STOQS assumes all times are GMT, which is the timezone of the database
# It's OK to use naiive datetimes with this policy
USE_TZ = False

# TEMPLATE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        'DIRS': [
            str(APPS_DIR.path('templates/stoqs')), '/tmp',
        ],
        'OPTIONS': {
            # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
            'debug': DEBUG,
            # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
            # https://docs.djangoproject.com/en/dev/ref/templates/api/#loader-types
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                ##'allauth.account.context_processors.account',
                ##'allauth.socialaccount.context_processors.socialaccount',
                ##'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                ##'django.template.context_processors.tz',
                ##'django.contrib.messages.context_processors.messages',
                # Your stuff: custom template context processors go here
            ],
        },
    },
]

# See: http://django-crispy-forms.readthedocs.org/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = 'bootstrap3'

# STATIC FILE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
# Nginx example: export STATIC_ROOT=/usr/share/nginx/html/static/
STATIC_ROOT = env('STATIC_ROOT', default=str(APPS_DIR('static')))
STATIC_URL = env('STATIC_URL', default='/static/')

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (
    str(ROOT_DIR.path('static')),
)

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# MEDIA CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
# Nginx example: export MEDIA_ROOT=/usr/share/nginx/html/media/
MEDIA_ROOT = env('MEDIA_ROOT', default=str(APPS_DIR('media')))
MEDIA_URL = env('MEDIA_URL', default='/media/')

# URL Configuration
# ------------------------------------------------------------------------------
ROOT_URLCONF = 'urls'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
# wsgi.py still imports from django-configurations, perhaps this will get
# fixed with https://github.com/pydanny/cookiecutter-django/issues/160
##WSGI_APPLICATION = 'wsgi.application'

# AUTHENTICATION CONFIGURATION
# ------------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

# Some really nice defaults
ACCOUNT_AUTHENTICATION_METHOD = 'username'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'

# Custom user app defaults
# Select the correct user model
##AUTH_USER_MODEL = 'users.User'
##LOGIN_REDIRECT_URL = 'users:redirect'
##LOGIN_URL = 'account_login'

# SLUGLIFIER
AUTOSLUG_SLUGIFY_FUNCTION = 'slugify.slugify'


# LOGGING CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#logging
# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

# Your common stuff: Below this line define 3rd party library settings

# Google Analytics code - get for your web site, if you want to track usage
# export DJANGO_GOOGLE_ANALYTICS_CODE='SET_YOUR_OWN_GA_CODE_TO_TRACK_USAGE'
GOOGLE_ANALYTICS_CODE = 'testing'

# Must be externally accessible if your STOQS server is to be externally accessible
# The default of 'localhost:8080' is for a Vagrant install, set MAPSERVER_HOST for
# other cases, e.g. export MAPSERVER_HOST='172.16.130.204'
MAPSERVER_HOST = env('MAPSERVER_HOST', default='localhost:8080')

# For template generated .map files
MAPFILE_DIR = '/dev/shm'


# STOQS specific logging
LOGGING['formatters'] = {
    'veryverbose': {
        'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(filename)s %(funcName)s():%(lineno)d %(message)s'
    },
    'verbose': {
        'format': '%(levelname)s %(asctime)s %(filename)s %(funcName)s():%(lineno)d %(message)s'
    },
    'simple': {
        'format': '%(levelname)s %(message)s'
    },
}
LOGGING['handlers']['console'] = {
                            'level':'DEBUG',
                            'class':'logging.StreamHandler',
                            'formatter': 'verbose'
}
LOGGING['loggers']['stoqs'] = {
                            'handlers':['console'],
                            'level':'INFO',
                            'formatter': 'verbose'
}
LOGGING['loggers']['stoqs.db_router'] = {
                            'handlers':['console'],
                            'propagate': True,
                            'level':'INFO',
                            'formatter': 'verbose'
}
LOGGING['loggers']['loaders'] = {
                            'handlers':['console'],
                            'propagate': True,
                            'level':'INFO',
                            'formatter': 'verbose'
}
LOGGING['loggers']['DAPloaders'] = {
                            'handlers':['console'],
                            'propagate': True,
                            'level':'INFO',
                            'formatter': 'verbose'
}
LOGGING['loggers']['SampleLoaders'] = {
                            'handlers':['console'],
                            'propagate': True,
                            'level':'INFO',
                            'formatter': 'verbose'
}
LOGGING['loggers']['utils'] = {
                            'handlers':['console'],
                            'propagate': True,
                            'level':'INFO',
                            'formatter': 'verbose'
}
LOGGING['loggers']['stoqs.tests'] = {
                            'handlers':['console'],
                            'level':'INFO',
                            'formatter': 'verbose'
}
LOGGING['loggers']['__main__'] = {
                            'handlers':['console'],
                            'level':'INFO',
                            'formatter': 'verbose'
}
LOGGING['loggers']['stoqs']['level'] = 'INFO'
