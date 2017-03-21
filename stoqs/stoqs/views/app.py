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
from stoqs.views import BaseOutputer, EmptyQuerySetException
import stoqs.models as mod
##import matplotlib.pyplot as plt
import logging 
from django.shortcuts import render
from django.template import RequestContext
from django.views.decorators.cache import cache_page

logger = logging.getLogger(__name__)


class SampleDataTable(BaseOutputer):
    '''
    Add Activity name and Instantpoint timevalue to the default fields
    '''
    fields = [  'uuid', 'depth', 'geom', 'name', 'sampletype__name', 'samplepurpose__name', 
                'volume', 'filterdiameter', 'filterporesize', 'laboratory', 'researcher',
                'instantpoint__timevalue', 'instantpoint__activity__name',
                'instantpoint__id', 'sampledparameter__parameter__name', 'sampledparameter__datavalue']

    def assign_qs(self):
        '''
        Assign the processed query string 'qs' with query parameters and fields. May be overridden to restructure response as needed.
        '''
        if not self.query_set:
            raise EmptyQuerySetException()

        fields = self.getFields()
        logger.debug(fields)
        self.applyQueryParams(self.ammendFields(fields))
        self.qs = self.query_set
      
        pNameList = [] 

        table = []
        for rec in self.qs.values(*fields):
            row = []
            # Get Measured parameters for this sample, they will be the same for all the recs, so get them just once
            if not table:
                mpDict = {}
                for mp in mod.MeasuredParameter.objects.filter(measurement__instantpoint__id=rec['instantpoint__id']):
                    logger.debug('parameter name = %s, value = %f', mp.parameter.name, mp.datavalue)
                    pName = mp.parameter.name.replace('_', '_ ')
                    pNameList.append(pName)
                    mpDict[pName] = mp.datavalue
          
            for k in pNameList: 
                row.append('%f' % mpDict[k]) 

            row.append('%.2f' % rec['depth'])
            row.append(rec['filterdiameter'])
            row.append(rec['filterporesize'])
            row.append('%.5f' % rec['geom'].x)
            row.append('%.5f' % rec['geom'].y)
            row.append(rec['instantpoint__activity__name'].replace('_', '_ '))
            row.append(rec['instantpoint__timevalue'])
            row.append(rec['laboratory'])
            row.append(rec['name'])
            row.append(rec['researcher'])
            row.append(rec['samplepurpose__name'])
            row.append(rec['sampletype__name'])
            row.append(rec['volume'])
            row.append(rec['sampledparameter__parameter__name'])
            row.append('%s' % rec['sampledparameter__datavalue'])
            table.append(row)
        
        colList = []
        for k in pNameList: 
            colList.append({'sTitle': k})

        colList.extend( [{'sTitle': 'depth'}, {'sTitle': 'filter diam'}, {'sTitle': 'filter pore size'}, 
                         {'sTitle': 'lon'}, {'sTitle': 'lat'}, {'sTitle': 'activity name'}, {'sTitle': 'time'}, 
                         {'sTitle': 'lab'}, {'sTitle': 'sample name'}, {'sTitle': 'res.'}, {'sTitle': 'purpose'}, 
                         {'sTitle': 'type'}, {'sTitle': 'volume'}, {'sTitle': 'parameter name'}, {'sTitle': 'data value'}] )

        # Format complete JSON for jQuery DataTables, see: http://stackoverflow.com/questions/8665309/jquery-datatables-get-columns-from-json
        logger.debug('len(colList) = %d', len(colList))
        logger.debug('len(row) = %d', len(row))
        self.qs = {'aaData': table, 'aoColumns': colList}
        logger.debug(self.qs)

class MeasuredParameter(BaseOutputer):
    '''
    Extend basic MeasuredParameter with additional fields that will return data values for many different constraints
    '''
    # Only fields that exists in the model can be included here.  Use '.x' and '.y' on measurement__geom to get latitude and longitude.
    fields = [ 'parameter__id', 'parameter__name', 'parameter__standard_name', 'measurement__depth', 'measurement__geom', 
               'measurement__instantpoint__timevalue',  'measurement__instantpoint__activity__name',
               'measurement__instantpoint__activity__platform__name', 'datavalue', 'parameter__units' ]


class SampledParameter(BaseOutputer):
    '''
    Extend basic SampledParameter with additional fields that will return data values for many different constraints
    '''
    # Only fields that exists in the model can be included here.  Use '.x' and '.y' on sample__geom to get latitude and longitude.
    fields = [ 'parameter__id', 'parameter__name', 'parameter__standard_name', 'sample__depth', 'sample__geom', 
               'sample__instantpoint__timevalue',  'sample__instantpoint__activity__name', 'sample__name',
               'sample__instantpoint__activity__platform__name', 'datavalue', 'parameter__units' ]


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


def showActivityParameterHistogram(request, fmt='png'):
    '''
    By default return a png image of the histogram for the parameter
    '''
    stoqs_object = mod.ActivityParameterHistogram
    query_set = stoqs_object.objects.all().order_by('binlo')

    aph = ActivityParameterHistogram(request, fmt, query_set, stoqs_object)
    return aph.process_request()

# Cache responses from this view for 15 minutes
@cache_page(60 * 15)
def showMeasuredParameter(request, fmt='json'):
    stoqs_object = mod.MeasuredParameter
    query_set = stoqs_object.objects.all().order_by('measurement__instantpoint__timevalue')

    mp = MeasuredParameter(request, fmt, query_set, stoqs_object)
    return mp.process_request()

def showSampledParameter(request, fmt='json'):
    stoqs_object = mod.SampledParameter
    query_set = stoqs_object.objects.all().order_by('sample__instantpoint__timevalue')

    sp = SampledParameter(request, fmt, query_set, stoqs_object)
    return sp.process_request()

def showResourceActivity(request, fmt='json'):
    stoqs_object = mod.Resource
    query_set = stoqs_object.objects.all().order_by('activityresource__activity__startdate')

    ra = ResourceActivity(request, fmt, query_set, stoqs_object)
    return ra.process_request()

def showQuickLookPlots(request):
    stoqs_object = mod.Resource
    query_set = stoqs_object.objects.filter(resourcetype__name='quick_look').order_by('name')

    ra = ResourceActivity(request, fmt, query_set, stoqs_object)
    ra.assign_qs()

    activityName = ''
    try:
        activityName = ra.request.GET.getlist('activityresource__activity__name__contains')[0]
    except:
        pass

    return render(request, 'quicklookplots.html', context={'activity': activityName, 'images': ra.qs})

def showSampleDT(request, fmt='json'):
    stoqs_object = mod.Sample
    query_set = stoqs_object.objects.all().order_by('name')

    s = SampleDataTable(request, fmt, query_set, stoqs_object)
    return s.process_request()


