__author__    = 'Mike McCann'
__copyright__ = '2011'
__license__   = 'GPL v3'
__contact__   = 'mccann at mbari.org'

__doc__ = '''

The view functions for the stoqsdb_* database web app.  These functions are called after successful matching
from the patterns in urls.py.  They query the database and format the output for the response.

Most responses return the positions in time order.  The exceptions are if the 'last' option is specified, or
if 'stride' is specified.  In these cases the results are returned in reverse time order so as to always return
the most recent position reports.

This web app derives from the MBARItracking web app.  I addition to delivering platform names, types, and
positions, it also delivers measured_paramaters based on various common query criteria.

@undocumented: __doc__ parser
@status: production
@license: GPL
'''

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse
from django.conf import settings
from django.db import connection
from django.utils import simplejson
from django.core import serializers

from datetime import datetime, timedelta
import time
import stoqs.models as mod
import csv
import sys
import logging 
import os

logger = logging.getLogger(__name__)

def generateMapFile(request, dbName, activity_list, mappath):
	'''Build mapfile for activity from template.  Write it to a location that mapserver can see it.'''

	response = render_to_response('activity.map', {'mapserver_host': 'odss-staging.shore.mbari.org',
							'DS': settings,
							'activity_list': activity_list,
							'wfs_title': 'WFS title for an Activity',
							'dbname': dbName,
							'mappath': mappath,
							'r': 200,
							'g': 100,
							'b': 99 },
				         		context_instance = RequestContext(request))
	# Note that an HttpResponse (what you get back from render_to_response) can be treated as a generator.
	fh = open(mappath, 'w')	
	for line in response:
		fh.write(line) 


def showActivitiesWMS(request):
	'''Render Activities as WMS via mapserver'''

	# You'd likely choose a "better" location than "/tmp", but as long as the file is someplace mapserver can read from, you're all set!
	mappathBase = '/tmp'

	if request.META['dbName'] == 'default':
		dbName = 'stoqs'
	else:
		dbName = request.META['dbName']

	aList = mod.Activity.objects.all().order_by('startdate')  
	mappath = os.path.join(mappathBase, 'activity.map')
	generateMapFile(request, dbName, aList, mappath)

	return render_to_response('activity_mapserver.html', {'mapserver_host': 'odss-staging.shore.mbari.org', 
								'activity_list': aList,
								'dbName': dbName,
								'mappath': mappath})

	# End showActivities()


def showPlatformTypes(request, format = 'html'):
	ptList = mod.PlatformType.objects.all().order_by('name')
	if format == 'csv':
		response = HttpResponse(mimetype='text/csv')
		response['Content-Disposition'] = 'attachment; filename=platformTypes.csv'
		writer = csv.writer(response)

		writer.writerow(['PlatformType'])
		for pt in ptList:
			writer.writerow([pt.name.rstrip()])
		return response
	else:
		return render_to_response('platformType.html', {'ptype_list': ptList})


def showPlatformNames(request, format = 'html'):
	pList = mod.Platform.objects.using('default').all().order_by('name')
	if format == 'csv':
		response = HttpResponse(mimetype='text/csv')
		response['Content-Disposition'] = 'attachment; filename=platformNames.csv'
		writer = csv.writer(response)

		writer.writerow(['PlatformName'])
		for p in pList:
			writer.writerow([p.name])
		return response
		
	else:
		return render_to_response('platformName.html', {'p_list': pList})


def showPlatformNamesOfType(request, ptn, format = 'html'):
	pList = mod.Platform.objects.filter(platformtype__name = ptn).order_by('name')
	return render_to_response('platformNamesOfType.html', {'p_list': pList, 'type': ptn})


def showParameters(request, format = 'html'):
	pList = mod.Parameter.objects.all().order_by('name')
	logger.debug("format = %s", format)
	if format == 'csv':
		response = HttpResponse(mimetype='text/csv')
		response['Content-Disposition'] = 'attachment; filename=parameters.csv'
		writer = csv.writer(response)

		writer.writerow(['id', 'name', 'type', 'description', 'standard_name', 'long_name', 'units', 'origin'])
		writer.writerows(pList)
		return response
	elif format == 'xml':
		return HttpResponse(serializers.serialize('xml', pList), 'application/xml')
	elif format == 'json':
		return HttpResponse(serializers.serialize('json', pList), 'application/json')
	else:
		return render_to_response('parameters.html', {'p_list': pList})


def showPlatformAssociations(request, format = 'html'):
	ptList = mod.PlatformType.objects.all().order_by('-name')
	csvList = []
	pptList = []
	for pt in ptList:
		pList = mod.Platform.objects.filter(platformtype__name = pt.name).order_by('name')
		csvList.extend([ "%s,%s" % (pt.name, p.name) for p in pList ])
		pptList.extend([ (pt.name, p.name) for p in pList ])

	if format == 'csv':
		response = HttpResponse(mimetype='text/csv')
		response['Content-Disposition'] = 'attachment; filename=platformAssociations.csv'
		writer = csv.writer(response)

		writer.writerow(['PlatformType', 'PlatformName'])
		for ppt in pptList:
			writer.writerow([ppt[0], ppt[1]])
		return response
	else:
		return render_to_response('platformAssociations.html', {'ppt_list': pptList})

# The show...() functions started off simple, but then I added options of 'ofType' and 'countFlag' and wished to
# reuse the query and output format functionality and the logic in the functions became more complicated.  Perhaps
# there is a better way to factor out functionality, but that will probably wait for another project.

def showLastPositions(request, name, number, unit = '', stride = '1', format = 'html', ofType = False, countFlag = False):
	'''Return last number of positions or as specified with optional time units'''
	num = int(number)
	if unit:
		'''Query looking back a specifice time'''
		if unit == 's': sDate = datetime.now() - timedelta(seconds = num)
		elif unit == 'm': sDate = datetime.now() - timedelta(minutes = num)
		elif unit == 'h': sDate = datetime.now() - timedelta(hours = num)
		elif unit == 'd': sDate = datetime.now() - timedelta(days = num)
		elif unit == 'w': sDate = datetime.now() - timedelta(weeks = num)
		else:
			return HttpResponseBadRequest()
		posList = []
		if ofType:
			'''Build a list of positions of platforms based on the list of platformTypes that match the PT name.'''
			count = 0
			plList = mod.Platform.objects.filter(platformtype__name = name).order_by('name')
			for pl in plList:
				if countFlag:
					count = count + mod.Measurement.objects.filter(instantpoint__activity__platform__name = 
							pl.name).filter(instantpoint__timevalue__gte = sDate).count()
				else:
					mList = mod.Measurement.objects.filter(instantpoint__activity__platform__name = 
							pl.name).filter(instantpoint__timevalue__gte = sDate)[::-int(stride)]
					posList.extend([ (pl.name, time.mktime(m.instantpoint.timevalue.timetuple()), 
							'%.6f' % m.geom.x, '%.6f' % m.geom.y, '%.1f' % m.depth,
							m.instantpoint.timevalue.strftime('%Y-%m-%dT%H:%M:%SZ')) for m in mList ])

		else:
			if countFlag: 
				count = mod.Measurement.objects.filter(instantpoint__activity__platform__name = 
						name).filter(instantpoint__timevalue__gte = sDate).count()
			else:
				mList = mod.Measurement.objects.filter(instantpoint__activity__platform__name = 
						name).filter(instantpoint__timevalue__gte = sDate)[::-int(stride)]
				posList.extend([ (name, time.mktime(m.instantpoint.timevalue.timetuple()), 
							'%.6f' % m.geom.x, '%.6f' % m.geom.y, '%.1f' % m.depth,
								m.instantpoint.timevalue.strftime('%Y-%m-%dT%H:%M:%SZ')) for m in mList ])
	else:
		'''Query looking back a number of items.  Return the result in reverse time order.  Do not negate stride.'''
		posList = []
		if ofType:
			'''Build a list of positions of platforms based on the list of platformTypes that match the PT name.'''
			count = 0
			plList = mod.Platform.objects.filter(platformtype__name = name).order_by('name')
			for pl in plList:
				mList = mod.Measurement.objects.filter(instantpoint__activity__platform__name = 
						pl.name).order_by('-instantpoint__timevalue')[:num:int(stride)]
				if countFlag:
					count = count + len(mList)
				else:
					posList.extend([ (pl.name, time.mktime(m.instantpoint.timevalue.timetuple()), 
							'%.6f' % m.geom.x, '%.6f' % m.geom.y, '%.1f' % m.depth,
							m.instantpoint.timevalue.strftime('%Y-%m-%dT%H:%M:%SZ')) for m in mList ])

		else:
			mList = mod.Measurement.objects.filter(instantpoint__activity__platform__name = 
						name).order_by('-instantpoint__timevalue')[:num:int(stride)]
			if countFlag: 
				count = len(mList)	# .count() does not work after a '[:num:-int(stride)]'
			else:
				posList.extend([ (name, time.mktime(m.instantpoint.timevalue.timetuple()), 
							'%.6f' % m.geom.x, '%.6f' % m.geom.y, '%.1f' % m.depth,
							m.instantpoint.timevalue.strftime('%Y-%m-%dT%H:%M:%SZ')) for m in mList ])

	if countFlag:
		response = HttpResponse("%d" % count, mimetype="text/plain")
		return response

	if format == 'csv':
		response = HttpResponse(mimetype='text/csv')
		response['Content-Disposition'] = 'attachment; filename=positionData_%s_last%s.csv' % (name, number + unit)
		writer = csv.writer(response)
		writer.writerow(['platformName', 'epochSeconds', 'longitude', 'latitude', 'isoformat'])
		writer.writerows(posList)
		return response
	else:
		return render_to_response('position.html', {'pList': posList})


def showSincePositions(request, name, startDate, stride = '1', format = 'html', ofType = False, countFlag = False):
	'''Return data in specified format from ISO8601 formatted startDate.  (There are no '-'s or ':'s in startDate -- they're not URL firendly.)
	'''
	
	sDate = datetime(*time.strptime(startDate, '%Y%m%dT%H%M%S')[:6])
	posList = []
	if ofType:
		'''Build a list of positions of platforms based on the list of platformTypes that match the PT name.'''
		count = 0
		plList = mod.Platform.objects.filter(platformtype__name = name).order_by('name')
		for pl in plList:
			if countFlag:
				count = count + mod.Measurement.objects.filter(instantpoint__activity__platform__name = 
						pl.name).filter(instantpoint__timevalue__gte = sDate).count()
			else:
				mList = mod.Measurement.objects.filter(instantpoint__activity__platform__name = 
						pl.name).filter(instantpoint__timevalue__gte = sDate).order_by('instantpoint__timevalue')[::-int(stride)]
				posList.extend([ (pl.name, time.mktime(m.instantpoint.timevalue.timetuple()), 
						'%.6f' % m.geom.x, '%.6f' % m.geom.y, '%.1f' % m.depth,
							m.instantpoint.timevalue.strftime('%Y-%m-%dT%H:%M:%SZ')) for m in mList ])
	else:
		if countFlag:
			count = mod.Measurement.objects.filter(instantpoint__activity__platform__name = 
					name).filter(instantpoint__timevalue__gte = sDate).count()
		else:
			mList = mod.Measurement.objects.filter(instantpoint__activity__platform__name = 
					name).filter(instantpoint__timevalue__gte = sDate).order_by('instantpoint__timevalue')[::-int(stride)]
			posList.extend([ (name, time.mktime(m.instantpoint.timevalue.timetuple()), 
						'%.6f' % m.geom.x, '%.6f' % m.geom.y, '%.1f' % m.depth,
						m.instantpoint.timevalue.strftime('%Y-%m-%dT%H:%M:%SZ')) for m in mList ])

	if countFlag:
		response = HttpResponse("%d" % count, mimetype="text/plain")
		return response

	'''Deliver the response to the client of the data in the posList '''
	if format == 'csv':
		response = HttpResponse(mimetype='text/csv')
		response['Content-Disposition'] = 'attachment; filename=positionData_%s_since%s.csv' % (name, startDate)
		writer = csv.writer(response)
		writer.writerow(['platformName', 'epochSeconds', 'longitude', 'latitude', 'isoformat'])
		writer.writerows(posList)
		return response

	elif format == 'kml':
		return render_to_response('position.kml', {'pList': posList}, mimetype="application/vnd.google-earth.kml+xml")
	else:
		'Default: render as html'
		return render_to_response('position.html', {'pList': posList})
	

def showBetweenPositions(request, name, startDate, endDate, stride = '1', format = 'html', ofType = False, countFlag = False):
	'''Return data in specified format from ISO8601 formatted startDate and endDate.  (There are no '-'s or ':'s in startDate -- they're not URL firendly.)
	The negative stride returns the positions in reverse time order.
	'''
	
	sDate = datetime(*time.strptime(startDate, '%Y%m%dT%H%M%S')[:6])
	eDate = datetime(*time.strptime(endDate, '%Y%m%dT%H%M%S')[:6])

	posList = []
	if ofType:
		'''Build a list of positions of platforms based on the list of platformTypes that match the PT name.'''
		count = 0
		plList = mod.Platform.objects.filter(platformtype__name = name).order_by('name')
		for pl in plList:
			if countFlag:
				count = count + mod.Measurement.objects.filter(instantpoint__activity__platform__name = 
						pl.name).filter(instantpoint__timevalue__gte = sDate, instantpoint__timevalue__lte = eDate).count()
			else:
				mList = mod.Measurement.objects.filter(instantpoint__activity__platform__name = 
						pl.name).filter(instantpoint__timevalue__gte = sDate, instantpoint__timevalue__lte = 
						eDate).order_by('instantpoint__timevalue')[::-int(stride)]
				posList.extend([ (pl.name, time.mktime(m.instantpoint.timevalue.timetuple()), 
							'%.6f' % m.geom.x, '%.6f' % m.geom.y, '%.1f' % m.depth,
							m.instantpoint.timevalue.strftime('%Y-%m-%dT%H:%M:%SZ')) for m in mList ])
	else:
		if countFlag:
			count = mod.Measurement.objects.filter(instantpoint__activity__platform__name = name).filter(instantpoint__timevalue__gte = sDate, 
						instantpoint__timevalue__lte = eDate).count()
		else:
			mList = mod.Measurement.objects.filter(instantpoint__activity__platform__name = name).filter(instantpoint__timevalue__gte = sDate, 
						instantpoint__timevalue__lte = eDate).order_by('instantpoint__timevalue')[::-int(stride)]
			posList.extend([ (name, time.mktime(m.instantpoint.timevalue.timetuple()), 
							'%.6f' % m.geom.x, '%.6f' % m.geom.y, '%.1f' % m.depth,
							m.instantpoint.timevalue.strftime('%Y-%m-%dT%H:%M:%SZ')) for m in mList ])

	if countFlag:
		response = HttpResponse("%d" % count, mimetype="text/plain")
		return response

	'''Deliver the response to the client of the data in the posList '''
	if format == 'csv':
		response = HttpResponse(mimetype='text/csv')
		response['Content-Disposition'] = 'attachment; filename=positionData_%s_between%s_%s.csv' % (name, startDate, endDate)
		writer = csv.writer(response)
		writer.writerow(['platformName', 'epochSeconds', 'longitude', 'latitude', 'isoformat'])
		writer.writerows(posList)
		return response

	elif format == 'kml':
		return render_to_response('position.kml', {'pList': posList}, mimetype="application/vnd.google-earth.kml+xml")
	else:
		'Default: render as html'
		return render_to_response('position.html', {'pList': posList})

	# End showBetweenPositions()	


def showPositionsOfActivity(request, aName, aType, stride = '1', format = 'html', countFlag = False):
	'''Return position in specified format that belong to the specified Activity name/type.
	'''

	posList = []
	qs = mod.Measurement.objects.filter(instantpoint__activity__name = aName,
                                               instantpoint__activity__activitytype__name = aType)
	if countFlag:
		count = qs.count()
	else:
		mList = qs.order_by('instantpoint__timevalue')[::-int(stride)]
		posList.extend([ (aName, time.mktime(m.instantpoint.timevalue.timetuple()), 
							'%.6f' % m.geom.x, '%.6f' % m.geom.y, '%.1f' % m.depth,
							m.instantpoint.timevalue.strftime('%Y-%m-%dT%H:%M:%SZ')) for m in mList ])

	if countFlag:
		response = HttpResponse("%d" % count, mimetype="text/plain")
		return response

	'''Deliver the response to the client of the data in the posList '''
	if format == 'csv':
		response = HttpResponse(mimetype='text/csv')
		response['Content-Disposition'] = 'attachment; filename=positionOfActivity_%s_%s.csv' % (aName, aType)
		writer = csv.writer(response)
		writer.writerow(['activityName', 'epochSeconds', 'longitude', 'latitude', 'isoformat'])
		writer.writerows(posList)
		return response

	elif format == 'kml':
		return render_to_response('position.kml', {'pList': posList}, mimetype="application/vnd.google-earth.kml+xml")
	else:
		'Default: render as html'
		return render_to_response('position.html', {'pList': posList})

	# End showPositionsOfActivity()	

