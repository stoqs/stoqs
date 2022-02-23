#!/usr/bin/env python
'''
Parse logged data from BEDs .EVT or .WAT file to compute translations in x, y, z and rotations
about these axes.  Output as NetCDF with the intention of of loading into a STOQS database.
The resulting Netcdf file will be of featureType timeSeries for stationary events (the default).
If the --trajectory option is given then a NetCDF file with featureType of trajectory will be
created using the path in the file specified with the --trajectory option.

--
Mike McCann
18 July 2013

$Id: bed2netcdf.py 13838 2019-08-12 22:59:15Z mccann $
'''

import os
import sys
import csv
import math
import coards
import datetime
import numpy as np
import numpy.ma as ma
from BEDS import BEDS, bcal, NoPressureData
from scipy.interpolate import interp1d
from seawater import eos80
from netCDF4 import Dataset


class BEDS_NetCDF(BEDS):

    def __init__(self):
        '''
        Initialize with options
        '''

        return super(BEDS_NetCDF, self).__init__()

    def createNetCDFfromFile(self):
        '''
        Read data from EVT or WAT file and apply operations to convert it to data with units that
        are then written to a NetCDF file.
        '''

        # Suppress 'util.py:70: RuntimeWarning: invalid value encountered in sqrt'
        np.seterr(all='ignore')

        if self.args.trajectory and self.args.beg_depth and self.args.end_depth:
            print("Extracting thalweg data between command line specified depths {} and {}".format(self.args.beg_depth, self.args.end_depth))
            self.readTrajectory(self.args.beg_depth, self.args.end_depth)

        for fileName in self.inputFileNames:
            # Make sure input file is openable
            print('Input fileName = ', fileName)
            try:
                with open(fileName): 
                    pass
            except IOError:
                raise Exception('Cannot open input file %s' % fileName)

            if self.sensorType == 'Invensense':
                try:
                    if self.args.read_csv:
                        self.readBEDs_csv_File(fileName)
                    else:
                        self.readBEDsFile(fileName)
                    self.processAccelerations()
                    self.processRotations(useMatlabCode=False)
                except NoPressureData as e:
                    print(str(e))
                    continue
            else:
                raise Exception("No handler for sensorType = %s" % self.sensorType)

        if not hasattr(self, 's2013'):
            print('Could not read time (s2013) from input file(s)')
            exit(-1)

        if self.args.seconds_offset:
            self.s2013 = self.s2013 + self.args.seconds_offset
            self.ps2013 = self.ps2013 + self.args.seconds_offset

        if self.args.output:
            self.outFile = self.args.output
        elif len(self.inputFileNames) == 1:
            self.outFile = self.inputFileNames[0].split('.')[0]
            if '.EVT' in self.inputFileNames[0]:
                self.outFile += '_full'
            elif '.E00' in self.inputFileNames[0]:
                self.outFile += '_decim'
            if self.args.trajectory:
                self.outFile += '_traj'
            self.outFile += '.nc'
        else:
            raise Exception("Must specify --output if more than one input file.")

        if self.args.trajectory and self.args.bed_name:
            # Expect we have well-calibrated and tide-corrected depths in bed_depth[] array
            print("Extracting thalweg data between depths {} and {}".format(self.bed_depth[0], self.bed_depth[-1]))
            self.readTrajectory(self.bed_depth[0], self.bed_depth[-1])

        if (not self.traj_lat or not self.traj_lon) and self.args.trajectory:
            raise Exception('Could not exctract trajectory between {} and {}.'
                            ' Consider processing as a stationary event.'.format(
                            self.bed_depth[0], self.bed_depth[-1]))

        if self.args.trajectory:
            self.featureType = 'trajectory'

        # Interpolate data to regularly spaced time values - may need to do this to improve accuracy
        # (See http://www.freescale.com/files/sensors/doc/app_note/AN3397.pdf)
        ##si = linspace(self.s2013[0], self.s2013[-1], len(self.s2013))
        ##axi = interp(si, self.s2013, self.ax)

        # TODO: Review this calculation - may need to rotate these to the absolute (not rotating) frame
        # Double integrate accelerations to get position and construct X3D position values string
        # (May need to high-pass filter the data to remove noise that can give unreasonably large positions.)
        ##x = self.cumtrapz(self.s2013, self.cumtrapz(self.s2013, self.ax))
        ##y = self.cumtrapz(self.s2013, self.cumtrapz(self.s2013, self.ay))
        ##z = self.cumtrapz(self.s2013, self.cumtrapz(self.s2013, self.az))

        dateCreated = datetime.datetime.now().strftime("%d %B %Y %H:%M:%S")
        yearCreated = datetime.datetime.now().strftime("%Y")

        # Create the NetCDF file
        self.ncFile = Dataset(self.outFile, 'w')

        # Time dimensions for both trajectory and timeSeries datasets - IMU and pressure have different times
        self.ncFile.createDimension('time', len(self.s2013))
        self.time = self.ncFile.createVariable('time', 'float64', ('time',))
        self.time.standard_name = 'time'
        self.time.long_name = 'Time(GMT)'
        self.time.units = 'seconds since 2013-01-01 00:00:00'
        self.time[:] = self.s2013

        if self.featureType == 'timeseries':
            self.ncFile.createDimension('ptime', len(self.ps2013))
            self.ptime = self.ncFile.createVariable('ptime', 'float64', ('ptime',))
            self.ptime.standard_name = 'time'
            self.ptime.long_name = 'Time(GMT)'
            self.ptime.units = 'seconds since 2013-01-01 00:00:00'
            self.ptime[:] = self.ps2013

            # Save with COARDS compliant station (singleton) coordinates
            self.ncFile.createDimension('latitude', 1)
            self.latitude = self.ncFile.createVariable('latitude', 'float64', ('latitude',))
            self.latitude.long_name = 'LATITUDE'
            self.latitude.standard_name = 'latitude'
            self.latitude.units = 'degree_north'
            self.latitude[0] = self.lat
    
            self.ncFile.createDimension('longitude', 1)
            self.longitude = self.ncFile.createVariable('longitude', 'float64', ('longitude',))
            self.longitude.long_name = 'LONGITUDE'
            self.longitude.standard_name = 'longitude'
            self.longitude.units = 'degree_east'
            self.longitude[0] = self.lon
    
            self.ncFile.createDimension('depth', 1)
            self.depth = self.ncFile.createVariable('depth', 'float64', ('depth',))
            self.depth.long_name = 'depth'
            self.depth.standard_name = 'depth'
            self.depth.comment = 'Value provided on bed2netcdf.py command line'
            self.depth.units = 'm'
            self.depth[0] = self.dpth

            # Record Variable - Pressure and Depth
            pr = self.ncFile.createVariable('PRESS', 'float64', ('ptime', 'depth', 'latitude', 'longitude'))
            pr.long_name = 'External Instrument Pressure'
            pr.coordinates = 'ptime depth latitude longitude'
            pr.units = 'bar'
            pr[:] = self.pr.reshape(len(self.pr), 1, 1, 1)

            bd = self.ncFile.createVariable('BED_DEPTH', 'float64', ('ptime', 'depth', 'latitude', 'longitude'))
            bd.long_name = 'Depth of BED'
            bd.coordinates = 'ptime depth latitude longitude'
            bd.comment = self.bed_depth_comment
            bd.units = 'm'
            bd[:] = self.bed_depth.reshape(len(self.bed_depth), 1, 1, 1)

            bdi = self.ncFile.createVariable('BED_DEPTH_LI', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            bdi.long_name = 'Depth of BED - Linerarly Interpolated to IMU Samples'
            bdi.coordinates = 'time depth latitude longitude'
            bdi.comment = self.bed_depth_comment
            bdi.units = 'm'
            bdi[:] = np.interp(self.s2013, self.ps2013, bd[:].reshape(len(self.pr))).reshape(len(self.s2013), 1, 1, 1)

            # Record Variables - Accelerations
            xa = self.ncFile.createVariable('XA', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            xa.long_name = 'Acceleration along X-axis'
            xa.coordinates = 'time depth latitude longitude'
            xa.units = 'g'
            xa[:] = self.ax.reshape(len(self.ax), 1, 1, 1)

            ya = self.ncFile.createVariable('YA', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            ya.long_name = 'Acceleration along Y-axis'
            ya.coordinates = 'time depth latitude longitude'
            ya.units = 'g'
            ya[:] = self.ay.reshape(len(self.ay), 1, 1, 1)

            za = self.ncFile.createVariable('ZA', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            za.long_name = 'Acceleration along X-axis'
            za.coordinates = 'time depth latitude longitude'
            za.units = 'g'
            za[:] = self.az.reshape(len(self.az), 1, 1, 1)

            a = self.ncFile.createVariable('A', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            a.long_name = 'Acceleration Magnitude'
            a.coordinates = 'time depth latitude longitude'
            a.units = 'g'
            a[:] = self.a.reshape(len(self.a), 1, 1, 1)

            # Record Variables - Rotations
            # Nose of model points to -Z (north) and Up is +Y
            xr = self.ncFile.createVariable('XR', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            xr.long_name = 'Rotation about X-axis'
            xr.coordinates = 'time depth latitude longitude'
            xr.units = 'degree'
            xr.standard_name = 'platform_pitch_angle'
            xr[:] = (self.rx * 180 / np.pi).reshape(len(self.rx), 1, 1, 1)

            yr = self.ncFile.createVariable('YR', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            yr.long_name = 'Rotation about Y-axis'
            yr.coordinates = 'time depth latitude longitude'
            yr.units = 'degree'
            yr.standard_name = 'platform_yaw_angle'
            yr[:] = (self.ry * 180 / np.pi).reshape(len(self.ry), 1, 1, 1)
    
            zr = self.ncFile.createVariable('ZR', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            zr.long_name = 'Rotation about Z-axis'
            zr.coordinates = 'time depth latitude longitude'
            zr.units = 'degree'
            zr.standard_name = 'platform_roll_angle'
            zr[:] = (self.rz * 180 / np.pi).reshape(len(self.rz), 1, 1, 1)

            axis_x = self.ncFile.createVariable('AXIS_X', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            axis_x.long_name = 'X-component of axis in axis-angle form of quaternion measurement'
            axis_x.comment = self.p_angle_axis_comment
            axis_x.coordinates = 'time depth latitude longitude'
            axis_x.units = ''
            axis_x[:] = self.px.reshape(len(self.px), 1, 1, 1)

            axis_y = self.ncFile.createVariable('AXIS_Y', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            axis_y.long_name = 'Y-component of axis in axis-angle form of quaternion measurement'
            axis_y.comment = self.p_angle_axis_comment
            axis_y.coordinates = 'time depth latitude longitude'
            axis_y.units = ''
            axis_y[:] = self.py.reshape(len(self.py), 1, 1, 1)

            axis_z = self.ncFile.createVariable('AXIS_Z', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            axis_z.long_name = 'Z-component of axis in axis-angle form of quaternion measurement'
            axis_z.comment = self.p_angle_axis_comment
            axis_z.coordinates = 'time depth latitude longitude'
            axis_z.units = ''
            axis_z[:] = self.pz.reshape(len(self.pz), 1, 1, 1)

            angle = self.ncFile.createVariable('ANGLE', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            angle.long_name = 'Angle rotated about axis in axis-angle form of quaternion measurement'
            angle.comment = self.p_angle_axis_comment
            angle.coordinates = 'time depth latitude longitude'
            angle.units = 'radian'
            angle[:] = self.angle.reshape(len(self.angle), 1, 1, 1)

            angle_rate = self.ncFile.createVariable('ANGLE_RATE', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            angle_rate.long_name = 'Absolute rate of ANGLE change'
            angle_rate.comment = self.angle_rate_comment
            angle_rate.coordinates = 'time depth latitude longitude'
            angle_rate.units = 'degree/second'
            angle_rate[:] = self.angle_rate.reshape(len(self.angle_rate), 1, 1, 1)

            angle_count = self.ncFile.createVariable('ANGLE_COUNT', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            angle_count.long_name = 'Absolute complete rotation count from ANGLE data'
            angle_count.comment = self.angle_count_comment
            angle_count.coordinates = 'time depth latitude longitude'
            angle_count.units = ''
            angle_count[:] = self.angle_count.reshape(len(self.angle_count), 1, 1, 1)

            # Axis about which platform is rotating - derived from dividing quaternions
            rot_x = self.ncFile.createVariable('ROT_X', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            rot_x.long_name = 'X-component of axis about which the BED is rotating from one time step to the next'
            rot_x.comment = self.m_angle_axis_comment
            rot_x.coordinates = 'time depth latitude longitude'
            rot_x.units = ''
            rot_x[:] = self.mx.reshape(len(self.mx), 1, 1, 1)

            rot_y = self.ncFile.createVariable('ROT_Y', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            rot_y.long_name = 'Y-component of axis about which the BED is rotating from one time step to the next'
            rot_y.comment = self.m_angle_axis_comment
            rot_y.coordinates = 'time depth latitude longitude'
            rot_y.units = ''
            rot_y[:] = self.my.reshape(len(self.my), 1, 1, 1)

            rot_z = self.ncFile.createVariable('ROT_Z', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            rot_z.long_name = 'Z-component of axis about which the BED is rotating from one time step to the next'
            rot_z.comment = self.m_angle_axis_comment
            rot_z.coordinates = 'time depth latitude longitude'
            rot_z.units = ''
            rot_z[:] = self.mz.reshape(len(self.mz), 1, 1, 1)

            rot_rate = self.ncFile.createVariable('ROT_RATE', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            rot_rate.long_name = 'Instantaneous rotation rate around axis about which the BED is rotating'
            rot_rate.comment = self.m_angle_axis_comment + ' and then angle / dt'
            rot_rate.coordinates = 'time depth latitude longitude'
            rot_rate.units = 'degree/second'
            rot_rate[:] = self.rotrate.reshape(len(self.rotrate), 1, 1, 1)

            rot_count = self.ncFile.createVariable('ROT_COUNT', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            rot_count.long_name = 'Rotation Count - Cumulative Sum of ROT_RATE * dt / 360 deg'
            rot_count.coordinates = 'time depth latitude longitude'
            rot_count.units = ''
            rot_count[:] = (self.rotcount).reshape(len(self.rotcount), 1, 1, 1)

            # Pressure sensor data interpolated to IMU samples
            p = self.ncFile.createVariable('P', 'float64', ('time','depth', 'latitude', 'longitude'))
            p.long_name = 'Pressure'
            p.coordinates = 'time depth latitude longitude'
            p.units = 'dbar'
            pres = np.interp(self.s2013, self.ps2013, self.pr)
            p[:] = pres.reshape(len(pres), 1, 1, 1)

            # Tumble rate & count
            tumble_rate = self.ncFile.createVariable('TUMBLE_RATE', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            tumble_rate.long_name = "Angular rate of change of BED's axis of rotation"
            tumble_rate.comment = 'Computed with: abs(last_vec.angle(vec)), where vec is the division of 2 successive quaternion measurements and last_vec is the previous vec'
            tumble_rate.coordinates = 'time depth latitude longitude'
            tumble_rate.units = 'degree/second'
            tumble_rate[:] = self.tumblerate.reshape(len(self.tumblerate), 1, 1, 1)

            tumble_count = self.ncFile.createVariable('TUMBLE_COUNT', 'float64', ('time', 'depth', 'latitude', 'longitude'))
            tumble_count.long_name = 'Tumble Count - Cumulative Sum of TUMBLE_RATE * dt / 360 deg'
            tumble_count.comment = 'Computed with: np.cumsum(np.absolute(self.difftumble)) / 2. / np.pi'
            tumble_count.coordinates = 'time depth latitude longitude'
            tumble_count[:] = self.tumblecount.reshape(len(self.tumblecount), 1, 1, 1)

            if hasattr(self, 'bed_depth_csi_comment'):
                # Spline interpolated bed_depth
                bed_depth_csi = self.ncFile.createVariable('BED_DEPTH_CSI', 'float64', ('time', 'depth', 'latitude', 'longitude'), fill_value=1.e20)
                bed_depth_csi.long_name = 'Depth of BED - Cubic Spline Interpolated to IMU Samples'
                bed_depth_csi.units = 'm'
                bed_depth_csi.coordinates = 'time depth latitude longitude'
                bed_depth_csi.comment = self.bed_depth_csi_comment
                bed_depth_csi[ma.clump_unmasked(self.p_mask)] = self.bed_depth_inside_spline

            if not self.args.no_tide_removal:
                # Tide data from OSTP Software calculation
                tide = self.ncFile.createVariable('TIDE', 'float64', ('ptime', 'depth', 'latitude', 'longitude'))
                tide.long_name = 'OSTP2 Tide model height'
                tide.coordinates = 'ptime depth latitude longitude'
                tide.comment = self.tide_comment
                tide.units = 'm'
                tide[:] = self.tide.reshape(len(self.tide), 1, 1, 1)

        elif self.featureType == 'trajectory':
            ifmt = '{var} linearly intepolated onto thalweg data from file {traj_file} using formula {formula}'
            print("Writing trajectory data")
            # Coordinate variables for trajectory 
            # Interpolate trajectory lat and lon onto the times of the data
            self.latitude = self.ncFile.createVariable('latitude', 'float64', ('time',))
            self.latitude.long_name = 'LATITUDE'
            self.latitude.standard_name = 'latitude'
            self.latitude.units = 'degree_north'
            self.latitude.comment = ifmt.format(var='Latitude', traj_file=self.args.trajectory, formula=
                    'np.interp(np.linspace(0,1,len(self.s2013)), np.linspace(0,1,len(self.traj_lat)), self.traj_lat)')
            self.latitude[:] = np.interp(np.linspace(0,1,len(self.s2013)), np.linspace(0,1,len(self.traj_lat)), self.traj_lat)
    
            self.longitude = self.ncFile.createVariable('longitude', 'float64', ('time',))
            self.longitude.long_name = 'LONGITUDE'
            self.longitude.standard_name = 'longitude'
            self.longitude.units = 'degree_east'
            self.longitude.comment = ifmt.format(var='Longitude', traj_file=self.args.trajectory, formula=
                    'np.interp(np.linspace(0,1,len(self.s2013)), np.linspace(0,1,len(self.traj_lon)), self.traj_lon)')
            self.longitude[:] = np.interp(np.linspace(0,1,len(self.s2013)), np.linspace(0,1,len(self.traj_lon)), self.traj_lon)
    
            self.depth = self.ncFile.createVariable('depth', 'float64', ('time',))
            self.depth.long_name = 'DEPTH'
            self.depth.standard_name = 'depth'
            self.depth.units = 'm'
            self.depth.comment = "{} Linearly interpolated to IMU samples.".format(self.bed_depth_comment)
            self.depth[:] = np.interp(self.s2013, self.ps2013, self.bed_depth)

            # Record Variables - Accelerations
            xa = self.ncFile.createVariable('XA', 'float64', ('time',))
            xa.long_name = 'Acceleration along X-axis'
            xa.comment = 'Recorded by instrument'
            xa.coordinates = 'time depth latitude longitude'
            xa.units = 'g'
            xa[:] = self.ax

            ya = self.ncFile.createVariable('YA', 'float64', ('time',))
            ya.long_name = 'Acceleration along Y-axis'
            ya.comment = 'Recorded by instrument'
            ya.coordinates = 'time depth latitude longitude'
            ya.units = 'g'
            ya[:] = self.ay

            za = self.ncFile.createVariable('ZA', 'float64', ('time',))
            za.long_name = 'Acceleration along X-axis'
            za.comment = 'Recorded by instrument'
            za.coordinates = 'time depth latitude longitude'
            za.units = 'g'
            za[:] = self.az

            a = self.ncFile.createVariable('A', 'float64', ('time',))
            a.long_name = 'Acceleration Magnitude'
            a.comment = 'Computed with: np.sqrt(self.ax**2 + self.ay**2 + self.az**2)'
            a.coordinates = 'time depth latitude longitude'
            a.units = 'g'
            a[:] = self.a

            # Record Variables - Rotations
            # Nose of model points to -Z (north) and Up is +Y
            xr = self.ncFile.createVariable('XR', 'float64', ('time',))
            xr.long_name = 'Rotation about X-axis'
            xr.standard_name = 'platform_pitch_angle'
            xr.comment = self.euler_comment
            xr.coordinates = 'time depth latitude longitude'
            xr.units = 'degree'
            xr[:] = (self.rx * 180 / np.pi)

            yr = self.ncFile.createVariable('YR', 'float64', ('time',))
            yr.long_name = 'Rotation about Y-axis'
            yr.standard_name = 'platform_yaw_angle'
            yr.comment = self.euler_comment
            yr.coordinates = 'time depth latitude longitude'
            yr.units = 'degree'
            if self.args.yaw_offset:
                yr.comment = yr.comment + '. Added {} degrees to original values.'.format(self.args.yaw_offset)
                yawl = []
                for y in (self.ry * 180 / np.pi) + self.args.yaw_offset:
                    if y > 360.0:
                        yawl.append(y - 360.0)
                    else:
                        yawl.append(y)

                yaw = np.array(yawl)
            else:
                yaw = (self.ry * 180 / np.pi)

            yr[:] = yaw
    
            zr = self.ncFile.createVariable('ZR', 'float64', ('time',))
            zr.long_name = 'Rotation about Z-axis'
            zr.standard_name = 'platform_roll_angle'
            zr.comment = self.euler_comment
            zr.coordinates = 'time depth latitude longitude'
            zr.units = 'degree'
            zr[:] = (self.rz * 180 / np.pi)

            # Axis coordinates & angle for angle_axis form of the quaternion
            # Note: STOQS UI has preference for AXIS_X, AXIS_Y, AXIS_Z, ANGLE over roll, pitch, and yaw
            axis_x = self.ncFile.createVariable('AXIS_X', 'float64', ('time',))
            axis_x.long_name = 'X-component of rotation vector'
            axis_x.comment = self.p_angle_axis_comment
            axis_x.coordinates = 'time depth latitude longitude'
            axis_x.units = ''
            axis_x[:] = self.px

            axis_y = self.ncFile.createVariable('AXIS_Y', 'float64', ('time',))
            axis_y.long_name = 'Y-component of rotation vector'
            axis_y.comment = self.p_angle_axis_comment
            axis_y.coordinates = 'time depth latitude longitude'
            axis_y.units = ''
            axis_y[:] = self.py

            axis_z = self.ncFile.createVariable('AXIS_Z', 'float64', ('time',))
            axis_z.long_name = 'Z-component of rotation vector'
            axis_z.comment = self.p_angle_axis_comment
            axis_z.coordinates = 'time depth latitude longitude'
            axis_z.units = ''
            axis_z[:] = self.pz

            angle = self.ncFile.createVariable('ANGLE', 'float64', ('time',))
            angle.long_name = 'Angle rotated about rotation vector'
            angle.comment = self.p_angle_axis_comment
            angle.coordinates = 'time depth latitude longitude'
            angle.units = 'radian'
            angle[:] = self.angle

            # Axis about which platform is rotating - derived from dividing quaternions
            rot_x = self.ncFile.createVariable('ROT_X', 'float64', ('time',))
            rot_x.long_name = 'X-component of platform rotation vector'
            rot_x.comment = self.m_angle_axis_comment
            rot_x.coordinates = 'time depth latitude longitude'
            rot_x.units = ''
            rot_x[:] = self.mx

            rot_y = self.ncFile.createVariable('ROT_Y', 'float64', ('time',))
            rot_y.long_name = 'Y-component of platform rotation vector'
            rot_y.comment = self.m_angle_axis_comment
            rot_y.coordinates = 'time depth latitude longitude'
            rot_y.units = ''
            rot_y[:] = self.my

            rot_z = self.ncFile.createVariable('ROT_Z', 'float64', ('time',))
            rot_z.long_name = 'Z-component of platform rotation vector'
            rot_z.comment = self.m_angle_axis_comment
            rot_z.coordinates = 'time depth latitude longitude'
            rot_z.units = ''
            rot_z[:] = self.mz

            # Rotation rate & count
            rot_rate = self.ncFile.createVariable('ROT_RATE', 'float64', ('time',))
            rot_rate.long_name = 'Absolute rotation rate about rotation vector'
            rot_rate.comment = 'Computed from angle output from Quaternion.get_euler() and the angle difference from one time step to the next'
            rot_rate.coordinates = 'time depth latitude longitude'
            rot_rate.units = 'degree/second'
            rot_rate[:] = self.rotrate

            rot_count = self.ncFile.createVariable('ROT_COUNT', 'float64', ('time', ))
            rot_count.long_name = 'Rotation Count - Cumulative Sum of ROT_RATE * dt / 360 deg'
            rot_count.comment = 'Computed with: np.cumsum(np.absolute(self.diffrot)) / 2. / np.pi'
            rot_count.coordinates = 'time depth latitude longitude'
            rot_count[:] = (self.rotcount)

            # Pressure sensor data linearly interpolated to IMU samples
            p = self.ncFile.createVariable('P', 'float64', ('time',))
            p.long_name = 'Pressure'
            p.comment = 'Recorded pressure linearly interpolated to IMU samples with np.interp(self.s2013, self.ps2013, self.pr)'
            p.coordinates = 'time depth latitude longitude'
            p.units = 'dbar'
            p[:] = np.interp(self.s2013, self.ps2013, self.pr)

            p_adj = self.ncFile.createVariable('P_ADJUSTED', 'float64', ('time',))
            p_adj.long_name = 'Adjusted Pressure'
            p_adj.coordinates = 'time depth latitude longitude'
            p_adj.units = 'dbar'
            p_adj.comment = self.pr_adj_comment
            p_adj[:] = np.interp(self.s2013, self.ps2013, self.pr_adj)

            # bed depth at pressure sample intervals
            bed_depth_li = self.ncFile.createVariable('BED_DEPTH_LI', 'float64', ('time',))
            bed_depth_li.long_name = 'Depth of BED - Linearly Interpolated to IMU samples'
            bed_depth_li.units = 'm'
            bed_depth_li.coordinates = 'time depth latitude longitude'
            bed_depth_li.comment = self.bed_depth_comment
            bed_depth_li[:] = np.interp(self.s2013, self.ps2013, self.bed_depth)

            # Avoid memory problems, see http://stackoverflow.com/questions/21435648/cubic-spline-memory-error
            if len(self.ps2013) < 6000:
                # Pressure sensor data linearly interpolated to IMU samples
                p_spline = self.ncFile.createVariable('P_SPLINE', 'float64', ('time',), fill_value=1.e20)
                p_spline.long_name = 'Pressure'
                p_spline.comment = ("Recorded pressure cubic spline interpolated to IMU samples with"
                                    " spline_func = scipy.interpolate.interp1d(self.ps2013, self.pr, kind='cubic');"
                                    " p_mask = ma.masked_less(ma.masked_greater(self.s2013, np.max(self.ps2013)), np.min(self.ps2013));"
                                    " inside_spline = spline_func(ma.compressed(p_mask));"
                                    " p_spline = spline_func(self.s2013); p_spline[ma.clump_unmasked(p_mask)] = inside_spline")
                p_spline.coordinates = 'time depth latitude longitude'
                p_spline.units = 'dbar'
                spline_func = interp1d(self.ps2013, self.pr_adj, kind='cubic')
                # Mask IMU points outside of pressure time, interpolate, then put back into filled array
                p_mask = ma.masked_less(ma.masked_greater(self.s2013, np.max(self.ps2013)), np.min(self.ps2013))
                inside_spline = spline_func(ma.compressed(p_mask))
                p_spline[ma.clump_unmasked(p_mask)] = inside_spline

                # First difference of splined pressure sensor data interpolated to IMU samples
                p_spline_rate = self.ncFile.createVariable('P_SPLINE_RATE', 'float64', ('time',), fill_value=1.e20)
                p_spline_rate.long_name = 'Rate of change of spline fit of pressure'
                p_spline_rate.comment = 'Pressure rate of change interpolated to IMU samples with p_spline_rate[ma.clump_unmasked(p_mask)] = np.append([0], np.diff(inside_spline)) * self.rateHz'
                p_spline_rate.coordinates = 'time depth latitude longitude'
                p_spline_rate.units = 'dbar/s'
                p_spline_rate[ma.clump_unmasked(p_mask)] = np.append([0], np.diff(inside_spline)) * self.rateHz

                # Spline interpolated bed depth
                bed_depth_csi = self.ncFile.createVariable('BED_DEPTH_CSI', 'float64', ('time',), fill_value=1.e20)
                bed_depth_csi.long_name = 'Depth of BED - Cubic Spline Interpolated to IMU Samples'
                bed_depth_csi.units = 'm'
                bed_depth_csi.coordinates = 'time depth latitude longitude'
                bed_depth_csi.comment = self.bed_depth_csi_comment
                bed_depth_csi[ma.clump_unmasked(self.p_mask)] = self.bed_depth_inside_spline

            else:
                print("Not creating cubic-spline interpolated variables, time series too long: {} points".format(len(self.ps2013)))

            # First difference of pressure sensor data interpolated to IMU samples
            p_rate = self.ncFile.createVariable('P_RATE', 'float64', ('time',))
            p_rate.long_name = 'Rate of change of pressure'
            p_rate.comment = 'Pressure rate of change interpolated to IMU samples with np.append([0], np.diff(np.interp(self.s2013, self.ps2013, self.pr))) * self.rateHz'
            p_rate.coordinates = 'time depth latitude longitude'
            p_rate.units = 'dbar/s'
            p_rate[:] = np.append([0], np.diff(np.interp(self.s2013, self.ps2013, self.pr_adj))) * self.rateHz

            # Compute implied distance and velocity based on 147 cm BED housing circumference
            rot_dist = self.ncFile.createVariable('ROT_DIST', 'float64', ('time', ))
            rot_dist.long_name = 'Implied distance traveled assuming pure rolling motion'
            rot_dist.comment = 'Computed with: ROT_COUNT * 1.47 m'
            rot_dist.coordinates = 'time depth latitude longitude'
            rot_dist.units = 'm'
            rot_dist[:] = rot_count[:] * 1.47

            implied_velocity = self.ncFile.createVariable('IMPLIED_VELOCITY', 'float64', ('time', ))
            implied_velocity.long_name = 'Implied BED velocity assuming pure rolling motion'
            implied_velocity.comment = 'Computed with: ROT_RATE * 1.47 / 360.0'
            implied_velocity.coordinates = 'time depth latitude longitude'
            implied_velocity.units = 'm/s'
            implied_velocity[:] = rot_rate[:] * 1.47 / 360.0

            if self.traj_dist_topo:
                # Distance over topo from mbgrdviz generated trajectory thalweg trace file
                self.dist_topo = self.ncFile.createVariable('DIST_TOPO', 'float64', ('time',))
                self.dist_topo.long_name = 'Distance over topography along thalweg'
                self.dist_topo.units = 'm'
                self.dist_topo.comment = ifmt.format(var='dist_topo', traj_file=self.args.trajectory, formula=
                        'np.interp(np.linspace(0,1,len(self.s2013)), np.linspace(0,1,len(self.traj_dist_topo)), self.traj_dist_topo)')
                self.dist_topo.coordinates = 'time depth latitude longitude'
                self.dist_topo[:] = np.interp(np.linspace(0,1,len(self.s2013)), np.linspace(0,1,len(self.traj_dist_topo)), self.traj_dist_topo)
    
            # Tumble rate & count
            tumble_rate = self.ncFile.createVariable('TUMBLE_RATE', 'float64', ('time', ))
            tumble_rate.long_name = 'Angle change of axis (vec) in axis-angle representation of BED rotation'
            tumble_rate.comment = 'Computed with: abs(last_vec.angle(vec))'
            tumble_rate.coordinates = 'time depth latitude longitude'
            tumble_rate.units = 'degree/second'
            tumble_rate[:] = self.tumblerate.reshape(len(self.tumblerate), 1, 1, 1)

            tumble_count = self.ncFile.createVariable('TUMBLE_COUNT', 'float64', ('time', ))
            tumble_count.long_name = 'Tumble Count - Cumulative Sum of TUMBLE_RATE * dt / 360 deg'
            tumble_count.comment = 'Computed with: np.cumsum(np.absolute(self.difftumble)) / 2. / np.pi'
            tumble_count.coordinates = 'time depth latitude longitude'
            tumble_count[:] = self.tumblecount

            # Compute tumble distance
            tumble_dist = self.ncFile.createVariable('TUMBLE_DIST', 'float64', ('time', ))
            tumble_dist.long_name = 'Implied distance traveled assuming tumbling translates to horizontal motion'
            tumble_dist.comment = 'Computed with: TUMBLE_COUNT * 1.47 m'
            tumble_dist.coordinates = 'time depth latitude longitude'
            tumble_dist.units = 'm'
            tumble_dist[:] = tumble_count[:] * 1.47

            # Sum of rotation and tumbling distances
            rot_plus_tumble_dist = self.ncFile.createVariable('ROT_PLUS_TUMBLE_DIST', 'float64', ('time', ))
            rot_plus_tumble_dist.long_name = 'Implied distance traveled assuming pure rolling motion'
            rot_plus_tumble_dist.comment = 'Computed with: ROT_DIST + TUMBLE_DIST'
            rot_plus_tumble_dist.coordinates = 'time depth latitude longitude'
            rot_plus_tumble_dist.units = 'm'
            rot_plus_tumble_dist[:] = rot_dist[:] + tumble_dist[:]

            # Tide data from OSTP Software calculation
            tide = self.ncFile.createVariable('TIDE', 'float64', ('time'))
            tide.long_name = 'OSTP2 Tide model height'
            tide.coordinates = 'time depth latitude longitude'
            tide.comment = self.tide_comment
            tide.units = 'm'
            tide[:] = np.interp(self.s2013, self.ps2013, self.tide)

        # Add the global metadata, overriding with command line options provided
        self.add_global_metadata()
        self.ncFile.title = 'Orientation and acceleration data from Benthic Event Detector'
        if self.args.title:
            self.ncFile.title = self.args.title
        if self.args.summary:
            self.ncFile.summary = self.args.summary

        self.ncFile.close()

    def process_command_line(self):

        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n\n'
        examples += '  For 12 April 2013 BED01 deployment:\n'
        examples += '    ' + sys.argv[0] + " --input BED00048.EVT --output BED00048.nc --lat 36.793458 --lon -121.845703 --depth 295 --decode\n"
        examples += '  For 1 June 2013 BED01 Canyon Event:\n'
        examples += '    ' + sys.argv[0] + " --input BED00038.EVT --lat 36.793458 --lon -121.845703 --depth 340 --decode\n"
        examples += '    ' + sys.argv[0] + " --input BED00039.EVT --lat 36.785428 --lon -121.903602 --depth 530 --decode\n"
        examples += '    ' + sys.argv[0] + " --input BED00038.EVT BED00039.EVT --output BED01_1_June_2013.nc --trajectory BEDSLocation1_ThalwegTrace.csv  --decode\n"
        examples += '  For 18 February 2014 BED03 Canyon Event:\n'
        examples += '    ' + sys.argv[0] + " --input 30100046_partial_decimated10.EVT --lat 36.793367 --lon -121.8456035 --depth 292 --decode\n"
        examples += '  For 15 January 2016 BED03 Canyon Event with clock set to PDT:\n'
        examples += '    ' + sys.argv[0] + " -i 30200101.EVT.OUT -o 30200101.nc --lat 36.795040 --lon -121.869912 --depth 390 --seconds_offset 28800 -t 'BED03 Deployment in Monterey Canyon in October 2015 for the CCE project'\n"

        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Convert BED event file(s) to a NetCDF file',
                                         epilog=examples)

        parser.add_argument('-i', '--input', action='store', nargs='*', required=True, help="Specify input event file name(s)")
        parser.add_argument('-o', '--output', action='store', help="Specify output NetCDF file name, if different from <base>.nc of input file name")
        parser.add_argument('-t', '--trajectory', action='store', help="csv file with columns of latitude and longitude where first and lat row corresponds to first and last records of input event files")
        parser.add_argument('--lat', type=float, action='store', help="latitude of BED device")
        parser.add_argument('--lon', type=float, action='store', help="longitude of BED device")
        parser.add_argument('--depth', type=float, action='store', help="depth of BED device")
        parser.add_argument('--seconds_offset', type=float, action='store', help="Add seconds to time in source file to make accurate GMT time", default=0.0)
        parser.add_argument('--seconds_slope', type=float, action='store', help="Adjust time in source file for drift, per second", default=0.0)
        parser.add_argument('--bar_offset', type=float, action='store', help="Add value to pressure in source file", default=0.0)
        parser.add_argument('--bar_slope', type=float, action='store', help="Adjust pressure in source file for drift", default=0.0)
        parser.add_argument('--bed_name', action='store', help='Name of the BED, e.g. BED06, BED10')
        parser.add_argument('--yaw_offset', type=float, action='store', help="Add value to yaw rotation angle", default=0.0)
        parser.add_argument('--decode', action='store_true', help="Pass the file contents through Bob's decode program")
        parser.add_argument('--title', action='store', help='A short description of the dataset')
        parser.add_argument('--summary', action='store', help='Additional information about the dataset')
        parser.add_argument('--beg_depth', type=float, action='store', help='Begining depth for lookup from trajectory file')
        parser.add_argument('--end_depth', type=float, action='store', help='Ending depth for lookup from trajectory file')
        parser.add_argument('--stride_imu', type=int, action='store', help='Records of IMU data to skip', default=1)
        parser.add_argument('--no_tide_removal', action='store_true', help='Default is to remove tides using OSTP2')
        parser.add_argument('--compare_euler', action='store_true', help='Report differences between Quaternion.get_euler() and transforms3d.euler.quat2euler()')
        parser.add_argument('--read_csv', action='store_true', help='Read from the csv format produced by decodeBEDS.py')

        parser.add_argument('-v', '--verbose', type=int, choices=list(range(3)), action='store', default=0, help="Specify verbosity level, values greater than 1 give more details ")

        self.args = parser.parse_args()

        if not self.args.input:
            parser.error("Must specify --input\n")

        if self.args.trajectory:
            pass
        else:
            if (self.args.lat and self.args.lon and self.args.depth):
                pass
            else:
                parser.error("If no --trajectory specified then must specify --lat, --lon, and --depth")

        self.commandline = ' '.join(sys.argv)
        self.inputFileNames = self.args.input
        if self.args.lat and self.args.lon and self.args.depth:
            self.lat = self.args.lat
            self.lon = self.args.lon
            self.dpth = self.args.depth
            self.featureType = 'timeseries'
            if self.args.verbose > 0:
                print("self.lat = %f, self.lon = %f, self.dpth = %f" % (self.lat, self.lon, self.dpth))
        elif self.args.trajectory:
            self.featureType = 'trajectory'
        else:
            raise Exception("Unknown featureType - must be timeseries or trajectory")

        for fileName in self.inputFileNames:
            if fileName[-3:] in self.invensense_extenstions:
                self.sensorType = 'Invensense'
            else:
                raise Exception("Unknown file: %s. Input file must end in %s." % (fileName, 
                                self.invensense_extenstions))
    
if __name__ == '__main__':

    beds_netcdf = BEDS_NetCDF()

    beds_netcdf.process_command_line()

    beds_netcdf.createNetCDFfromFile()

    print("Wrote file %s\n" % beds_netcdf.outFile)

