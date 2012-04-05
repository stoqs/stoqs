import sys
import os.path, os
#
# The following are required to ensure that the GeoDjango models can be loaded up.
#
os.environ['DJANGO_SETTINGS_MODULE']='settings'
sys.path.insert(0, os.path.abspath('..'))
