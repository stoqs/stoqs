# Django settings for STOQS project.

import os
project_dir = os.path.dirname(__file__)


# This should always be False in production
TEMPLATE_DEBUG = DEBUG = True

# Installation-specific configuration information is kept in a privateSettings file
# in the project_dir directory that is not checked into source code control and is
# protected from prying eyes on the system.  See privateSettings.tmpl for an example.

# Contact info - set to nothing here.  Import from privateSettings file.
ADMIN_NAME = ''
ADMIN_EMAIL = ''

# Other settings that need to be set in privateSettings
MY_DATABASES = ''
MY_SECRET_KEY = ''

# Mapserver hostname, just the name.  Assumes that mapserv is install in /cgi-bin
MAPSERVER_HOST = ''

# The logging defined here can be overridden in the privateSettings file, as needed
# See http://docs.djangoproject.com/en/dev/topics/logging for more details
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'veryverbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(filename)s %(funcName)s():%(lineno)d %(message)s'
        },
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(filename)s %(funcName)s():%(lineno)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'null': {
            'level':'ERROR',
            'class':'django.utils.log.NullHandler',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },
    # These settings may be overriden in privateSettings
    'loggers': {
        '__main__': {
            'handlers':['console'],
            'propagate': True,
            'level':'ERROR',
        },
        'stoqs': {
            'handlers':['console'],
            'propagate': True,
            'level':'ERROR',
        },
        'utils': {
            'handlers':['console'],
            'propagate': True,
            'level':'ERROR',
        },
        'stoqs.db_router': {
            'handlers':['console'],
            'propagate': False,
            'level':'ERROR',
        },
        'loaders': {
            'handlers':['console'],
            'propagate': True,
            'level':'ERROR',
        },
        'django': {
            'handlers':['console'],
            'propagate': True,
            'level':'ERROR',
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

# Load sensitive settings and modifications to above from a local file that has tight file system permissions
execfile(os.path.join(project_dir, 'privateSettings'))

ADMINS = (
    (ADMIN_NAME, ADMIN_EMAIL),
)

MANAGERS = ADMINS

DATABASES = MY_DATABASES

DATABASE_ROUTERS = ['stoqs.db_router.DatabaseRouter']

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# Note that this setting affects only Django's interaction with the
# database. In order for mapserver's and other queries to understand 
# the GMT timezone, the postgres databases must be altered to use the
# 'GMT' timezone. You must alter the databases as described in the 
# STOQS INSTALL file.
USE_TZ = True
TIME_ZONE = 'GMT'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = '/var/www/html/stoqs/media'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/stoqs/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = '/var/www/html/stoqs/static'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/stoqs/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(project_dir, 'stoqs/static'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Use the SECRET_KEY from the privateSettings file
SECRET_KEY = MY_SECRET_KEY

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'stoqs.db_router.RouterMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(project_dir, 'stoqs/templates'),
    '/tmp',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'django.contrib.gis',
    'djcelery',
    'stoqs',
    'django_extensions',
)

# RabbitMQ settings - required for Celery to process long-running tasks
# the values on the rhs of '=' should be set in your privateSettings file.
BROKER_HOST = RABBITMQ_HOST
BROKER_PORT = RABBITMQ_PORT
BROKER_VHOST = RABBITMQ_VHOST
BROKER_USER = RABBITMQ_USER
BROKER_PASSWORD = RABBITMQ_PASSWORD



TEMPLATE_CONTEXT_PROCESSORS=("django.contrib.auth.context_processors.auth",
                             "django.core.context_processors.debug",
                             "django.core.context_processors.request",
                             "django.core.context_processors.i18n",
                             "django.core.context_processors.media",
                             "django.core.context_processors.static",
                             "django.contrib.messages.context_processors.messages")

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        ##'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'LOCATION': MEMCACHED_LOCATION,
    }
} 
