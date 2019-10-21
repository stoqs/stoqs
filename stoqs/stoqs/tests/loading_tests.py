#!/usr/bin/env python

'''
Tests special case data loaders, e.g.:
- Non-GridType Trajectory data
- EPIC data from CCE Campaign

Mike McCann
MBARI 24 October 2017
'''

import os
import sys
parent_dir = os.path.join(os.path.dirname(__file__), "../../loaders")
sys.path.insert(0, parent_dir)  # So that CCE is found

import time
import json
import time
import logging

from datetime import timedelta
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from stoqs.models import MeasuredParameter, ActivityParameter, ParameterResource, Parameter
from CCE.loadCCE_2015 import lores_event_times

logger = logging.getLogger('stoqs.tests')
settings.LOGGING['loggers']['stoqs.tests']['level'] = 'INFO'

class MeasuredParameterTestCase(TestCase):
    fixtures = ['stoqs_load_test.json']
    multi_db = False

    def test_epic_timeseries_lastday(self):

        # Expected number of records for the timeseries Parameters from 
        # the MS moorings
        parm_counts = dict(Hdg_1215=12, P_1=6, Ptch_1216=12, 
                           Roll_1217=12, S_41=6, T_28=6)

        # Use last day of the 2nd event from CCE.loadCCE_2015 - March 2016
        one_day_from_end = lores_event_times[1][1] - timedelta(days=1)
        logger.debug(f'one_day_from_end = {one_day_from_end}')

        for parm in list(parm_counts.keys()):
            # one_day_from_end = 2016-03-07T00:00:00
            mp_count = MeasuredParameter.objects.filter(parameter__name__contains=parm,
                            measurement__instantpoint__timevalue__gt=one_day_from_end).count()
            logger.debug(f'{parm:10s}({parm_counts[parm]:2d}) {mp_count:-6d}')
            self.assertNotEquals(mp_count, 0, f'Expected {parm_counts[parm]} values for {parm}')

    def test_epic_timeseries_full(self):

        # Expected number of records 
        parm_counts = dict(NEP_56=1, T_28=9)

        for parm in list(parm_counts.keys()):
            mp_count = MeasuredParameter.objects.filter(parameter__name__contains=parm).count()
            logger.debug(f'{parm:10s}({parm_counts[parm]:2d}) {mp_count:-6d}')
            self.assertNotEquals(mp_count, 0, f'Expected {parm_counts[parm]} values for {parm}')

    def test_glider_trajectory(self):

        # Non-grid type data with CF-1.6 coordinates attributes and original data containing a nan
        act_name = 'OS_Glider_L_662_20151124_TS'
        parm_names = ('PSAL', 'TEMP', 'FLU2')
        ap_fields = ('min', 'max', 'mean', 'median', 'mode', 'p025', 'p975', 'p010', 'p990')

        for parm in parm_names:
            ap = ActivityParameter.objects.get(activity__name__contains=act_name, parameter__name__contains=parm)
            for field in ap_fields:
                self.assertIsNotNone(getattr(ap, field), f'ActivityParameter field {field} cannot be None')

    def test_oxygen_units(self):

        # Case when Glider_L_662 and daphne both have an 'oxygen' Parameter, but with different units
        original_oxygen_name = 'oxygen'
        prs = (ParameterResource.objects
                    .filter(parameter__name=original_oxygen_name, resource__name='units')
                    .values_list('resource__value', flat=True))
        ps = (Parameter.objects.filter(name=original_oxygen_name).values_list('units', flat=True))
        self.assertEquals(len(prs), len(ps), 'Should not have more that one units for a Parameter name')

        
