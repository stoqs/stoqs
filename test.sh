#!/bin/bash
# Do database operations to create default database and create fixture for testing.
# Designed for re-running on development system - ignore errors in Vagrant and Travis-ci.
# Pass the stoqsadm password as an argument on first execution in order to create the
# stoqsadm user; it must match what's in DATABASE_URL.  Must also set MAPSERVER_HOST.
# Make sure none of these are set: STATIC_FILES, STATIC_URL, MEDIA_FILES, MEDIA_URL 
# and that nothing is connected to the default stoqs database.

if [ -z $1 ]
then
    echo "Please provide the password for the local PostgreSQL stoqsadm account."
    echo "Usage: $0 <stoqsadm_db_password>"
    exit -1
fi
if [ -L stoqs/campaigns.py ]
then
    echo "Found stoqs/campaigns.py symbolic link.  For faster processing it's"
    echo "suggested that you remove stoqs/campaigns.py and stoqs/campaigns.pyc so"
    echo "that test_ databases don't get created for all the campaigns there."
    exit -1
fi
psql -c "CREATE USER stoqsadm WITH PASSWORD '$1';" -U postgres
psql -c "DROP DATABASE IF EXISTS stoqs;" -U postgres
psql -c "CREATE DATABASE stoqs owner=stoqsadm;" -U postgres
psql -c "CREATE EXTENSION postgis;" -d stoqs -U postgres
psql -c "CREATE EXTENSION postgis_topology;" -d stoqs -U postgres
if [ $? != 0 ]
then
    echo "Cannot create default database stoqs; refer to above message."
    exit -1
fi
psql -c "ALTER DATABASE stoqs SET TIMEZONE='GMT';" -U postgres

# DATABASE_URL environment variable must be set outside of this script
stoqs/manage.py makemigrations stoqs --settings=config.settings.ci --noinput
stoqs/manage.py migrate --settings=config.settings.ci --noinput --database=default
if [ $? != 0 ]
then
    echo "Cannot migrate default database; refer to above error message."
    exit -1
fi
psql -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO stoqsadm;" -U postgres -d stoqs

# Assume starting in project home (stoqsgit) directory, get bathymetry, and load data
cd stoqs
wget -q -N -O loaders/Monterey25.grd http://stoqs.mbari.org/terrain/Monterey25.grd
coverage run --include="loaders/__in*,loaders/DAP*,loaders/Samp*" loaders/loadTestData.py
if [ $? != 0 ]
then
    echo "loaders/loadTestData.py failed to load initial database; exiting test.sh."
    exit -1
fi

# Label some data in the test database
coverage run -a --include="contrib/analysis/classify.py" contrib/analysis/classify.py \
  --createLabels --groupName Plankton --database default  --platform dorado \
  --inputs bbp700 fl700_uncorr --discriminator salinity --labels diatom dino1 dino2 sediment \
  --mins 33.33 33.65 33.70 33.75 --maxes 33.65 33.70 33.75 33.93 -v

# Create database fixture and run tests using the continuous integration (ci) setting
# Need to create and drop test_ databases using shell account, hence reassign DATABASE_URL
./manage.py dumpdata --settings=config.settings.ci stoqs > stoqs/fixtures/stoqs_test_data.json
echo "Unit tests..."
DATABASE_URL=postgis://127.0.0.1:5432/stoqs bash -c "coverage run -a --source=utils,stoqs \
    manage.py test stoqs.tests.unit_tests --settings=config.settings.ci"
unit_tests_status=$?

# Run the development server in the background for the functional tests with full DATABASE_URL
# so that mapserver can connect to the database
coverage run -a --source=utils,stoqs manage.py runserver --noreload \
    --settings=config.settings.ci > /tmp/functional_tests_server.log 2>&1 &
pid=$!
echo "Functional tests with development server running as pid = $pid ..."
DATABASE_URL=postgis://127.0.0.1:5432/stoqs bash -c "./manage.py test \
    stoqs.tests.functional_tests --settings=config.settings.ci"
functional_tests_status=$?
ps -ef | grep $pid
echo "Trying to kill with TERM signal..."
/usr/bin/kill -s TERM $pid
ps -ef | grep $pid
##cat /tmp/functional_tests_server.log
tools/removeTmpFiles.sh > /dev/null 2>&1

# Report results of unit and functional tests
coverage report -m
cd ..
##exit $(($unit_tests_status + $functional_tests_status))
exit $unit_tests_status

