#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__credits__ = ["Chander Ganesan, Open Technology Group"]
__license__ = "GPL"
__version__ = "$Revision: 12197 $".split()[1]
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

<replace with short module description>

Mike McCann
MBARI Jan 3, 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''


from stoqs import custom_admin as admin
from stoqs import models

class ActivityAdmin(admin.OSMGeoAdmin):
    list_display=('platform', 'activitytype', 'comment')


admin.site.register(models.Activity, ActivityAdmin)


