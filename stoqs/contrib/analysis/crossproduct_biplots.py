#!/usr/bin/env python
'''
Script to create biplots of a cross product of all Parameters in a database.

Mike McCann
MBARI 10 February 2014
'''

import os
import sys
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE']='settings'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))  # settings.py is one dir up

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from utils.utils import round_to_n, pearsonr
from textwrap import wrap
from numpy import polyfit
from pylab import polyval

from contrib.analysis import BiPlot, NoPPDataException, NoTSDataException


class CrossProductBiPlot(BiPlot):
    '''
    Make customized BiPlots (Parameter Parameter plots) for platforms from STOQS.
    '''

    def getFileName(self, figCount):
        '''
        Construct plot file name
        '''
        fileName = 'cpBiPlot_%02d' % figCount
        if self.args.daytime:
            fileName += '_day'
        if self.args.nighttime:
            fileName += '_night'
        fileName += '.png'

        fileName = os.path.join(self.args.plotDir, self.args.plotPrefix + fileName)

        return fileName

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
        print('Saving file', fileName)
        fig.savefig(fileName)

    def makeCrossProductBiPlots(self):
        '''
        Cycle through Parameters in alphabetical order and make biplots against each of the other parameters
        Parameters can be restricted with --ignore, --sampled, and --r2_greater arguments.
        '''
        allActivityStartTime, allActivityEndTime, allExtent  = self._getActivityExtent(self.args.platform)
        allParmsHash = self._getParametersPlatformHash(ignoreNames=self.args.ignore)
        setList = []
        if self.args.sampled:
            xParmsHash = self._getParametersPlatformHash(groupNames=['Sampled'], ignoreNames=self.args.ignore)
        else:
            xParmsHash = allParmsHash

        axisNum = 1
        figCount = 1
        newFigFlag = True
        xpList = list(xParmsHash.keys())
        xpList.sort(key=lambda p: p.name.lower())
        for xP in xpList:
            xPlats = xParmsHash[xP]
            if self.args.verbose: print(xP.name)
            ypList = list(allParmsHash.keys())
            ypList.sort(key=lambda p: p.name.lower())
            for yP in ypList:
                yPlats = allParmsHash[yP]
                commonPlatforms = xPlats.intersection(yPlats)
                if xP.name == yP.name or set((xP.name, yP.name)) in setList or not commonPlatforms:
                    continue
                if self.args.verbose: print('\t%s' % yP.name)

                try:
                    x, y, points = self._getPPData(None, None, None, xP.name, yP.name, {})
                except (NoPPDataException, TypeError) as e:
                    if self.args.verbose: print(f"\tCan't plot {yP.name}: {str(e)}")
                    continue

                # Assess the correlation
                try:
                    m, b = polyfit(x, y, 1)
                except ValueError as e:
                    if self.args.verbose: print(f"\tCan't polyfit {yP.name}: {str(e)}")
                    continue

                yfit = polyval([m, b], x)
                r = np.corrcoef(x, y)[0,1]
                r2 = r**2
                pr = pearsonr(x, y)

                if r2 < self.args.r2_greater or len(x) < self.args.n_greater:
                    continue

                if newFigFlag:
                    fig = plt.figure(figsize=(9, 9))
                    newFigFlag = False

                # Make subplot
                ax = fig.add_subplot(self.args.nrow, self.args.ncol, axisNum)
                ax.scatter(x, y, marker='.', s=3, c='k')
                ax.plot(x, yfit, color='k', linewidth=0.5)
                if not self.args.ticklabels:
                    ax.set_xticklabels([])
                    ax.set_yticklabels([])
                if self.args.units:
                    ax.set_xlabel('%s (%s)' % (xP.name, xP.units))
                    ax.set_ylabel('%s (%s)' % (yP.name, yP.units))
                else:
                    ax.set_xlabel(xP.name)
                    ax.set_ylabel(yP.name)
                statStr = '$r^2 = %.3f$\n$n = %d$' % (r2, len(x))
                ax.text(0.65, 0.05, statStr, size=8, transform=ax.transAxes, horizontalalignment='left', verticalalignment='bottom')
                platStr = '\n'.join([pl.name for pl in commonPlatforms])
                ax.text(0.05, 0.95, platStr, size=8, transform=ax.transAxes, horizontalalignment='left', verticalalignment='top')

                # Save this pair so that we don't plot it again, even with axes reversed
                setList.append(set((xP.name, yP.name)))

                axisNum += 1
                if axisNum > self.args.nrow * self.args.ncol:
                    self.saveFigure(fig, figCount)
                    newFigFlag = True
                    axisNum = 1
                    figCount += 1

            # End for yP in ypList

        # Save last set of subplots
        self.saveFigure(fig, figCount)

        print('Done.')

    def process_command_line(self):
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n\n' 
        examples += sys.argv[0] + ' -d default\n'
        examples += sys.argv[0] + ' -d stoqs_simz_aug2013 --ignore mass_concentration_of_chlorophyll_in_sea_water --sampled --r2_greater 0.6\n'
        examples += '\nIf running from cde-package replace ".py" with ".py.cde" in the above list.'
    
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
        parser.add_argument('--r2_greater', action='store', help='Plot only correlations with r^2 greater than thisvalue', default=0.0, type=float)
        parser.add_argument('--n_greater', action='store', help='Plot only correlations with n greater than this value', default=1, type=int)
        parser.add_argument('--ignore', action='store', help='Ignore these Parameter names', nargs='*')
        parser.add_argument('--nrow', action='store', help='Number of subplots in a column', default=4, type=int)
        parser.add_argument('--ncol', action='store', help='Number of subplots in a row', default=4, type=int)
        parser.add_argument('--ticklabels', action='store_true', help='Label ticks')
        parser.add_argument('--units', action='store_true', help='Add (units) to axis names')
        parser.add_argument('--plotDir', action='store', help='Directory where to write the plot output', default='.')
        parser.add_argument('--plotPrefix', action='store', help='Prefix to use in naming plot files', default='')
        parser.add_argument('--title', action='store', help='Title to appear on top of plot')
        parser.add_argument('-v', '--verbose', nargs='?', choices=[1,2,3], type=int, help='Turn on verbose output. Higher number = more output.', const=1, default=0)
    
        self.args = parser.parse_args()
        self.commandline = ' '.join(sys.argv)
    
    
if __name__ == '__main__':

    bp = CrossProductBiPlot()
    bp.process_command_line()
    bp.makeCrossProductBiPlots()

