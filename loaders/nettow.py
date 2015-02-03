#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2015, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

Script to load Sampling events for Net Tow data
- Produce a .csv file from subsample information file and db info
- Load Samples from that .csv file into specified database

Mike McCann
MBARI 3 February 2015

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE']='settings'
project_dir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, project_dir)

import csv
import time
import pyproj
import urllib2
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytz 
from datetime import datetime
from collections import defaultdict
from stoqs.models import MeasuredParameter, NominalLocation, ActivityParameter
from django.http import HttpRequest


class NetTow():
    '''Data and methods to support Net Tow Sample data loading
    '''

    def make_csv(self):
        '''Construct parent Sample csv file and write to output file
        '''
        pass

    def load_samples(self):
        '''Load parent Samples into the database
        '''
        pass

    def process_command_line(self):
        '''The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Example:' + '\n\n' 
        examples += "  Step 1 - Create .cvs file of parent Sample information:\n"
        examples += "    " + sys.argv[0] + " --database stoqs_simz_aug2013_t"
        examples += " --subsampleFile 2013_SIMZ_TowNets_STOQS.csv"
        examples += " --csvFile 2013_SIMZ_TowNet_ParentSamples.csv\n"
        examples += "\n"
        examples += "  Step 2 - Load parent Sample information:\n"
        examples += "    " + sys.argv[0] + " --database stoqs_simz_aug2013_t"
        examples += " --loadFile 2013_SIMZ_TowNet_ParentSamples.csv\n"
        examples += '\nIf running from cde-package replace ".py" with ".py.cde".'
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Script to load parent Samples for Tow Net data',
                                         epilog=examples)
                                             
        parser.add_argument('-d', '--database', action='store', help='Database alias', required=True)

        parser.add_argument('-s', '--subsampleFile', action='store', help='File name containing analysis data from net tows in STOQS subsample format')
        parser.add_argument('-c', '--csvFile', action='store', help='Output comma separated value file containing parent Sample data')

        parser.add_argument('-l', '--loadFile', action='store', help='Load parent Sample data into database')

        parser.add_argument('-v', '--verbose', nargs='?', choices=[1,2,3], type=int, help='Turn on verbose output. Higher number = more output.', const=1)
    
        self.args = parser.parse_args()
        self.commandline = ' '.join(sys.argv)

        if self.args.subsampleFile:
            if not self.args.csvFile:
                parser.error('Must include --csvFile argument with --subsampleFile option')
                
        elif self.args.loadFile:
            pass

        else:
            parser.error('Must provide either --subsampleFile or --loadFile option')

    
if __name__ == '__main__':

    nt = NetTow()
    nt.process_command_line()


    if nt.args.subsampleFile and nt.args.csvFile:
        nt.make_csv()

    elif nt.args.loadFile:
        nt.load_samples()

