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
from django.db.models import Q
from utils.utils import round_to_n, pearsonr
from textwrap import wrap
from numpy import polyfit
from pylab import polyval
from stoqs.models import Activity, ResourceType, Resource, Measurement, MeasuredParameter, MeasuredParameterResource
from utils.STOQSQManager import LABEL

from contrib.analysis import BiPlot, NoPPDataException

from sklearn.preprocessing import StandardScaler
from sklearn.cross_validation import train_test_split
from sklearn.svm import SVC
import pickle

LABELED = 'Labeled'
TRAIN = 'Train'
TEST = 'Test'

class Classifier(BiPlot):
    '''
    To hold methods and data to support classification of measurements in a STOQS database.
    See http://scikit-learn.org/stable/auto_examples/plot_classifier_comparison.html
    '''
    def getActivity(self, mpx, mpy):
        '''
        Return activity object which MeasuredParameters mpx and mpy belong to
        '''
        meas = Measurement.objects.using(self.args.database).filter(measuredparameter__id__in=(mpx,mpy)).distinct()
        acts = Activity.objects.using(self.args.database).filter(instantpoint__measurement__measuredparameter__id__in=(mpx,mpy)).distinct()
        if len(acts) != 1:
            raise Exception('Not exactly 1 activity returned with SQL = \n%s' % str(acts.query))
        else:
            return acts[0]
        
    def saveLabelSet(self, label, x_ids, y_ids, typeName, typeDescription):
        '''
        Save the set of labels in MeasuredParameterResource. Accepts 2 input vectors. (TODO: generalize to N input vectors)
        '''
        try:
            rt, created = ResourceType.objects.using(self.args.database).get_or_create(name=typeName, description=typeDescription)
            r, created = Resource.objects.using(self.args.database).get_or_create(name=LABEL, value=label, resourcetype=rt)
        except IntegrityError as e:
            print e
            print "Ignoring"

        if self.args.verbose:
            print "  Saving %d values of '%s' with type '%s'" % (len(x_ids), label, typeName)
        for x_id,y_id in zip(x_ids, y_ids):
            a = self.getActivity(x_id, y_id)
            mp_x = MeasuredParameter.objects.using(self.args.database).get(pk=x_id)
            mp_y = MeasuredParameter.objects.using(self.args.database).get(pk=y_id)
            mpr_x, created = MeasuredParameterResource.objects.using(self.args.database).get_or_create(
                                activity=a, measuredparameter=mp_x, resource=r)
            mpr_y, created = MeasuredParameterResource.objects.using(self.args.database).get_or_create(
                                activity=a, measuredparameter=mp_y, resource=r)

    def removeLabelSet(self, label, type):
        '''
        Deep MeasuredParameterResources that have Resource.name=label (such as 'label') and ResourceType.name=type (such as 'Train')
        '''
        mprs = MeasuredParameterResource.objects.using(self.args.database).filter(
                                    resource__name=LABEL, resource__value=label, resource__resourcetype__name=type)
        if self.args.verbose > 1:
            print "  Removing MeasuredParameterResources with label = '%s' and type = '%s'" % (label, type)
        for mpr in mprs:
            mpr.delete(using=self.args.database)

    def partOfClass(self, x_all, y_all, x_class, y_class):
        '''
        Return array of 0 or 1 with 1 representing indices where x_class, y_class is in x_all, y_all
        '''
        y = []
        count = 0
        for xa, ya in zip(x_all, y_all):
            if xa in x_class and ya in y_class:
                y.append(1)
                count += 1
            else:
                y.append(0)

        if self.args.verbose > 1:
            print "  %d values in class" % count

        return y

    def doLabel(self):
        '''
        Using discriminator, mins, and maxes label MeasuredParameters in the database so that we can do supervised learning
        '''
        sdt = datetime.strptime(self.args.start, '%Y%m%dT%H%M%S')
        edt = datetime.strptime(self.args.end, '%Y%m%dT%H%M%S')

        for label, min, max in zip(self.args.labels, self.args.mins, self.args.maxes):
            # Multiple discriminators are possible...
            pvDict = {self.args.discriminator: (min, max)}
            if self.args.verbose:
                print "Making label '%s' with discriminator %s" % (label, pvDict)

            try:
                x_ids, y_ids, xx, yy, points = self._getPPData(sdt, edt, self.args.platform, self.args.inputs[0], 
                                                               self.args.inputs[1], pvDict, returnIDs=True, sampleFlag=False)
            except NoPPDataException, e:
                print e

            if self.args.verbose:
                print "  (%d, %d) MeasuredParameters returned from database %s" % (len(x_ids), len(y_ids), self.args.database)

            if self.args.clobber:
                self.removeLabelSet(label, LABELED)
            self.saveLabelSet(label, x_ids, y_ids, LABELED, 'Labeled with %s as discriminator' % self.args.discriminator)

    def doTrainTest(self):
        '''
        Query the database for labeled training data, fit a model to it, and save the pickled model back to the database
        '''
        clf = SVC(gamma=2, C=1)

        f0 = np.array(0)
        f1 = np.array(0)
        y = np.array(0, dtype=int)
        target = 0
        for label in self.args.labels:
            mprs = MeasuredParameterResource.objects.using(self.args.database).filter(resource__name=LABEL, 
                                                resource__resourcetype__name=LABELED, resource__value=label
                                                ).values_list('measuredparameter__datavalue', flat=True)
            count = mprs.filter(measuredparameter__parameter__name=self.args.inputs[0]).count()
            f0 = np.append(f0, mprs.filter(measuredparameter__parameter__name=self.args.inputs[0]))
            f1 = np.append(f1, mprs.filter(measuredparameter__parameter__name=self.args.inputs[1]))
            y = np.append(y, np.ones(count) * target)
            target += 1

        import pdb
        X = np.concatenate((f0.reshape(-1,1), f1.reshape(-1,1)), axis=1)
        pdb.set_trace()
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=self.args.test_size, train_size=self.args.train_size)


        X_train = StandardScaler().fit_transform(X_train)

        import pdb
        clf.fit(X_train, y_train)
        pdb.set_trace()
        score = clf.score(X_test, y_test)
        if self.args.verbose:
            print "  score = %f" % score

        s = pickle.dumps(clf)


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
        if self.args.verbose:
            print '  Saving file', fileName
        fig.savefig(fileName)

    def process_command_line(self):
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n\n' 
        examples += "Step 1: Save Labeled features in the database using salinity as a discriminator:\n"
        examples += sys.argv[0] + " -d stoqs_september2013_t --doLabel -p dorado --start 20130916T124035 --end 20130919T233905 --inputs bbp700 fl700_uncorr --discriminator salinity --labels diatom dino1 dino2 sediment --mins 33.33 33.65 33.70 33.75 --maxes 33.65 33.70 33.75 33.93 --clobber -v\n\n"
        examples += "Step 2: Create a prediction model using the labels created in Step 1\n"
        examples += sys.argv[0] + " -d stoqs_september2013_t --doTrainTest --classifier SVC --labels diatom dino1 dino2 sediment --inputs bbp700 fl700_uncorr --discriminator salinity --modelBaseName SVC_20140625T180100\n\n"
        examples += "Step 3: Use a model to classify new measurements\n"
        examples += '\nIf running from cde-package replace ".py" with ".py.cde" in the above list.'
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Read Parameter-Parameter data from a STOQS database and make bi-plots',
                                         epilog=examples)
                                             
        parser.add_argument('-p', '--platform', action='store', help='STOQS Platform name for training data access')
        parser.add_argument('-d', '--database', action='store', help='Database alias', default='stoqs_september2013_o', required=True)
        ##parser.add_argument('--minDepth', action='store', help='Minimum depth for data queries', default=None, type=float)
        ##parser.add_argument('--maxDepth', action='store', help='Maximum depth for data queries', default=None, type=float)

        parser.add_argument('--doLabel', action='store_true', help='Label data with --discriminator, --labels, --mins, and --maxes options')
        parser.add_argument('--doTrainTest', action='store_true', help='Fit a model to Labeled data with --classifier to labels in --labels and save in database as --modelName')
        parser.add_argument('--inputs', action='store', help='List of STOQS Parameter names to use as features, separated by spaces', nargs='*')
        parser.add_argument('--start', action='store', help='Start time in YYYYMMDDTHHMMSS format')
        parser.add_argument('--end', action='store', help='End time in YYYYMMDDTHHMMSS format')
        parser.add_argument('--discriminator', action='store', help='Parameter name to use to discriminate the data')
        parser.add_argument('--labels', action='store', help='List of labels to create separated by spaces', nargs='*')
        parser.add_argument('--mins', action='store', help='List of labels to create separated by spaces', nargs='*')
        parser.add_argument('--maxes', action='store', help='List of labels to create separated by spaces', nargs='*')
        parser.add_argument('--test_size', action='store', help='Proportion of discriminated sample to save as Test set', default=0.4, type=float)
        parser.add_argument('--train_size', action='store', help='Proportion of discriminated sample to save as Train set', default=0.4, type=float)
        parser.add_argument('--classifier', choices=['SVC'], help='Specify classifier to use with --fit option')
        parser.add_argument('--modelBaseName', action='store', help='Base name of the model to store in the database')

        parser.add_argument('--clobber', action='store_true', help='Remove existing MeasuredParameterResource records before adding new classification')
        parser.add_argument('-v', '--verbose', nargs='?', choices=[1,2,3], type=int, help='Turn on verbose output. Higher number = more output.', const=1)
    
        self.args = parser.parse_args()
        self.commandline = ' '.join(sys.argv)
    
    
if __name__ == '__main__':

    c = Classifier()
    c.process_command_line()
    if c.args.doLabel:
        c.doLabel()
    elif c.args.doTrainTest:
        c.doTrainTest()

