#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2014, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

Script produce products (plots, kml, etc.) to help understand drifting data.
- Make progressive vector diagram from moored ADCP data (read from STOQS)
- Plot drogued drifter data (read from Tracking DB)
- Plot sensor data (read from STOQS)

Output as a .png map, .kml file, or ...

Mike McCann
MBARI 22 September 2014

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE']='settings'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))  # settings.py is one dir up

import csv
import urllib2
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from collections import defaultdict
from stoqs.models import MeasuredParameter


class Drift():
    '''Data and methods to support drift data product preparation
    '''
    drifters = defaultdict(lambda: {'es': [], 'lat': [], 'lon': []})

    def process(self):
        '''Read in data and build structures that we can generate products from
        '''
        # Drifter data
        for url in self.args.drifterData:
            # Careful - trackingdb returns the records in reverse time order
            for r in csv.DictReader(urllib2.urlopen(url)):
                self.drifters[r['platformName']]['es'].append(float(r['epochSeconds']))
                self.drifters[r['platformName']]['lat'].append(float(r['latitude']))
                self.drifters[r['platformName']]['lon'].append(float(r['longitude']))

        # ADCP data
        if self.args.adcpPlatform:
            adcpQS = MeasuredParameter.objects.using(self.args.database).filter(
                                measurement__instantpoint__activity__platform__name=self.args.adcpPlatform)

        if self.startDatetime:
            adcpQS = adcpQS.filter(measurement__instantpoint__gte=self.startDatetime)
        if self.endDatetime:
            adcpQS = adcpQS.filter(measurement__instantpoint__lte=self.endDatetime)

        if self.args.adcpMinDepth:
            adcpQS = adcpQS.filter(measurement__depth__gte=self.args.adcpMinDepth)
        if self.args.adcpMaxDepth:
            adcpQS = adcpQS.filter(measurement__depth__lte=self.args.adcpMaxDepth)

        utd = adcpQS.filter(parameter__standard_name='eastward_sea_water_velocity').values_list(
                                'datavalue', 'measurement__instantpoint__timevalue', 'measurement__depth').order_by(
                                        'measurement__depth', 'measurement__instantpoint__timevalue')
        vtd = adcpQS.filter(parameter__standard_name='northward_sea_water_velocity').values_list(
                                'datavalue', 'measurement__instantpoint__timevalue', 'measurement__depth').order_by(
                                        'measurement__depth', 'measurement__instantpoint__timevalue')

        # Compute positions (progressive vectors) - horizontal displacement in meters
        x = defaultdict(lambda: [0])
        y = defaultdict(lambda: [0])
        for i, ((u, ut, ud), (v, vt, vd)) in enumerate(zip(utd, vtd)):
            try:
                udiff = utd[i+1][1] - ut
                vdiff = vtd[i+1][1] - vt
            except IndexError:
                # Extrapolate using last time difference, assuming it's regular and that we are at the last point
                udiff = utd[i-1][1] - utd[i][1]
                vdiff = vtd[i-1][1] - vtd[i][1]
                
            if udiff != vdiff:
                raise Exception('udiff != vdiff')
            else:
                dt = udiff.seconds + udiff.days * 24 * 3600

            x[ud].append(u * dt / 1000)
            y[ud].append(u * dt / 1000)

        import pdb
        pdb.set_trace()

    def saveFigure(self, fig, figCount):
        '''
        Save this page
        '''
        provStr = 'Created with STOQS command ' + '\\\n'.join(wrap(self.commandline, width=160)) + ' on ' + datetime.now().ctime()
        plt.figtext(0.0, 0.0, provStr, size=7, horizontalalignment='left', verticalalignment='bottom')
        plt.tight_layout()
        if self.args.title:
            fig.text(0.5, 0.975, self.args.title, horizontalalignment='center', verticalalignment='top')

        fileName = self.getFileName(figCount)
        if self.args.verbose:
            print '  Saving file', fileName
        fig.savefig(fileName)

    def createGeoTiff(self):
        '''Your image must be only the geoplot with no decorations like axis titles, axis labels, etc., and you 
        will need accurate upper-left and lower-right coordinates in EPSG:4326 projection, also known as WGS 84 projection,...

        The syntax is pretty straightforward, something like the following will convert your image to the correct format:

            gdal_translate <image.png> <image.tiff> -a_ullr -122.25 37.1 -121.57365 36.67558 

        There is also a python wrapper for the GDAL library
 
        https://pypi.python.org/pypi/GDAL/
        '''

    def process_command_line(self):
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n\n' 
        examples += "M1 ADCP progressive vector diagram and Stella drifter data:\n"
        examples += sys.argv[0] + " --database stoqs_september2014 --adcpPlatform M1_Mooring --adcpMinDepth 30 --adcpMaxDepth 40"
        examples += " --drifterData http://odss.mbari.org/trackingdb/position/stella101/between/20140922T171500/20141010T000000/data.csv"
        examples += " http://odss.mbari.org/trackingdb/position/stella110/between/20140922T171500/20141010T000000/data.csv"
        examples += " http://odss.mbari.org/trackingdb/position/stella122/between/20140922T171500/20141010T000000/data.csv"
        examples += "\n"
        examples += '\nIf running from cde-package replace ".py" with ".py.cde" in the above list.'
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Script to produce products to help understand drift caused by currents in the ocean',
                                         epilog=examples)
                                             
        parser.add_argument('-d', '--database', action='store', help='Database alias', default='stoqs_september2014', required=True)

        parser.add_argument('--adcpPlatform', action='store', help='STOQS Platform Name for ADCP data')
        parser.add_argument('--adcpMinDepth', action='store', help='Minimum depth of ADCP data for progressive vector data', type=float)
        parser.add_argument('--adcpMaxDepth', action='store', help='Maximum depth of ADCP data for progressive vector data', type=float)

        parser.add_argument('--drifterData', action='store', help='List of MBARItracking database .csv urls for drifter data', nargs='*', default=[])
    
        parser.add_argument('--start', action='store', help='Start time in YYYYMMDDTHHMMSS format')
        parser.add_argument('--end', action='store', help='End time in YYYYMMDDTHHMMSS format')

        parser.add_argument('--kmlFileName', action='store', help='Name of file for KML output')
        parser.add_argument('--pngFileName', action='store', help='Name of file for PNG image of map')
        parser.add_argument('--geotiffFileName', action='store', help='Name of file for geotiff image of map')

        parser.add_argument('-v', '--verbose', nargs='?', choices=[1,2,3], type=int, help='Turn on verbose output. Higher number = more output.', const=1)
    
        self.args = parser.parse_args()
        self.commandline = ' '.join(sys.argv)

        self.startDatetime = None
        if self.args.start:
            self.startDatetime = datetime.strptime(self.args.start, '%Y%m%dT%H%M%S')
        self.endDatetime = None
        if self.args.end:
            self.endDatetime = datetime.strptime(self.args.end, '%Y%m%dT%H%M%S')
    
    
if __name__ == '__main__':

    d = Drift()
    d.process_command_line()

    d.process()
    if c.args.kmlFileName:
        c.createKML()

    if c.args.pngFileName:
        c.createPNG()

