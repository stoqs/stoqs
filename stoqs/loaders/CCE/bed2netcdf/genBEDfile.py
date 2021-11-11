#!/usr/bin/env python
'''
Generate a simulated BED data file in the same format as output from decode and as
used as input for bed2netcdf.py.  Useful for testing rotation metrics produced by
bed2netcdf.py, e.g. validating the ROT_DIST numbers based on an assumption of pure
rolling motion.

Mike McCann

$Id: genBEDfile.py 13719 2017-03-02 16:33:28Z mccann $
'''

import sys
import numpy as np
from BEDS import BEDS
from datetime import datetime, timedelta, date
from euclid import Quaternion, Vector3
from seawater import eos80

class BED_SIM(BEDS):

    def genRotations(self, distance):
        '''Generate rotations so as to roll a specified distance, units in meters
        '''

        # Aim for 2 complete rotations per second at 5 Hz, this will give:
        bed_circumference = 1.47
        num_rots = distance / bed_circumference
        num_rot_recs = int(5 * num_rots / 2)
        angle_to_rotate = 4 * np.pi / 15.0

        axis = Vector3(1, 0, 0)
        angle = 0.0
        self.quat_list = []
        for i in range(num_rot_recs):
            if self.args.cycle_rot_axes:
                if i < num_rot_recs / 3:
                    axis = Vector3(1, 0, 0)
                elif i >= (num_rot_recs / 3) and i < (2 * num_rot_recs / 3):
                    axis = Vector3(0, 1, 0)
                elif i >= (2 * num_rot_recs / 3):
                    axis = Vector3(0, 0, 1)
        
            angle += angle_to_rotate
            q = Quaternion.new_rotate_axis(angle, axis)
            self.quat_list.append((q.w, q.x, q.y, q.z))

        for i in range(num_rot_recs):
            if self.args.cycle_rot_axes:
                axis = Vector3(i/num_rot_recs, (num_rot_recs-i)/num_rot_recs, 0)
        
            angle += angle_to_rotate
            q = Quaternion.new_rotate_axis(angle, axis.normalize())
            self.quat_list.append((q.w, q.x, q.y, q.z))

    def write_data(self):
        '''Output to look like:

        Decoding file 60200012.E00:
        FileHdr ver=1 ID=6 rate=300 03/06/2016 09:36:45.540 dur=20.460
        Inertial Data  acc:  0.23561  0.07825  0.00249  quat:  0.07684 -0.90497  0.35278 -0.22516 norm:  1.000012
        Inertial Data  acc:  0.25409  0.03091  0.00056  quat:  0.22827 -0.88080  0.32874 -0.25317 norm:  1.000039
        Inertial Data  acc:  0.25119  0.02328 -0.01088  quat:  0.38928 -0.83716  0.29706 -0.24377 norm:  1.000022
        Inertial Data  acc:  0.24738  0.07303 -0.00119  quat:  0.53876 -0.76898  0.28101 -0.19867 norm:  1.000013
        Second Marker 03/06/2016 09:36:57
        Ext Pressure 28380 counts 1.083 volts 41.631 bar
        Inertial Data  acc:  0.17386  0.06453 -0.02126  quat:  0.67798 -0.67175  0.25696 -0.15186 norm:  0.999997
        Inertial Data  acc:  0.14592  0.00752 -0.01176  quat:  0.78870 -0.55945  0.22827 -0.11310 norm:  0.999962
        Inertial Data  acc:  0.14661  0.06511  0.00432  quat:  0.87585 -0.43665  0.18616 -0.08667 norm:  0.999973
        Inertial Data  acc:  0.10504  0.10452  0.04430  quat:  0.94153 -0.30627  0.12201 -0.06946 norm:  0.999995
        Inertial Data  acc:  0.03142  0.13852  0.02765  quat:  0.98322 -0.17206  0.03015 -0.05170 norm:  0.999949
        Second Marker 03/06/2016 09:36:58
        Ext Pressure 28398 counts 1.083 volts 41.665 bar
        Inertial Data  acc: -0.10565  0.10538  0.01256  quat:  0.99536 -0.03009 -0.08911 -0.02020 norm:  0.999999
        Inertial Data  acc: -0.17039  0.08000  0.13490  quat:  0.96661  0.12323 -0.22369  0.01947 norm:  0.999973
        '''

        self.readTrajectory(self.args.beg_depth, self.args.end_depth)
        self.genRotations(self.traj_dist_topo[-1] - self.traj_dist_topo[0])

        # Create simulated decimated 5 Hz file with number of rotations to make it down the whole canyon
        hz = 5
        head1_fmt = 'Decoding file {}:\n'
        head2_fmt = 'FileHdr ver=1 ID=6 rate={:d} {} dur={:6.3f}\n'
        imu_fmt = "Inertial Data  acc: {:8.5f} {:8.5f} {:8.5f}  quat: {:8.5f} {:8.5f} {:8.5f} {:8.5f} norm:  1.0\n"
        sm_fmt = "Second Marker {}\n"
        ep_fmt = "Ext Pressure {:d} counts {:5.3f} volts {:6.3f} bar\n"

        if self.args.use_today_as_start:
            sm = datetime(date.today().year, date.today().month, date.today().day)
        else:
            ##sm = datetime(2016, 11, 11, 0, 0, 0)
            sm = datetime(2013, 4, 30, 0, 0, 0)
        lat = np.mean(self.traj_lat)
        depths = np.interp(np.linspace(0, len(self.traj_depth), len(self.quat_list)), 
                           np.arange(len(self.traj_depth)), self.traj_depth)

        with open(self.args.output, 'w') as f:
            f.write(head1_fmt.format(self.args.output.replace('.OUT', '')))
            f.write(head2_fmt.format(hz * 60, sm.strftime('%m/%d/%Y %H:%M:%S'), len(self.quat_list) / float(hz)))
            for i, (q, d) in enumerate(zip(self.quat_list, depths)):
                if not i % 5:
                    sm += timedelta(seconds=1)
                    f.write(sm_fmt.format(sm.strftime('%m/%d/%Y %H:%M:%S')))
                    f.write(ep_fmt.format(0, 0, eos80.pres(d, lat) / 10.0))

                str = imu_fmt.format(0, 0, 0, *q)
                f.write(str)

    def process_command_line(self):

        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n\n'
        examples += '    ' + sys.argv[0] + " -o BED00048.E00.OUT -t ../MontereyCanyonBeds_1m+5m_profile.ssv\n"

        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Convert BED event file(s) to a NetCDF file',
                                         epilog=examples)

        parser.add_argument('-o', '--output', action='store', help="Specify output .E00.OUT file name",
                             required=True)
        parser.add_argument('-t', '--trajectory', action='store', help="Thalweg trace file produced by Program MBgrdviz",
                             required=True)
        # Default depth limits set to range of file MontereyCanyonBeds_1m+5m_profile.ssv
        parser.add_argument('--beg_depth', type=float, action='store', help='Begining depth for lookup from trajectory file',
                             default=145.0)
        parser.add_argument('--end_depth', type=float, action='store', help='Ending depth for lookup from trajectory file',
                             default=722.0)
        parser.add_argument('--cycle_rot_axes', action='store_true', help='Divide into 3 sections with rotations about X, Y and axes')
        parser.add_argument('--use_today_as_start', action='store_true', help='Use current year, month, day as the start time')

        self.args = parser.parse_args() 


if __name__ == '__main__':
    bs = BED_SIM()
    bs.process_command_line()
    bs.write_data()

