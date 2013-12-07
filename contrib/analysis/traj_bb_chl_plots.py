#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2013, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

Script to query the database for measured parameters from the same instantpoint and to
make scatter plots of temporal segments of the data.  A simplified trackline of the
trajectory data and the start time of the temporal segment are added to each plot.

Make use of STOQS metadata to make it as simple as possible to use this script for
different platforms, parameters, and campaigns.

Mike McCann
MBARI Dec 6, 2013

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE']='settings'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))  # settings.py is one dir up

import matplotlib.pyplot as plt
from django.db import connections
from datetime import datetime, timedelta
from stoqs.models import Activity, ActivityParameter, ParameterResource, Platform
from django.contrib.gis.geos import LineString, Point
from django.db.models import Max, Min
from utils.utils import round_to_n

# Change these options
dbAlias = 'stoqs_september2013_t'
pName = 'tethys'
xParmName = 'bb470'
yParmName = 'chlorophyll'
#pName = 'dorado'
#xParmName = 'bbp420'
#yParmName = 'fl700_uncorr'
timeInterval = timedelta(hours=12)

# Should not need to change anything below
# ----------------------------------------

# SQL template copied from STOQS UI Parameter-Parameter -> sql tab
sql_template = '''SELECT DISTINCT stoqs_measurement.depth,
                mp_x.datavalue AS x, mp_y.datavalue AS y,
                ST_X(stoqs_measurement.geom) AS lon, ST_Y(stoqs_measurement.geom) AS lat,
                stoqs_instantpoint.timevalue 
FROM stoqs_activity
INNER JOIN stoqs_platform ON stoqs_platform.id = stoqs_activity.platform_id
INNER JOIN stoqs_instantpoint ON stoqs_instantpoint.activity_id = stoqs_activity.id
INNER JOIN stoqs_measurement ON stoqs_measurement.instantpoint_id = stoqs_instantpoint.id
INNER JOIN stoqs_measurement m_y ON m_y.instantpoint_id = stoqs_instantpoint.id
INNER JOIN stoqs_measuredparameter mp_y ON mp_y.measurement_id = m_y.id
INNER JOIN stoqs_parameter p_y ON mp_y.parameter_id = p_y.id
INNER JOIN stoqs_measurement m_x ON m_x.instantpoint_id = stoqs_instantpoint.id
INNER JOIN stoqs_measuredparameter mp_x ON mp_x.measurement_id = m_x.id
INNER JOIN stoqs_parameter p_x ON mp_x.parameter_id = p_x.id
WHERE (p_x.name = '{pxname}')
  AND (p_y.name = '{pyname}')
  AND (stoqs_instantpoint.timevalue >= '{start}'
       AND stoqs_instantpoint.timevalue <= '{end}')
  AND stoqs_platform.name IN ('{platform}')
ORDER BY stoqs_instantpoint.timevalue '''

# Get connection to database; dbAlias must be defined in privateSettings
cursor = connections[dbAlias].cursor()

# Get start and end datetimes, color and geographic extent of the activity
aQS = Activity.objects.using(dbAlias).filter(platform__name=pName)
seaQS = aQS.aggregate(Min('startdate'), Max('enddate'))
aStart, aEnd = (seaQS['startdate__min'], seaQS['enddate__max'])
color = '#' + Platform.objects.using(dbAlias).filter(name=pName).values_list('color')[0][0]
extent = aQS.extent(field_name='maptrack')

# Get the 1 & 99 percentiles of the data for setting limits on the scatter plot
apQS = ActivityParameter.objects.using(dbAlias).filter(activity__platform__name=pName)
xpQS = apQS.filter(parameter__name=xParmName).aggregate(Min('p010'), Max('p990'))
ypQS = apQS.filter(parameter__name=yParmName).aggregate(Min('p010'), Max('p990'))
xmin, xmax = (xpQS['p010__min'], xpQS['p990__max'])
ymin, ymax = (ypQS['p010__min'], ypQS['p990__max'])

# Get units for each parameter
prQS = ParameterResource.objects.using(dbAlias).filter(resource__name='units').values_list('resource__value')
xUnits = prQS.filter(parameter__name=xParmName)[0][0]
yUnits = prQS.filter(parameter__name=yParmName)[0][0]

# Pull out data and plot at timeInterval intervals
startTime = aStart
endTime = startTime + timeInterval
while endTime < aEnd:
    cursor.execute(sql_template.format(start=startTime, end=endTime, pxname=xParmName, pyname=yParmName, platform=pName))
    x = [] 
    y = []
    points = []
    for row in cursor:
        x.append(float(row[1]))
        y.append(float(row[2]))
        points.append(Point(float(row[3]), float(row[4])))

    if len(points) < 2:
        startTime = endTime
        endTime = startTime + timeInterval
        continue

    path = LineString(points).simplify(tolerance=.001)

    fig = plt.figure()
    plt.grid(True)
    ax = fig.add_subplot(111)

    # Scale path points to appear in upper right of the plot as a crude indication of the track
    xp = []
    yp = []
    for p in path:
        xp.append(0.30 * (p[0] - extent[0]) * (xmax - xmin) / (extent[2] - extent[0]) + 0.70 * (xmax - xmin))
        yp.append(0.18 * (p[1] - extent[1]) * (ymax - ymin) / (extent[3] - extent[1]) + 0.75 * (ymax - ymin))
       
    # Make the plot 
    ax.set_xlim(round_to_n(xmin, 1), round_to_n(xmax, 1))
    ax.set_ylim(round_to_n(ymin, 1), round_to_n(ymax, 1))
    ax.set_xlabel('%s (%s)' % (xParmName, xUnits))
    ax.set_ylabel('%s (%s)' % (yParmName, yUnits))
    ax.set_title('%s from %s' % (pName, dbAlias)) 
    ax.scatter(x, y, marker='.', s=10, c='k', lw = 0, clip_on=False)
    ax.plot(xp, yp, c=color)
    ax.text(0.0005, 5.3, startTime.strftime('%Y-%m-%d %H:%M'))
    fileName = 'chl_bb_' + startTime.strftime('%Y%m%dT%H%M') + '.png'
    fig.savefig(fileName)
    print 'Saved file', fileName
    plt.close()

    startTime = endTime
    endTime = startTime + timeInterval

print 'Done. Make an animated gif with: convert -delay 100 chl_bb_*.png chl_bb_%s.gif' % pName

