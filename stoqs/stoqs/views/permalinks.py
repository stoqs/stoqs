__author__    = 'Chander Ganesan'
__copyright__ = '2013'
__license__   = 'GPL v3'
__contact__   = 'chander at otg-nc.com'

__doc__ = '''

A set of views designed to generate a permalink based on a set of STOQS query
parameters.

Note that there should be work done at some point to prevent this view from
being misused, by validating the paramters/values passed in, I didn't do this
since I'm not 100% sure of all the use cases for STOQS. However, the danger
right now is that anyone could use this view to store arbitrary json data
in the database - and abuse the services of the provider hosting STOQS (and
even do nasty things like javascript injection things - though such things
won't impact STOQS web services, which only load the json, not run it.)  Enabling
CSRF protection and account login as well would be great ideas and greatly mitigate
the danger here.

@undocumented: __doc__ parser
@status: production
@license: GPL
'''
from django.core.exceptions import ObjectDoesNotExist, SuspiciousOperation
from django.http import Http404
from django.http import HttpResponse
from stoqs.views import BaseOutputer
from stoqs import models
##import matplotlib.pyplot as plt
import logging 
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt
import simplejson as json
from django.core.urlresolvers import reverse
import threading
_thread_local_vars = threading.local()
logger=logging.getLogger(__name__)

@csrf_exempt
def generate_permalink(request):
    data=request.POST.get('parameters')
    if data:
        try:
            # Just make sure it is valid json before storing it.
            parameters=json.loads(data)
            m=models.PermaLink(parameters=data)
            m.save()
            logger.debug('Saved link with id of %s', m.pk)
            url="%s?permalink_id=%s" % (reverse('stoqs-query-ui', 
                                                kwargs={'dbAlias' : 
                                                        request.META['dbAlias']}),
                                                m.pk)
#            url=reverse('redirect_permalink',
#                            kwargs={'dbAlias' : (request.META['dbAlias']),
#                                    'id': m.pk})
        except Exception, e:
            logger.exception('Doh!')
            logger.debug('Attempt to create permalink without valid data')
            raise SuspiciousOperation('Attempt to create permalink without any data, or with invalid data')
    else:
        # In the case where they request a permalink, but without selecting
        # any parameters, we'll just return to them the current URL for the
        # tool, so we don't store unnecessary permalinks
        url=reverse('stoqs-query-ui', 
                    kwargs={'dbAlias' : request.META['dbAlias']})
        
    return HttpResponse(request.build_absolute_uri(url))
    
def load_permalink(request, id):
    logger.debug('Got request for link with ID of %s', id)
    try:
        m=models.PermaLink.objects.get(pk=id)
        m.usage_count = m.usage_count + 1
        m.save()
        # return the JSON for the permalink data
        response=HttpResponse(m.parameters,
                              content_type="application/json")
        return response
    except ObjectDoesNotExist, e:
        logger.debug('Attempted to get a permalink that does not exist: %s', id)
        raise Http404 
