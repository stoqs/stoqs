'''
Automatically route requests to the proper database and named in the first
parameter parsed from the request url.

Mike McCann
MBARI Jan 3, 2012
'''

import logging
import threading
from django.conf import settings
from django.db.utils import ConnectionDoesNotExist
from django.http import HttpResponseBadRequest

logger = logging.getLogger(__name__)
_thread_local_vars = threading.local()


class RouterMiddleware(object):

    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    def process_view(self, request, view_func, pargs, kwargs):
        logger.debug(f'pargs = {pargs}')
        logger.debug(f'kwargs = {kwargs}')

        if 'dbAlias' in kwargs:
            if kwargs['dbAlias'] not in settings.DATABASES.keys():
                return HttpResponseBadRequest('Bad request: Database "' + kwargs['dbAlias'] + '" Does Not Exist in settings.DATABASES')

            # Add a thread local variable, and remove the dbAlias, since it's handled by the middleware.
            _thread_local_vars.dbAlias = kwargs.pop('dbAlias')
            # If 'stoqs' is used make it 'default', for every other dbAlias the convention is that
            # the Django alias is the same as the database name. (Need to standardize on using alias...)
            if _thread_local_vars.dbAlias == 'stoqs':
                _thread_local_vars.dbAlias = 'default'
            
            logger.debug("_thread_local_vars.dbAlias = %s", _thread_local_vars.dbAlias)
            # Add as a META tag for those views that wish to use the dbAlias
            
            request.META['dbAlias'] = _thread_local_vars.dbAlias

        # See http://dustinfarris.com/2012/2/sharing-django-users-and-sessions-across-projects/
        if request.path.startswith('/admin'):
            _thread_local_vars.admin = True

        return view_func(request, *pargs, **kwargs)
    
    def process_response(self, _, response):
        # Get rid of the thread local variable, since it isn't needed anymore.
        if hasattr(_thread_local_vars, 'dbAlias'):
            del _thread_local_vars.dbAlias
        if hasattr(_thread_local_vars, 'admin'):
            del(_thread_local_vars.admin)
        return response



class DatabaseRouter(object):
    def _default_db( self ):
        from django.conf import settings
        logger.debug('_thread_local_vars = %s', _thread_local_vars)
        logger.debug('settings.DATABASES = %s', settings.DATABASES)
        if hasattr( _thread_local_vars, 'dbAlias' ) and _thread_local_vars.dbAlias in settings.DATABASES:
            logger.debug("DatabaseRouter: Returning dbAlias = %s", _thread_local_vars.dbAlias)
            return _thread_local_vars.dbAlias
        else:
            logger.debug("DatabaseRouter: Returning default")
            return 'default'
    def db_for_read(self, _, **kwargs):
        return self._default_db()
    
    def db_for_write(self, _, **kwargs):
        return self._default_db()
        
    def allow_relation(self, obj1, obj2 ,**kwargs):
        if obj1._meta.app_label ==  'stoqs' or obj2._meta.app_label == 'stoqs':
            return True
        return None

