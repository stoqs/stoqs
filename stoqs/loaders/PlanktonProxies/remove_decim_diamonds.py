#!/usr/bin/env python
'''
After loading stoqs_mb_diamonds there are extra Dorado*_decim.nc Activities
that are not diamonds. Compare against auv-python dorado*_1S.nc Activities 
and remove the extras.

Mike McCann
MBARI 14 November 2022
'''

import os
import sys

# Insert Django App directory (parent of config) into python path
sys.path.insert(0, os.path.abspath(os.path.join(
                        os.path.dirname(__file__), "../../")))
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
import django
django.setup()


from stoqs.models import Activity

db_alias = "stoqs_mb_diamonds"
diamond_decims = []
print(f"Finding non-Diamond missions in db_alias = {db_alias}")
acts = Activity.objects.using(db_alias).filter(name__contains="1S.nc")
for act in acts:
    if not act.name.endswith("1S.nc"):
        continue
    # print(act)
    yyyy, yd, mn = act.name.split("_")[1].split(".")
    diamond_decims.append(f"Dorado389_{yyyy}_{yd}_{mn}_{yd}_{mn}_decim.nc")

acts_to_delete = Activity.objects.using(db_alias).exclude(name__in=diamond_decims).filter(name__contains="Dorado389_").order_by('startdate')
print(acts_to_delete)
ans = input("Delete these non-Diamond Activities? [yN] ") or "N"
if ans.upper() == "Y":
    for act_to_delete in acts_to_delete:
        act_to_delete.delete(using=db_alias)
        print(f"Deleted {act_to_delete}")

