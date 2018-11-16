'''
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
'''

from django.core.exceptions import ObjectDoesNotExist, SuspiciousOperation
from django.http import Http404
from django.http import HttpResponse
from stoqs import models
import logging 
from django.views.decorators.csrf import csrf_exempt
import simplejson as json
from django.urls import reverse
import threading
_thread_local_vars = threading.local()
logger=logging.getLogger(__name__)

# Set client_side_permalink = false; in stoqsquery.html to use these functions
@csrf_exempt
def generate_permalink(request):
    data=request.POST.get('parameters')
    if data:
        try:
            # Just make sure it is valid json before storing it.
            json.loads(data)
            m=models.PermaLink(parameters=data)
            m.save()
            logger.debug('Saved link with id of %s', m.pk)
            url="%s?permalink_id=%s" % (reverse('stoqs:stoqs-query-ui', 
                                                kwargs={'dbAlias' : 
                                                        request.META['dbAlias']}),
                                                m.pk)
#            url=reverse('redirect_permalink',
#                            kwargs={'dbAlias' : (request.META['dbAlias']),
#                                    'id': m.pk})
        except Exception:
            logger.exception('Doh!')
            logger.debug('Attempt to create permalink without valid data')
            raise SuspiciousOperation('Attempt to create permalink without any data, or with invalid data')
    else:
        # In the case where they request a permalink, but without selecting
        # any parameters, we'll just return to them the current URL for the
        # tool, so we don't store unnecessary permalinks
        url=reverse('stoqs:stoqs-query-ui', 
                    kwargs={'dbAlias' : request.META['dbAlias']})
        
    return HttpResponse(request.build_absolute_uri(url))
    
def load_permalink(request, pid):
    logger.debug('Got request %r for link with ID of %s', request, pid)
    try:
        m=models.PermaLink.objects.get(pk=pid)
        m.usage_count = m.usage_count + 1
        m.save()
        # return the JSON for the permalink data
        response=HttpResponse(m.parameters,
                              content_type="application/json")
        return response
    except ObjectDoesNotExist:
        logger.debug('Attempted to get a permalink that does not exist: %s', pid)
        raise Http404 
