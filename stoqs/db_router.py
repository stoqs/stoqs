#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__credits__ = ["Chander Ganesan, Open Technology Group"]
__license__ = "GPL"
__version__ = "$Revision: 12293 $".split()[1]
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

Automatically route requests to the proper database and named in the first
parameter parsed from the request url.

Mike McCann
MBARI Jan 3, 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

import logging

logger = logging.getLogger(__name__)

import threading
_thread_local_vars = threading.local()

class RouterMiddleware(object):
    def process_view(self, request, view_func, pargs, kwargs):
        logger.debug("pargs =")
        logger.debug(pargs)
        logger.debug("kwargs =")
        logger.debug(kwargs)
        if kwargs.has_key('dbName'):
            # Add a thread local variable, and remove the dbName, since it's handled by the middleware.
            _thread_local_vars.dbName = kwargs.pop('dbName')
            # If 'stoqs' is used make it 'default', for every other dbName the convention is that
            # the Django alias is the same as the database name.
            if _thread_local_vars.dbName == 'stoqs':
                _thread_local_vars.dbName = 'default'
            
            logger.debug("_thread_local_vars.dbName = " + _thread_local_vars.dbName)
            # Add as a META tag for those views that wish to use the dbName
            
            request.META['dbName'] = _thread_local_vars.dbName
        return view_func(request, *pargs, **kwargs)
    
    def process_response(self, request, response):
        # Get rid of the thread local variable, since it isn't needed anymore.
        if hasattr(_thread_local_vars, 'dbName'):
            del _thread_local_vars.dbName
        return response



class DatabaseRouter(object):
    def _default_db( self ):
        from django.conf import settings
        if hasattr( _thread_local_vars, 'dbName' ) and _thread_local_vars.dbName in settings.DATABASES:
            logger.debug("DatabaseRouter: Returning dbName = " + _thread_local_vars.dbName)
            return _thread_local_vars.dbName
        else:
            logger.debug("DatabaseRouter: Returning default")
            return 'default'
    def db_for_read( self, model, **hints ):
        return self._default_db()
    
    def db_for_write( self, model, **hints ):
        return self._default_db()
        
    def allow_relation(self, obj1, obj2 ,**hints):
        if obj1._meta.app_label ==  'stoqs' or obj2._meta.app_label == 'stoqs':
            return True
        return None
