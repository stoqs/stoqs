#!/bin/bash
# Do database operations to create default database and load data for testing
# Designed for re-running on development system - ignore errors in Vagrant and Travis-ci

psql -c "CREATE USER stoqsadm WITH PASSWORD 'CHANGEME';" -U postgres
psql -c "DROP DATABASE stoqs;" -U postgres
psql -c "CREATE DATABASE stoqs owner=stoqsadm template=template_postgis;" -U postgres
psql -c "ALTER DATABASE stoqs SET TIMEZONE='GMT';" -U postgres
psql -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO stoqsadm;" -U postgres -d stoqs

# Assume in stoqsgit directory
export DJANGO_SECRET_KEY='SET_YOUR_OWN_IMPOSSIBLE_TO_GUESS_SECRET_KEY'
export DATABASE_URL="postgis://stoqsadm:CHANGEME@127.0.0.1:5432/stoqs"
stoqs/manage.py syncdb --settings=config.local --noinput --database=default

cd stoqs
wget -q -N -O loaders/Monterey25.grd http://stoqs.mbari.org/terrain/Monterey25.grd
coverage run --include="loaders/__in*,loaders/DAP*,loaders/Samp*" loaders/loadTestData.py

# Run tests using the continuous integration setting and default Local class configuration
# test_stoqs database created and dropped by role of the shell account using Test framework's DB names
./manage.py dumpdata --settings=config.ci stoqs > fixtures/stoqs_test_data.json
unset DATABASE_URL
coverage run -a --source=utils,stoqs ./manage.py test stoqs.tests.tests --settings=config.ci
test_status=$?
tools/removeTmpFiles.sh
coverage report -m
cd ..
exit $test_status
