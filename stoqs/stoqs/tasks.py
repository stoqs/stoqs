#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__credits__ = ["Chander Ganesan, Open Technology Group"]
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

Long-running tasks for STOQS are here.  Run the celery daemon like this:

    python manage.py celeryd -l INFO
    

Mike McCann
MBARI Jan 4, 2012

@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

from celery.task import task
from stoqs import models

@task()
def delete_activity(dbAlias, activity_id):
    activityId = int(activity_id)
    logger = delete_activity.get_logger()
    logger.info('dbAlias = %s', dbAlias)
    
    # Must use using for both get() and delete(), irregardless of what it states at:
    # https://docs.djangoproject.com/en/dev/topics/db/multi-db/#selecting-a-database-to-delete-from
    try:
        activity = models.Activity.objects.using(dbAlias).get(id = activityId)
    except models.Activity.DoesNotExist:
        logger.error("Activity with id = %d in dbAlias = '%s' DoesNotExist", (activityId, dbAlias))
    else:
        activity.delete(using=dbAlias)
    
    return "Deleted Activity with id = %d." % activityId    # Will be output as a logger info message by celeryd

    
