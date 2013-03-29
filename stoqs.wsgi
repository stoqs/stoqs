__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__credits__ = ["Chander Ganesan, Open Technology Group"]
__license__ = "GPL"
__version__ = "$Revision: 12274 $".split()[1]
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

The Apache httpd WSGI configuration for the stoqs application.  This file is to be
referenced where it is installed on the web server in the /etc/httpd/conf.d/stoqs.conf
file.  Example content of stoqs.conf file:

WSGISocketPrefix /var/run/wsgi
WSGIDaemonProcess stoqs user=apache group=root process=1 threads=10 maximum-requests=10 inactivity-timeout=30
WSGIProcessGroup stoqs
WSGIScriptAlias /canon /home/student/dev/stoqsproj/stoqs.wsgi

(Edit last line above for your installation)

Mike McCann
MBARI Jan 5, 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''


import os
import sys
import site

# For some reason the Python 2.6 installation on odss-staging (MBARI's shared dev server) is missing these dirs. 
# These probably cause no harm, but nevertheless if your installation doesn't need them they should be removed.
sys.path.append('/opt/python/lib/python2.6/lib-dynload') 	# to load _functools
sys.path.append('/opt/python/lib/python2.6/dist-packages') 	# cautionary to load django
sys.path.append('/opt/python/lib/python2.6') # to load os

project_path=os.path.dirname(__file__)

# Add the site-packages of our virtualenv as a site dir
vepath=os.path.join(project_path, 'venv-stoqs/lib/python2.6/site-packages')
prev_sys_path=sys.path[:]
site.addsitedir(vepath)
sys.path[:0] = [sys.path.pop(pos) for pos, p in enumerate(sys.path) if p not in prev_sys_path]
del prev_sys_path
print sys.path

# Configure logging settings for Apache logs
import logging
log_level=logging.DEBUG
logger = logging.getLogger('')
logger.setLevel(log_level)
handler = logging.StreamHandler(sys.stderr)
handler.setLevel(log_level)
formatter = logging.Formatter('%(levelname)-8s %(name)s %(funcName)s():%(lineno)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


# Avoid ``[Errno 13] Permission denied: '/var/www/.python-eggs'`` messages
os.environ['PYTHON_EGG_CACHE'] =  os.path.join(project_path, 'egg-cache')
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
os.environ['CELERY_LOADER'] = 'django'

# add the app's directory to the PYTHONPATH
sys.path.append(project_path)

# import from down here to pull in possible virtualenv django install
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()



# Don't uncomment this line, it masks print statements that shouldn't be in code to start with.
#sys.stdout = sys.stderr  

# Add the virtual Python environment site-packages directory to the path
wsgi_dir=os.path.dirname(__file__)
project_dir=os.path.dirname(wsgi_dir) # Find the project directory



# Set up the virtualenv components.
venv_dir=os.path.join(project_dir, 'venv/lib/python2.6/site-packages')
prev_sys_path=sys.path[:]
site.addsitedir(venv_dir)
sys.path[:0] = [sys.path.pop(pos) for pos, p in enumerate(sys.path) if p not in prev_sys_path]



