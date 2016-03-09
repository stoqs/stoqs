'''
A views designed to provide information on a Parameter from the UI
Supports both Sampled Parameter and Measured Parameter.  Provide
linkage to vocabulary URIs if they exist...
'''

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.http import HttpResponse
from stoqs.models import Parameter, ParameterResource
import logging 
import simplejson as json
import threading

_thread_local_vars = threading.local()
logger=logging.getLogger(__name__)

def parameterinfo(request, pid):
    logger.info('Got request %r for Parameter with ID of %s', request, pid)
    db_alias = request.META.get('dbAlias')
    p = Parameter.objects.using(db_alias).get(pk=pid)
    pr = ParameterResource.objects.using(db_alias).filter(parameter=p).values('resource__name', 'resource__value')
    response = HttpResponse(p.description, content_type="application/json")
    return response
