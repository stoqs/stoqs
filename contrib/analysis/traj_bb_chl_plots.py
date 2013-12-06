# To be executed in the STOQS virtualenv with manage.py shell_plus

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))  # settings.py is one dir up

import matplotlib.pyplot as plt
from django.db import connections
from datetime import datetime, timedelta
from stoqs.models import Activity, ActivityParameter
from django.contrib.gis.geos import LineString, Point
from utils.utils import round_to_n

# Options:campaign, platform, activity, and parameters
dbAlias = 'stoqs_september2013_t'
aName = 'Tethys_CANON_Fall2013'
pName = 'tethys'
xParmName = 'bb470'
yParmName = 'chlorophyll'
timeInterval = timedelta(hours=6)


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
WHERE (p_y.name = 'chlorophyll')
  AND (p_x.name = 'bb470')
  AND (stoqs_instantpoint.timevalue >= '{start}'
       AND stoqs_instantpoint.timevalue <= '{end}')
  AND stoqs_platform.name IN ('tethys')
ORDER BY stoqs_instantpoint.timevalue '''

# Get connection to database using dbAlias defined in privateSettings
cursor = connections[dbAlias].cursor()

# Get start and end datetimes, color and geographic extent of the activity
aQS = Activity.objects.using(dbAlias).filter(name__contains=aName)
aStart = aQS.values_list('startdate')[0][0]
aEnd = aQS.values_list('enddate')[0][0]
color = '#' + aQS.values_list('platform__color')[0][0]
extent = aQS.extent(field_name='maptrack')

# Get the 1 & 99 percentiles of the data for setting limits on the scatter plot
apQS = ActivityParameter.objects.using(dbAlias).filter(activity__name__contains=aName)
xmin, xmax = apQS.filter(parameter__name=xParmName).values_list('p010', 'p990')[0]
ymin, ymax = apQS.filter(parameter__name=yParmName).values_list('p010', 'p990')[0]

# Pull out data and plot at timeInterval intervals
startTime = aStart
endTime = startTime + timeInterval
while endTime < aEnd:
    cursor.execute(sql_template.format(start=startTime, end=endTime))
    x = [] 
    y = []
    points = []
    for row in cursor:
        x.append(float(row[1]))
        y.append(float(row[2]))
        points.append(Point(float(row[3]), float(row[4])))

    path = LineString(points).simplify(tolerance=.001)

    fig = plt.figure()
    plt.grid(True)
    ax = fig.add_subplot(111)
    #xmin = 0.0 
    #xmax = 0.006
    #ymin = 0.0
    #ymax = 6.0

    # Scale path points to appear in upper right of the plot
    xp = []
    yp = []
    for p in path:
        xp.append(0.3 * (p[0] - extent[0]) * (xmax - xmin) / (extent[2] - extent[0]) + 0.7 * (xmax - xmin))
        yp.append(0.3 * (p[1] - extent[1]) * (ymax - ymin) / (extent[3] - extent[1]) + 0.7 * (ymax - ymin))
        
    ax.set_xlim(round_to_n(xmin, 1), round_to_n(xmax, 1))
    ax.set_ylim(round_to_n(ymin, 1), round_to_n(ymax, 1))
    ax.set_xlabel('bb470 (m^{-1})')
    ax.set_ylabel('chlorophyll (mg m-3)')
    ax.scatter(x, y, marker='.', s=10, c='k', lw = 0, clip_on=False)
    ax.plot(xp, yp, c=color)
    ax.text(0.0005, 5.5, startTime.strftime('%Y-%m-%d %H:%M'))
    fileName = 'chl_bb_' + startTime.strftime('%Y%m%dT%H%M') + '.png'
    fig.savefig(fileName)
    print 'Saved file', fileName
    plt.close()

    startTime = endTime
    endTime = startTime + timeInterval


