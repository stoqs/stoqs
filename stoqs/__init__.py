import traceback            
from time import time
from django.db.backends import util
from django.utils.log import getLogger

logger = getLogger('django.db.backends')

class PrintQueryWrapper(util.CursorDebugWrapper):
    """Override the django wrapper that surrounds all queries to the database.  This can be quite useful for tracking
    down performance issues.  If settings.DEBUG is False then just the logger output is suspended; the queries
    dictionary is still built.  To prevent this additional overhead from happening set 
        from django.db import connection
        connection.use_debug_cursor = False 
    in your view code.
    """

    def execute(self, sql, params=()):
        start = time()
        try:
            # Add stack trace as comment to sql query
            sql += "-- %s" % ''.join([str(info[0])+'():'+str(info[1])+' <- ' for info in traceback.extract_stack()])
            return self.cursor.execute(sql, params)
        finally:
            stop = time()
            duration = stop - start
            sql = self.db.ops.last_executed_query(self.cursor, sql, params)
            self.db.queries.append({
                'sql': sql,
                'time': "%.3f" % duration,
            })
            logger.debug('(%.3f) %s; args=%s' % (duration, sql, params),
                extra={'duration':duration, 'sql':sql, 'params':params}
            )

from django.conf import settings
logger.info("settings.DEBUG = %s", settings.DEBUG)
if settings.DEBUG:            
	util.CursorDebugWrapper = PrintQueryWrapper
