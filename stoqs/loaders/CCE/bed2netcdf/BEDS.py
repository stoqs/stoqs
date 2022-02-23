#!/usr/bin/env python
'''
Base classes for reading and writing data for the BEDs project.
Calibrations and assignment of comment text are done here based
on args assigned by subclasses of BEDS.

--
Mike McCann
MBARI 3 April 2014

$Id: BEDS.py 13837 2019-08-12 22:58:11Z mccann $
'''

import os
import sys
import csv
import time
import coards
import glob
import numpy as np
import numpy.ma as ma
from collections import namedtuple
from datetime import datetime
from euclid import Quaternion, Vector3
from pupynere import netcdf_file
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter
from seawater import eos80
from subprocess import Popen, PIPE
from transforms3d.euler import quat2euler
from util import quatern2euler, quaternConj, quatern2eulervector


Polynomial = namedtuple('Polynomial', ['a', 'b', 'c'])

bcal = { 'BED00': Polynomial(1, 1, 0),
         'BED02': Polynomial(0.5469, 23.411, -11.36), 
         'BED03': Polynomial(0.5773, 23.01987, -11.76974),
         'BED04': Polynomial(0.57435, 23.21402, -11.49648),
         # Tuned by hand to get initial depth of 392.4 m per email exchange with Roberto on 8 April 2019
         'BED05': Polynomial(0.55, 23.2, -12.09),
         'BED06': Polynomial(0.4777, 23.14, -11.88),
         'BED07': Polynomial(0.4693, 23.611, -11.719),
         'BED08': Polynomial(0.5558, 23.188, -11.406),
         'BED09': Polynomial(0.5421, 23.221, -11.85),
         'BED10': Polynomial(0.4229, 23.622, -12.012),
         'BED11': Polynomial(0.3953, 23.522, -11.29),
       }

class NoPressureData(Exception):
    pass


class BEDS(object):
    '''
    Container for common methods to be reused by BEDs processing software.
    Initially used by bed2netcdf.py and bed2x3d.py to read the data.
    '''

    invensense_extenstions = ('EVT', 'WAT', 'E00', 'OUT')

    def __init__(self):
        '''
        Initialize arrays
        '''
        self.secList = []
        self.pSecList = []
        self.pFromCountList = []
        self.dFromCountList = []
        self.pBarList = []
        self.bed_depth = []

        self.axList = []
        self.ayList = []
        self.azList = []
        self.quatList = []

        self.rxList = []
        self.ryList = []
        self.rzList = []

        self.pxList = []
        self.pyList = []
        self.pzList = []
        self.protList = []

        self.mxList = [0]
        self.myList = [0]
        self.mzList = [0]
        self.diffrotList = [0]
        self.difftumbleList = [0]

        self.traj_lat = []
        self.traj_lon = []
        self.traj_dist_topo = []
        self.traj_depth = []

    def read_ssv_file(self, beg_depth, end_depth):
        '''File provided by Eve in July 2016. Fill traj_ arrays for depths between beg_depth and end_depth.
        '''
        self.traj_lat = []
        self.traj_lon = []
        self.traj_dist_topo = []
        self.traj_depth = []
        with open(self.args.trajectory) as fp:
            for r in csv.DictReader((row for row in fp if not row.startswith('#')), delimiter=' '):
                if abs(float(r['topo_m'])) >= beg_depth and abs(float(r['topo_m'])) <= end_depth:
                    self.traj_lat.append(float(r['lat']))
                    self.traj_lon.append(float(r['long']))
                    self.traj_dist_topo.append(float(r['dist_topo_m']))
                    self.traj_depth.append(-float(r['topo_m']))

        if not self.traj_lat:
            print("No downhill trajectory read, trying uphill")
            with open(self.args.trajectory) as fp:
                for r in reversed(list(csv.DictReader((row for row in fp if not row.startswith('#')), delimiter=' '))):
                    if abs(float(r['topo_m'])) <= beg_depth and abs(float(r['topo_m'])) >= end_depth:
                        self.traj_lat.append(float(r['lat']))
                        self.traj_lon.append(float(r['long']))
                        self.traj_dist_topo.append(float(r['dist_topo_m']))
                        self.traj_depth.append(-float(r['topo_m']))

    def readTrajectory(self, beg_depth, end_depth):
        '''Read file specified with --trajectory option into lists of lats and lons
        '''
        if self.args.trajectory.endswith('.ssv'):
            self.read_ssv_file(beg_depth, end_depth)
        else:
            # Entire file defines the trajectory - as .csv files created for BEDs floating up
            for r in csv.DictReader(open(self.args.trajectory), delimiter=','):
                self.traj_lat.append(float(r['latitude']))
                self.traj_lon.append(float(r['longitude']))

    def cumtrapz(self, x, y):
        '''Returns indefinite integral of discrete data in y wrt x.  

        Test with:
            >> cumtrapz([0,.2,.4,.6,.8],[1:5])                              ! Matlab
            ans =
                     0    0.3000    0.8000    1.5000    2.4000

            print self.cumtrapz([.0,.2,.4,.6,.8], np.array([1,2,3,4,5]))    ! Python
            [ 0.   0.3  0.8  1.5  2.4]
        '''

        sumA = 0
        sumAList = [sumA]
        for i in range(len(y))[:-1]:
            A = (x[i+1] - x[i]) * (y[i] + y[i+1]) / 2.0
            sumA = sumA + A
            sumAList.append(sumA)

        return np.array(sumAList)

    def add_global_metadata(self):
        '''Use instance variables to write metadata specific for the data that are written
        '''

        iso_now = datetime.utcnow().isoformat() + 'Z'

        summary = 'Benthic Event Detector data from an in situ instrument designed to capture turbidity currents. '
        if self.args.seconds_offset:
            summary += 'Time adjusted with --seconds_offset {}'.format(self.args.seconds_offset)
        if self.args.seconds_slope:
            summary += ' --seconds_slope {}. '.format(self.args.seconds_slope)
        if self.args.bar_offset:
            summary += 'Pressure adjusted with --bar_offset {}'.format(self.args.bar_offset)
        if self.args.bar_slope:
            summary += '--bar_slope {}. '.format(self.args.bar_slope)
        if self.args.yaw_offset:
            summary += 'Yaw angle adjusted with --yaw_offset {}.'.format(self.args.yaw_offset)
        if self.args.trajectory and self.args.beg_depth and self.args.end_depth:
            summary += ' Positions extracted from thalweg file {} between depths {} and {}.'.format(
                        self.args.trajectory, self.args.beg_depth, self.args.end_depth)
        if self.args.trajectory:
            summary += ' Positions extracted from thalweg file {} between depths {} and {}.'.format(
                        self.args.trajectory, self.bed_depth[0], self.bed_depth[-1])

        summary += ' Data read from input file(s) {}.'.format(self.args.input)

        for v in ('seconds_offset', 'seconds_slope', 'bar_offset', 'bar_slope', 'yaw_offset'):
            setattr(self.ncFile, v, getattr(self.args, v))

        self.ncFile.summary = summary
        self.ncFile.netcdf_version = '3.6'
        self.ncFile.Conventions = 'CF-1.6'
        self.ncFile.date_created = iso_now
        self.ncFile.date_update = iso_now
        self.ncFile.date_modified = iso_now
        self.ncFile.featureType = self.featureType
        if self.featureType == 'trajectory':
            self.ncFile.geospatial_lat_min = np.min(self.latitude[:])
            self.ncFile.geospatial_lat_max = np.max(self.latitude[:])
            self.ncFile.geospatial_lon_min = np.min(self.longitude[:])
            self.ncFile.geospatial_lon_max = np.max(self.longitude[:])
            self.ncFile.geospatial_lat_units = 'degree_north'
            self.ncFile.geospatial_lon_units = 'degree_east'

            self.ncFile.geospatial_vertical_min= np.min(self.depth[:])
            self.ncFile.geospatial_vertical_max= np.max(self.depth[:])
            self.ncFile.geospatial_vertical_units = 'm'
            self.ncFile.geospatial_vertical_positive = 'down'

            self.ncFile.comment = ('BED devices measure 3 axes of acceleration and rotation about those'
                                   ' 3 axes at 50 Hz. They also measure pressure at 1 Hz during an event.'
                                   ' Those data are represented in this file as variables XA, YA, ZA, XR,'
                                   ' YR, ZR, and P. Additional variables are computed by the bed2netcdf.py'
                                   ' program; see the long_name and comment attributes for explanations.'
                                   ' Source code for the calucations are in the bed2netcdf.py, BEDS.py,'
                                   ' and util.py files on the subversion source code control server at MBARI:'
                                   ' http://kahuna.shore.mbari.org/viewvc/svn/BEDs/trunk/BEDs/Visualization/py/.')

        self.ncFile.time_coverage_start = coards.from_udunits(self.time[0], self.time.units).isoformat() + 'Z'
        self.ncFile.time_coverage_end = coards.from_udunits(self.time[-1], self.time.units).isoformat() + 'Z'

        self.ncFile.distribution_statement = 'Any use requires prior approval from the MBARI BEDS PI: Dr. Charles Paull'
        self.ncFile.license = self.ncFile.distribution_statement
        self.ncFile.useconst = 'Not intended for legal use. Data may contain inaccuracies.'
        self.ncFile.history = 'Created by "%s" on %s' % (' '.join(sys.argv), iso_now,)

    def pCount2Bar(self, count):
        '''
        Simple hard coding of Bob & Denis adc.c adcEngValue() function to convert pressure in counts to engineering units,
        in this case bars.  From adc.c and decode.c:

            #define VREF            2.50
            #define RAW_TO_VOLTS(n)     ((float)(n) * VREF / 65536.0)


            typedef struct
            {
                Flt32   a;
                Flt32   b;
                char    *units;
            } ADConversion;
            
            MLocal ADConversion adConv[] =
            { {12.11, 0.0, "Batt Volts"},  {12.11, 0.0, "Batt Volts"},
              {35.0, 8.75, "bar"}, {50.0, 12.5, "psia"},
              {100.0, 50.0, "degC"}, {47.175, 23.82, "%"},
              {1.0, 0.0, "Volts"}
            };
            
              dcEngValue(Nat16 chan, Nat16 counts, char **unitp)
            {
                if (chan >= NumberOf(adConv))
                chan = HUMIDITY_CHAN + 1;
            
                           if (unitp != NULL)
                   *unitp = adConv[chan].units;
            
               return((adConv[chan].a * RAW_TO_VOLTS(counts)) - adConv[chan].b);
            
            } /* adcEngValue() */
        '''

        return 35.0 * (count * 2.50 / 65536.0)  - 8.75 

    def pCount2p_and_d(self, name, count):
        ''' 
        Convert pressure count to pressure and depth using second degree polynomial.
        Return corrected pressure and depth.


        From: Roberto Gwiazda <rgwiazda@mbari.org>
        Subject: BEDs Equations
        Date: November 9, 2016 at 8:12:16 AM PST
        To: Mike McCann <mccann@mbari.org>

        Hi Mike,

        Here are the equations:

        First convert counts to volts:

        volts = 5 * (65536 / counts)
        N.B.: Confirmed that instead it's "volts = 5 * (counts / 65536)" 

        Then volts and pressure are related in a second degree polynomial = a Volts ^2 + b Volts + c

                a       b           c
        BED 2   0.5469  23.411      -11.36  
        BED 3   0.5773  23.01987    -11.76974
        BED 4   0.57435 23.21402    -11.49648
        BED 5   -0.5621 25.074      -13.087
        BED 6   0.4777  23.14       -11.88
        BED 7   0.4693  23.611      -11.719
        BED 8   0.5558  23.188      -11.406
        BED 9   0.5421  23.221      -11.85
        BED 10  0.4229  23.622      -12.012
        BED 11  0.3953  23.522      -11.29

        Then I converted pressure to depth by multiplying by 9.948.

        Roberto


        from: Roberto Gwiazda <rgwiazda@mbari.org>
        Subject: Re: BEDs Equations
        Date: February 2, 2017 at 9:55:13 AM PST
        To: Mike McCann <mccann@mbari.org>

        Hi Mike,
        You are correct about the formula. I had used the 9.948 factor in the past because it was 
        simple and I knew I had not corrected yet for tide, but once I started to correct for tide 
        I switched to the UNESCO formula.

        Roberto
        On Feb 2, 2017, at 9:43 AM, Mike McCann <mccann@mbari.org> wrote:

        Hi Roberto,

        I'm reviewing my pressure to depth calculations for BEDs data and have a question about the 9.948 factor.

        Does this come from the Fofonoff and Millard algorithm? (http://unesdoc.unesco.org/images/0005/000598/059832eb.pdf)

        I usually use the seawater.eos80.dpth(p, lat) Python function to convert pressure to depth: 
        https://pythonhosted.org/seawater/eos80.html#seawater.eos80.dpth

        For BED09 at 202 m (April 2016 .WAT files) I get a factor that's different from yours:

        np.mean(eos80.dpth(self.pr_adj, lat) / self.pr_adj) * 10
        9.921347164833179

        This calculation uses a lat value of 36.796156. Can the difference between your factor and mine be 
        explained by a different value for latitude?

        -Mike

        '''

        if self.args.bed_name == 'BED03' and datetime.utcfromtimestamp(self.secList[0]).year < 2015:
            p = 87.5 * float(count) / 65536.0 - 8.75 - 1.0
        else:
            volts = 5.0 * float(count / 65536.0)
            p = bcal[name].a * volts ** 2 + bcal[name].b * volts + bcal[name].c


        if self.traj_lat:
            lat = np.mean(self.traj_lat)
        elif self.args.lat is not None:
            lat = self.args.lat
        else:
            # Initial lat is near Monterey
            dp = eos80.dpth(p * 10, 36.8)
            self.readTrajectory(dp, dp + 10)
            lat = np.mean(self.traj_lat)
            print("Initial extraction of thalweg between depths {} and {} to get latitude for depth calculation: {}".format(dp, dp + 10, lat))

        # Convert pressures from bar to dbar here
        p = p * 10
        d = eos80.dpth(p, lat)

        return p, d

    def second_marker_to_esec(self, dt_string):
        '''Convert string like '01/15/2016 14:54:23' to 
        Unix epoch seconds.  Assumes dt_string is GMT.
        '''
        return (datetime.strptime(dt_string, '%m/%d/%Y %H:%M:%S') -
                datetime(1970, 1, 1)).total_seconds()

    def readBEDsFile(self, infile, decode=False):
        '''
        Open @infile, read values, apply offsets and scaling.
        Return numpy arrays of the acceleration and rotation data as originally recorded.

        Output from 'decode -d <file>' looks like:

            FileHdr ver=1 ID=0 rate=3000 2013/02/11 09:23:53.700 dur=26.614
            Second Marker 1360574634 2013/02/11 09:23:54
            Ext Pressure 0 counts  0.00 volts
            Inertial Data  acc:  0.00397  0.00249  0.03131  quat:  0.99365  0.00409 -0.01617  0.11078
            Inertial Data  acc:  0.00137  0.00266  0.03006  quat:  0.99365  0.00415 -0.01624  0.11078

        Note: A special version of decode.c exists in this directory with printf customizations beyond
        what Bob initially wrote.  This is a stopgap solution until this python script can be modified 
        to read the records directly.  We want to eventually do this modification so that this script
        can work everywhere.

        This method may be called multiple times in order to append data from multiple .EVT files.
        '''

        self.rateHz = None
        esec = None

        # Use Bob's decode program and pipe its output into our parser
        if decode:
            p1 = Popen(["./decode", "-d", infile], stdout=PIPE)
            reader = p1.stdout
        else:
            reader = open(infile)

        imu_count = 0
        for line in reader:
            if self.args.verbose > 1: 
                    print(line)

            if line.startswith('FileHdr'):
                # FileHdr ver=1 ID=0 rate=3000 2013/02/11 09:23:53.700 dur=26.614
                # convert cycles/min to Hz
                self.rateHz = float(line.split()[3].split('=')[1]) / 60.0

            if line.startswith('Second Marker'):
                # From my specially modified decode.c: Second Marker 1360574634 2013/02/11 09:23:54
                # After move to 64-bit my decode no longer works; original format: Second Marker 2013/02/11 09:23:54
                # Note: the 'Second Marker' is jittery, compare with accumulated time (esec) from the beginning
                dt_str = ' '.join(line.split()[2:])
                if not esec:
                    esec = self.second_marker_to_esec(dt_str)

                esec_diff = abs(self.second_marker_to_esec(dt_str) - esec)
                if self.args.verbose > 1:
                    print('esec_diff =', esec_diff)

                if esec_diff > 2 and 'WAT' not in infile:
                    # Ignore warning from .WAT.OUT files
                    print("WARNING: esec_diff is greater than 2", esec_diff)

            if line.startswith('Ext Pressure'):
                count = float(line.split()[2])
                if self.args.bed_name:
                    p, d = self.pCount2p_and_d(self.args.bed_name, count)
                    self.pFromCountList.append(p)
                    self.dFromCountList.append(d)

                # In 2016 decoded data now look like:
                # Second Marker 01/15/2016 14:35:57
                # Ext Pressure 17655 counts 0.673 volts 21.174 bar
                self.pSecList.append(esec)
                self.pBarList.append(float(line.split()[6]) * 10.0)

            if esec and line.startswith('Inertial'):
                imu_count += 1
                if imu_count % self.args.stride_imu != 0:
                    continue

                acc = line.split(':')[1].split()[:3]

                # Time and accelerations
                self.secList.append(esec)
                self.axList.append(float(acc[0]))
                self.ayList.append(float(acc[1]))
                self.azList.append(float(acc[2]))

                # Rotations as quaternions
                qs = line.split(':')[2].split()[:4]
                self.quatList.append( (float(qs[0]), float(qs[1]), float(qs[2]), float(qs[3])) )

                esec += self.args.stride_imu / self.rateHz
                if self.args.verbose > 1:
                    print(esec)

        # Bail out if no pressure data - event must be at least a second in duration
        if len(self.pSecList) == 0:
            raise NoPressureData('No pressure data in file %s' % infile)

        # Make the Lists numpy arrays so that we can do matrix math operations; they have units of seconds and bar
        self.s = np.array(self.secList)
        self.s2013 = self.s - 1356998400.0      # (date(2013,1,1)-date(1970,1,1)).total_seconds() in python2.7
        self.ps = np.array(self.pSecList)
        self.ps2013 = np.array(self.pSecList) - 1356998400.0
        self.pr = np.array(self.pBarList)

        self.process_bed_depth()

    def readBEDs_csv_File(self, infile, decode=False):
        '''
        Open @infile, read values, apply offsets and scaling.
        Return numpy arrays of the acceleration and rotation data as originally recorded.

        Output from 'decodeBEDS.py -o 20200995.EVT.OUT 20200995.EVT' looks like:

            recNum,epoch_time,date_time,accel_x,accel_y,accel_z,roll,pitch,heading,quat_w,quat_x,quat_y,quat_z,pressureCnts,pressure,units,startTimeEpoch,startTime,duration,maxAccel,filename,startTimeEpoch,startTime,battV,minModemBatt,extPressure,intPresssure,intTemp,intHumidity,
            0,1641329599.200,2022-01-04 20:53:19.200000,-0.06299,-0.01514,1.003,179.5,18.85,175.8,0.1635,-0.03646,-0.009919,0.9858,,,,,,,,,,,,,,,,,
            1,1641329599.200,2022-01-04 20:53:19.200000,-0.0708,0.009766,1.0,179.6,18.82,175.8,0.1633,-0.03629,-0.009298,0.9859,,,,,,,,,,,,,,,,,
            2,1641329599.000,2022-01-04 20:53:19,-0.0708,0.009766,1.0,179.6,18.82,175.8,0.1633,-0.03629,-0.009298,0.9859,,,,,,,,,,,,,,,,,
        '''

        self.rateHz = 50

        last_esec = 0.0
        for r in csv.DictReader(open(infile), delimiter=','):
            if self.args.verbose > 1: 
                print(r)
            if float(r['epoch_time']) <= last_esec:
                print(f"Skipping duplicate or decreasing time: {float(r['epoch_time'])}")
                continue
            self.secList.append(float(r['epoch_time']))
            last_esec = float(r['epoch_time'])
            self.axList.append(float(r['accel_x']))
            self.ayList.append(float(r['accel_y']))
            self.azList.append(float(r['accel_z']))
            self.quatList.append( (float(r['quat_w']), float(r['quat_x']), float(r['quat_y']), float(r['quat_z'])) )
            if r.get('pressure'):
                self.pBarList.append(float(r['pressure']))
            else:
                self.pBarList.append(np.nan)


        # Make the Lists numpy arrays so that we can do matrix math operations; they have units of seconds and bar
        self.s = np.array(self.secList)
        self.s2013 = self.s - 1356998400.0      # (date(2013,1,1)-date(1970,1,1)).total_seconds() in python2.7
        # In csv file pressure is at same time intervalsa as the IMU data
        self.ps = np.array(self.secList)
        self.ps2013 = self.s - 1356998400.0      # (date(2013,1,1)-date(1970,1,1)).total_seconds() in python2.7
        self.pr = np.array(self.pBarList)

        self.process_bed_depth()



    def process_bed_depth(self):
        '''Build depth paramters that will be the coordinate variable for trajectory data
        and record variables for both timeseries and trajectory data. Original sampled
        (1 second) data is available, but commonly used bed_depth (bed_depth_csi member
        variable) will be cubic spline interpolated to IMU samples.
        '''
       
        self.pr_adj_comment = '' 
        if self.args.bed_name:
            if self.args.bed_name == 'BED03' and datetime.utcfromtimestamp(self.secList[0]).year < 2015:
                self.pr_adj_comment = "Recorded pressure computed with p = 87.5 * float(count) / 65536.0 - 8.75 - 1.0"
            else:
                # Use pressure and depth computed from count with 2nd degree polynomial calibration
                self.pr_adj_comment = "Recorded pressure adjusted with bcal[{}] = {}".format(
                                                    self.args.bed_name, bcal[self.args.bed_name])
            self.pr_adj = np.array(self.pFromCountList)
            self.bed_depth_comment = "{}. Depth computed using UNESCO formula.".format(self.pr_adj_comment)
            self.bed_depth = np.array(self.dFromCountList)
        else:
            if self.args.bar_offset or self.args.bar_slope:
                self.pr_adj_comment = 'Recorded pressure adjusted with bar_offset = {bo} and bar_slope = {bs}'.format(
                                                    bo=self.args.bar_offset, bs=self.args.bar_slope)
            self.pr_adj = self.pr + 10.0 * self.args.bar_offset + self.pr * 10.0 * self.args.bar_slope
            if hasattr(self, 'pr_adj_comment'):
                pr_comment = self.pr_adj_comment
            else:
                pr_comment = ''
            self.bed_depth_comment = "{}. Depth computed with eos80.dpth(self.pr_adj, np.mean(self.traj_lat)).".format(
                                                pr_comment)
            if self.traj_lat:
                lat = np.mean(self.traj_lat)
            elif self.args.lat is not None:
                lat = self.args.lat
            else:
                raise Exception('Cannot compute depth without a latitude value')

            self.bed_depth = eos80.dpth(self.pr_adj, lat)

        # Default behaviour is to remove the tide
        if not self.args.no_tide_removal:
            tide_command = self.computeTide()
            print("Subtracting tide, mean value = {} m".format(np.mean(self.tide)))
            self.bed_depth_comment += " Tide removed using output from: {}".format(tide_command)
            self.bed_depth -= self.tide

        # Spline interpolated bed depth - Mask IMU points outside of 
        #   pressure time, interpolate, save as member variables for 
        #   putting back into filled array in derived class
        try:
            spline_func = interp1d(self.ps2013, self.bed_depth, kind='cubic')
        except (TypeError, ValueError) as e:
            print((str(e)))
            print('Not able to calculate spline interpolation of depth data')
        else:
            self.p_mask = ma.masked_less(ma.masked_greater(self.s2013, np.max(self.ps2013)), np.min(self.ps2013))
            self.bed_depth_inside_spline = spline_func(ma.compressed(self.p_mask))
            self.bed_depth_csi_comment = "{} Cubic spline interpolated to IMU samples.".format(self.bed_depth_comment)

    def processAccelerations(self):
        '''
        For member component accelerations produce additional useful member lists
        '''
        self.ax = np.array(self.axList)
        self.ay = np.array(self.ayList)
        self.az = np.array(self.azList)

        self.a = np.sqrt(self.ax**2 + self.ay**2 + self.az**2)

    def processRotations(self, useMatlabCode=False):
        '''
        For member quatList of quaternion tuples produce additional useful member lists for graphical display and analysis
        '''
        # "Quaternions came from Hamilton after his really good work had been done; and, though beautifully ingenious, 
        # have been an unmixed evil to those who have touched them in any way, including Clerk Maxwell." - Lord Kelvin, 1892.

        # If readBEDsFile() processes multiple BED files then subsequent self.quatLists will include concatenated data, initialize appended to lists
        self.rxList = []
        self.ryList = []
        self.rzList = []

        self.pxList = []
        self.pyList = []
        self.pzList = []
        self.protList = []
   
        self.mxList = [0]
        self.myList = [0]
        self.mzList = [0]
        self.diffrotList = [0]
        self.difftumbleList = [0]

        mx = my = mz = 0
        diffrot = 0
        diffrot_sum = 0
        for i, quat in enumerate(self.quatList):
            if self.args.verbose > 1:
                print("quat = ",  quat)

            if useMatlabCode:
                # Convert to Euler angles using same code that Brian's Matlab conversion uses
                q = Quaternion(*quat)
                zRot, yRot, xRot = quatern2euler([q.x, q.y, q.z, q.w])
                self.euler_comment = 'Converted from recorded Quaternion with quatern2euler() function'
            else:
                q = Quaternion(*quat)
                # Quaternion.get_euler() returns heading, attitude, bank (For X3D we get: yRot, zRot, xRot)

                yRot, zRot, xRot = q.get_euler()
                self.euler_comment = 'Converted from recorded Quaternion with Python euclid package Quaternion.get_euler() method'

                # In March of 2017 I had some doubt about the validity of the output from .get_euler(), so
                # I ran some comparisons using quat2euler() from the transforms3d package. Use --compare_euler
                # to execute the code. My conclusion is that instances where the values are not all close
                # are instances where gymbol lock happens due to the ambiguity of Euler angle representation
                # of coordinate system rotations.  I don't have exterme confidence in this conclusion, but 
                # just the same when we have original data in quaternion form it's better to use the angle_axis
                # form of the coordinate system rotation as it is more concise in its X3D represetation and
                # does not have the gimbol lock problem.  - Mike McCann, 6 March 2017
                if self.args.compare_euler:
                    tyRot, tzRot, txRot = quat2euler((q.w, q.x, q.y, q.z), axes='ryzx')
                    if not np.allclose((yRot, zRot, xRot), (tyRot, tzRot, txRot), atol=0.01):
                        print(('Quaternion.get_euler() does not agree with transforms3d.euler.quat2euler() at i = {}:'.format(i)))
                        print(('.get_euler()  y, z, x: {:7.3f} {:7.3f} {:7.3f}'.format(yRot, zRot, xRot)))
                        print(('.quat2euler() y, z, x: {:7.3f} {:7.3f} {:7.3f}'.format(tyRot, tzRot, txRot)))
                    
                ##self.euler_comment = 'Converted from recorded Quaternion with Python transforms3d.taitbryan package quat2euler() function'

            if useMatlabCode:
                # Convert to Euler Vectors using SpinCalc code
                q = Quaternion(*quat)
                px, py, pz, prot = quatern2eulervector(quaternConj([q.x, q.y, q.z, q.w]))
                pvec = Vector3(px, py, pz)
                prot = prot * np.pi / 180.0
                self.p_angle_axis_comment = 'Converted from recorded Quaternion with Matlab quatern2eulervector() function'
            else:
                q = Quaternion(*quat)
                try:
                    prot, pvec = q.get_angle_axis()
                except ValueError as e:
                    print(e)
                    print('WARNING: Using previous quaternion at index %d' % i)
                    q = Quaternion(*last_quat)
                    prot, pvec = q.get_angle_axis()

                px = pvec.x
                py = pvec.y
                pz = pvec.z
                self.p_angle_axis_comment = 'Converted from recorded Quaternion measurement with Python euclid package Quaternion.get_angle_axis() method'

            self.rxList.append(xRot)
            self.ryList.append(yRot)
            self.rzList.append(zRot)

            # Because of potential ambiguities of quaternion conversion to Euler angles (roll, pitch, yaw) also
            # save the .get_angle_axis() version of the quaternion.
            self.pxList.append(px)
            self.pyList.append(py)
            self.pzList.append(pz)
            self.protList.append(prot)
       
            # Compute first difference (division) to get rotation rate
            if i > 0:
                dq = Quaternion(*quat) * Quaternion(*last_quat).conjugated()
                if useMatlabCode:
                    mx, my, mz, diffrot = quatern2eulervector([dq.x, dq.y, dq.z, dq.w])
                    vec = Vector3(mx, my, mz)
                    diffrot = diffrot * np.pi / 180.0
                    self.m_angle_axis_comment = 'Converted from division of Quaternions with Matlab quatern2eulervector() function'
                else:
                    try:
                        diffrot, vec = dq.get_angle_axis()
                    except ValueError as e:
                        print(e)
                        print('WARNING: Using previous quaternion difference at index %d' % i)
                        diffrot, vec = last_dq.get_angle_axis()

                    self.m_angle_axis_comment = 'Computed with dq = Quaternion(*quat) * Quaternion(*last_quat).conjugated(); dq.get_angle_axis()'
                    vec = vec.normalize()
                    mx = vec.x
                    my = vec.y
                    mz = vec.z

                self.mxList.append(mx)
                self.myList.append(my)
                self.mzList.append(mz)
                self.diffrotList.append(diffrot)

                try:
                    self.difftumbleList.append(abs(last_vec.angle(vec)))
                except ValueError:
                    self.difftumbleList.append(0.0)
                except ZeroDivisionError:
                    self.difftumbleList.append(0.0)

                if self.args.verbose > 1:
                    print("diffrot = ",  diffrot)

                diffrot_sum += diffrot
                last_dq = dq
                last_vec = vec
            else:
                last_vec = pvec

            last_quat = quat

            if self.args.verbose:
                fmtStr = "%2d. xRot, yRot, zRot, diffrot, diffrot_sum = %6.3f %6.3f %6.3f %6.3f %6.3f"
                fmtStr += "  px, py, pz, prot = %6.3f %6.3f %6.3f %6.3f"
                print(fmtStr % (i+1, xRot, yRot, zRot, diffrot, diffrot_sum, px, py, pz, prot))

        self.rx = np.array(self.rxList)
        self.ry = np.array(self.ryList)
        self.rz = np.array(self.rzList)

        self.mx = np.array(self.mxList)
        self.my = np.array(self.myList)
        self.mz = np.array(self.mzList)

        self.px = np.array(self.pxList)
        self.py = np.array(self.pyList)
        self.pz = np.array(self.pzList)
        self.angle = np.array(self.protList)
        self.angle_rate_comment = 'Calculated with: np.absolute(np.concatenate(([0], np.diff(self.angle)))) * self.rateHz * 180.0 / np.pi'
        self.angle_rate = np.absolute(np.concatenate(([0], np.diff(self.angle)))) * self.rateHz * 180.0 / np.pi
        self.angle_count_comment = 'Calculated with: np.cumsum(np.absolute(np.concatenate(([0], np.diff(self.angle))))) / 2. / np.pi'
        self.angle_count = np.cumsum(np.absolute(np.concatenate(([0], np.diff(self.angle))))) / 2. / np.pi

        self.diffrot = np.array(self.diffrotList)
        self.difftumble = np.array(self.difftumbleList)

        # Rate of rotation in deg/sec - pure rotation and tumbling
        self.rotrate = np.absolute(self.diffrot * self.rateHz * 180.0 / np.pi)
        self.tumblerate = np.absolute(self.difftumble * self.rateHz * 180.0 / np.pi)

        # Cumultative rotation count - pure rotation and tumbling - filter noisy diffrot before doing cumsum
        diffrot_filt = savgol_filter(np.absolute(self.diffrot), 11, 3)
        self.rotcount = np.cumsum(diffrot_filt) / 2. / np.pi
        self.tumblecount = np.cumsum(np.absolute(self.difftumble)) / 2. / np.pi

    def computeTide(self):
        '''Use MB-System command to run OSTP2 model for computing tides from time and location
        '''
        # Sample from /Volumes/MappingAUVOps2016/MontereyCanyon/BEDSTides/process.cmd:
        # mbotps -A2 -B2016/01/15/21/55/42 -E2016/1/15/21/59/53 -D1 -R-121.87763/36.79286 -OBED5event55.txt
        cmd_fmt = 'mbotps -A2 -B{} -E{} -D1 -R{}/{} -O{}'

        start_time = coards.from_udunits(self.ps[0], 'seconds since 1970-01-01').strftime('%Y/%m/%d/%H/%M')
        end_time = coards.from_udunits(self.ps[-1], 'seconds since 1970-01-01').strftime('%Y/%m/%d/%H/%M')

        if self.args.trajectory:
            lon = np.mean(self.traj_lon)
            lat = np.mean(self.traj_lat)
        else:
            lon = self.lon
            lat = self.lat

        tide_file = 'mbotps_out.txt'
        cmd = cmd_fmt.format(start_time, end_time, lon, lat, tide_file)
        if self.args.verbose:
            print("Executing: {}".format(cmd))
        os.system(cmd + '&> /dev/null')

        # Read the tide time series data into member items
        tSecList = []
        tideList = []
        with(open(tide_file)) as tf:
            for line in tf:
                if not line.startswith('#'):
                    yr, mo, dy, hr, mn, se, tide = line.split()
                    es = (datetime(int(yr), int(mo), int(dy), int(hr), int(mn), int(se)) - 
                                                    datetime(1970, 1, 1)).total_seconds()
                    tSecList.append(es)
                    tideList.append(float(tide))

        ts2013 = np.array(tSecList) - 1356998400.0
        self.tide = np.interp(self.ps2013, ts2013, np.array(tideList))
        self.tide_comment = 'Computed with command: {}'.format(cmd)

        for fn in glob.glob('tmp_mbotps*.txt') + [tide_file]:
            if self.args.verbose:
                print("Removing file {}".format(fn))
            os.remove(fn)
            
        return cmd

