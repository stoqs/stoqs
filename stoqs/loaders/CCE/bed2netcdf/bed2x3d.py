#!/usr/bin/env python
'''
Parse logged data from BEDs .EVT or .WAT file to compute translations in x, y, z and rotations
about these axes.  Output as X3D text so that the data can be visualized in an X3D Browser.

--
Mike McCann
1 April 2013

$Id: bed2x3d.py 13595 2016-06-16 16:31:02Z mccann $
'''

import os
import sys
import csv
import math
import datetime
import numpy as np
from BEDS import BEDS
from util import quatern2euler, quaternConj, quatern2eulervector
from optparse import OptionParser


class BEDS_X3D(BEDS):

    def __init__(self, args, argv):
        '''
        Initialize with options and set base X3D text
        '''

        self.args = args
        self.argv = argv
        self.inputFileNames = args.input
        for fileName in self.inputFileNames:
            if fileName.endswith('.log'): 
                self.sensorType = 'Atomic'
            elif fileName[-3:] in self.invensense_extenstions:
                self.sensorType = 'Invensense'

        self.x3dEulerBaseText = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 3.2//EN" "http://www.web3d.org/specifications/x3d-3.2.dtd">
<X3D profile="Immersive" version="3.2" xmlns:xsd="http://www.w3.org/2001/XMLSchema-instance" xsd:noNamespaceSchemaLocation="http://www.web3d.org/specifications/x3d-3.2.xsd">
    <head>
        <meta content="BEDS_Vis1.x3d" name="title"/>
        <meta content="Translation and orientation visualization of Benthic Event Detectors." name="description"/>
        <meta content="Mike McCann mccann@mbari.org" name="creator"/>
        <meta content="%(dateCreated)s" name="created"/>
        <meta content="Copyright (c) Monterey Bay Aquarium Research Institute %(yearCreated)s" name="rights"/>
        <meta content="%(commandLine)s" name="generator"></meta>
    </head>
    <Scene>
        <Viewpoint position='0 0 2'></Viewpoint>
        <!--
        <Background groundAngle='0.1 1.309 1.57' groundColor='0 0 0 0.4 0.4 0.34 0.4 0.4 0.34 0.4 0.4 0.34' skyAngle='0.1 0.15 1.309 1.57' skyColor='0.4 0.4 0.1 0.4 0.4 0.1 0.8 0.8 0.8 0 0.2 0.6 0 0.1 0.3'>
        </Background>
        -->
        <Background groundColor='0.4 0.4 0.34' skyColor='0.4 0.4 0.34'></Background>
        <Transform DEF="TRANSLATE">
            <Transform DEF="XROT">
                <Transform DEF="YROT">
                    <Transform DEF="ZROT">
                        <Transform>
                            <Inline url="beds_housing_with_axes.x3d"></Inline>
                            <TouchSensor DEF="TOUCH"/>
                        </Transform>
                    </Transform>
                </Transform>
            </Transform>
        </Transform>

        <!-- Stationary axes -->
        <Transform>
            <Inline url="axes.x3d"></Inline>
        </Transform>

        <!-- Location that BED rotation axes points to -->
        <!--
        <Transform>
            <Transform DEF="ROTVEC">
                <Shape>
                    <Appearance>
                        <Material DEF="BALL" diffuseColor="0.0 0.0 1.0"/>
                    </Appearance>
                    <Sphere radius=".015"></Sphere>
                </Shape>
            </Transform>
        </Transform>
        -->

        <!-- HUD for the timeline slider -->
        <ProximitySensor DEF="PROX" size="1000 1000 1000"></ProximitySensor>
        <Transform DEF="HUD">
            <!-- Scale the overall transform for maximum slider size in fullscreen window on Mac -->
            <Transform translation="0.0 -0.5 -1.5" scale="1.8 1 1">
                <Transform translation="-0.5 0 0 ">
                    <Transform DEF="TL">
                        <PlaneSensor DEF="PS" maxPosition="1.0 0.0" autoOffset='true' />
                        <Transform>
                            <Shape>
                                <Appearance>
                                    <Material DEF="BALL" diffuseColor="0.0 1.0 0.0"/>
                                </Appearance>
                                <Sphere radius=".015"></Sphere>
                            </Shape>
                        </Transform>
                        <Transform translation="0 .05 0">
                            <Shape>
                                <Text DEF="TimeDisplay">
                                    <FontStyle family="SANS" size="0.05" style="PLAIN" justify='"MIDDLE" "MIDDLE"'/>
                                </Text>
                            </Shape>
                        </Transform>
                    </Transform>
                    <Transform translation="0 -.05 0">
                        <Shape>
                            <Text DEF="DateDisplay">
                                <FontStyle family="SANS" size="0.05" style="PLAIN"/>
                            </Text>
                        </Shape>
                    </Transform>
                    <Transform translation="0 .15 0">
                        <Shape>
                            <Text DEF="RotRateDisplay">
                                <FontStyle family="SANS" size="0.05" style="PLAIN"/>
                            </Text>
                        </Shape>
                    </Transform>
                </Transform>
                <Transform rotation="0 0 1 1.570796326794">
                    <Shape>
                        <Cylinder height="1" radius="0.001"></Cylinder>
                    </Shape>
                </Transform>
            </Transform>
        </Transform>

        <!-- 6 DOF data from the BEDS coded here as position and orientation interpolators -->
        <PositionInterpolator DEF="POS_INTERP" key="%(pKeys)s" keyValue="%(posValues)s"/>
        <OrientationInterpolator DEF="X_OI" key="%(oKeys)s" keyValue="%(xRotValues)s"/>
        <OrientationInterpolator DEF="Y_OI" key="%(oKeys)s" keyValue="%(yRotValues)s"/>
        <OrientationInterpolator DEF="Z_OI" key="%(oKeys)s" keyValue="%(zRotValues)s"/>

        <!-- Rotation Rate data -->
        <ScalarInterpolator DEF="ROTRATE_SI" key="%(oKeys)s" keyValue="%(RotRateValues)s"/>

        <!-- Rotation Vector data - shown by a point in 3-space -->
        <!--<CoordinateInterpolator DEF="ROTVEC_CI" key="%(oKeys)s" keyValue="%(RotVecValues)s"/>-->

        <!-- Borrowed from PowerDivePlaybackProto.x3d -->
        <Script DEF="Stop_and_Go_Script">
                <field accessType="inputOnly" type="SFTime" name="touchTime"></field>
                <field accessType="inputOnly" type="SFBool" name="isOver"></field>
                <field accessType="outputOnly" type="SFColor" name="color_changed"></field>
                <field accessType="outputOnly" type="SFTime" name="startIt"></field>
                <field accessType="outputOnly" type="SFTime" name="stopIt"></field>
                <field accessType="outputOnly" type="MFString" name="text_changed"></field>
                <field accessType="outputOnly" type="SFBool" name="active"></field>
                <field accessType="initializeOnly" type="SFColor" name="red" value="1 0 0"></field>
                <field accessType="initializeOnly" type="SFColor" name="green" value="0 1 0"></field>
                <field accessType="initializeOnly" type="SFInt32" name="state" value="1"></field>
                    <![CDATA[ecmascript:
                        // Handler for event touchTime of type SFTime.
                        function touchTime (value, timestamp)
                        {
                                // Red to Green
                                if (state == 0) {
                                        color_changed = green;
                                        text_changed[0] = 'REPLAY';
                                        state = ! state;
                                        startIt = timestamp;
                                        active = true;
                                }
                                // Green to Red
                                else if (state == 1) {
                                        color_changed = red;
                                        text_changed[0] = 'PAUSED';
                                        state = ! state;
                                        stopIt = timestamp;
                                        active = false;
                                }
                                else {
                                        color_changed = green;
                                        text_changed[0] = 'REPLAY';
                                        state = 1;
                                        startIt = timestamp;
                                        active = true;
                                }
                        }
                        function isOver (value, timestamp)
                        {
                                if ( value ) {
                                        if ( state == 1 ) {
                                                browser.Description = 'Click to pause';
                                        }
                                        else {
                                                browser.Description = 'Click to play';
                                        }
                                }
                                else {
                                        Browser.setDescription('');
                                }
                        }
                   ]]>
        </Script>

        <Script DEF="TimeCalc">
            <field accessType="inputOnly" type="SFFloat" name="set_fraction"> </field>
            <field accessType="inputOnly" type="SFFloat" name="set_rotratevalue"> </field>
            <field accessType="outputOnly" type="SFString" name="TimeString"> </field>
            <field accessType="outputOnly" type="SFString" name="DateString"> </field>
            <field accessType="outputOnly" type="SFString" name="RotRateString"> </field>
            <field accessType="initializeOnly" type="SFFloat" name="startEpoch" value="%(startEpoch)s"></field>
            <field accessType="initializeOnly" type="SFFloat" name="endEpoch" value="%(endEpoch)s"></field>
            <![CDATA[
                ecmascript:
                    function set_fraction (value, timestamp)
                    { 
                        es = (endEpoch - startEpoch) * value + startEpoch;
                        var d = new Date(es * 1000);
                        //print('fraction value = ' + value);
                        //print('d.toUTCString() = ' + d.toUTCString());
                        // Sat, 01 Jun 2013 02:59:43 GMT
                        TimeString = d.toUTCString().replace(/[a-zA-Z,\\s]+\\d+[a-zA-Z,\\s]+\\d\\d\\d\\d\\s/, '').replace(/\\s+GMT/, '');
                        DateString = d.toUTCString().replace(/\\s+\\d\\d:\\d\\d:\\d\\d\\s+GMT/, '').replace(/[a-zA-Z,\\s]+/, '');
                        //print(TimeString);
                    }
                    function set_rotratevalue (value, timestamp)
                    { 
                        RotRateString = 'Rotation rate (deg/sec): ' + value.toPrecision(3);
                    }
            ]]>
        </Script>

        <Script DEF="Scrubber">
            <field accessType="inputOnly" type="SFFloat" name="set_offset"> </field>
            <field accessType="inputOnly" type="SFVec3f" name="set_translation"> </field>
            <field accessType="inputOnly" type="SFBool" name="set_enabled"> </field>
            <field accessType="inputOnly" type="SFFloat" name="set_tsfraction"> </field>
            <field accessType="inputOnly" type="SFBool" name="set_active"> </field>
            <field accessType="outputOnly" type="SFBool" name="playing"> </field>
            <field accessType="outputOnly" type="SFVec3f" name="translation_changed"> </field>
            <field accessType="outputOnly" type="SFFloat" name="fraction_changed"> </field>
            <field accessType="initializeOnly" type="SFFloat" name="cycleInterval" value="%(cycInt)s"></field>
            <![CDATA[
                ecmascript:
                    var offset;
                    var playing;
                    var active = true;
                    var psfraction = 0.0;
                    var tsfraction;
                    var start_tsfraction = 0.0;
                    function set_offset (value, timestamp)
                    { 
                        //print('offset value = ' + value);
                        offset = value;
                    }
                    function set_translation (value, timestamp)
                    { 
                        //print('-----------------');
                        //print('set_translation value = ' + value);
                        //print('offset = ' + offset);
                        psfraction = value[0];
                        fraction_changed = value[0];
                        translation_changed[0] = value[0];
                        translation_changed[1] = 0;
                        translation_changed[2] = 0;
                        //print('translation_changed = ' + translation_changed);
                    }
                    function set_enabled (value, timestamp)
                    { 
                        if (active){
                            //print('enabled value = ' + value);
                            playing = ! value;
                        }
                        // Remember TimeSensor fraction for applying to PlaneSensor translation
                        start_tsfraction = tsfraction;
                        //print('start_tsfraction = ' + start_tsfraction);
                    }
                    function set_active (value, timestamp)
                    { 
                        //print('active value = ' + value);
                        active = value;
                        if (! active) {
                            start_tsfraction = tsfraction;
                        }
                        //print('start_tsfraction = ' + start_tsfraction);
                    }
                    function set_tsfraction (value, timestamp)
                    { 
                        if (active) {
                            // Event-driven based on output from TimeSensor, simply mod add the offset
                            //print('-----------------');
                            tsfraction = value;
                            //print('tsfraction = ' + tsfraction);
                            //print('psfraction = ' + psfraction);
                            fraction_changed = tsfraction - start_tsfraction + psfraction;
                            //print('fraction_changed = ' + fraction_changed);
                            if (fraction_changed > 1) {
                                // Restart TimeSensor?
                                fraction_changed = fraction_changed - 1;
                            }
                        }
                    }
            ]]>
        </Script>

        <!-- The cycleInterval is the time duration in seconds of the data -->
        <TimeSensor DEF="TS" cycleInterval="%(cycInt)s" loop="true"/>

        <!-- Wire up the connections between the nodes to animate the motion of the Shape -->
        <ROUTE fromField="value_changed" fromNode="POS_INTERP" toField="translation" toNode="TRANSLATE"/>

        <ROUTE fromField="value_changed" fromNode="X_OI" toField="rotation" toNode="XROT"/>
        <ROUTE fromField="value_changed" fromNode="Y_OI" toField="rotation" toNode="YROT"/>
        <ROUTE fromField="value_changed" fromNode="Z_OI" toField="rotation" toNode="ZROT"/>

        <!--<ROUTE fromField="value_changed" fromNode="ROTVEC_CI" toField="translation" toNode="ROTVEC"/>-->

        <!-- Start and stop playback -->
        <ROUTE fromField="touchTime" fromNode="TOUCH" toField="touchTime" toNode="Stop_and_Go_Script"/>
        <ROUTE fromField="active" fromNode="Stop_and_Go_Script" toField="enabled" toNode="TS"/>
        <ROUTE fromField="active" fromNode="Stop_and_Go_Script" toField="set_active" toNode="Scrubber"/>
        <ROUTE fromField="startIt" fromNode="Stop_and_Go_Script" toField="startTime" toNode="TS"/>
        <ROUTE fromField="color_changed" fromNode="Stop_and_Go_Script" toField="diffuseColor" toNode="BALL"/>

        <!-- Date & time display -->
        <ROUTE fromField="fraction_changed" fromNode="Scrubber" toField="set_fraction" toNode="TimeCalc"/>
        <ROUTE fromField="TimeString" fromNode="TimeCalc" toField="string" toNode="TimeDisplay"/>
        <ROUTE fromField="DateString" fromNode="TimeCalc" toField="string" toNode="DateDisplay"/>

        <!-- Rotation Rate data -->
        <ROUTE fromField="fraction_changed" fromNode="Scrubber" toField="set_fraction" toNode="ROTRATE_SI"/>
        <ROUTE fromField="value_changed" fromNode="ROTRATE_SI" toField="set_rotratevalue" toNode="TimeCalc"/>
        <ROUTE fromField="RotRateString" fromNode="TimeCalc" toField="string" toNode="RotRateDisplay"/>

        <!-- Scrubber -->
        <ROUTE fromField="fraction_changed" fromNode="Scrubber" toField="set_offset" toNode="Scrubber"/>
        <ROUTE fromField="translation_changed" fromNode="PS" toField="set_translation" toNode="Scrubber"/>
        <ROUTE fromField="isActive" fromNode="PS" toField="set_enabled" toNode="Scrubber"/>
        <ROUTE fromField="playing" fromNode="Scrubber" toField="enabled" toNode="TS"/>

        <ROUTE fromField="fraction_changed" fromNode="TS" toField="set_tsfraction" toNode="Scrubber"/>

        <ROUTE fromField="fraction_changed" fromNode="Scrubber" toField="set_fraction" toNode="POS_INTERP"/> -->
        <ROUTE fromField="fraction_changed" fromNode="Scrubber" toField="set_fraction" toNode="X_OI"/>
        <ROUTE fromField="fraction_changed" fromNode="Scrubber" toField="set_fraction" toNode="Y_OI"/>
        <ROUTE fromField="fraction_changed" fromNode="Scrubber" toField="set_fraction" toNode="Z_OI"/>

        <!--<ROUTE fromField="fraction_changed" fromNode="Scrubber" toField="set_fraction" toNode="ROTVEC_CI"/>-->

        <ROUTE fromField="translation_changed" fromNode="Scrubber" toField="set_translation" toNode="TL"/>

        <!-- HUD routes -->
        <ROUTE fromField="orientation_changed" fromNode="PROX" toField="rotation" toNode="HUD"></ROUTE>
        <ROUTE fromField="position_changed" fromNode="PROX" toField="translation" toNode="HUD"></ROUTE>
    </Scene>

</X3D>
'''
        # TODO: x3dQuaternionBaseText is out of sync with x3dEulerBaseText for Scrubber operation
        self.x3dQuaternionBaseText = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 3.2//EN" "http://www.web3d.org/specifications/x3d-3.2.dtd">
<X3D profile="Immersive" version="3.2" xmlns:xsd="http://www.w3.org/2001/XMLSchema-instance" xsd:noNamespaceSchemaLocation="http://www.web3d.org/specifications/x3d-3.2.xsd">
    <head>
        <meta content="BEDS_Vis1.x3d" name="title"></meta>
        <meta content="Translation and orientation visualization of Benthic Event Detectors." name="description"></meta>
        <meta content="Mike McCann mccann@mbari.org" name="creator"></meta>
        <meta content="%(dateCreated)s" name="created"></meta>
        <meta content="Copyright (c) Monterey Bay Aquarium Research Institute %(yearCreated)s" name="rights"></meta>
        <meta content="%(commandLine)s" name="generator"></meta>
    </head>
    <Scene>
        <Viewpoint position='0 0 2'></Viewpoint>
        <Background groundAngle='0.1 1.309 1.57' groundColor='0 0 0 0.4 0.4 0.34 0.4 0.4 0.34 0.4 0.4 0.34' skyAngle='0.1 0.15 1.309 1.57' skyColor='0.4 0.4 0.1 0.4 0.4 0.1 0.8 0.8 0.8 0 0.2 0.6 0 0.1 0.3'>
        </Background>
        <Transform DEF="TRANSLATE">
            <Transform DEF="ORIENT">
                <Inline url="beds_housing_with_axes.x3d"></Inline>
                <TouchSensor DEF="TOUCH"/>
            </Transform>
        </Transform>

        <!-- HUD for the timeline slider -->
        <ProximitySensor DEF="PROX" size="1000 1000 1000"></ProximitySensor>
        <Transform DEF="HUD">
            <Transform translation="0.0 -0.5 -1.5">
                <Transform translation="-0.5 0 0 ">
                    <Transform DEF="TL">
                        <Shape>
                            <Appearance>
                                <Material DEF="BALL" diffuseColor="0.0 1.0 0.0"/>
                            </Appearance>
                            <Sphere radius=".015"></Sphere>
                            <Text DEF="TimeDisplay">
                                <FontStyle family="SANS" size="0.05" style="PLAIN"/>
                            </Text>
                        </Shape>
                    </Transform>
                </Transform>
                <Transform rotation="0 0 1 1.570796326794">
                    <Shape>
                        <Cylinder height="1" radius="0.001"></Cylinder>
                    </Shape>
                </Transform>
            </Transform>
        </Transform>

        <!-- Timeline slider interpolator-->
        <PositionInterpolator DEF="PI" key="0 1" keyValue="0 0 0 1 0 0"></PositionInterpolator>

        <!-- 6 DOF data from the BEDS coded here as position and orientation interpolators -->
        <PositionInterpolator DEF="POS_INTERP" key="%(pKeys)s" keyValue="%(posValues)s"></PositionInterpolator>
        <OrientationInterpolator DEF="ORIENT_INTERP" key="%(oKeys)s" keyValue="%(orientValues)s"></OrientationInterpolator>

        <!-- The cycleInterval is the time duration in seconds of the data -->
        <TimeSensor DEF="TS" cycleInterval="%(cycInt)s" loop="true"></TimeSensor>

        <!-- Wire up the connections between the nodes to animate the motion of the Shape -->
        <ROUTE fromField="value_changed" fromNode="POS_INTERP" toField="translation" toNode="TRANSLATE"></ROUTE>
        <ROUTE fromField="value_changed" fromNode="ORIENT_INTERP" toField="rotation" toNode="ORIENT"></ROUTE>
        <ROUTE fromField="fraction_changed" fromNode="TS" toField="set_fraction" toNode="POS_INTERP"></ROUTE>
        <ROUTE fromField="fraction_changed" fromNode="TS" toField="set_fraction" toNode="ORIENT_INTERP"></ROUTE>
        <ROUTE fromField="touchTime" fromNode="TOUCH" toField="startTime" toNode="TS"/>

        <!-- Routes for the timeline slider -->
        <ROUTE fromField="value_changed" fromNode="PI" toField="translation" toNode="TL"></ROUTE>
        <ROUTE fromField="fraction_changed" fromNode="TS" toField="set_fraction" toNode="PI"></ROUTE>

        <!-- HUD routes -->
        <ROUTE fromField="orientation_changed" fromNode="PROX" toField="rotation" toNode="HUD"></ROUTE>
        <ROUTE fromField="position_changed" fromNode="PROX" toField="translation" toNode="HUD"></ROUTE>

    </Scene>

</X3D>
''' 

        return super(BEDS_X3D, self).__init__()

        # End __init__()

    def readAtomicLogFile(self, infile):
        '''
        Open @infile, read values, apply offsets and scaling.
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
            if self.args.verbose > 1: 
                print r
            try:
                secList.append(float(r[0]) / 1000.0)
                axList.append((float(r[1]) - zeroOffset) * gPerCount)
                ayList.append((float(r[2]) - zeroOffset) * gPerCount)
                azList.append((float(r[3]) - zeroOffset) * gPerCount - 1.0)
                pitchList.append((float(r[4]) - zeroOffset) * degPerCount * math.pi / 180)
                rollList.append((float(r[5]) - zeroOffset) * degPerCount * math.pi / 180)
                yawList.append((float(r[6]) - zeroOffset) * degPerCount * math.pi / 180)
            except ValueError:
                if self.args.verbose > 1: 
                    print "Skipping row = %s" % r

        # Make the Lists numpy arrays so that we can do Matlab-like operations
        # These arrays have units of seconds, g, and radians.
        self.s = np.array(secList)
        self.ax = np.array(axList)
        self.ay = np.array(ayList)
        self.az = np.array(azList)
        self.pitch = np.array(pitchList)
        self.roll = np.array(rollList)
        self.yaw = np.array(yawList)

        return 

    def readFiles(self):
        '''
        Read accelerometer and rotation data from log file(s). Using potentially inherited methos (e.g. readBEDsFile())
        creates member items secList, axList, ayList, azList, quatList and member nparrays s, ps, pr, ax, ay, az.
        '''
        for fileName in self.inputFileNames:
            # Make sure input file is openable
            print 'Input fileName = ', fileName
            try:
                with open(fileName): 
                    pass
            except IOError:
                raise Exception('Cannot open input file %s' % fileName)

            if self.sensorType == 'Atomic':
                self.readAtomicLogFile(fileName)
            elif self.sensorType == 'Invensense':
                self.readBEDsFile(fileName)
            else:
                raise Exception("No handler for sensorType = %s" % self.sensorType)

    def createX3D(self):
        '''
        Apply processing operations to convert logged data to geometric things for X3D and produce .x3d file
        '''

        if self.sensorType == 'Invensense':
            self.processAccelerations()
            self.processRotations()
        else:
            raise Exception("No handler for sensorType = %s" % self.sensorType)

        # Interpolate data to regularly spaced time values - may need to do this to improve accuracy
        # (See http://www.freescale.com/files/sensors/doc/app_note/AN3397.pdf)
        ##si = linspace(self.s[0], self.s[-1], len(self.s))
        ##axi = interp(si, self.s, self.ax)

        t = self.s
        if self.args.translate: 
            # Double integrate accelerations to get position and construct X3D position values string
            # (May need to high-pass filter the data to remove noise that can give unreasonably large positions.)
            xA = self.cumtrapz(t, self.cumtrapz(t, self.ax))
            yA = self.cumtrapz(t, self.cumtrapz(t, self.ay))
            zA = self.cumtrapz(t, self.cumtrapz(t, self.az))

            # Construct X3D strings for keys, positions, orientations, and duration of the data
            pKeys = ' '.join(['%.4f' % k for k in (t - t[0]) / (t[-1] - t[0])])
            posList = ['%.4f %.4f %.4f' % (x, y, z) for (x, y, z) in zip(xA, yA, zA)]
            posValues = ' '.join(posList)
        else:
            # Dummy key-frame parameters to do no translation
            pKeys = '0 1'
            posValues = '0 0 0 0 0 0'
        
        if self.args.verbose:
            print "Applying playback speedup factor = %s" % self.args.speedup    

        cycInt = '%.4f' % ((t[-1] - t[0]) / float(self.args.speedup))

        dateCreated = datetime.datetime.now().strftime("%d %B %Y %H:%M:%S")
        yearCreated = datetime.datetime.now().strftime("%Y")

        if self.sensorType == 'Atomic':
            oKeys = ' '.join(['%.4f' % k for k in (t - t[0]) / (t[-1] - t[0])])
            xRotValues = ' '.join(['1 0 0 %.6f' % p for p in self.pitch])
            yRotValues = ' '.join(['0 1 0 %.6f' % r for r in self.roll])
            zRotValues = ' '.join(['0 0 1 %.6f' % y for y in self.yaw])
            x3dText = self.x3dEulerBaseText % {'input': self.args.input, 'output': self.args.output,
                                               'pKeys': pKeys, 'posValues': posValues, 'oKeys': oKeys, 'xRotValues': xRotValues, 
                                               'yRotValues': yRotValues, 'zRotValues': zRotValues, 'cycInt': cycInt,
                                               'dateCreated': dateCreated, 'yearCreated': yearCreated,
                                               'startEpoch': self.s[0], 'endEpoch': self.s[-1]}
        elif self.sensorType == 'Invensense':
            oKeys = ' '.join(['%.4f' % k for k in (t - t[0]) / (t[-1] - t[0])])
            # Map Invensense axes to X3D axes
            xRotValues = ' '.join(['1 0 0 %.6f' % x for x in self.rxList])
            yRotValues = ' '.join(['0 1 0 %.6f' % z for z in self.rzList])
            zRotValues = ' '.join(['0 0 1 %.6f' % -y for y in self.ryList])
            RotRateValues = ' '.join(['%f' % rr for rr in self.rotrate])
            RotVecValues = ' '.join(['%f %f %f' % (mx,my,mz) for mx,my,mz in zip(self.mxList,self.myList,self.mzList)])
            x3dText = self.x3dEulerBaseText % {'commandLine': ' '.join(sys.argv),
                                               'pKeys': pKeys, 'posValues': posValues, 'oKeys': oKeys, 'xRotValues': xRotValues, 
                                               'yRotValues': yRotValues, 'zRotValues': zRotValues, 'cycInt': cycInt,
                                               'dateCreated': dateCreated, 'yearCreated': yearCreated,
                                               'startEpoch': self.s[0], 'endEpoch': self.s[-1],
                                               'RotRateValues': RotRateValues, 'RotVecValues': RotVecValues}
        return x3dText


if __name__ == '__main__':

    import argparse
    from argparse import RawTextHelpFormatter

    examples = 'Examples:' + '\n\n'
    examples += '  Original Atomic imu:\n'
    examples += '    ' + sys.argv[0] + ' --input 20110518135934_atomic_imu.log --output 20110518135934_atomic_imu.x3d\n'
    examples += '  BEDs files:\n'
    examples += '    ' + sys.argv[0] + ' --input BED00012.EVT --output BED00012.x3d --translate\n'
    examples += '    ' + sys.argv[0] + ' --input BED00001.WAT --output BED00001_wat.x3d --speedup 100\n'
    examples += '  Combine 2 event files into one output:\n'
    examples += '    ' + sys.argv[0] + ' --input BED00038.EVT BED00039.EVT --output BED01_1_June_2013.x3d\n'

    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                     description='Convert BED event file(s) to a NetCDF file',
                                     epilog=examples)

    parser.add_argument('-i', '--input', action='store', nargs='*', required=True, help="Specify input BED log file name(s)")
    parser.add_argument('-o', '--output', action='store', help="Specify output x3d file name")
    parser.add_argument('-s', '--speedup', type=int, action='store', default=1, help="Specify playback speedup, e.g. 10 for 10 times faster that realtime")
    parser.add_argument('--translate', action='store_true', default=False, help="Specify to integrate accelerations to translations")
    parser.add_argument('--rotation', action='store', default='EA', help="Specify 'EA' or 'EV' for Euler Angle or Euler Vector to specify rotations")
    parser.add_argument('--trajectory', action='store', help="csv file with columns of latitude and longitude where first and lat row corresponds to first and last reords of input event files")
    parser.add_argument('-v', '--verbose', type=int, action='store', default=0, help="Specify verbosity level, values greater than 1 give more details ")

    args = parser.parse_args()

    if not (args.input and args.output):
        parser.error("Must specify both --input and --output options.\n")

    beds_x3d = BEDS_X3D(args, sys.argv)

    beds_x3d.readFiles()
    x3dText = beds_x3d.createX3D()
    if args.verbose > 1: 
        print "x3dText = %s" % x3dText

    f = open(args.output, 'w')
    f.write(x3dText)
    f.close()

    print "Wrote file %s - open it in InstantReality Player, BS Contact, Xj3D, X3DOM, or other X3D browser." % args.output



