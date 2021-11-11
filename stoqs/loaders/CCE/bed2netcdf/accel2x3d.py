#!/usr/bin/env python
'''
Parse logged data from accelerometer to compute translations in x, y, z and rotations
about these axes.  Output as X3D text so that the data can be visualized in an X3D Browser.

--
Mike McCann
5 May 2011

$Id: accel2x3d.py 13595 2016-06-16 16:31:02Z mccann $
'''

import csv
from numpy import *
from optparse import OptionParser
import math


class BEDS_X3D:

	def __init__(self, opts):
		'''Initialize with options and set base X3D text
		'''

		self.inputFileName = opts.input

		self.x3dBaseText = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 3.2//EN" "http://www.web3d.org/specifications/x3d-3.2.dtd">
<X3D profile="Immersive" version="3.2" xmlns:xsd="http://www.w3.org/2001/XMLSchema-instance" xsd:noNamespaceSchemaLocation="http://www.web3d.org/specifications/x3d-3.2.xsd">
	<head>
		<meta content="BEDS_Vis1.x3d" name="title"/>
		<meta content="Translation and orientation visualization of Benthic Event Detectors." name="description"/>
		<meta content="Mike McCann mccann@mbari.org" name="creator"/>
		<meta content="21 May 2011" name="created"/>
		<meta content="Copyright (c) Monterey Bay Aquarium Research Institute 2011" name="rights"/>
		<meta content="accel2x3d.py --input %(input)s --output %(output)s" name="generator"/>
	</head>
	<Scene>
		<Transform DEF="TRANSLATE">
			<Transform DEF="XROT">
				<Transform DEF="YROT">
					<Transform DEF="ZROT">
						<Shape>
							<Appearance>
								<Material/>
							</Appearance>
							<Box DEF="BEDS_BOX"/>
	
						</Shape>
						<TouchSensor DEF="TOUCH"/>
					</Transform>
				</Transform>
			</Transform>
		</Transform>

		<!-- 6 DOF data from the BEDS coded here as position and orientation interpolators -->
		<PositionInterpolator DEF="POS_INTERP" key="%(iKeys)s" keyValue="%(posValues)s"/>
		<OrientationInterpolator DEF="X_OI" key="%(iKeys)s" keyValue="%(xRotValues)s"/>
		<OrientationInterpolator DEF="Y_OI" key="%(iKeys)s" keyValue="%(yRotValues)s"/>
		<OrientationInterpolator DEF="Z_OI" key="%(iKeys)s" keyValue="%(zRotValues)s"/>

		<!-- The cycleInterval is the time duration in seconds of the data -->
		<TimeSensor DEF="TS" cycleInterval="%(cycInt)s" loop="true"/>

		<!-- Wire up the connections between the nodes to animate the motion of the Shape -->
		<ROUTE fromField="value_changed" fromNode="POS_INTERP" toField="translation" toNode="TRANSLATE"/>

		<ROUTE fromField="value_changed" fromNode="X_OI" toField="rotation" toNode="XROT"/>
		<ROUTE fromField="value_changed" fromNode="Y_OI" toField="rotation" toNode="YROT"/>
		<ROUTE fromField="value_changed" fromNode="Z_OI" toField="rotation" toNode="ZROT"/>

		<ROUTE fromField="fraction_changed" fromNode="TS" toField="set_fraction" toNode="POS_INTERP"/>
		<ROUTE fromField="fraction_changed" fromNode="TS" toField="set_fraction" toNode="X_OI"/>
		<ROUTE fromField="fraction_changed" fromNode="TS" toField="set_fraction" toNode="Y_OI"/>
		<ROUTE fromField="fraction_changed" fromNode="TS" toField="set_fraction" toNode="Z_OI"/>

		<ROUTE fromField="touchTime" fromNode="TOUCH" toField="startTime" toNode="TS"/>
	</Scene>

</X3D>
''' 
		# End __init__()

	def readAtomicLogFile(self, infile):
		'''Open `infile`, read values, apply offsets and scaling.
		Return numpy arrays of the acceleration and rotation data in engineering units.
		'''

		# From: "Kieft, Brian" <bkieft@mbari.org>
		# Date: Wed, 18 May 2011 14:42:54 -0700
		# To: Mike McCann <mccann@mbari.org>
		# Cc: "Herlien, Bob" <bobh@mbari.org>
		# Subject: data scaling
		# 
		# Hi Mike,
		#  
		# Here's the first two lines of the log file 20110518135934_atomic_imu.log in your tempbox:
		#  
		# epoch ms,accel x, accel y, accel z, pitch, roll, yaw
		# 1305752376772,470.0,483.0,780.0,521.0,527.0,500.0
		#  
		# For this sensor, in this configuration, we're running full scale at 10 bits. 
		# For accelerations measured in g we have: 0.00403 g/count. So, in this line you'll 
		# see (780-512)*.00403 = 1.08g for the Z axis. This is when it was sitting on the desk 
		# before I picked it up. So, 0g would be 512 counts and you'll notice the other two 
		# axis are slightly negative (since it all has to add up to 1 g since it was just sitting there). 
		#  
		# For pitch,roll, and yaw we're looking at .977 degrees/count, same A/D. 
		#  
		# Does that work for you? 
		#  
		# -bk-

		zeroOffset = 512
		gPerCount = 0.00403
		degPerCount = 0.977

		# Header is:
		# ['epoch ms', 'accel x', ' accel y', ' accel z', ' pitch', ' roll', ' yaw']	
	
		secList = []
		axList = []
		ayList = []
		azList = []
		pitchList = []
		rollList = []
		yawList = []
	
		reader = csv.reader(open(infile))
		for r in reader:
			if opts.verbose: print r
			try:
				secList.append(float(r[0]) / 1000.0)
				axList.append((float(r[1]) - zeroOffset) * gPerCount)
				ayList.append((float(r[2]) - zeroOffset) * gPerCount)
				azList.append((float(r[3]) - zeroOffset) * gPerCount - 1.0)
				pitchList.append((float(r[4]) - zeroOffset) * degPerCount * math.pi / 180)
				rollList.append((float(r[5]) - zeroOffset) * degPerCount * math.pi / 180)
				yawList.append((float(r[6]) - zeroOffset) * degPerCount * math.pi / 180)
			except ValueError:
				if opts.verbose: print "Skipping row = %s" % r

		# Make the Lists numpy arrays so that we can do Matlab-like operations
		# These arrays have units of seconds, g, and radians.
		self.s = array(secList)
		self.ax = array(axList)
		self.ay = array(ayList)
		self.az = array(azList)
		self.pitch = array(pitchList)
		self.roll = array(rollList)
		self.yaw = array(yawList)

		return 

	def cumtrapz(self, x, y):
		'''Returns indefinite integral of discrete data in y wrt x.  

		Test with:
			>> cumtrapz([0,.2,.4,.6,.8],[1:5])							! Matlab
			ans =
			         0    0.3000    0.8000    1.5000    2.4000

			print self.cumtrapz([.0,.2,.4,.6,.8], array([1,2,3,4,5]))	! Python
			[ 0.   0.3  0.8  1.5  2.4]
		'''

		sumA = 0
		sumAList = [sumA]
		for i in range(len(y))[:-1]:
			A = (x[i+1] - x[i]) * (y[i] + y[i+1]) / 2.0
			sumA = sumA + A
			sumAList.append(sumA)

		return array(sumAList)

	def createX3DfromFile(self):
		'''Read accelerometer data from log file and apply operations to convert it to the keys and values of
		position and orientation the X3D likes.
		'''
	
		self.readAtomicLogFile(self.inputFileName)

		# Iterpolate data to regularly spaced time values - may need to do this to improve accuracy
		# (See http://www.freescale.com/files/sensors/doc/app_note/AN3397.pdf)
		##si = linspace(self.s[0], self.s[-1], len(self.s))
		##axi = interp(si, self.s, self.ax)

		# Double integrate accelerations to get position and construct X3D position values string
		# (May need to high-pass filter the data to remove noise that can give unreasonably large positions.)
		t = self.s
		xA = self.cumtrapz(t, self.cumtrapz(t, self.ax))
		yA = self.cumtrapz(t, self.cumtrapz(t, self.ay))
		zA = self.cumtrapz(t, self.cumtrapz(t, self.az))

		# Construct X3D strings for keys, positions, orientations, and duration of the data
		iKeys = ' '.join(['%.4f' % k for k in (t - t[0]) / (t[-1] - t[0])])
		posList = ['%.4f %.4f %.4f' % (x, y, z) for (x, y, z) in zip(xA, yA, zA)]
		posValues = ' '.join(posList)

		xRotValues = ' '.join(['1 0 0 %.6f' % p for p in self.pitch])
		yRotValues = ' '.join(['0 1 0 %.6f' % r for r in self.roll])
		zRotValues = ' '.join(['0 0 1 %.6f' % y for y in self.yaw])

		cycInt = '%.4f' % (t[-1] - t[0])

		return self.x3dBaseText % {'input': opts.input, 'output': opts.output,
									'iKeys': iKeys, 'posValues': posValues, 'xRotValues': xRotValues, 
									'yRotValues': yRotValues, 'zRotValues': zRotValues, 'cycInt': cycInt}


if __name__ == '__main__':

	parser = OptionParser(usage="""\

Synopsis: %prog --input <accelerometer_log_file_name> --ouptut <x3d_ouptut_file_name>

Given an input file name of accelerometer data in this format:

    epoch ms,accel x, accel y, accel z, pitch, roll, yaw
    1305752376772,470.0,483.0,780.0,521.0,527.0,500.0

Produce an X3D file such that the data can be visualized in any number of X3D browsers.

Example: 

	%prog --input 20110518135934_atomic_imu.log --output 20110518135934_atomic_imu.x3d	
""")

	parser.add_option('', '--input',
		type='string', action='store',
		help="Specify input log file name")
	parser.add_option('', '--output',
		type='string', action='store',
		help="Specify output x3d file name")
	parser.add_option('-v', '--verbose',
		action='store_true', default=False,
		help="Specify verbose output to the screen")

	opts, args = parser.parse_args()

	if not (opts.input and opts.output):
		parser.error("Must specify both --input and --output options.\n")

	beds_x3d = BEDS_X3D(opts)

	x3dText = beds_x3d.createX3DfromFile()
	if opts.verbose: print "x3dText = %s" % x3dText

	f = open(opts.output, 'w')
	f.write(x3dText)
	f.close()

	print "Wrote file %s.  Open it in InstantReality Player, BS Contact, Xj3D, or other X3D browser." % opts.output



