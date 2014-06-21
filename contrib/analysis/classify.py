#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2013, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

Script to execute steps in the classification of measurements including:

1. Labeling specific MeasuredParameters
2. Tagging MeasuredParameters based on a model

Mike McCann
MBARI 16 June 2014

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
from datetime import datetime
from utils.utils import round_to_n, pearsonr
from textwrap import wrap
from numpy import polyfit
from pylab import polyval
from stoqs.models import Activity, ResourceType, Resource, MeasuredParameter, MeasuredParameterResource

from contrib.analysis import BiPlot, NoPPDataException

from sklearn.cross_validation import train_test_split
from sklearn.svm import SVC


class Classifier(BiPlot):
    '''
    To hold methods and data to support classification of measurements in a STOQS database
    '''

    def getActivity(self, mpx, mpy):
        '''
        Return activity object which MeasuredParameters mpx and mpy belong to
        '''
        acts = Activity.objects.using(self.args.database).filter(instantpoint__measurement__measuredparameter__id__in=(mpx,mpy)).distinct()
        if len(acts) != 1:
            raise Exception('Not exactly 1 activity returned for MeasuredParameter IDs = (%s, %s)' % (mpx, mpy))
        else:
            return acts[0]
        
    def hashIDs(self, ids, datavalues):
        '''
        Create lookup for ID given datavalue
        '''
        hash = {}
        for id,dv in zip(ids, datavalues):
            hash[dv] = id

        return hash

    def fitModel(self):
        '''
        Use scikit-learn module to create a model from the training set on the input vector
        '''
        classifier = SVC(gamma=2, C=1)
        sdt = datetime.strptime(self.args.start, '%Y%m%dT%H%M%S')
        edt = datetime.strptime(self.args.end, '%Y%m%dT%H%M%S')

        for label,min,max in zip(self.args.labels, self.args.mins, self.args.maxes):
            pvDict = {self.args.discriminator: (min, max)}

            try:
                X_id, y_id, X, y, points = self._getPPData(sdt, edt, self.args.platform, self.args.inputs[0], self.args.inputs[1], pvDict, returnIDs=True, sampleFlag=False)
            except NoPPDataException, e:
                print e

            # Hash the IDs
            X_id_hash = self.hashIDs(X_id, X)
            y_id_hash = self.hashIDs(y_id, y)

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.4)

            # Save the training set in MeasuredParameterResource
            rt_train, created = ResourceType.objects.using(self.args.database).get_or_create(name='Training Set', description='Used for supervised machine learning')
            r_train, created = Resource.objects.using(self.args.database).get_or_create(name='label', value=label, resourcetype=rt_train)
            for xt,yt in zip(X_train, y_train):
                a = self.getActivity(X_id_hash[xt], y_id_hash[yt])
                mp_x = MeasuredParameter.objects.using(self.args.database).get(pk=X_id_hash[xt])
                mp_y = MeasuredParameter.objects.using(self.args.database).get(pk=y_id_hash[yt])
                mpr_x, created = MeasuredParameterResource.objects.using(self.args.database).get_or_create(
                                    activity=a, measuredparameter=mp_x, resource=r_train)
                mpr_y, created = MeasuredParameterResource.objects.using(self.args.database).get_or_create(
                                    activity=a, measuredparameter=mp_y, resource=r_train)
                


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
        print 'Saving file', fileName
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
        xpList = xParmsHash.keys()
        xpList.sort(key=lambda p: p.name.lower())
        for xP in xpList:
            xPlats = xParmsHash[xP]
            if self.args.verbose: print xP.name
            ypList = allParmsHash.keys()
            ypList.sort(key=lambda p: p.name.lower())
            for yP in ypList:
                yPlats = allParmsHash[yP]
                commonPlatforms = xPlats.intersection(yPlats)
                if xP.name == yP.name or set((xP.name, yP.name)) in setList or not commonPlatforms:
                    continue
                if self.args.verbose: print '\t%s' % yP.name

                try:
                    x, y, points = self._getPPData(None, None, None, xP.name, yP.name)
                except NoPPDataException, e:
                    if self.args.verbose: print e
                    continue

                # Assess the correlation
                m, b = polyfit(x, y, 1)
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

        print 'Done.'

    def process_command_line(self):
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n\n' 
        examples += sys.argv[0] + " -d stoqs_september2013 -p dorado --train --start 20130916T124035 --end 20130919T233905 --inputs bbp700 fl700_uncorr --discriminator salinity --labels diatom dino1 dino2 sediment --mins 33.33 33.65 33.65 33.75 --maxes 33.65 33.70 33.75 33.93\n"
        examples += '\nIf running from cde-package replace ".py" with ".py.cde" in the above list.'
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Read Parameter-Parameter data from a STOQS database and make bi-plots',
                                         epilog=examples)
                                             
        parser.add_argument('-p', '--platform', action='store', help='Platform name')
        parser.add_argument('-d', '--database', action='store', help='Database alias', default='stoqs_september2013_o', required=True)
        parser.add_argument('--daytime', action='store_true', help='Select only daytime hours: 10 am to 2 pm local time')
        parser.add_argument('--nighttime', action='store_true', help='Select only nighttime hours: 10 pm to 2 am local time')
        parser.add_argument('--minDepth', action='store', help='Minimum depth for data queries', default=None, type=float)
        parser.add_argument('--maxDepth', action='store', help='Maximum depth for data queries', default=None, type=float)

        parser.add_argument('--train', action='store_true', help='Train the model with the --discriminator, --labels, --mins, and --maxes options')
        parser.add_argument('--inputs', action='store', help='List of Parameters for sample and feature separated by spaces', nargs='*')
        parser.add_argument('--start', action='store', help='Start time in YYYYMMDDTHHMMSS format')
        parser.add_argument('--end', action='store', help='End time in YYYYMMDDTHHMMSS format')
        parser.add_argument('--discriminator', action='store', help='Parameter name to use to discriminate the data')
        parser.add_argument('--labels', action='store', help='List of labels to create separated by spaces', nargs='*')
        parser.add_argument('--mins', action='store', help='List of labels to create separated by spaces', nargs='*')
        parser.add_argument('--maxes', action='store', help='List of labels to create separated by spaces', nargs='*')

        parser.add_argument('-v', '--verbose', action='store_true', help='Turn on verbose output')
    
        self.args = parser.parse_args()
        self.commandline = ' '.join(sys.argv)
    
    
if __name__ == '__main__':

    c = Classifier()
    c.process_command_line()
    if c.args.train:
        c.fitModel()

