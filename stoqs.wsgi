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
WSGIDaemonProcess stoqs user=apache group=root threads=25
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


import sys
import site
import os
import logging

prev_sys_path = list(sys.path)

# Add the site-packages of our virtualenv as a site dir
vepath=os.path.join(os.path.dirname(__file__),'venv-stoqs/lib/python2.6/site-packages')
site.addsitedir(vepath)

# add the app's directory to the PYTHONPATH
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Reorder sys.path so new directories from the addsitedir show up first
new_sys_path = [p for p in sys.path if p not in prev_sys_path]

for item in new_sys_path:
     sys.path.remove(item)

sys.path[:0] = new_sys_path

# Configure logging settings for Apache logs
log_level=logging.DEBUG
logger = logging.getLogger('')
logger.setLevel(log_level)
handler = logging.StreamHandler(sys.stderr)
handler.setLevel(log_level)
formatter = logging.Formatter('%(levelname)-8s %(name)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# import from down here to pull in possible virtualenv django install
from django.core.handlers.wsgi import WSGIHandler
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
os.environ['CELERY_LOADER'] = 'django'
application = WSGIHandler()

