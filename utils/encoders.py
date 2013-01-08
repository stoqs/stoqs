from django.utils import simplejson
from decimal import Decimal
import datetime
import logging

logger = logging.getLogger(__name__)
 
class STOQSJSONEncoder(simplejson.JSONEncoder):
    def default(self, object_to_encode):
        '''
        Convert Decimal object to something we can serialize
        '''
        ##logger.debug('type(object_to_encode) = %s', type(object_to_encode))
        if isinstance(object_to_encode, Decimal):
            return object_to_encode.to_eng_string()

        elif isinstance(object_to_encode, datetime.datetime):
            return object_to_encode.isoformat()

        else:
            try:
                iterable = iter(object_to_encode)
            except TypeError:
                pass
            else:
                return list(iterable)

        return simplejson.JSONEncoder.default(self, object_to_encode)
