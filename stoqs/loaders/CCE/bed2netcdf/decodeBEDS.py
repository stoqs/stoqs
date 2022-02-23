#! /usr/bin/env python
# MBARI decode program to turn .WAT, .EVT and .Z files 
# into machine readable tab delimited files
# For use python3 without any packages
#
# Copied from https://bitbucket.org/mbari/beds/src/master/tools/decode/
# and maintained here for use by STOQS.

import gzip
import os
import struct 
import argparse
import datetime
import sys
from bedsadc import adcEngValue, EXT_PRESS_CHAN
from euclid import Quaternion
from euclid import *
import math

def degrees(angles):
    out = []
    for i in range(len(angles)):
        rad = angles[i]
        deg = rad * 180.0 / math.pi
        out.append(deg)
    return out

class Record():
    def __init__(self, headerTypeString, headerType, parseString, parseLen, outputHeaderString):
        self.headerTypeString = headerTypeString
        self.headerType = headerType
        self.parseString = parseString
        self.parseLen = parseLen
        self.outputHeaderString = outputHeaderString
        self.count = 0
        if outputHeaderString is None:
            self.numOutputs = 0
            self.outputHeaderString = ""
        else:
            self.numOutputs = outputHeaderString.count(',')
    def __str__(self):
        return "Record {}: type {} len {}".format(self.headerTypeString, 
            self.headerType, self.parseLen)
    def __repr__(self):
        return self.__str__()

    def checkRecType(self, recType):
        if recType != self.headerType:
            print("Incorrect header type for {}s expected {} got {}".
                format(self.headerTypeString, self.headerType, recType))
            raise KeyError

    def readFromFile(self, inputfile):
        self.count +=1
        data = inputfile.read(self.parseLen)
        # Need as list for adding fractional seconds to SecMarkerType's varlist
        self.varlist = list(struct.unpack(self.parseString, data))

    def outputSparse(self, rec):
        if rec.headerType == self.headerType:
            return self.outputLine()
        else:
            return self.outputEmpty()
       
    def outputHeader(self):
        return self.outputHeaderString
    def outputEmpty(self):
        output = ""
        for i in range(self.numOutputs):
            output += ","
        return output

    def outputLine(self, varlist): # record handler should implement these
        raise NotImplementedError()

class FileHdrType(Record):
    def __init__(self, varlist=None):
        headerTypeString = "FileHdrType"
        headerType = 0
        parseLen = 20
        parseString = "bxHHHHHII"
        self.varlist = varlist
        outputHeader = ""
        super().__init__(headerTypeString, headerType, parseString, parseLen, outputHeader)
    def startTime(self):
        if self.varlist == None: return self.outputEmpty()
        [recType, fmtVersion, platformID, dataSize, dataRate, startMs, startTime, durationMs] = self.varlist
        self.checkRecType(recType)
        startTime = startTime + startMs/1000.0
        t = datetime.datetime.fromtimestamp(startTime)
        outputString="FileHdr formatVersion {} platformID {}, dataSize {}, dataRate {} \r\n" \
                        "startTime {:0.3f} {}, duration {:0.3f}s" .format(
                        fmtVersion, platformID, dataSize, dataRate, startTime,
                        t, durationMs/1000.0)
        print(outputString)
        return startTime
    def outputLine(self):
        if self.varlist == None: return self.outputEmpty()
        [recType, fmtVersion, platformID, dataSize, dataRate, startMs, startTime, durationMs] = self.varlist
        self.checkRecType(recType)
        return ""
    def outputOldStype(self):
        [recType, fmtVersion, platformID, dataSize, dataRate, startMs, startTime, durationMs] = self.varlist
        self.checkRecType(recType)
        t = datetime.datetime.fromtimestamp(startTime+startMs/1000.0)
        outputString="FileHdr formatVersion {} platformID {}, dataSize {}, dataRate {} \r\n" \
                        "startTime {}, duration {:0.3f}" .format(
                        fmtVersion, platformID, dataSize, dataRate,
                        t, durationMs/1000.0)
        return outputString

class SecMarkerType(Record):
    def __init__(self, varlist=None):
        headerTypeString = "SecMarkerType"
        headerType = 1
        parseLen = 8
        parseString = "bxxxI"
        outputHeader = "epoch_time,date_time,"
        self.varlist = varlist
        super().__init__(headerTypeString, headerType, parseString, parseLen, outputHeader)   
        return 
    def outputLine(self):
        if self.varlist == None: return self.outputEmpty()
        [recType, rcdTime] = self.varlist
        self.checkRecType(recType)
        t = datetime.datetime.fromtimestamp(rcdTime)
        outputString="{:0.3f},{},".format(rcdTime,t)
        return outputString        
    def outputOldStype(self, varlist):
        [recType, rcdTime] = varlist
        self.checkRecType(recType)
        t = datetime.datetime.fromtimestamp(rcdTime)
        outputString="SecondMarker {}".format(t)
        return outputString

class InertialDataType(Record):
    def __init__(self, varlist=None):
        headerTypeString = "InertialDataType"
        headerType = 2
        parseLen = 32
        parseString = "bxfffffff"
        outputHeader = "accel_x,accel_y,accel_z,roll,pitch,heading,quat_w,quat_x,quat_y,quat_z,"
        self.varlist = varlist
        super().__init__(headerTypeString, headerType, parseString, parseLen, outputHeader)
    def outputLine(self):
        if self.varlist == None: return self.outputEmpty()
        [recType, ax, ay, az, qw, qx, qy, qz] = self.varlist
        self.checkRecType(recType)
        q = Quaternion(qw, qx, qy, qz)       
        [heading, pitch, roll] = degrees(q.get_euler())
        outputString="{:0.4},{:0.4},{:0.4}," \
                     "{:0.4},{:0.4},{:0.4},"\
                     "{:0.4},{:0.4},{:0.4},{:0.4},".format(
                        ax, ay, az, roll, pitch, heading, qw, qx, qy, qz)
        return outputString
    def outputOldStyle(self, varlist):
        [recType, ax, ay, az, qw, qx, qy, qz] = varlist
        self.checkRecType(recType)
        q = Quaternion(qw, qx, qy, qz)
        [heading, pitch, roll] = degrees(q.get_euler())
        outputString="Inertial acc,{:0.4},{:0.4},{:0.4},euler,{:0.4},{:0.4},{:0.4}quat,{:0.4},{:0.4},{:0.4},{:0.4},".format(
                        ax, ay, az, roll, pitch, heading, qw, qx, qy, qz)
        return outputString

class PressureType(Record):
    def __init__(self, varlist=None):
        headerTypeString = "PressureType"
        headerType = 3
        parseLen = 4
        parseString = "bxH"
        outputHeader = "pressureCnts,pressure,units,"
        self.varlist = varlist
        super().__init__(headerTypeString, headerType, parseString, parseLen, outputHeader)
    def outputLine(self):
        if self.varlist == None: return self.outputEmpty()
        [recType, pressure] = self.varlist
        self.checkRecType(recType)
        engval,units = adcEngValue(EXT_PRESS_CHAN, pressure)
        outputString="{},{},{},".format(pressure, engval, units)
        return outputString
    def outputOldStype(self, varlist):
        [recType, pressure] = varlist
        self.checkRecType(recType)
        engval,units = adcEngValue(EXT_PRESS_CHAN, pressure)
        outputString="Pressure,{},{},{}".format(pressure, engval, units)
        return outputString

class IndexType(Record):
    def __init__(self, varlist=None):
        headerTypeString = "IndexType"
        headerType = 4
        parseLen = 32
        parseString = "bxHIIis"
        outputHeader = "startTimeEpoch,startTime,duration,maxAccel,filename,"
        self.varlist = varlist
        super().__init__(headerTypeString, headerType, parseString, parseLen, outputHeader)
    def outputLine(self):
        if self.varlist == None: return self.outputEmpty()
        [recType, startMs, startTime, durationMs, maxVal, filename] = self.varlist
        self.checkRecType(recType)
        print("I don't think index record types are supposed to be in wat or event files....")
        startTime = startTime+startMs/1000.0
        t = datetime.datetime.fromtimestamp(startTime)
        outputString="{:0.4f},{},{:0.3f},{},{}" .format(                       
                        startTime, t, durationMs/1000.0, maxVal, filename)
        return outputString
    def outputOldStype(self, varlist):
        [recType, startMs, startTime, durationMs, maxVal, filename] = varlist
        self.checkRecType(recType)
        t = datetime.datetime.fromtimestamp(startTime+startMs/1000.0)
        outputString="Index " \
                        "startTime {}, duration {:0.3f}, maxAccel {}, filename {}" .format(                       
                        t, durationMs/1000.0, maxVal, filename)
        return outputString

class SysRecType(Record):
    def __init__(self, varlist=None):
        headerTypeString = "SysRecType"
        headerType = 5
        parseLen = 20
        parseString = "bxxxIHHHHHH"
        outputHeader="startTimeEpoch,startTime,battV,minModemBatt,extPressure,intPresssure,intTemp,intHumidity,"
        self.varlist = varlist
        super().__init__(headerTypeString, headerType, parseString, parseLen, outputHeader)
    def outputLine(self):
        if self.varlist == None: return self.outputEmpty()
        [recType, rcdTime, battV, minModemBat, extPresure, intPressure, intTemp, intHumidity] = self.varlist
        self.checkRecType(recType)
        t = datetime.datetime.fromtimestamp(rcdTime)
        outputString="{:0.4f},{},{},{},{},{},{},{},".format(
            rcdTime, t, battV, minModemBat, extPresure, intPressure, intTemp, intHumidity)
        return outputString
    def outputOldStyle(self, varlist):
        [recType, rcdTime, battV, minModemBat, extPresure, intPressure, intTemp, intHumidity] = varlist
        self.checkRecType(recType)
        t = datetime.datetime.fromtimestamp(rcdTime)
        outputString="System,{} battV {} minModemBatt {} extPressure {} intPresssure {} intTemp {} intHumidity {}".format(t, battV, minModemBat, extPresure, intPressure, intTemp, intHumidity)
        return outputString

class RecordTypeIterator():
    def __init__(self, RecordType):
        self.recordTypeList = RecordType.recordType
        self.index = 0
    def __next__(self):
        if self.index < len(self.recordTypeList):
            result = self.recordTypeList[self.index]
            self.index += 1
            return result
        raise StopIteration


class RecordType():
    def __init__(self):
        self.recordType = [
            FileHdrType(),
            SecMarkerType(),
            InertialDataType(),
            PressureType(),
            IndexType(),
            SysRecType()
        ]
        self.InitialDictOfEach()
    def __iter__(self):
        return RecordTypeIterator(self)

    def LookUp(self, header):
        if header is None: return None
        if len(header) == 0: return None

        header = header[0]
        if header < len(self.recordType):
            return self.recordType[header]
        else:
            return None
    def InitialDictOfEach(self):
        self.rtDict = {}
        for rt in self.recordType:
            self.rtDict[rt.headerTypeString] = rt
            
    def setRec(self, rec):
        self.rtDict[rec.headerTypeString] = rec
    
    def getRecOfType(self, rec):
        return self.rtDict[rec.headerTypeString]



def peek(f, length=1):
    pos = f.tell()
    try:
        data = f.read(length) # Might try/except this line, and finally: f.seek(pos)
    except:
        print("Exception ", sys.exc_info()[0])    
    f.seek(pos)
    return data

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected: '+v)

def main(internal_arguments=None):
    parser = argparse.ArgumentParser(description='Decode BEDS .Z?? .WAT and .EVT files')
    parser.add_argument("-s", "--sparse_output", help="If CSV file should be sparse, with only new lines being printed, default false", type=str2bool, nargs='?', const='True', default=False)
    parser.add_argument("-a", "--no_header_do_append", help="Append data to existing file, default false", type=str2bool, nargs='?', default=False)
    parser.add_argument("-o", "--output", help="Ouput .csv filename, defaults to output.csv", default="output.csv")
    parser.add_argument('input', nargs='+', help='Input file (may be zipped)')

    if internal_arguments is not None:
        print("Internal arguments")
        args=parser.parse_args(internal_arguments)
    else: # running from the command line
        args = parser.parse_args()

    print(args)

    recList = RecordType()

    inputfilename = args.input[0]
    suffix = os.path.splitext(inputfilename)[1][1:].strip().lower()
    if "z" in suffix:
        print("Treating file as zipped")
        inputfile = gzip.open(inputfilename) 
    else:
        inputfile = open(inputfilename, "rb")

    if args.no_header_do_append:
        output = open(args.output, "wa")
    else:
        output = open(args.output, "w")        
        header = "recNum,"
        for rec in recList:
            header += rec.outputHeader()
        header += "\n"
        output.write(header)

    # read the first inputfile, it is the file header type which we'll use for timing until we get a secRec
    rec = FileHdrType()
    rec.readFromFile(inputfile)
    sample_rate = rec.varlist[4]
    startTime = rec.startTime()
    secrec = SecMarkerType()
    secrec.varlist = [secrec.headerType, startTime]
    recList.setRec(secrec)

    # read in the file
    rec = recList.LookUp(peek(inputfile,1)) 
    recNum = 0 
    frac_sec = 0.0
    last_esec = secrec.varlist[1]
    while rec is not None:
        line = "{},".format(recNum)
        recNum += 1
        rec.readFromFile(inputfile)
        recList.setRec(rec)
        for recType in recList:
            rt = recList.getRecOfType(recType)
            if isinstance(rt, SecMarkerType):
                # Fill in the fractional seconds between the second markers
                if int(rt.varlist[1]) > last_esec:
                    frac_sec = 0.0
                rt.varlist[1] = int(rt.varlist[1]) + frac_sec
                frac_sec += 1 / sample_rate
                last_esec = int(rt.varlist[1])
            if args.sparse_output:
                line += rt.outputSparse()
            else:
                line += rt.outputLine()
        line += "\n"
        output.write(line)
        rec = recList.LookUp(peek(inputfile,1))

    inputfile.close()
    output.close()
    print("Records decoded:")
    for recType in recList:
        print("{}\t\t{}".format(recType.headerTypeString, recType.count))



if __name__ == "__main__":
    if sys.version_info[0] == 3:
        main()
    else:
        print("Need python version 3.x to run this program")
         
