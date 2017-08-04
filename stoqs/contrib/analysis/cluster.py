#!/usr/bin/env python

"""
Complement to the classify.py script.

Script to implement unsupervised machine learning on data using clustering algorithms.

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
#from sklearn.cluster import KMeans
#from sklearn.cluster import AffinityPropagationscore
#from sklearn.cluster import SpectralClustering
from sklearn.cluster import AgglomerativeClustering
from sklearn.cluster import DBSCAN
from sklearn.cluster import Birch
from sklearn.cluster import MeanShift
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
    algorithms = {'Hierarchical_Clustering': AgglomerativeClustering(),
                  'DBSCAN': DBSCAN(),
                  'Mean_Shift': MeanShift(),
                  'Birch': Birch()
                  }

    def getActivity(self, mpx, mpy):
        '''
        Return activity object which MeasuredParameters mpx and mpy belong to
        '''
        acts = Activity.objects.using(self.args.database).filter(
            instantpoint__measurement__measuredparameter__id__in=(mpx, mpy)).distinct()
        if not acts:
            print("acts = %s" % acts)
            raise Exception('Not exactly 1 activity returned with SQL = \n%s' % str(acts.query))
        else:
            return acts[0]

    def saveCommand(self):
        '''
        Save the command executed to a Resource and return it for the doXxxx() method to associate it with the resources it creates
        '''
        rt, _ = ResourceType.objects.using(self.args.database).get_or_create(name=LABEL, description='metadata')
        r, _ = Resource.objects.using(self.args.database).get_or_create(name=COMMANDLINE, value=self.commandline,
                                                                        resourcetype=rt)

        return r

    def saveClusters(self, labeledGroupName):
        '''
        Save the set of labels in MeasuredParameterResource. Accepts 2 input vectors. (TODO: generalize to N input vectors);
        description is used to describe the criteria for assigning this label. The labeledGroupName may be used to
        refer to the grouping, and the clusters are each labeled with a letter from A-Z.
        '''
        X, y_clusters, X_ids = c.createClusters()
        clResource = c.saveCommand()

        # assign each cluster a letter
        for i in range(-1, max(y_clusters) + 1):
            letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            if i == -1:
                label = 'OUTLIER'
            else:
                label = letters[i]

            cluster = X[y_clusters == i]
            cluster_ids = X_ids[y_clusters == i]

            try:
                # Label
                rt, _ = ResourceType.objects.using(self.args.database).get_or_create(name=labeledGroupName,
                                                                                description='unsupervised classification')
                r, _ = Resource.objects.using(self.args.database).get_or_create(name=LABEL, value=label, resourcetype=rt)

                ResourceResource.objects.using(self.args.database).get_or_create(fromresource=r, toresource=clResource)

            except IntegrityError as e:
                print(str(e))
                print("Ignoring")

            # Associate MeasuredParameters with Resource
            if self.args.verbose:
                print("  Saving %d values in cluster '%s'" % (len(cluster), label))
            for x_id, y_id in cluster_ids:

                a = self.getActivity(x_id, y_id)
                mp_x = MeasuredParameter.objects.using(self.args.database).get(id=x_id)
                mp_y = MeasuredParameter.objects.using(self.args.database).get(id=y_id)
                MeasuredParameterResource.objects.using(self.args.database).get_or_create(
                    activity=a, measuredparameter=mp_x, resource=r)
                MeasuredParameterResource.objects.using(self.args.database).get_or_create(
                    activity=a, measuredparameter=mp_y, resource=r)

    def saveClustersSeq(self, labeledGroupName):
        '''
        Save the set of labels in MeasuredParameterResource for each step as the method flips through the data in a specified
        time interval. Accepts 2 input vectors. (TODO: generalize to N input vectors). The labeledGroupName may be used to refer to the grouping,
        and is given a number (appended to the labeledGroupName for each time interval step. Within each grouping, each cluster is labeled with a
        letter from A-Z.
        '''
        clResource = c.saveCommand()
        clf = self.algorithms[self.args.algorithm]

        kwargs = {}
        kwargs[self.args.interval.split('=')[0]] = int(self.args.interval.split('=')[1])
        interval = timedelta(**kwargs)
        start = datetime.strptime(self.args.start, '%Y%m%dT%H%M%S')
        end = datetime.strptime(self.args.end, '%Y%m%dT%H%M%S')

        sdt = start
        edt = start + interval
        stepnumber = 0

        while edt <= end:
            try:
                x, y, x_ids, y_ids = self.loadData(sdt, edt)
            except NoPPDataException as e:
                print('Just so you know: '+str(e))
                sdt = sdt + interval
                edt = edt + interval
                continue

            x = np.array(x)
            y = np.array(y)
            X = np.column_stack((x,y))

            x_ids = np.array(x_ids)
            y_ids=np.array(y_ids)
            X_ids = np.column_stack((x_ids,y_ids))

            clf.fit(X)

            y_clusters = clf.labels_

            # assign each cluster a letter
            for i in range(-1, max(y_clusters) + 1):
                letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                if i == -1:
                    label = 'OUTLIER'
                else:
                    label = letters[i]

                cluster = X[y_clusters == i]
                cluster_ids = X_ids[y_clusters == i]

                try:
                    # Label
                    rt, _ = ResourceType.objects.using(self.args.database).get_or_create(name=(labeledGroupName + '_' + str(stepnumber)),
                                                                                    description='unsupervised classification')
                    r, _ = Resource.objects.using(self.args.database).get_or_create(name=LABEL, value=label, resourcetype=rt)

                    ResourceResource.objects.using(self.args.database).get_or_create(fromresource=r, toresource=clResource)

                except IntegrityError as e:
                    print(str(e))
                    print("Ignoring")

                # Associate MeasuredParameters with Resource
                if self.args.verbose:
                    print("  Saving %d values in cluster '%s'" % (len(cluster), label))
                for x_id, y_id in cluster_ids:

                    a = self.getActivity(x_id, y_id)
                    mp_x = MeasuredParameter.objects.using(self.args.database).get(id=x_id)
                    mp_y = MeasuredParameter.objects.using(self.args.database).get(id=y_id)
                    MeasuredParameterResource.objects.using(self.args.database).get_or_create(
                        activity=a, measuredparameter=mp_x, resource=r)
                    MeasuredParameterResource.objects.using(self.args.database).get_or_create(
                        activity=a, measuredparameter=mp_y, resource=r)

            sdt = sdt + interval
            edt = edt + interval
            stepnumber = stepnumber + 1

    def removeLabels(self, labeledGroupName):  # pragma: no cover
        '''
        Delete labeled MeasuredParameterResources that have ResourceType.name=labeledGroupName (such as 'Cluster label').
        Note: Some metadatda ResourceTypes will not be removed even though the Resources that use them will be removed.
        '''
        mprs = MeasuredParameterResource.objects.using(self.args.database).filter(
            resource__resourcetype__name=labeledGroupName
            ).select_related('resource')

        if self.args.verbose > 1:
            print("  Removing MeasuredParameterResources with labelGroupName = %s" % (labeledGroupName))

        rs = []
        for mpr in mprs:
            rs.append(mpr.resource)
            mpr.delete(using=self.args.database)

        for r in set(rs):
            r.delete(using=self.args.database)

    def removeLabelsSeq(self, labeledGroupName):  # pragma: no cover
        '''
        Delete sequentially labeled MeasuredParameterResources created by the saveClustersSeq method that have ResourceType.name=labeledGroupName.
        Note: Some metadatda ResourceTypes will not be removed even though the Resources that use them will be removed.
        '''
        stepnumber = 0
        steps = ResourceType.objects.using(self.args.database).filter(resource__resourcetype__name__contains=labeledGroupName).count()

        for step in range(steps + 1):

            try:
                mprs = MeasuredParameterResource.objects.using(self.args.database).filter(
                    resource__resourcetype__name=(labeledGroupName + '_' + str(stepnumber))
                    ).select_related('resource')

                rt = ResourceType.objects.using(self.args.database).get(name=(labeledGroupName + '_' + str(stepnumber)))

                if self.args.verbose > 1:
                    print(("  Removing MeasuredParameterResources with labelGroupName = %s" + '_' + str(stepnumber)) % (labeledGroupName))

                rs = []
                for mpr in mprs:
                    rs.append(mpr.resource)
                    mpr.delete(using=self.args.database)

                for r in set(rs):
                    r.delete(using=self.args.database)

                rt.delete(using=self.args.database)

                stepnumber = stepnumber + 1

            except:
                stepnumber = stepnumber + 1

    def loadData(self, sdt, edt): # pragma: no cover
        '''
        Retrieve data from the database and return the x, and y values and IDs (in list form) that the scikit-learn package uses.
        May raise NoPPDataException.
        '''
        pvDict = {}
        x_ids, y_ids, x, y, _ = self._getPPData(sdt, edt, self.args.platform, self.args.inputs[0],
                                                self.args.inputs[1], pvDict, returnIDs=True, sampleFlag=False)

        return x, y, x_ids, y_ids

    def createClusters(self, sdt=None, edt=None):  # pragma: no cover
        '''
        Query the database for data , convert to the standard X and y arrays for
        sci-kit learn, and identify clusters in the data.
        '''
        if not sdt and not edt:
            sdt = datetime.strptime(self.args.start, '%Y%m%dT%H%M%S')
            edt = datetime.strptime(self.args.end, '%Y%m%dT%H%M%S')

        clf = self.algorithms[self.args.algorithm]

        try:
            x, y, x_ids, y_ids = self.loadData(sdt, edt)
        except NoPPDataException as e:
            print(str(e))

        x = np.array(x)
        y = np.array(y)
        X = np.column_stack((x,y))

        x_ids = np.array(x_ids)
        y_ids = np.array(y_ids)
        X_ids = np.column_stack((x_ids, y_ids))

        clf.fit(X)

        y_clusters = clf.labels_

        if max(y_clusters) >= 26:
            print("Too many clusters, there probably aren't any significant patterns here.")
        else:
            return X, y_clusters, X_ids

    def clusterSeq(self):
        '''
        Flip through the data at a specified time interval and identify clusters.
        '''
        clf = self.algorithms[self.args.algorithm]

        kwargs = {}
        kwargs[self.args.interval.split('=')[0]] = int(self.args.interval.split('=')[1])
        interval = timedelta(**kwargs)
        start = datetime.strptime(self.args.start, '%Y%m%dT%H%M%S')
        end = datetime.strptime(self.args.end, '%Y%m%dT%H%M%S')

        sdt = start
        edt = start + interval

        while edt <= end:
            try:
                x, y, x_ids, y_ids = self.loadData(sdt, edt)
            except NoPPDataException as e:
                print('Just so you know: '+str(e))
                sdt = sdt + interval
                edt = edt + interval
                continue

            x = np.array(x)
            y = np.array(y)
            X = np.column_stack((x,y))

            x_ids = np.array(x_ids)
            y_ids=np.array(y_ids)
            X_ids = np.column_stack((x_ids,y_ids))

            clf.fit(X)

            y_clusters = clf.labels_

            sdt = sdt + interval
            edt = edt + interval

        return X, y_clusters, X_ids

    def process_command_line(self):
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Example machine learning workflow:' + '\n\n'
        examples += "Identify clusters in data and save to the database:\n"
        examples += sys.argv[0] + (" --saveClusters --database stoqs_september2013"
                                   " --platform Slocum_260 --start 20130923T124038 --end 20130923T150613"
                                   " --inputs optical_backscatter700nm fluorescence --algorithm DBSCAN "
                                   "--labeledGroupName DBSCANclusters -v\n\n")
        examples += "Remove labels from the database\n"
        examples += sys.argv[0] + (" --removeLabels --database stoqs_september2013"
                                   " --platform Slocum_260 --start 20130923T124038 --end 20130923T150613"
                                   " --inputs optical_backscatter700nm fluorescence "
                                   "--labeledGroupName DBSCANclusters -v\n\n")
        examples += '''Typical workflow:
0. Test creating a cluster with --createClusters; does not update database with cluster names (Attributes)
0. Test stepping through database with --clusterSeq; does not update database with cluster names (Attributes)
1. Use --saveClusters to update database with clusters for single specified time period
2. Use --saveClustersSeq to step through time updating the database with cluster names (Attributes)
'''

        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Script to execute steps in the classification of measurements',
                                         epilog=examples)

        parser.add_argument('-p', '--platform', action='store', help='STOQS Platform name for training data access')
        parser.add_argument('-d', '--database', action='store', help='Database alias', default='stoqs_september2013_o',
                            required=True)
        parser.add_argument('--createClusters', action='store_true', help='Identify clusters in data')
        parser.add_argument('--clusterSeq', action='store_true', help='Flip through data at specified interval and identify data clusters')
        parser.add_argument('--saveClusters', action='store_true', help='Identify clusters in data and save labels to database with --labeledGroupName option')
        parser.add_argument('--saveClustersSeq', action='store_true', help='Flip through data at specified interval, identify data clusters,'
                                                                          'and save labels to database with --labeledGroupName option')
        parser.add_argument('--removeLabels', action='store_true', help='Remove Labels created by --createClusters with --groupName option')
        parser.add_argument('--removeLabelsSeq', action='store_true', help='Remove Labels created by --createClustersSeq with --groupName option')
        parser.add_argument('--inputs', action='store',
                            help='List of STOQS Parameter names to use as features, separated by spaces', nargs='*')
        parser.add_argument('--start', action='store', help='Start time in YYYYMMDDTHHMMSS format',
                            default='19000101T000000')
        parser.add_argument('--end', action='store', help='End time in YYYYMMDDTHHMMSS format',
                            default='22000101T000000')
        parser.add_argument('--interval', action='store', help='Time interval for which clusterSeq() flips through the'
                                                               'data, in format "days=x, seconds=x, minutes=x, hours=x,'
                                                               ' weeks=x" ', default='days=0, seconds=0, minutes=10, '
                                                               'hours=0, weeks=0') # default 10 minutes
        parser.add_argument('--algorithm', choices=list(self.algorithms.keys()),
                            help='Specify clustering algorithm to use with --createClusters, --clusterSeq, --saveClusters, '
                                                                'or --saveClusterSeq option')
        parser.add_argument('--labeledGroupName', action='store', help='Name used to refer to the grouping, such as '
                                                                '"Cluster label" or "DBSCAN labels"')
        parser.add_argument('-v', '--verbose', nargs='?', choices=[1, 2, 3], type=int,
                            help='Turn on verbose output. Higher number = more output.', const=1, default=0)

        self.args = parser.parse_args()
        self.commandline = ' '.join(sys.argv)


if __name__ == '__main__':

    c = Clusterer()
    c.process_command_line()

    if c.args.createClusters:
        c.createClusters()

    elif c.args.clusterSeq:
        c.clusterSeq()

    elif c.args.saveClusters:
        c.saveClusters(' '.join((LABELED, c.args.labeledGroupName)))

    elif c.args.saveClustersSeq:
        c.saveClustersSeq(' '.join((LABELED, c.args.labeledGroupName)))

    elif c.args.removeLabels:
        c.removeLabels(' '.join((LABELED, c.args.labeledGroupName)))

    elif c.args.removeLabelsSeq:
        c.removeLabelsSeq(' '.join((LABELED, c.args.labeledGroupName)))

    else:
        print("fix your inputs")
