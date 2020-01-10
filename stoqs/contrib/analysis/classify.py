#!/usr/bin/env python
"""
Script to execute steps in the classification of measurements including:

1. Labeling specific MeasuredParameters
2. Tagging MeasuredParameters based on a model

Mike McCann
MBARI 16 June 2014
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
mpl.use('Agg')               # Force matplotlib to not use any Xwindows backend
import matplotlib.pyplot as plt
import numpy as np
import warnings
from datetime import datetime
from django.db.utils import IntegrityError
from textwrap import wrap
from stoqs.models import (Activity, ResourceType, Resource, Measurement, MeasuredParameter,
                          MeasuredParameterResource, ResourceResource)
from utils.STOQSQManager import LABEL, DESCRIPTION, COMMANDLINE

from contrib.analysis import BiPlot, NoPPDataException

from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis as QDA
import pickle

LABELED = 'Labeled'
TRAIN = 'Train'
TEST = 'Test'

class Classifier(BiPlot):
    '''
    To hold methods and data to support classification of measurements in a STOQS database.
    See http://scikit-learn.org/stable/auto_examples/plot_classifier_comparison.html
    '''
    classifiers = { 'Nearest_Neighbors': KNeighborsClassifier(3),
                    'Linear_SVM': SVC(kernel="linear", C=0.025),
                    'RBF_SVM': SVC(gamma=2, C=1),
                    'Decision_Tree': DecisionTreeClassifier(max_depth=5),
                    'Random_Forest': RandomForestClassifier(max_depth=5, n_estimators=10, max_features=1),
                    'AdaBoost': AdaBoostClassifier(),
                    'Naive_Bayes': GaussianNB(),
                    'LDA': LDA(),
                    'QDA': QDA()
                  }
    def getActivity(self, mpx, mpy):
        '''
        Return activity object which MeasuredParameters mpx and mpy belong to
        '''
        acts = Activity.objects.using(self.args.database).filter(
            instantpoint__measurement__measuredparameter__id__in=(mpx,mpy)).distinct()
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
        r, _ = Resource.objects.using(self.args.database).get_or_create(name=COMMANDLINE, value=self.commandline, resourcetype=rt)

        return r
        
    def saveLabelSet(self, clResource, label, x_ids, y_ids, description, typeName, typeDescription):
        '''
        Save the set of labels in MeasuredParameterResource. Accepts 2 input vectors. (TODO: generalize to N input vectors);
        description is used to describe the criteria for assigning this label. The typeName and typeDecription may be used to
        refer to the grouping, and associate via the grouping the other labels made in the heuristic applied.
        '''
        try:
            # Label
            rt, _ = ResourceType.objects.using(self.args.database).get_or_create(name=typeName, description=typeDescription)
            r, _ = Resource.objects.using(self.args.database).get_or_create(name=LABEL, value=label, resourcetype=rt)
            # Label's description
            rdt, _ = ResourceType.objects.using(self.args.database).get_or_create(name=LABEL, description='metadata')
            rd, _ = Resource.objects.using(self.args.database).get_or_create(name=DESCRIPTION, value=description, resourcetype=rdt)
            rr = ResourceResource(fromresource=r, toresource=rd)
            rr.save(using=self.args.database)
            # Associate with commandlineResource
            ResourceResource.objects.using(self.args.database).get_or_create(fromresource=r, toresource=clResource)

        except IntegrityError as e:
            print(str(e))
            print("Ignoring")

        # Associate MeasuredParameters with Resource
        if self.args.verbose:
            print("  Saving %d values of '%s' with type '%s'" % (len(x_ids), label, typeName))
        for x_id,y_id in zip(x_ids, y_ids):
            a = self.getActivity(x_id, y_id)
            mp_x = MeasuredParameter.objects.using(self.args.database).get(pk=x_id)
            mp_y = MeasuredParameter.objects.using(self.args.database).get(pk=y_id)
            MeasuredParameterResource.objects.using(self.args.database).get_or_create(
                                activity=a, measuredparameter=mp_x, resource=r)
            MeasuredParameterResource.objects.using(self.args.database).get_or_create(
                                activity=a, measuredparameter=mp_y, resource=r)

    def removeLabels(self, labeledGroupName, label=None, description=None, commandline=None): # pragma: no cover
        '''
        Delete labeled MeasuredParameterResources that have ResourceType.name=labeledGroupName (such as 'Labeled Plankton').  
        Restrict deletion to the other passed in options, if specified: label is like 'diatom', description is like 
        'Using Platform dorado, Parameter {'salinity': ('33.65', '33.70')} from 20130916T124035 to 20130919T233905'
        (commandline is too long to show in this doc string - see examples in usage note).  Note: Some metadatda
        ResourceTypes will not be removed even though the Resources that use them will be removed.
        '''
        # Remove MeasuredParameter associations with Resource (Labeled data)
        mprs = MeasuredParameterResource.objects.using(self.args.database).filter(resource__resourcetype__name=labeledGroupName
                                ).select_related('resource')
        if label:
            mprs = mprs.filter(resource__name=LABEL, resource__value=label)

        if self.args.verbose > 1:
            print("  Removing MeasuredParameterResources with type = '%s' and label = %s" % (labeledGroupName, label))

        rs = []
        for mpr in mprs:
            rs.append(mpr.resource)
            mpr.delete(using=self.args.database)

        # Remove Resource associations with Resource (label metadata), make rs list distinct with set() before iterating on the delete()
        if label and description and commandline:
            try:
                rrs = ResourceResource.objects.using(self.args.database).filter(
                                                    (QDA(fromresource__name=LABEL) & QDA(fromresource__value=label)) &
                                                    ((QDA(toresource__name=DESCRIPTION) & QDA(toresource__value=description)) |
                                                     (QDA(toresource__name=COMMANDLINE) & QDA(toresource__value=commandline)) ) )
                if self.args.verbose > 1:
                    print("  Removing ResourceResources with fromresource__value = '%s' and toresource__value = '%s'" % (label, description))

                for rr in rrs:
                    rr.delete(using=self.args.database)

            except TypeError:
                # Likely TypeError: __init__() got an unexpected keyword argument 'fromresource__name'
                if self.args.verbose > 1:
                    print("  Previous Resource associations not found.")
        else:
            if self.args.verbose > 1:
                print("  Removing Resources associated with labeledGroupName = %s'" % labeledGroupName)

            for r in set(rs):
                r.delete(using=self.args.database)

    def createLabels(self, labeledGroupName):
        '''
        Using discriminator, mins, and maxes label MeasuredParameters in the database so that we can do supervised learning
        '''
        sdt = datetime.strptime(self.args.start, '%Y%m%dT%H%M%S')
        edt = datetime.strptime(self.args.end, '%Y%m%dT%H%M%S')

        commandlineResource = self.saveCommand()

        for label, dmin, dmax in zip(self.args.labels, self.args.mins, self.args.maxes):
            # Multiple discriminators are possible...
            pvDict = {self.args.discriminator: (dmin, dmax)}
            if self.args.verbose:
                print("Making label '%s' with discriminator %s" % (label, pvDict))

            try:
                x_ids, y_ids, _, _, _ = self._getPPData(sdt, edt, self.args.platform, self.args.inputs[0], 
                                                        self.args.inputs[1], pvDict, returnIDs=True, sampleFlag=False)
            except NoPPDataException as e:
                print(str(e))

            if self.args.verbose:
                print("  (%d, %d) MeasuredParameters returned from database %s" % (len(x_ids), len(y_ids), self.args.database))

            description = 'Using Platform %s, Parameter %s from %s to %s' % (self.args.platform, pvDict, self.args.start, self.args.end)

            if self.args.clobber:
                self.removeLabels(labeledGroupName, label, description, commandlineResource.value)

            self.saveLabelSet(commandlineResource, label, x_ids, y_ids, description, labeledGroupName, 
                                    'Labeled with %s as discriminator' % self.args.discriminator)

    def loadLabeledData(self, labeledGroupName, classes): # pragma: no cover
        '''
        Retrieve from the database to set of Labeled data and return the standard X, and y arrays that the scikit-learn package uses
        '''
        if len(classes) > 2:
            raise Exception('Maximum classes length is 2')

        f0 = np.array(0)
        f1 = np.array(0)
        y = np.array(0, dtype=int)
        target = 0
        for label in classes:
            mprs = MeasuredParameterResource.objects.using(self.args.database).filter(
                        resource__name=LABEL, resource__resourcetype__name=labeledGroupName, 
                        resource__value=label
                        ).values_list('measuredparameter__datavalue', flat=True)
            count = mprs.filter(measuredparameter__parameter__name=self.args.inputs[0]).count()
            if self.args.verbose:
                print('count = {} for label = {}'.format(count, label))
            if count == 0:
                warnings.warn('count = 0 for label = {}'.format(label))
            f0 = np.append(f0, mprs.filter(measuredparameter__parameter__name=self.args.inputs[0]))
            f1 = np.append(f1, mprs.filter(measuredparameter__parameter__name=self.args.inputs[1]))
            y = np.append(y, np.ones(count) * target)
            target += 1

        # Form the feature vectors into the X matrix that sklearn wants
        X = np.concatenate((f0.reshape(-1,1), f1.reshape(-1,1)), axis=1)

        return X, y

    def doModelsScore(self, labeledGroupName):
        '''
        Print scores for several different classifiers
        '''
        X, y = self.loadLabeledData(labeledGroupName, classes=self.args.classes)
        X = StandardScaler().fit_transform(X)

        if X.any() and y.any():
            for name, clf in list(self.classifiers.items()):
                scores = cross_val_score(clf, X, y, cv=5)
                print("%-18s accuracy: %0.2f (+/- %0.2f)" % (name, scores.mean(), scores.std() * 2))
        else:
            raise Exception('No data returned for labeledGroupName = %s' % labeledGroupName)

    def createClassifier(self, labeledGroupName): # pragma: no cover
        '''
        Query the database for labeled training data, fit a model to it, and save the pickled 
        model back to the database.  Follow the pattern in the example at 
        http://scikit-learn.org/stable/auto_examples/classification/plot_classifier_comparison.html
        and learn about Learning at https://www.youtube.com/watch?v=4ONBVNm3isI (see at time 2:33 and 
        following - though the whole tutorial is worth watching).
        '''
        clf = self.classifiers[self.args.classifier]

        X, y = self.loadLabeledData(labeledGroupName, classes=self.args.classes)
        X = StandardScaler().fit_transform(X)

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=self.args.test_size, train_size=self.args.train_size)

        import pdb
        pdb.set_trace()
        # TODO: Implement graphical evaluation as in http://scikit-learn.org/stable/auto_examples/classification/plot_classifier_comparison.html

        clf.fit(X_train, y_train)
        score = clf.score(X_test, y_test)
        if self.args.verbose:
            print("  score = %f" % score)

        self._saveModel(labeledGroupName, clf)

    def _saveModel(self, labeledGroupName, clf):
        '''
        Pickle and save the model in the database 
        '''
        # Save pickled mode to the database and relate it to the LABELED data resource
        if self.args.modelBaseName:
            rt, _ = ResourceType.objects.using(self.args.database).get_or_create(name='FittedModel', description='SVC(gamma=2, C=1)')
            labeledResource = Resource.objects.using(self.args.database).filter(resourcetype__name=labeledGroupName)[0]
            modelValue = pickle.dumps(clf).encode("zip").encode("base64").strip()
            modelResource = Resource(name=self.args.modelBaseName, value=modelValue, resourcetype=rt)
            modelResource.save(using=self.args.database)
            rr = ResourceResource(fromresource=labeledResource, toresource=modelResource)
            rr.save(using=self.args.database)

            if self.args.verbose:
                print('Saved fitted model to the database with name = %s' % self.args.modelBaseName)
                print('Retrieve with "clf = pickle.loads(r.value.decode("base64").decode("zip"))"')

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
            print('  Saving file', fileName)
        fig.savefig(fileName)

    def process_command_line(self):
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Example machine learning workflow:' + '\n\n' 
        examples += "Step 1: Create Labeled features in the database using salinity as a discriminator:\n"
        examples += sys.argv[0] + (" --createLabels --groupName Plankton --database stoqs_september2013_t"
                                  " --platform dorado --start 20130916T124035 --end 20130919T233905"
                                  " --inputs bbp700 fl700_uncorr --discriminator salinity"
                                  " --labels diatom dino1 dino2 sediment --mins 33.33 33.65 33.70 33.75"
                                  " --maxes 33.65 33.70 33.75 33.93 --clobber -v\n\n")
        examples += "Step 2: Evaluate classifiers using the labels created in Step 1\n"
        examples += sys.argv[0] + (" --doModelsScore --groupName Plankton --database stoqs_september2013_t"
                                   " --classes diatom sediment --inputs bbp700 fl700_uncorr\n\n")
        examples += "Step 3: Create a prediction model using the labels created in Step 1\n"
        examples += sys.argv[0] + (" --createClassifier --groupName Plankton --database stoqs_september2013_t"
                                  " --classifier Nearest_Neighbors --classes diatom sediment"
                                  " --modelBaseName Nearest_Neighbors_1\n\n")
        examples += "Step 4: Use a model to classify new measurements\n"
        examples += '\nIf running from cde-package replace ".py" with ".py.cde" in the above list.'
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Script to execute steps in the classification of measurements',
                                         epilog=examples)
                                             
        parser.add_argument('-p', '--platform', action='store', help='STOQS Platform name for training data access')
        parser.add_argument('-d', '--database', action='store', help='Database alias', default='stoqs_september2013_o', required=True)
        ##parser.add_argument('--minDepth', action='store', help='Minimum depth for data queries', default=None, type=float)
        ##parser.add_argument('--maxDepth', action='store', help='Maximum depth for data queries', default=None, type=float)

        parser.add_argument('--createLabels', action='store_true', help='Label data with --discriminator, --groupName --labels, --mins, and --maxes options')
        parser.add_argument('--removeLabels', action='store_true', help='Remove Labels with --groupName option')
        parser.add_argument('--createClassifier', action='store_true', help='Fit a model to Labeled data with --classifier to labels in --labels and save in database as --modelBaseName')
        parser.add_argument('--doModelsScore', action='store_true', help='Print scores for fits of various models for --groupName')
        parser.add_argument('--inputs', action='store', help='List of STOQS Parameter names to use as features, separated by spaces', nargs='*')
        parser.add_argument('--start', action='store', help='Start time in YYYYMMDDTHHMMSS format', default='19000101T000000')
        parser.add_argument('--end', action='store', help='End time in YYYYMMDDTHHMMSS format', default='22000101T000000')
        parser.add_argument('--discriminator', action='store', help='Parameter name to use to discriminate the data')
        parser.add_argument('--groupName', action='store', help='Name to follow "Labeled" in UI describing the group of --labels for --createLabels option')
        parser.add_argument('--labels', action='store', help='List of labels to create separated by spaces', nargs='*')
        parser.add_argument('--mins', action='store', help='List of labels to create separated by spaces', nargs='*')
        parser.add_argument('--maxes', action='store', help='List of labels to create separated by spaces', nargs='*')
        parser.add_argument('--test_size', action='store', help='Proportion of discriminated sample to save as Test set', default=0.4, type=float)
        parser.add_argument('--train_size', action='store', help='Proportion of discriminated sample to save as Train set', default=0.4, type=float)
        parser.add_argument('--classifier', choices=list(self.classifiers.keys()), help='Specify classifier to use with --createClassifier option')
        parser.add_argument('--modelBaseName', action='store', help='Base name of the model to store in the database')
        parser.add_argument('--classes', action='store', help='Labels to load from the database for --doModelsScore and --createClassifier', nargs='*')

        parser.add_argument('--clobber', action='store_true', help='Remove existing MeasuredParameterResource records before adding new classification')
        parser.add_argument('-v', '--verbose', nargs='?', choices=[1,2,3], type=int, help='Turn on verbose output. Higher number = more output.', const=1, default=0)
    
        self.args = parser.parse_args()
        self.commandline = ' '.join(sys.argv)

        # Conditional tests
        if self.args.doModelsScore:
            if not c.args.classes:
                parser.error('--doModelsScore requires --classes')
            if not c.args.inputs:
                parser.error('--doModelsScore requires --inputs')
    
    
if __name__ == '__main__':

    c = Classifier()
    c.process_command_line()

    if c.args.createLabels:
        c.createLabels(' '.join((LABELED, c.args.groupName)))

    if c.args.removeLabels:
        c.removeLabels(' '.join((LABELED, c.args.groupName)))

    elif c.args.doModelsScore:
        c.doModelsScore(' '.join((LABELED, c.args.groupName)))

    elif c.args.createClassifier:
        c.createClassifier(' '.join((LABELED, c.args.groupName)))

