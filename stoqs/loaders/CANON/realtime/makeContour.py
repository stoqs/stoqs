__author__ = 'dcline'


import os
import sys
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../toNetCDF"))      # lrauvNc4ToNetcdf.py is in sister toNetCDF dir
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))           # settings.py is two dirs up
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "./"))
import pytz
from . import Contour

from .Contour import Contour 
from datetime import datetime, timedelta

class makeContour(object):
    '''
    Create contour plots for visualizing data from LRAUV vehicles
    '''

    def process_command_line(self):
        '''The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Script to create contour plots of CTD data collected by the LRAUV')

        parser.add_argument('-d', '--database', action='store', help='database', default='stoqs')
        parser.add_argument('--start', action='store', help='Start time in YYYYMMDDTHHMMSS format', default='20150310T210000', required=False)
        parser.add_argument('--end', action='store', help='End time in YYYYMMDDTHHMMSS format',default='20150311T21000', required=False)
        parser.add_argument('--daily', action='store', help='True to generate a daily plot',default=True, required=False)
        parser.add_argument('--animate', action='store', help='if True will create frames to make animation from',default=False, required=False)
        parser.add_argument('--zoom', action='store', help='time window in hours to zoom animation',default=8, required=False)
        parser.add_argument('--overlap', action='store', help='time window in hours to overlap animation',default=2, required=False)
        parser.add_argument('--title', action='store', help='Title for plots, will override default title created if --start specified', default='MBARI LRAUV Survey')
        parser.add_argument('-v', '--verbose', nargs='?', choices=[1,2,3], type=int, help='Turn on verbose output. Higher number = more output.', const=1)
        parser.add_argument('--minDepth', action='store', help='Minimum depth for data queries', default=0, type=float)
        parser.add_argument('--maxDepth', action='store', help='Maximum depth for data queries', default=80, type=float)
        parser.add_argument('-o', '--outDir', action='store', help='output directory to store contour image file', default='/tmp',required=False)
        parser.add_argument('--parms', action='store', help='List of space separated parameters to contour plot', nargs='*', default=
                                    ['sea_water_temperature', 'sea_water_salinity', 'mass_concentration_of_chlorophyll_in_sea_water'])
        parser.add_argument('--platformName', action='store', help='Filename to store output image to', default='daphne',required=False)
        parser.add_argument('-t', '--contourUrl', action='store', help='base url to store cross referenced contour plot resources', default='http://elvis.shore.mbari.org/thredds/catalog/LRAUV/stoqs',required=False)

        self.args = parser.parse_args()
        self.commandline = ' '.join(sys.argv)

        startDatetime = datetime.strptime(self.args.start, '%Y%m%dT%H%M%S')
        endDatetime = datetime.strptime(self.args.end, '%Y%m%dT%H%M%S')

        self.endDatetimeUTC = pytz.utc.localize(endDatetime)
        endDatetimeLocal = self.endDatetimeUTC.astimezone(pytz.timezone('America/Los_Angeles'))

        self.startDatetimeUTC = pytz.utc.localize(startDatetime)
        startDatetimeLocal = self.startDatetimeUTC.astimezone(pytz.timezone('America/Los_Angeles'))

        # If daily image round the UTC time to the local time and do the query for the 24 hour period
        if self.args.daily:
            startDatetimeLocal = startDatetimeLocal.replace(hour=0,minute=0,second=0,microsecond=0)
            endDatetimeLocal = startDatetimeLocal.replace(hour=23,minute=0,second=0,microsecond=0)
            self.startDatetimeUTC = startDatetimeLocal.astimezone(pytz.utc)
            self.endDatetimeUTC = endDatetimeLocal.astimezone(pytz.utc)

    def run(self):
        title = 'MBARI LRAUV Survey'
        outFile = self.args.outDir + '/' + self.args.platformName  + '_log_' + self.startDatetimeUTC.strftime('%Y%m%dT%H%M%S') + '_' + self.endDatetimeUTC.strftime('%Y%m%dT%H%M%S') + '.png'
        c = Contour(self.startDatetimeUTC, self.endDatetimeUTC, self.args.database, self.args.platformName, self.args.parms, title, outFile, False)
        c.run()

        cmd = r'scp %s stoqsadm@elvis.shore.mbari.org:/mbari/LRAUV/stoqs' % (outFile)
        #logger.debug('%s', cmd)
        import pdb; pdb.set_trace()
        os.system(cmd)


if __name__ == '__main__':

    d = makeContour()
    d.process_command_line()
    d.run()
