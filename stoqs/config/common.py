# -*- coding: utf-8 -*-
"""
Django settings for stoqs project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import dj_database_url
from os.path import join, dirname

from configurations import Configuration, values

BASE_DIR = dirname(dirname(__file__))


class Common(Configuration):

    # APP CONFIGURATION
    DJANGO_APPS = (
        # Default Django apps:
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',
        'django.contrib.messages',
        'django.contrib.staticfiles',

        # Useful template tags:
        # 'django.contrib.humanize',

        # Admin
        'django.contrib.admin',
    )
    THIRD_PARTY_APPS = (
        ##'crispy_forms',  # Form layouts
        ##'avatar',  # for user avatars
        ##'allauth',  # registration
        ##'allauth.account',  # registration
        ##'allauth.socialaccount',  # registration
    )

    # Apps specific for this project go here.
    LOCAL_APPS = (
        ##'users',  # custom users app
        # Your stuff: custom apps go here
        'stoqs',
    )

    # See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
    INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
    # END APP CONFIGURATION

    # MIDDLEWARE CONFIGURATION
    MIDDLEWARE_CLASSES = (
        # Make sure djangosecure.middleware.SecurityMiddleware is listed first
        'djangosecure.middleware.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
        'stoqs.db_router.RouterMiddleware',
    )
    # END MIDDLEWARE CONFIGURATION

    # MIGRATIONS CONFIGURATION
    MIGRATION_MODULES = {
        'sites': 'contrib.sites.migrations'
    }
    # END MIGRATIONS CONFIGURATION

    # DEBUG
    # See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
    DEBUG = values.BooleanValue(False)

    # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
    TEMPLATE_DEBUG = DEBUG
    # END DEBUG

    # SECRET CONFIGURATION
    # See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
    # Note: This key only used for development and testing.
    #       In production, this is changed to a values.SecretValue() setting
    # export DJANGO_SECRET_KEY='SET_YOUR_OWN_IMPOSSIBLE_TO_GUESS_SECRET_KEY_ENVIRONMENT_VARIABLE'
    SECRET_KEY = values.SecretValue()
    # END SECRET CONFIGURATION

    # Google Analytics code - get for your web site, if you want to track usage
    # export DJANGO_GOOGLE_ANALYTICS_CODE='SET_YOUR_OWN_GA_CODE_TO_TRACK_USAGE'
    GOOGLE_ANALYTICS_CODE = values.Value('testing')

    # FIXTURE CONFIGURATION
    # See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
    FIXTURE_DIRS = (
        join(BASE_DIR, 'fixtures'),
    )
    # END FIXTURE CONFIGURATION

    # EMAIL CONFIGURATION
    ##EMAIL_BACKEND = values.Value('django.core.mail.backends.smtp.EmailBackend')
    EMAIL_BACKEND = values.Value('django.core.mail.backends.console.EmailBackend')
    # END EMAIL CONFIGURATION

    # MANAGER CONFIGURATION
    # See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
    ADMINS = (
        ("""Mike McCann""", 'MBARIMike@gmail.com'),
    )

    # See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
    MANAGERS = ADMINS
    # END MANAGER CONFIGURATION

    # DATABASE CONFIGURATION
    # See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
    # To connect to the database with specific username and password set DATABASE_URL 
    # environment variable, e.g.: export DATABASE_URL="postgis://<u>:<p>@127.0.0.1:5432/stoqs"
    #   With DATABASE_URL set as above dj_database_url.config() will construct the proper dictionary
    #   This permits sensitive information to be set in environment variables instead of in config
    #   files as advocated by 12factor.net.
    # The default DatabaseURLValue of 'postgis://127.0.0.1:5432/stoqs' will try and connect with the
    # current shell account id.  Note that multiple databases are not supported yet by configurations:
    # https://github.com/jezdez/django-configurations/issues/97
    DATABASES = values.DatabaseURLValue('postgis://127.0.0.1:5432/stoqs')
    # END DATABASE CONFIGURATION

    DATABASE_ROUTERS = ['stoqs.db_router.DatabaseRouter']

    # CACHING
    # Do this here because thanks to django-pylibmc-sasl and pylibmc
    # memcacheify (used on heroku) is painful to install on windows.
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': ''
        }
    }
    # END CACHING

    # GENERAL CONFIGURATION

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
    # END GENERAL CONFIGURATION

    # TEMPLATE CONFIGURATION
    # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
    TEMPLATE_CONTEXT_PROCESSORS = (
        'django.contrib.auth.context_processors.auth',
        'allauth.account.context_processors.account',
        'allauth.socialaccount.context_processors.socialaccount',
        'django.core.context_processors.debug',
        'django.core.context_processors.i18n',
        'django.core.context_processors.media',
        'django.core.context_processors.static',
        'django.core.context_processors.tz',
        'django.contrib.messages.context_processors.messages',
        'django.core.context_processors.request',
        # Your stuff: custom template context processers go here
    )

    # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
    TEMPLATE_DIRS = (
        join(BASE_DIR, 'stoqs/templates/stoqs'), '/tmp',
    )

    TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )

    # See: http://django-crispy-forms.readthedocs.org/en/latest/install.html#template-packs
    CRISPY_TEMPLATE_PACK = 'bootstrap3'
    # END TEMPLATE CONFIGURATION

    # STATIC FILE CONFIGURATION
    # See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
    STATIC_ROOT = join(os.path.dirname(BASE_DIR), 'static')

    # See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
    STATIC_URL = '/stoqs/static/'

    # See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
    STATICFILES_DIRS = (
        join(BASE_DIR, 'static'),
    )

    # See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
    STATICFILES_FINDERS = (
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    )
    # END STATIC FILE CONFIGURATION

    # MEDIA CONFIGURATION
    # See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
    MEDIA_ROOT = join(BASE_DIR, 'media')

    # See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
    MEDIA_URL = '/media/'
    # END MEDIA CONFIGURATION

    # URL Configuration
    ROOT_URLCONF = 'urls'

    # See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
    WSGI_APPLICATION = 'wsgi.application'
    # End URL Configuration

    # AUTHENTICATION CONFIGURATION
    AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.ModelBackend',
        'allauth.account.auth_backends.AuthenticationBackend',
    )

    # Some really nice defaults
    ACCOUNT_AUTHENTICATION_METHOD = 'username'
    ACCOUNT_EMAIL_REQUIRED = True
    ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
    # END AUTHENTICATION CONFIGURATION

    # Custom user app defaults
    # Select the correct user model
    ##AUTH_USER_MODEL = 'users.User'
    ##LOGIN_REDIRECT_URL = 'users:redirect'
    ##LOGIN_URL = 'account_login'
    # END Custom user app defaults

    # SLUGLIFIER
    AUTOSLUG_SLUGIFY_FUNCTION = 'slugify.slugify'
    # END SLUGLIFIER

    # LOGGING CONFIGURATION
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
    # END LOGGING CONFIGURATION

    @classmethod
    def post_setup(cls):
        cls.DATABASES['default']['ATOMIC_REQUESTS'] = True

    #
    # Your common stuff: Below this line define 3rd party library settings
    #

    # STOQS specific logging
    LOGGING['formatters'] = {
        'veryverbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(filename)s %(funcName)s():%(lineno)d %(message)s'
        },
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(filename)s %(funcName)s():%(lineno)d %(message)s'
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
    LOGGING['loggers']['stoqs.loaders'] = {
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
    LOGGING['loggers']['stoqs']['level'] = 'DEBUG'

    # END STOQS specific logging
