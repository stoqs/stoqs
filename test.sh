#!/bin/bash
# Run tests using the continuous integration configuaration

export DJANGO_SECRET_KEY='SET_YOUR_OWN_IMPOSSIBLE_TO_GUESS_SECRET_KEY_ENVIRONMENT_VARIABLE'
export DATABASE_URL="postgis://postgres:@localhost:5432/stoqs_test"
cd stoqs
./manage.py test stoqs.tests --settings=config.ci
