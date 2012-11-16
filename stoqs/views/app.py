__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

Support functions fo the stoqsquery web app.  Most of these will override methods
of classes in views/__init__.py to obtain specialized functionality for use by the 
query view and REST API to the data.

@undocumented: __doc__ parser
@status: production
@license: GPL
'''

from django.http import HttpResponse
from stoqs.views import BaseOutputer
import stoqs.models as mod
##import matplotlib.pyplot as plt
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
            row.append('%.5f' % rec['geom'].x)
            row.append('%.5f' % rec['geom'].y)
            row.append('_ '.join(rec['instantpoint__activity__name'].split('_')[1:5]))
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

class MeasuredParameter(BaseOutputer):
    '''
    Extend basic MeasuredParameter with additional fields that will return data values for many different constraints
    '''
    fields = [ 'parameter__name', 'parameter__standard_name', 'measurement__depth', 'measurement__geom', 'measurement__instantpoint__timevalue',
               'measurement__instantpoint__activity__platform__name', 'datavalue', 'parameter__units' ]


class ResourceActivity(BaseOutputer):
    '''
    Extend basic Resource with additional fields that stitches it up to Activity fields 
    '''
    fields = [ 'name', 'value', 'uristring', 'resourcetype__name', 'activityresource__activity__platform__name', 'activityresource__activity__name' ]


class ActivityParameterHistogram(BaseOutputer):
    '''
    Return combined data for ActivityParameter statistics, including a png image of the histogram and other stats
    '''
    fields = [ 'binlo', 'binhi', 'bincount', 'activityparameter__parameter__name', 'activityparameter__activity__name']

    def process_request(self):
        fields = self.getFields()
        self.assign_qs()
        self.responses.append('.png')
        if self.format == 'png':
            apn = self.request.GET.getlist('activityparameter__parameter__name')[0]
            if apn:
                # Make a plot
                response = HttpResponse()
                response['Content-type'] = 'image/png'
                l = []
                h = []
                w = []
                for obj in self.qs:
                    l.append(obj['binlo'])
                    h.append(obj['bincount'])
                    w.append(obj['binhi'] - obj['binlo'])

                ##plt.bar(l,h,w)
                ##plt.title('Histogram of %s' % apn)
                ##plt.xlabel(apn)
                ##plt.ylabel('Count')
                ##plt.savefig(response)
                ##plt.close()
            else:
                # Return a message
                helpText = 'Please specify an activityparameter__parameter__name' 
                response = HttpResponse(helpText, mimetype="text/plain")
            return response

        return super(ActivityParameterHistogram, self).process_request()


def showActivityParameterHistogram(request, format='png'):
    '''
    By default return a png image of the histogram for the parameter
    '''
    stoqs_object = mod.ActivityParameterHistogram
    query_set = stoqs_object.objects.all().order_by('binlo')

    aph = ActivityParameterHistogram(request, format, query_set, stoqs_object)
    return aph.process_request()

def showMeasuredParameter(request, format = 'json'):
    stoqs_object = mod.MeasuredParameter
    query_set = stoqs_object.objects.all().order_by('measurement__instantpoint__timevalue')

    mp = MeasuredParameter(request, format, query_set, stoqs_object)
    return mp.process_request()

def showResourceActivity(request, format = 'json'):
    stoqs_object = mod.Resource
    query_set = stoqs_object.objects.all().order_by('activityresource__activity__startdate')

    ra = ResourceActivity(request, format, query_set, stoqs_object)
    return ra.process_request()

def showSampleDT(request, format = 'json'):
    stoqs_object = mod.Sample
    query_set = stoqs_object.objects.all().order_by('name')

    s = SampleDataTable(request, format, query_set, stoqs_object)
    return s.process_request()


