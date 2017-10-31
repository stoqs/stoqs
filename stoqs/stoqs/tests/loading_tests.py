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
from django.core.urlresolvers import reverse
from stoqs.models import MeasuredParameter
from CCE.loadCCE_2015 import lores_event_times

logger = logging.getLogger('stoqs.tests')
settings.LOGGING['loggers']['stoqs.tests']['level'] = 'INFO'

class MeasuredParameterTestCase(TestCase):
    fixtures = ['stoqs_load_test.json']
    multi_db = False

    def test_epic_timeseries_lastday(self):

        # Expected number of records for the timeseries Parameters from 
        # the MS moorings
        parm_counts = dict(D_3=6, Hdg_1215=12, P_1=6, Ptch_1216=12, 
                           Roll_1217=12, S_41=6, T_28=6)

        # Use last day of the 2nd event from CCE.loadCCE_2015 - March 2016
        one_day_from_end = lores_event_times[1][1] - timedelta(days=1)
        logger.debug(f'one_day_from_end = {one_day_from_end}')

        for parm in list(parm_counts.keys()):
            # one_day_from_end = 2016-03-07T00:00:00
            mp_count = MeasuredParameter.objects.filter(parameter__name=parm,
                            measurement__instantpoint__timevalue__gt=one_day_from_end).count()
            logger.debug(f'{parm:10s}({parm_counts[parm]:2d}) {mp_count:-6d}')
            self.assertNotEquals(mp_count, 0, f'Expected {parm_counts[parm]} values for {parm}')

    def test_epic_timeseries_full(self):

        # Expected number of records 
        parm_counts = dict(NEP_56=1, Trb_980=1)

        for parm in list(parm_counts.keys()):
            mp_count = MeasuredParameter.objects.filter(parameter__name=parm).count()
            logger.debug(f'{parm:10s}({parm_counts[parm]:2d}) {mp_count:-6d}')
            self.assertNotEquals(mp_count, 0, f'Expected {parm_counts[parm]} values for {parm}')

