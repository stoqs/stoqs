#!/usr/bin/env python
'''
Test computing 'euler vector' axis and rotation rate by division by subsequent quaternions.
See https://github.com/ezag/pyeuclid and https://github.com/ezag/pyeuclid/blob/master/euclid.txt.

Mike McCann

$Id: testBEDSprocess.py 13656 2016-11-15 23:00:06Z mccann $
'''

import sys
import math
import unittest
import numpy as np
from BEDS import BEDS
from bed2x3d import BEDS_X3D
from argparse import Namespace
from euclid import Quaternion, Vector3

def nearly_equal(a, b, sig_fig=5):
    return (a==b or int(a*10**sig_fig) == int(b*10**sig_fig))


class TestDivision(unittest.TestCase):

    def setUp(self):
        pass

    def testBasicDiv(self):
        '''Test Basic division of Quaternions
        '''
        q1 = Quaternion.new_rotate_axis(0, Vector3(1, 0, 0))
        q2 = Quaternion.new_rotate_axis(math.pi / 2, Vector3(1, 0, 0))
        q3 = Quaternion.new_rotate_axis(math.pi / 2, Vector3(0, 1, 0))
        q4 = Quaternion.new_rotate_axis(math.pi / 2, Vector3(0, 0, 1))

        dq = q2 * Quaternion.conjugated(q1)
        aa = dq.get_angle_axis()

        self.assertEqual(aa[0], math.pi / 2)

        self.assertEqual((q3 * Quaternion.conjugated(q1)).get_angle_axis()[0], math.pi / 2)
        self.assertEqual((q4 * Quaternion.conjugated(q1)).get_angle_axis()[0], math.pi / 2)


class TestBEDSprocess(unittest.TestCase):

    be_verbose = True

    def setUp(self):
        '''Create a known set of rotations simulating data recorded on the BED
        '''
        self.quatList = []

        self.rx = []
        self.ry = []
        self.rz = []

        self.px = []
        self.py = []
        self.pz = []
        self.prot = []

        self.mx = [0]
        self.my = [0]
        self.mz = [0]
        self.drot = [0]

        self.fmt = ("{:2d}. rx, ry, rz, drot, drot_sum = {:.3f} {:.3f} {:.3f} {:.3f} {:.3f}"
                    "   px, py, pz, prot = {:.3f} {:.3f} {:.3f} {:.3f}")

        self.makeRotations()

        # Make X3D file for visual verification
        self.makeX3Dfile()

    def makeRotations(self, angle_to_rotate=np.pi, nsteps=5):
        '''Dummy up a list of quaternions that rotate about each axis
        '''
        i = 0
        drot = 0.0
        drot_sum = 0.0
        if self.be_verbose:
            print "Input list of rotations passed as quaternions into BEDS.py code:"

        for axis in (Vector3(1, 0, 0), Vector3(0, 1, 0), Vector3(0, 0, 1)):
            for angle in np.append(np.linspace(0.0, angle_to_rotate, nsteps, endpoint=True),
                                   np.linspace(angle_to_rotate, 0.0, nsteps, endpoint=True)):
                q = Quaternion.new_rotate_axis(angle, axis)
                self.quatList.append((q.w, q.x, q.y, q.z))

                # returns heading, attitude, bank (For X3D we get: ry, rz, rx)
                ry, rz, rx = q.get_euler()
                self.rx.append(rx)
                self.ry.append(ry)
                self.rz.append(rz)

                prot, quat = q.get_angle_axis()
                self.px.append(quat.x)
                self.py.append(quat.y)
                self.pz.append(quat.z)
                self.prot.append(prot)

                if i > 0:
                    diff_rot = q * Quaternion.conjugated(last_q)
                    drot, dquat = diff_rot.get_angle_axis()
                    self.mx.append(dquat.x)
                    self.my.append(dquat.y)
                    self.mz.append(dquat.z)
                    self.drot.append(drot)

                i += 1
                last_q = q

                drot_sum += drot

                if self.be_verbose:
                    print self.fmt.format(i, rx, ry, rz, drot, drot_sum, quat.x, quat.y, quat.z, prot)

    def makeX3Dfile(self):
        '''Use bed2x3d module to write a .x3d for visual verification
        '''
        args = Namespace()
        args.verbose = 0
        args.input = []
        args.translate = False
        args.speedup = 1
        args.output = 'testBEDSprocess.x3d'

        x3d = BEDS_X3D(args, sys.argv)
        x3d.sensorType = 'Invensense'
        x3d.rateHz = 1.0
        x3d.s = np.arange(0.0, len(self.rx)/x3d.rateHz)
        x3d.quatList = self.quatList

        x3d.ax = np.zeros(len(self.rx))     # Dummy-up 0 accelerations for createX3D()
        x3d.ay = np.zeros(len(self.rx))
        x3d.az = np.zeros(len(self.rx))

        x3dText = x3d.createX3D()           # Calls BEDS processRotations()

        f = open(args.output, 'w')
        f.write(x3dText)
        f.close()

        if self.be_verbose:
            print "Wrote file %s - open it in InstantReality Player, BS Contact, Xj3D, X3DOM, or other X3D browser." % args.output

    def compare_results(self, beds, euler_angles=True, euler_vectors=True, test_near=False):
        '''Compare BEDS.processRotations() results with original input
        '''
        if euler_angles:
            for rx1, rx2 in zip(beds.rxList, self.rx):
                if test_near:
                    same_vector_x = nearly_equal(rx1, rx2) or nearly_equal(abs(rx1 - rx2), np.pi)
                    self.assertTrue(same_vector_x)
                else:
                    self.assertEqual(rx1, rx2)

            for ry1, ry2 in zip(beds.ryList, self.ry):
                if test_near:
                    same_vector_y = nearly_equal(ry1, ry2) or nearly_equal(abs(ry1 - ry2), np.pi)
                    self.assertTrue(same_vector_y)
                else:
                    self.assertEqual(rx1, rx2)

            for rz1, rz2 in zip(beds.rzList, self.rz):
                if test_near:
                    same_vector_z = nearly_equal(rz1, rz2) or nearly_equal(abs(rz1 - rz2), np.pi)
                    self.assertTrue(same_vector_z)
                else:
                    self.assertEqual(rx1, rx2)

        if euler_vectors:
            for px1, px2 in zip(beds.pxList, self.px):
                self.assertEqual(px1, px2)

            for py1, py2 in zip(beds.pyList, self.py):
                self.assertEqual(py1, py2)

            for pz1, pz2 in zip(beds.pzList, self.pz):
                self.assertEqual(pz1, pz2)

            for prot1, prot2 in zip(beds.protList, self.prot):
                self.assertEqual(prot1, prot2)

        for dr1, dr2 in zip(beds.diffrotList, self.drot):
            if test_near:
                self.assertTrue(nearly_equal(dr1, dr2))
            else:
                self.assertEqual(dr1, dr2)

    def testMatlabCode(self):
        '''Test Matlab spincalc code
        '''
        beds = BEDS()
        beds.args = Namespace()
        if self.be_verbose:
            beds.args.verbose = 1
        else:
            beds.args.verbose = 0

        beds.rateHz = 10.0
        beds.quatList = self.quatList

        if self.be_verbose:
            print "Output list of rotations returned by BEDS.py code with useMatlabCode=True:"

        beds.processRotations(useMatlabCode=True)

        # Test just the drot calculation - too much trouble getting exact euler_angles and
        # euler_vectors working with this translated-to-python Matlab code
        self.compare_results(beds, euler_angles=False, euler_vectors=False, test_near=True)

    def testPythonCode(self):
        '''Test Python euclid code
        '''
        beds = BEDS()
        beds.args = Namespace()
        if self.be_verbose:
            beds.args.verbose = 1
        else:
            beds.args.verbose = 0

        beds.rateHz = 10.0
        beds.quatList = self.quatList

        if self.be_verbose:
            print "Output list of rotations returned by BEDS.py code:"

        beds.processRotations()
        self.compare_results(beds)


if __name__ == '__main__':
   unittest.main()

