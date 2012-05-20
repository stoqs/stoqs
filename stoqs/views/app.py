__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Support functions fo the stoqsquery web app.  Most of these will override methods
of classes in views/__init__.py to obtain specialized functionality for use by the 
query view.

@undocumented: __doc__ parser
@status: production
@license: GPL
'''

from stoqs.views import BaseOutputer
import stoqs.models as mod
import logging 

logger = logging.getLogger(__name__)


class SampleDataTable(BaseOutputer):
    '''
    Add Activity name and Instantpoint timevalue to the default fields
    '''
    fields = [  'uuid', 'depth', 'geom', 'name', 'sampletype__name', 'samplepurpose__name', 
                'volume', 'filterdiameter', 'filterporesize', 'laboratory', 'researcher',
                'instantpoint__timevalue', 'instantpoint__activity__name']

    def assign_qs(self):
        '''
        Assign the processed query string 'qs' with query parameters and fields. May be overridden to restructure response as needed.
        '''
        fields = self.getFields()
        logger.debug(fields)
        self.applyQueryParams(self.ammendFields(fields))
        self.qs = self.query_set
        table = []
        for rec in self.qs.values(*fields):
            row = []
            row.append('%.2f' % rec['depth'])
            row.append(rec['filterdiameter'])
            row.append(rec['filterporesize'])
            row.append(rec['geom'])
            row.append(rec['instantpoint__activity__name'])
            row.append(rec['instantpoint__timevalue'])
            row.append(rec['laboratory'])
            row.append(rec['name'])
            row.append(rec['researcher'])
            row.append(rec['samplepurpose__name'])
            row.append(rec['sampletype__name'])
            row.append(rec['volume'])
            table.append(row)

        self.qs = {'aaData': table}
        logger.debug(self.qs)


def showSampleDT(request, format = 'json'):
    stoqs_object = mod.Sample
    query_set = stoqs_object.objects.all().order_by('name')

    s = SampleDataTable(request, format, query_set, stoqs_object)
    return s.process_request()

