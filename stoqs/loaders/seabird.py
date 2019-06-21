#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2012, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__doc__ = '''

Support functions for reading data from Seabird .asc, .hdr, and .btl files.
A place from whihch to import factored out functions.

Would be nice to use PyCNV from https://github.com/castelao/pycnv, for more
robust Sea Bird data file handling.  The .cnv files can gotten from the BOG_Archive 
on atlas in directory (e.g.):

/net/atlas/ifs/mbariarchive/BOG_Archive/DataArchives/Regions/NortheastPacific/CruiseData/SECRET-CalCOFI-CN-CANON/2012/C0912.WF/pCTD

Mike McCann
MBARI 23 October 2012

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@license: __license__
'''

import os
import sys
from urllib.request import urlopen

class HdrFileNotFound(Exception):
    pass


class PositionNotFound(Exception):
    pass


def get_year_lat_lon(*args, **kwargs):
    '''
    Open .hdr file to get the year, lat, and lon of this cast.  Can be called with hdrUrl='' argument in which case
    data will be read from the specified URL instead of from file.
    Returns (year, lat, lon) tuple
    '''
    try:
        FH = urlopen(kwargs['hdrUrl'])
    except KeyError:
        hdrFile = '.'.join(args[0].split('.')[:-1]) + '.hdr'
        if os.path.exists(hdrFile):
            FH = open(hdrFile, errors='ignore')
        else:
            raise HdrFileNotFound('Header file %s not found' % hdrFile)

    for line in FH:
        ##print(line)
        try:
            line = line.decode('utf-8')
        except AttributeError:
            # line likely aleady a str object w/o the decode attribute
            pass
        if line.find('NMEA Latitude') != -1:
            latD = int(line.split(' ')[4])
            latM = float(line.split(' ')[5])
            latNS = line.split(' ')[6].strip()
        if line.find('NMEA Longitude') != -1:
            lonD = int(line.split(' ')[4])
            lonM = float(line.split(' ')[5])
            lonEW = line.split(' ')[6].strip()
        if line.find('NMEA UTC (Time)') != -1:
            year = int(line.split(' ')[7])
            # Breaking here assumes that the Time line appears after Latitude & Longitude
            break

    try:
        if latNS == 'N':
            lat = float("%4.7f" % (latD + latM / 60))
        else:
            lat = float("-%4.7f" % (latD + latM / 60))

        if lonEW == 'W':
            lon = float("-%4.7f" % (lonD + lonM / 60))
        else:
            lon = float("%4.7f" % (lonD + lonM / 60))

    except UnboundLocalError:
        raise PositionNotFound('No NMEA Latitude and Longitude in file %s' % hdrFile)

    return year, lat, lon


def convert_up_to_down(file):
    '''
    Convert an upcast SeaBird pctd file to a downcast file
    '''
    newName = '.'.join(file.split('.')[:-1]) + 'up.asc'
    outFile = open(newName, 'w')
    lines = []
    i = 0
    for line in open(file):
        if i == 0:
            outFile.write(line)
        else:
            lines.append(line)
        i = i + 1

    for line in reversed(lines):
            outFile.write(line)

    outFile.close()

    return newName


if __name__ == '__main__':

    # Tests
    yr,la,lo = get_year_lat_lon(hdrUrl= 'http://odss.mbari.org/thredds/fileServer/CANON_september2012/wf/pctd/c0912c53.hdr')
    if yr != 2012 or la != 36.3916667 or lo != -122.6896667:
        print("*** ERRROR.  The test of get_year_lat_lon should return (2012, 36.3916667, -122.6896667) ***")
    print((yr, la, lo))
