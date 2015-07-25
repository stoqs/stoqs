#!/bin/bash
# Do database operations to create default database and load data for testing
# Designed for re-running on development system - ignore errors in Vagrant and Travis-ci
# (You may want a different password than CHANGEME on your system)

psql -c "CREATE USER stoqsadm WITH PASSWORD 'CHANGEME';" -U postgres
psql -c "DROP DATABASE stoqs;" -U postgres
psql -c "CREATE DATABASE stoqs owner=stoqsadm template=template_postgis;" -U postgres
psql -c "ALTER DATABASE stoqs SET TIMEZONE='GMT';" -U postgres
psql -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO stoqsadm;" -U postgres -d stoqs

# Set environment variables and create initial default database that is used for testing
export DJANGO_SECRET_KEY='SET_YOUR_OWN_IMPOSSIBLE_TO_GUESS_SECRET_KEY'
export DATABASE_URL="postgis://stoqsadm:CHANGEME@127.0.0.1:5432/stoqs"
stoqs/manage.py makemigrations stoqs --settings=config.settings.local --noinput
stoqs/manage.py migrate --settings=config.settings.local --noinput --database=default

# Assume starting in project home (stoqsgit) directory, get bathymetry, and load data
cd stoqs
wget -q -N -O loaders/Monterey25.grd http://stoqs.mbari.org/terrain/Monterey25.grd
coverage run --include="loaders/__in*,loaders/DAP*,loaders/Samp*" loaders/loadTestData.py

# Label some data in the test database
coverage run -a --include="contrib/analysis/classify.py" contrib/analysis/classify.py \
  --createLabels --groupName Plankton --database default  --platform dorado \
  --inputs bbp700 fl700_uncorr --discriminator salinity --labels diatom dino1 dino2 sediment \
  --mins 33.33 33.65 33.70 33.75 --maxes 33.65 33.70 33.75 33.93 -v

# Run tests using the continuous integration setting and default Local class configuration
# test_stoqs database created and dropped by role of the shell account using Test framework's DB names
./manage.py dumpdata --settings=config.settings.ci stoqs > stoqs/fixtures/stoqs_test_data.json
unset DATABASE_URL
coverage run -a --source=utils,stoqs ./manage.py test stoqs.tests.unit_tests --settings=config.settings.ci
unit_tests_status=$?

# Run the development server in the background for the functional tests
coverage run -a --source=utils,stoqs ./manage.py runserver 0.0.0.0:8000 --settings=config.settings.ci &
pid=$!
./manage.py test stoqs.tests.functional_tests --settings=config.settings.ci
pkill -TERM -P $pid
tools/removeTmpFiles.sh

# Report results of unit and functional tests
coverage report -m
cd ..
exit $unit_tests_status
