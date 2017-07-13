#!/usr/bin/env python

"""
Complement to the classify.py script.

Script to implement unsupervised machine learning on data.
Involves clustering data using unsupervised machine learning.

Rachel Kahn
MBARI July 2017
"""

import os
import sys

# Insert Django App directory (parent of config) into python path
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../../")))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
# django >=1.7
try:
    import django

    django.setup()
except AttributeError:
    pass

import matplotlib as mpl

mpl.use('Agg')  # Force matplotlib to not use any Xwindows backend
import matplotlib.pyplot as plt
import numpy as np
import warnings
from datetime import datetime
from datetime import timedelta
from django.db.models import Q
from django.db.utils import IntegrityError
from textwrap import wrap
from stoqs.models import Activity, ResourceType, Resource, Measurement, MeasuredParameter, MeasuredParameterResource, \
    ResourceResource
from utils.STOQSQManager import LABEL, DESCRIPTION, COMMANDLINE

from contrib.analysis import BiPlot, NoPPDataException

from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
#from sklearn.cluster import KMeans
#from sklearn.cluster import AffinityPropagation
#from sklearn.cluster import SpectralClustering
#from sklearn.cluster import AgglomerativeClustering
from sklearn.cluster import DBSCAN
#from sklearn.cluster import Birch
#from sklearn.cluster import MeanShift
from sklearn.mixture import GaussianMixture
import pickle

LABELED = 'Labeled'
TRAIN = 'Train'
TEST = 'Test'


class Clusterer(BiPlot):
    '''
    To hold methods and data to support clustering of measurements in a STOQS database.
    See http://scikit-learn.org/stable/modules/clustering.html#overview-of-clustering-methods
    '''
    #clusterers = {'Hierarchical_Clustering': AgglomerativeClustering(),
    #              'DBSCAN': DBSCAN(),
    #              'Mean_Shift': MeanShift(),
    #              'Birch': Birch()
    #              }




    def doModelsScore(self, labeledGroupName):
        '''
        Print scores for several different clusterers
        '''
        X, y = self.loadData()

        if X.any() and y.any():
            for name, clf in list(self.clusterers.items()):
                scores = cross_val_score(clf, X, y, cv=5)
                print("%-18s accuracy: %0.2f (+/- %0.2f)" % (name, scores.mean(), scores.std() * 2))
        else:
            raise Exception('No data returned for labeledGroupName = %s' % labeledGroupName)


    def loadData(self): # pragma: no cover
        '''
        Retrieve data from the database and return the x, and y values (in list form) that the scikit-learn package uses
        '''
        sdt = datetime.strptime(self.args.start, '%Y%m%dT%H%M%S')
        edt = datetime.strptime(self.args.end, '%Y%m%dT%H%M%S')

        pvDict = {}
        try:
            x, y, _ = self._getPPData(sdt, edt, self.args.platform, self.args.inputs[0],
                                                    self.args.inputs[1], pvDict, returnIDs=False, sampleFlag=False)


        except NoPPDataException as e:
            print(str(e))

        return x, y



    def createClusters(self):  # pragma: no cover
        '''
        Query the database for data , convert to the standard X and y arrays for
        sci-kit learn, and identify clusters in the data.
        '''

        #clf = self.clusterers[self.args.clusterer]
        clf = DBSCAN()

        x, y = self.loadData()
        x = np.array(x)
        y = np.array(y)
        X = np.column_stack((x,y))

        clf.fit(X)

        #score = clf.score(X)
        #if self.args.verbose:
        #    print("  score = %f" % score)

        y_clusters = clf.labels_

        return X, y_clusters


    def process_command_line(self):
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Example machine learning workflow:' + '\n\n'
        examples += "Identify clusters in data:\n"
        examples += sys.argv[0] + (" --createClusters --database stoqs_september2013"
                                   " --platform Slocum_260 --start 20130923T124038 --end 20130923T150613"
                                   " --inputs optical_backscatter700nm fluorescence -v\n\n")
        examples += '\nIf running from cde-package replace ".py" with ".py.cde" in the above list.'

        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Script to execute steps in the classification of measurements',
                                         epilog=examples)

        parser.add_argument('-p', '--platform', action='store', help='STOQS Platform name for training data access')
        parser.add_argument('-d', '--database', action='store', help='Database alias', default='stoqs_september2013_o',
                            required=True)
        ##parser.add_argument('--minDepth', action='store', help='Minimum depth for data queries', default=None, type=float)
        ##parser.add_argument('--maxDepth', action='store', help='Maximum depth for data queries', default=None, type=float)


        parser.add_argument('--createClusters', action='store_true',
                            help='Fit a model to data clusters')
        parser.add_argument('--doModelsScore', action='store_true',
                            help='Print scores for fits of various models')
        parser.add_argument('--inputs', action='store',
                            help='List of STOQS Parameter names to use as features, separated by spaces', nargs='*')
        parser.add_argument('--start', action='store', help='Start time in YYYYMMDDTHHMMSS format',
                            default='19000101T000000')
        parser.add_argument('--end', action='store', help='End time in YYYYMMDDTHHMMSS format',
                            default='22000101T000000')
        parser.add_argument('--test_size', action='store',
                            help='Proportion of discriminated sample to save as Test set', default=0.4, type=float)
        parser.add_argument('--train_size', action='store',
                            help='Proportion of discriminated sample to save as Train set', default=0.4, type=float)
        #parser.add_argument('--interval', action='store', help='Time interval for which clusterSeq() flips through the'
                                                               #'data, in format "days=x,seconds=x,minutes=x,hours=x,'
                                                               #'weeks=x" ',
                            #default='days=0, seconds=0, minutes=0, hours=0, weeks=0') # default 10 minutes
        #parser.add_argument('--clusterer', choices=list(self.clusterers.keys()),
        #                    help='Specify classifier to use with --createClassifier option')
        #parser.add_argument('--n_clusters', action='store',
        #                    help='Number of clusters desired', default=2)

        parser.add_argument('-v', '--verbose', nargs='?', choices=[1, 2, 3], type=int,
                            help='Turn on verbose output. Higher number = more output.', const=1, default=0)

        self.args = parser.parse_args()
        self.commandline = ' '.join(sys.argv)

        # Conditional tests
        if self.args.doModelsScore:
            if not c.args.classes:
                parser.error('--doModelsScore requires --classes')
            if not c.args.inputs:
                parser.error('--doModelsScore requires --inputs')


if __name__ == '__main__':

    c = Clusterer()
    c.process_command_line()

    if c.args.platform and c.args.inputs:
        c.loadData()

    elif c.args.doModelsScore:
        c.doModelsScore(' '.join((LABELED, c.args.groupName)))

    elif c.args.createClusters:
        c.createClusters(' '.join((LABELED, c.args.groupName)))

    else:
        print("fix your inputs")

