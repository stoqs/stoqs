'''
Class(es) responsible for delivering X3D content displaying animation
of data from STOQS databases.
'''

import logging
import math
import numpy as np
import os
import time
from collections import namedtuple
from datetime import datetime
from itertools import izip
from loaders import X3DPLATFORMMODEL, X3D_MODEL, X3D_MODEL_SCALEFACTOR
from matplotlib.colors import hex2color
from stoqs import models

PA_MAX_POINTS = 10000000       # Set to avoid memory error on development system


class PlatformAnimation(object):
    '''Build X3D scene graph fragments for platforms that have X3D
    models; for those that have roll, pitch, and yaw route in orientation
    data, always route in position data.
    '''
    logger = logging.getLogger(__name__)

    position_template = '''
        <GeoLocation id="{pName}_LOCATION" DEF="{pName}_LOCATION">
            {geoOriginStr}
            <Transform id="{pName}_SCALE" DEF="{pName}_SCALE" scale="{scale} {scale} {scale}">
                <Transform scale="{plat_scale} {plat_scale} {plat_scale}">
                    <Inline url="{pURL}"></Inline>
                </Transform>
            </Transform>
        </GeoLocation>
        <GeoPositionInterpolator DEF="{pName}_POS_INTERP" key="{pKeys}" keyValue="{posValues}">{geoOriginStr}</GeoPositionInterpolator>       
        <ROUTE fromField="geovalue_changed" fromNode="{pName}_POS_INTERP" toField="geoCoords" toNode="{pName}_LOCATION"></ROUTE>       
        <ROUTE fromField="fraction_changed" fromNode="TS" toField="set_fraction" toNode="{pName}_POS_INTERP"></ROUTE>      
    '''
    position_orientation_template = '''
        <GeoLocation id="{pName}_LOCATION" DEF="{pName}_LOCATION">
            {geoOriginStr}
            <Transform id="{pName}_SCALE" DEF="{pName}_SCALE" scale="{scale} {scale} {scale}">
                <!-- Cylinder height = 0.410 in axes_enu.x3d, scale to make length = 10 m -->
                <Transform scale="24.390244 24.390244 24.390244">
                    <Inline url="http://stoqs.mbari.org/x3d/beds/axes_enu.x3d" nameSpaceName="{pName}_axesENU"></Inline>
                </Transform>
                <Transform scale="3 3 3" translation="0 1 0">
                    <Billboard axisOfRotation="0,0,0">
                        <Shape>
                            <Appearance>
                                <Material ambientIntensity="1" diffuseColor="{pColor}"></Material>
                            </Appearance>
                            <Text string="{pName}">
                            </Text>
                        </Shape>
                    </Billboard>
                </Transform>
                <Transform id="{pName}_YROT" DEF="{pName}_YROT">
                    <Transform id="{pName}_XROT" DEF="{pName}_XROT">
                        <Transform id="{pName}_ZROT" DEF="{pName}_ZROT">
                            <Transform scale="{plat_scale} {plat_scale} {plat_scale}">
                                <Inline url="{pURL}"></Inline>
                            </Transform>
                        </Transform>
                    </Transform>
                </Transform>
            </Transform>
        </GeoLocation>

        <!-- 6 DOF data coded here as position and orientation interpolators -->
        <GeoPositionInterpolator DEF="{pName}_POS_INTERP" key="{pKeys}" keyValue="{posValues}">{geoOriginStr}</GeoPositionInterpolator>
        <OrientationInterpolator DEF="{pName}_X_OI" key="{oKeys}" keyValue="{xRotValues}"></OrientationInterpolator>
        <OrientationInterpolator DEF="{pName}_Y_OI" key="{oKeys}" keyValue="{yRotValues}"></OrientationInterpolator>
        <OrientationInterpolator DEF="{pName}_Z_OI" key="{oKeys}" keyValue="{zRotValues}"></OrientationInterpolator>
        
        <!-- Wire up the connections between the nodes to animate the motion of the Shape -->       
        <ROUTE fromField="geovalue_changed" fromNode="{pName}_POS_INTERP" toField="geoCoords" toNode="{pName}_LOCATION"></ROUTE>

        <ROUTE fromField="value_changed" fromNode="{pName}_X_OI" toField="rotation" toNode="{pName}_XROT"></ROUTE>
        <ROUTE fromField="value_changed" fromNode="{pName}_Y_OI" toField="rotation" toNode="{pName}_YROT"></ROUTE>
        <ROUTE fromField="value_changed" fromNode="{pName}_Z_OI" toField="rotation" toNode="{pName}_ZROT"></ROUTE>

        <ROUTE fromField="fraction_changed" fromNode="TS" toField="set_fraction" toNode="{pName}_POS_INTERP"></ROUTE>
        <ROUTE fromField="fraction_changed" fromNode="TS" toField="set_fraction" toNode="{pName}_X_OI"></ROUTE>
        <ROUTE fromField="fraction_changed" fromNode="TS" toField="set_fraction" toNode="{pName}_Y_OI"></ROUTE>
        <ROUTE fromField="fraction_changed" fromNode="TS" toField="set_fraction" toNode="{pName}_Z_OI"></ROUTE>
    '''
    global_template = '<TimeSensor id="PLATFORMS_TS" DEF="TS" cycleInterval="{cycInt}" loop="true" enabled="false" onoutputchange="setSlider(event)"></TimeSensor>'
    x3d_info = namedtuple('x3d_info', ['x3d', 'all_x3d', 'platforms', 'times', 'limits', 'platforms_not_shown'])

    def __init__(self, platforms, kwargs, request, qs, qs_mp):
        self.platforms = platforms
        self.kwargs = kwargs
        self.request = request
        self.qs = qs
        self.qs_mp = qs_mp      # Need the ordered version of the query set

        self.lon_by_plat = {}
        self.lat_by_plat = {}
        self.depth_by_plat = {}
        self.time_by_plat = {}

        self.roll_by_plat = {}
        self.pitch_by_plat = {}
        self.yaw_by_plat = {}

        # Platform model must be oriented with nose to -Z (north) and up to +Y
        self.xRotFmt = '1 0 0 {:.6f} '    # pitch
        self.yRotFmt = '0 -1 0 {:.6f} '   # yaw
        self.zRotFmt = '0 0 -1 {:.6f} '   # roll

    def getX3DPlatformModel(self, pName):
        # Expect only one X3DPLATFORMMODEL per platform (hence .get())
        return models.PlatformResource.objects.using(self.request.META['dbAlias']
                ).get(platform__name=pName, resource__name=X3D_MODEL,
                        resource__resourcetype__name=X3DPLATFORMMODEL
                ).resource.uristring

    def getX3DPlatformModelScale(self, pName):
        # Expect only one X3DPLATFORMMODEL per platform (hence .get())
        try:
            factor = float(models.PlatformResource.objects.using(self.request.META['dbAlias']
                ).get(platform__name=pName, resource__name=X3D_MODEL_SCALEFACTOR,
                        resource__resourcetype__name=X3DPLATFORMMODEL
                ).resource.value)
        except models.PlatformResource.DoesNotExist:
            factor = 1.0

        return factor

    def loadData(self, platform):
        '''Read the data from the database into member variables for construction 
        of platform orientation time series.
        '''
        # Save to '_by_plat' dictionaries so that each platform can be 
        # separately controlled by ROUTEs, interpolators, and JavaScript
        pqs = self.qs_mp.filter(measurement__instantpoint__activity__platform=platform)

        # Must filter on one Parameter, otherwise we get multiple measurement values, 
        # choose 'yaw' - this means that a platform must have yaw (heading) to be visualized
        for mp in pqs.filter(parameter__standard_name='platform_yaw_angle'):
            self.lon_by_plat.setdefault(platform.name, []).append(mp['measurement__geom'].x)
            self.lat_by_plat.setdefault(platform.name, []).append(mp['measurement__geom'].y)
            self.depth_by_plat.setdefault(platform.name, []).append(mp['measurement__depth'])

            # Need millisecond accuracy, add microseconds to what timetuple() provides 
            # (only to the second); time_by_plat is in Unix epoch milliseconds
            dt = mp['measurement__instantpoint__timevalue']
            self.time_by_plat.setdefault(platform.name, []).append(
                    int((time.mktime(dt.timetuple()) + dt.microsecond / 1.e6) * 1000.0))

        for mp in pqs.filter(parameter__standard_name='platform_roll_angle'):
            self.roll_by_plat.setdefault(platform.name, []).append(mp['datavalue'])
        for mp in pqs.filter(parameter__standard_name='platform_pitch_angle'):
            self.pitch_by_plat.setdefault(platform.name, []).append(mp['datavalue'])
        for mp in pqs.filter(parameter__standard_name='platform_yaw_angle'):
            self.yaw_by_plat.setdefault(platform.name, []).append(mp['datavalue'])

    def overlap_time(self, r1, r2):
        '''Return timedelta of overlap between the arguments. Positive return value
        has time overlap, negative value means there is no overlap.
        '''
        # See http://stackoverflow.com/questions/9044084/efficient-date-range-overlap-calculation-in-python
        latest_start = max(r1.start, r2.start)
        earliest_end = min(r1.end, r2.end)
        overlap = (earliest_end - latest_start).total_seconds()

        return overlap

    def _assemble_platforms(self, platforms, vert_ex, geoOrigin, scale, speedup,
                            force_overlap):
        '''Assemble X3D text for platforms in the selection. If force_overlap is
        True then start with earliest animation and check other platform animations; 
        if they overlap then build and include them in the returned information.
        '''
        x3d_dict = {}
        time_ranges = {}
        assembled_times = []
        assembled_platforms = []

        Range = namedtuple('Range', ['start', 'end'])
        for p in platforms:
            self.loadData(p)
            time_ranges[p] = Range(
                        start=datetime.utcfromtimestamp(self.time_by_plat[p.name][0]/1000.0),
                        end=datetime.utcfromtimestamp(self.time_by_plat[p.name][-1]/1000.0)
            )
        # Find earliest platform animation, time and latest time
        min_start_time = datetime.utcnow()
        max_end_time = datetime.utcfromtimestamp(0)
        for p, r in time_ranges.iteritems():
            if r.start < min_start_time:
                min_start_time = r.start
                st_ems = int((time.mktime(min_start_time.timetuple()) + 
                                min_start_time.microsecond / 1.e6) * 1000.0)
                earliest_platform = p
            if r.end > max_end_time:
                max_end_time = r.end
                et_ems = int((time.mktime(max_end_time.timetuple()) + 
                                max_end_time.microsecond / 1.e6) * 1000.0)

        # Build X3D and assemble
        for p, r in time_ranges.iteritems():
            if force_overlap:
                # Compare earliest platform animation with all the rest, build x3d for only overlapping
                if self.overlap_time(time_ranges[earliest_platform], r) > 0:
                    x3d_dict[p.name] = self._animationX3D_for_platform(p, vert_ex, geoOrigin, scale, st_ems, et_ems)
                    assembled_times.extend(self.time_by_plat[p.name])
                    assembled_platforms.append(p)
            else:
                x3d_dict[p.name] = self._animationX3D_for_platform(p, vert_ex, geoOrigin, scale, st_ems, et_ems)
                assembled_times.extend(self.time_by_plat[p.name])
                assembled_platforms.append(p)

        cycInt = (max_end_time -  min_start_time).total_seconds() / speedup
        all_x3d = self.global_template.format(cycInt=cycInt)
        platforms_not_shown = (set(p.name for p in platforms) -
                               set(p.name for p in assembled_platforms))

        # Create equal interval times that fill in gaps in assembled_times, setting time step from earliest_platform
        equal_times = np.arange(st_ems, et_ems,
                                self.time_by_plat[earliest_platform.name][2] - self.time_by_plat[earliest_platform.name][1])

        return self.x3d_info(x3d=x3d_dict, all_x3d=all_x3d, platforms=assembled_platforms,
                             times=equal_times, limits=(0, len(equal_times)),
                             platforms_not_shown=platforms_not_shown)

    def _deg2rad(self, angle):
        '''Given an angle in degrees return angle in radians
        '''
        return np.pi * angle / 180.0

    def _pitch_with_ve(self, angle, ve):
        '''Given an angle in degrees return pitch angle in radians properly
        adjusted for vertical exaggeration'''
        if ve == 1:
            return np.pi * angle / 180.0
        else:
            # Account for all 4 quadrants by using atan2()
            x = math.cos(np.pi * angle / 180.0)
            y = math.sin(np.pi * angle / 180.0)

            return math.atan2(y * ve, x)

    def _append_animation_values(self, st_ems, et_ems, pName, lat, lon, depth, t, vert_ex, pitch, yaw, roll):
        '''Append formatted values to X3D text items
        '''
        self.points += '%.6f %.6f %.1f ' % (lat, lon, -depth * vert_ex)
        self.keys += '%.4f ' % ((t - st_ems) / float(et_ems - st_ems))

        # Apply vertical exaggeration to pitch angle
        self.xRotValues += self.xRotFmt.format(self._pitch_with_ve(pitch, vert_ex))
        self.yRotValues += self.yRotFmt.format(self._deg2rad(yaw))
        self.zRotValues += self.zRotFmt.format(self._deg2rad(roll))

    def _animationX3D_for_platform(self, platform, vert_ex, geoOrigin, scale, st_ems, et_ems):
                                    
        '''Build X3D text for a platform's animation
        '''
        geoorigin_use = ''
        if geoOrigin:
            # Count on JavaScript code to add <GeoOrgin DEF="GO" ... > to the scene
            geoorigin_use = '<GeoOrigin use="GO"></GeoOrigin>'

        pName = platform.name
        pColor = ' '.join(str(c) for c in hex2color('#' + platform.color))

        self.points = ''
        self.keys = ''
        self.xRotValues = ''
        self.yRotValues = ''
        self.zRotValues = ''

        if self.time_by_plat[pName][0] > st_ems:
            # Pad with stationary pose of first position if platform not the earliest
            for t in (st_ems, self.time_by_plat[pName][0]):
                self._append_animation_values(st_ems, et_ems, pName,
                                                self.lat_by_plat[pName][0], 
                                                self.lon_by_plat[pName][0],
                                                self.depth_by_plat[pName][0], t, vert_ex,
                                                self.pitch_by_plat[pName][0],
                                                self.yaw_by_plat[pName][0],
                                                self.roll_by_plat[pName][0] )

        for lon, lat, depth, t, pitch, yaw, roll in izip(
                                                self.lon_by_plat[pName], 
                                                self.lat_by_plat[pName], 
                                                self.depth_by_plat[pName],
                                                self.time_by_plat[pName],
                                                self.pitch_by_plat[pName],
                                                self.yaw_by_plat[pName],
                                                self.roll_by_plat[pName]):
            self._append_animation_values(st_ems, et_ems, pName, lat, lon, depth, t, vert_ex,
                                          pitch, yaw, roll)

        if self.xRotValues and self.yRotValues and self.zRotValues:
            x3d = self.position_orientation_template.format(pName=pName,
                    plat_scale=self.getX3DPlatformModelScale(pName),
                    pURL=self.getX3DPlatformModel(pName), pKeys=self.keys[:-1], 
                    posValues=self.points, oKeys=self.keys[:-1], xRotValues=self.xRotValues, 
                    yRotValues=self.yRotValues, zRotValues=self.zRotValues, scale=scale,
                    geoOriginStr=geoorigin_use, pColor=pColor)
        else:
            x3d = self.position_template.format(pName=pName, 
                    plat_scale=self.getX3DPlatformModelScale(pName),
                    pURL=self.getX3DPlatformModel(pName), pKeys=self.keys[:-1], 
                    posValues=self.points, scale=scale, geoOriginStr=geoorigin_use)

        return x3d

    def platformAnimationDataValuesForX3D(self, vert_ex=10.0, geoOrigin='', scale=1,
                                          speedup=1, force_overlap=False):
        '''Public method called by STOQSQManager.py
        '''
        info = self.x3d_info(x3d='', all_x3d='', times=(), platforms=(), limits=(), 
                             platforms_not_shown=())
        try:
            info = self._assemble_platforms(self.platforms, vert_ex, geoOrigin, scale,
                                           speedup, force_overlap)
        except Exception as e:
            self.logger.exception(str(e))

        if len(info.times) > PA_MAX_POINTS:
            self.logger.warn('time array to large for rendering: %s', len(info.times))
            return {'x3d': '', 'message': '{} are too many values to animate. Filter to get below {}.'.format(
                                           len(info.times), PA_MAX_POINTS)}
        else:
            return {'x3d': info.x3d, 'all': info.all_x3d, 'limits': info.limits, 'time': info.times, 
                    'platforms_not_shown': info.platforms_not_shown, 'speedup': speedup, 'scale': scale}

