#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2013, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

Script to create biplots of a cross product of all Parameters in a database.

Mike McCann
MBARI 10 February 2014

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

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.dates import DAILY
from datetime import datetime, timedelta
from django.contrib.gis.geos import LineString, Point
from utils.utils import round_to_n
from textwrap import wrap
from mpl_toolkits.basemap import Basemap
import matplotlib.gridspec as gridspec

from contrib.analysis import BiPlot, NoPPDataException, NoTSDataException


class CrossProductBiPlot(BiPlot):
    '''
    Make customized BiPlots (Parameter Parameter plots) for platforms from STOQS.
    '''

    def ppSubPlot(self, x, y, platform, color, xParm, yParm, ax, startTime):
        '''
        Given names of platform, x & y paramters add a subplot to figure fig.
        '''

        xmin, xmax, xUnits = self._getAxisInfo(platform, xParm)
        ymin, ymax, yUnits = self._getAxisInfo(platform, yParm)

        # Make the plot 
        ax.set_xlim(round_to_n(xmin, 1), round_to_n(xmax, 1))
        ax.set_ylim(round_to_n(ymin, 1), round_to_n(ymax, 1))

        if self.args.xLabel == '':
            ax.set_xticks([])
        elif self.args.xLabel:
            ax.set_xlabel(self.args.xLabel)
        else:
            ax.set_xlabel('%s (%s)' % (xParm, xUnits))

        if self.args.yLabel == '':
            ax.set_yticks([])
        elif self.args.yLabel:
            ax.set_ylabel(self.args.yLabel)
        else:
            ax.set_ylabel('%s (%s)' % (yParm, yUnits))

        ax.scatter(x, y, marker='.', s=10, c='k', lw = 0, clip_on=True)
        ax.text(0.0, 1.0, platform, transform=ax.transAxes, color=color, horizontalalignment='left', verticalalignment='top')

        return ax

    def getFilename(self, startTime):
        '''
        Construct plot file name
        '''
        fnTempl= 'platforms_{time}' 
        fileName = fnTempl.format(time=startTime.strftime('%Y%m%dT%H%M'))
        wcName = fnTempl.format(time=r'*')
        wcName = os.path.join(self.args.plotDir, self.args.plotPrefix + wcName)
        if self.args.daytime:
            fileName += '_day'
            wcName += '_day'
        if self.args.nighttime:
            fileName += '_night'
            wcName += '_night'
        fileName += '.png'

        fileName = os.path.join(self.args.plotDir, self.args.plotPrefix + fileName)

        return fileName, wcName

    def makeCrossProductBiPlots(self):
        '''
        Cycle through Parameters and make biplots against each of the other parameters
        Parameters can be restricted with --ignore and and --sampled arguments.
        '''
        allActivityStartTime, allActivityEndTime, allExtent  = self._getActivityExtent(self.args.platform)
        allParms = self._getParameters(ignoreNames=self.args.ignore)
        if self.args.sampled:
            xParms = self._getParameters(groupNames=['Sampled'], ignoreNames=self.args.ignore)
        else:
            xParms = allParms

        fig = plt.figure(figsize=(9, 9))
        axisNum = 1
        for xP in xParms:
            if self.args.verbose: print xP.name
            print xP.name
            for yP in allParms:
                if xP.name == yP.name:
                    continue
                if self.args.verbose: print '\t"%s"' % yP.name
                print '\t%s' % yP.name

                try:
                    x, y = self._getPPData(None, None, None, xP.name, yP.name)
                except NoPPDataException, e:
                    if self.args.verbose: print e
                    print e
                    continue

                ax = fig.add_subplot(4, 4, axisNum)
                ax.scatter(x, y, marker='.', s=1, c='k')
                ax.set_xticklabels([])
                ax.set_yticklabels([])
                ax.set_xlabel(xP.name)
                ax.set_ylabel(yP.name)

                axisNum += 1
                if axisNum > 16:
                    break
            else:
                continue
            break


        provStr = 'Created with STOQS command ' + '\\\n'.join(wrap(self.commandline, width=160)) + ' on ' + datetime.now().ctime()
        plt.figtext(0.0, 0.0, provStr, size=7, horizontalalignment='left', verticalalignment='bottom')
        plt.tight_layout()

        fileName = 'cpBiPlot.png'
        print 'Saving to file', fileName
        fig.savefig(fileName)

        print 'Done.'

    def process_command_line(self):
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n\n' 
        examples += sys.argv[0] + ' -d stoqs_september2013_o -p dorado -x bbp420 -y fl700_uncorr\n'
        examples += '(Image files will be written to the current working directory)'
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Read Parameter-Parameter data from a STOQS database and make bi-plots',
                                         epilog=examples)
                                             
        parser.add_argument('-p', '--platform', action='store', help='One or more platform names separated by spaces', nargs='*')
        parser.add_argument('-d', '--database', action='store', help='Database alias', default='stoqs_september2013_o', required=True)
        parser.add_argument('--daytime', action='store_true', help='Select only daytime hours: 10 am to 2 pm local time')
        parser.add_argument('--nighttime', action='store_true', help='Select only nighttime hours: 10 pm to 2 am local time')
        parser.add_argument('--minDepth', action='store', help='Minimum depth for data queries', default=None, type=float)
        parser.add_argument('--maxDepth', action='store', help='Maximum depth for data queries', default=None, type=float)
        parser.add_argument('--sampled', action='store_true', help='Compare Sampled Parameters to every other Parameter')
        parser.add_argument('--ignore', action='store', help='Ignore these Parameter names', nargs='*')
        parser.add_argument('--plotDir', action='store', help='Directory where to write the plot output', default='.')
        parser.add_argument('--plotPrefix', action='store', help='Prefix to use in naming plot files', default='')
        parser.add_argument('--title', action='store', help='Title to appear on top of plot')
        parser.add_argument('-v', '--verbose', action='store_true', help='Turn on verbose output')
    
        self.args = parser.parse_args()
        self.commandline = ' '.join(sys.argv)
    
    
if __name__ == '__main__':

    bp = CrossProductBiPlot()
    bp.process_command_line()
    bp.makeCrossProductBiPlots()

