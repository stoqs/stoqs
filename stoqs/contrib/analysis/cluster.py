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
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
# django >=1.7
try:
    import django

    django.setup()
except AttributeError:
    pass

import matplotlib as mpl

mpl.use('Agg')  # Force matplotlib to not use any Xwindows backend
import argparse
import matplotlib.pyplot as plt
import numpy as np
import warnings
from datetime import datetime
from datetime import timedelta
from django.db.models import Q
from django.db.utils import IntegrityError
from django.db import transaction
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

CLUSTERED = 'Clustered'


class DefaultsRawTextHelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawTextHelpFormatter):
    pass

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

    def saveClusters(self, clusteredGroupName):
        '''
        Save the set of labels in MeasuredParameterResource. Accepts 2 input vectors. (TODO: generalize to N input vectors);
        description is used to describe the criteria for assigning this label. The clusteredGroupName may be used to
        refer to the grouping, and the clusters are each clustered with a letter from A-Z.
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
                rt, _ = ResourceType.objects.using(self.args.database).get_or_create(name=clusteredGroupName,
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
                act = self.getActivity(x_id, y_id)
                if self.args.verbose > 1:
                    print(f'  Activity: {act}')

                mp_x = MeasuredParameter.objects.using(self.args.database).get(id=x_id)
                mp_y = MeasuredParameter.objects.using(self.args.database).get(id=y_id)
                MeasuredParameterResource.objects.using(self.args.database).get_or_create(
                    activity=act, measuredparameter=mp_x, resource=r)
                MeasuredParameterResource.objects.using(self.args.database).get_or_create(
                    activity=act, measuredparameter=mp_y, resource=r)

    def _parseTimeDelta(self, arg):
        # Help documentation implies that multiple comma-separated time intervals may be in 'arg'
        # but only one is parsed.
        kwargs = {}
        kwargs[arg.split('=')[0]] = int(arg.split('=')[1])

        return timedelta(**kwargs)

    def _saveMPRassociations(self, cluster_ids, label, r_cluster):

        if self.args.verbose:
            print("  Saving %d values in cluster '%s'" % (len(cluster_ids), label))

        try:
            # See https://docs.djangoproject.com/en/dev/topics/db/transactions/#django.db.transaction.atomic
            with transaction.atomic():
                for x_id, y_id in cluster_ids:
                    act = self.getActivity(x_id, y_id)

                    mp_x = MeasuredParameter.objects.using(self.args.database).get(id=x_id)
                    mp_y = MeasuredParameter.objects.using(self.args.database).get(id=y_id)

                    mprx = MeasuredParameterResource(activity=act, measuredparameter=mp_x, resource=r_cluster)
                    mpry = MeasuredParameterResource(activity=act, measuredparameter=mp_y, resource=r_cluster)

                    mprx.save(self.args.database)
                    mpry.save(self.args.database)

        except IntegrityError as e:
            # Likely duplicate key value violates unique constraint...
            if self.args.verbose > 2:
                print(str(e))

    def saveClustersSeq(self, clusteredGroupName):
        '''
        Save the set of labels in MeasuredParameterResource for each step as the method steps through the data in a specified
        time interval. Accepts 2 input vectors. (TODO: generalize to N input vectors). The clusteredGroupName may be used to refer to the grouping,
        and is given a number (appended to the clusteredGroupName for each time interval step. Within each grouping, each cluster is named with a
        letter from A-Z.
        '''
        clResource = c.saveCommand()
        clf = self.algorithms[self.args.algorithm]

        start = datetime.strptime(self.args.start, '%Y%m%dT%H%M%S')
        end = datetime.strptime(self.args.end, '%Y%m%dT%H%M%S')

        interval = self._parseTimeDelta(self.args.interval)
        step = self._parseTimeDelta(self.args.step)

        sdt = start
        edt = start + interval

        while edt <= end:
            if self.args.verbose > 0:
                print(sdt)
            try:
                x, y, x_ids, y_ids = self.loadData(sdt, edt)
            except NoPPDataException as e:
                print('Just so you know: '+str(e))
                sdt = sdt + step
                edt = edt + step
                continue

            x = np.array(x)
            y = np.array(y)
            X = np.column_stack((x,y))

            x_ids = np.array(x_ids)
            y_ids = np.array(y_ids)
            X_ids = np.column_stack((x_ids,y_ids))

            try:
                clf.fit(X)
            except ValueError as e:
                # Likely no clusters returned: Expected n_neighbors > 0. Got 0
                if self.args.verbose > 0:
                    print(str(e))
                sdt = sdt + step
                edt = edt + step
                continue

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
                    rt, _ = ResourceType.objects.using(self.args.database).get_or_create(
                                name=clusteredGroupName, description='unsupervised classification')
                    r_cluster, _ = Resource.objects.using(self.args.database).get_or_create(name=LABEL, value=label, resourcetype=rt)
                    # Associate with commandlineResource
                    ResourceResource.objects.using(self.args.database).get_or_create(fromresource=r_cluster, toresource=clResource)

                except IntegrityError as e:
                    print(str(e))
                    print("Ignoring")

                # Associate MeasuredParameters with Resource
                self._saveMPRassociations(cluster_ids, label, r_cluster)

            sdt = sdt + step
            edt = edt + step

    def describeClusterLabels(self, clusteredGroupName):
        '''
        To be called after clusters are saved.  Adds description text to appear in UI next to the Attributes button.
        '''
        mprs = MeasuredParameterResource.objects.using(self.args.database).filter(
            resource__resourcetype__name=clusteredGroupName
            ).select_related('resource')

        labels = mprs.values_list('resource__value', flat=True).distinct()

        for label in labels:
            rt, _ = ResourceType.objects.using(self.args.database).get_or_create(
                        name=clusteredGroupName, description='unsupervised classification')
            r, _ = Resource.objects.using(self.args.database).get_or_create(name=LABEL, 
                        value=label, resourcetype=rt)
            description = 'Automated {} classification of {} datavalues from {} features'.format(
                                self.args.algorithm,
                                mprs.filter(resource__value=label).count(),
                                len(self.args.inputs))
            if self.args.verbose:
                print(f'Describing label {label}: {description}')

            rdt, _ = ResourceType.objects.using(self.args.database).get_or_create(name=LABEL, description='metadata')
            rd, _ = Resource.objects.using(self.args.database).get_or_create(name=DESCRIPTION, value=description, resourcetype=rdt)
            rr = ResourceResource(fromresource=r, toresource=rd)
            rr.save(using=self.args.database)

    def removeLabels(self, clusteredGroupName):  # pragma: no cover
        '''
        Delete named MeasuredParameterResources that have ResourceType.name=clusteredGroupName (such as 'Cluster label').
        Note: Some metadatda ResourceTypes will not be removed even though the Resources that use them will be removed.
        '''
        mprs = MeasuredParameterResource.objects.using(self.args.database).filter(
            resource__resourcetype__name=clusteredGroupName
            ).select_related('resource')

        rt = ResourceType.objects.using(self.args.database).get(name=clusteredGroupName)

        if self.args.verbose > 1:
            print("Removing MeasuredParameterResources with labelGroupName = %s" % (clusteredGroupName,))

        rs = []
        for mpr in mprs:
            rs.append(mpr.resource)
            mpr.delete(using=self.args.database)

        for r in set(rs):
            r.delete(using=self.args.database)

        rt.delete(using=self.args.database)

    def loadData(self, sdt=None, edt=None): # pragma: no cover
        '''
        Retrieve data from the database and return the x, and y values and IDs (in list form) that the scikit-learn package uses.
        May raise NoPPDataException.
        Normalize the x and y data based on the statistics of the parameter from the platform stored in STOQS.
        '''
        if not sdt and not edt:
            sdt = datetime.strptime(self.args.start, '%Y%m%dT%H%M%S')
            edt = datetime.strptime(self.args.end, '%Y%m%dT%H%M%S')
            
        pvDict = {}
        x_ids, y_ids, xs, ys, _ = self._getPPData(sdt, edt, self.args.platform, self.args.inputs[0],
                                                  self.args.inputs[1], pvDict, returnIDs=True, sampleFlag=False)

        if self.args.do_not_normalize:
            x = xs
            y = ys
        else:
            # See http://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.MinMaxScaler.html
            xmin, xmax, xUnits = self._getAxisInfo(self.args.platform, self.args.inputs[0])
            ymin, ymax, yUnits = self._getAxisInfo(self.args.platform, self.args.inputs[1])
            x = [((x1 - xmin) / (xmax - xmin)) for x1 in xs]
            y = [((y1 - ymin) / (ymax - ymin)) for y1 in ys]

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
        Step through the data at a specified time interval and identify clusters.
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
        examples = 'Examples:' + '\n\n'
        examples += "Identify clusters in data and save to the database:\n"
        examples += sys.argv[0] + (" --saveClusters --database stoqs_september2013"
                                   " --platform Slocum_260 --start 20130923T124038 --end 20130923T150613"
                                   " --inputs optical_backscatter700nm fluorescence --algorithm DBSCAN "
                                   "--clusteredGroupName DBSCANclusters -v\n\n")
        examples += "Remove labels from the database\n"
        examples += sys.argv[0] + (" --removeLabels --database stoqs_september2013"
                                   " --platform Slocum_260 --start 20130923T124038 --end 20130923T150613"
                                   " --inputs optical_backscatter700nm fluorescence "
                                   "--clusteredGroupName DBSCANclusters -v\n\n")
        examples += '''Typical workflow:
0. Test creating a cluster with --createClusters; does not update database with cluster names (Attributes)
0. Test stepping through database with --clusterSeq; does not update database with cluster names (Attributes)
1. Use --saveClusters to update database with clusters for single specified time period
2. Use --saveClustersSeq to step through time updating the database with cluster names (Attributes)
'''

        parser = argparse.ArgumentParser(formatter_class=DefaultsRawTextHelpFormatter,
                                         description='Script to execute steps in the classification of measurements',
                                         epilog=examples)

        parser.add_argument('-p', '--platform', action='store', help='STOQS Platform name for training data access')
        parser.add_argument('-d', '--database', action='store', help='Database alias', default='stoqs_september2013_o',
                            required=True)
        parser.add_argument('--createClusters', action='store_true', help='Identify clusters in data')
        parser.add_argument('--clusterSeq', action='store_true', help='Step through data at specified interval and identify data clusters')
        parser.add_argument('--saveClusters', action='store_true', help='Identify clusters in data and save labels to database with --clusteredGroupName option')
        parser.add_argument('--saveClustersSeq', action='store_true', help='Step through data at specified interval, identify data clusters,'
                                                                          'and save labels to database with --clusteredGroupName option')
        parser.add_argument('--removeLabels', action='store_true', help='Remove Labels created by --saveClusters with --clusteredGroupName option')
        parser.add_argument('--inputs', action='store',
                            help='List of STOQS Parameter names to use as features, separated by spaces', nargs='*')
        parser.add_argument('--start', action='store', help='Start time in YYYYMMDDTHHMMSS format',
                            default='19000101T000000')
        parser.add_argument('--end', action='store', help='End time in YYYYMMDDTHHMMSS format',
                            default='22000101T000000')
        parser.add_argument('--interval', action='store', help='Time interval for which clusterSeq() steps through the'
                                                               'data, in format "days=x, seconds=x, minutes=x, hours=x,'
                                                               ' weeks=x" ', default='hours=1')
        parser.add_argument('--step', action='store', help='Time step for clusterSeq() to use when stepping through the'
                                                               'data, in format "days=x, seconds=x, minutes=x, hours=x,'
                                                               ' weeks=x" ', default='minutes=10')
        parser.add_argument('--algorithm', choices=list(self.algorithms.keys()),
                            help='Specify clustering algorithm to use with --createClusters, --clusterSeq, --saveClusters, '
                                                                'or --saveClusterSeq option')
        parser.add_argument('--clusteredGroupName', action='store', help='Name used to refer to the grouping, such as '
                                                                '"Cluster label" or "DBSCAN labels"')
        parser.add_argument('--do_not_normalize', action='store_true', help='Pass non-normalized data to the fitting algorithm')
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
        c.saveClusters(' '.join((CLUSTERED, c.args.clusteredGroupName)))
        c.describeClusterLabels(' '.join((CLUSTERED, c.args.clusteredGroupName)))

    elif c.args.saveClustersSeq:
        c.saveClustersSeq(' '.join((CLUSTERED, c.args.clusteredGroupName)))
        c.describeClusterLabels(' '.join((CLUSTERED, c.args.clusteredGroupName)))

    elif c.args.removeLabels:
        c.removeLabels(' '.join((CLUSTERED, c.args.clusteredGroupName)))

    else:
        print("fix your inputs")

