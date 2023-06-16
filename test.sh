#!/bin/bash
# Do database operations to create default database and create fixture(s) for testing.
# Designed for re-running on development system and on CI services.
# Pass the stoqsadm password as an argument in order to create the
# stoqsadm user; it must match what's in DATABASE_URL.  Must also set MAPSERVER_HOST.
# Make sure none of these are set: STATIC_FILES, STATIC_URL, MEDIA_FILES, MEDIA_URL 
# and that nothing is using to the default stoqs database.  Standard execution on
# a development system is to execute like: './test.sh <DB_PASSWORD>'; optional
# arguments like './test.sh CHANGEME load noextraload' may be used, e.g. on travis-ci,
# to skip some of the loading tests.
#
# To run tests in a docker-based development system set some env variable first, e.g.:
#   docker-compose run --rm stoqs /bin/bash
#   export DATABASE_URL=postgis://stoqsadm:CHANGEME@stoqs-postgis:5432/stoqs
#   export DATABASE_SUPERUSER_URL=postgis://postgres:changeme@stoqs-postgis:5432/stoqs
#   ./test.sh CHANGEME load noextraload
#   To run just the functional tests:
#   DATABASE_URL=$DATABASE_SUPERUSER_URL stoqs/manage.py test stoqs.tests.functional_tests --settings=config.settings.ci
#   and just one of them:
#   DATABASE_URL=$DATABASE_SUPERUSER_URL stoqs/manage.py test stoqs.tests.functional_tests.BrowserTestCase.test_campaign_page --settings=config.settings.ci

if [ -z $1 ]
then
    echo "Please provide the password for the local PostgreSQL stoqsadm account."
    echo "Usage: $0 stoqsadm_db_password [skip_load]"
    exit -1
fi
if [ -L stoqs/campaigns.py ]
then
    echo "Found stoqs/campaigns.py symbolic link.  For faster processing it's"
    echo "suggested that you remove stoqs/campaigns.py so"
    echo "that test_ databases don't get created for all the campaigns there."
    exit -1
fi

PGPORT=`echo $DATABASE_URL | cut -d':' -f4 | cut -d'/' -f1`

if [ -z $DATABASE_SUPERUSER_URL ]
then
    DATABASE_SUPERUSER_URL=postgis://127.0.0.1:$PGPORT/stoqs
fi

# Assume starting in project home (stoqsgit) directory
cd stoqs

# Create database roles used by STOQS applications - don't print out errors, e.g.: if role already exists
psql -p $PGPORT -c "CREATE USER stoqsadm WITH PASSWORD '$1';" -U postgres 2> /dev/null
psql -p $PGPORT -c "CREATE USER everyone WITH PASSWORD 'guest';" -U postgres 2> /dev/null

export DJANGO_SETTINGS_MODULE=config.settings.ci

# If there is a third argument and it is 'extraload' execute this block, use 3rd arg of 'noextraload' to not execute
if [ ${3:-extraload} == 'extraload' ]
then
    echo "Loading additional data (EPIC, etc.) to test loading software..."
    DATABASE_URL=$DATABASE_SUPERUSER_URL coverage run -a --include="loaders/__in*,loaders/DAP*,loaders/Samp*" stoqs/tests/load_data.py
    if [ $? != 0 ]
    then
        echo "Cannot create default database stoqs; refer to above message."
        exit -1
    fi
    DATABASE_URL=$DATABASE_SUPERUSER_URL ./manage.py dumpdata --settings=config.settings.ci stoqs > stoqs/fixtures/stoqs_load_test.json
    echo "Loading tests..."
    # Need to create and drop test_ databases using shell account, hence reassign DATABASE_URL.
    # Note that DATABASE_URL is exported before this script is executed, this is so that it also works in Travis-CI.
    DATABASE_URL=$DATABASE_SUPERUSER_URL coverage run -a --source=utils,stoqs manage.py test stoqs.tests.loading_tests --settings=config.settings.ci
    loading_tests_status=$?
fi

# If there is a second argument and it is 'load' execute this block, use 2nd arg of 'noload' to not execute; execute if no second argument
# Note: These manual database creation and migration steps are performed by loaders/load.py, which is used above in the 'extraload' test block
if [ ${2:-load} == 'load' ]
then
    echo "Loading standard data for unit and functional tests..."
    psql -p $PGPORT -c "DROP DATABASE IF EXISTS stoqs;" -U postgres
    psql -p $PGPORT -c "CREATE DATABASE stoqs owner=stoqsadm;" -U postgres
    psql -p $PGPORT -c "CREATE EXTENSION postgis;" -d stoqs -U postgres
    psql -p $PGPORT -c "CREATE EXTENSION postgis_topology;" -d stoqs -U postgres
    if [ $? != 0 ]
    then
        echo "Cannot create default database stoqs; refer to above message."
        exit -1
    fi
    psql -p $PGPORT -c "ALTER DATABASE stoqs SET TIMEZONE='GMT';" -U postgres

    ./manage.py makemigrations stoqs --settings=config.settings.ci --noinput
    ./manage.py migrate --settings=config.settings.ci --noinput --database=default
    if [ $? != 0 ]
    then
        echo "Cannot migrate default database; refer to above error message."
        exit -1
    fi
    psql -p $PGPORT -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO stoqsadm;" -U postgres -d stoqs
    psql -p $PGPORT -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO stoqsadm;" -U postgres -d stoqs

    echo "Copy x3dom javascript library version that works with SRC binary terrain"
    mkdir static/x3dom-1.8.1
    wget --no-check-certificate -O static/x3dom-1.8.1/x3dom-full.debug.js https://stoqs.mbari.org/static/x3dom-1.8.1/x3dom-full.debug.js

    # Get bathymetry and load data from MBARI data servers
    wget --no-check-certificate -O loaders/Monterey25.grd https://stoqs.mbari.org/terrain/Monterey25.grd
    coverage run --include="loaders/__in*,loaders/DAP*,loaders/Samp*" loaders/loadTestData.py
    if [ $? != 0 ]
    then
        echo "loaders/loadTestData.py failed to load initial database; exiting test.sh."
        exit -1
    fi

    coverage run --include="loaders/__in*,loaders/DAP*,loaders/Samp*" loaders/loadMoreData.py --append
    if [ $? != 0 ]
    then
        echo "loaders/loadMoreData.py failed to load more data to existing Activity; exiting test.sh."
        exit -1
    fi

    # Label some data in the test database
    coverage run -a --include="contrib/analysis/classify.py" contrib/analysis/classify.py \
      --createLabels --groupName Plankton --database default  --platform dorado \
      --inputs bbp700 fl700_uncorr --discriminator salinity --labels diatom dino1 dino2 sediment \
      --mins 33.33 33.65 33.70 33.75 --maxes 33.65 33.70 33.75 33.93 -v

    # Show how to add everyone select permission to a database
    psql -p $PGPORT -c "GRANT select on all tables in schema public to everyone;" -U postgres -d stoqs 2> /dev/null

    # Create database fixture
    ./manage.py dumpdata --settings=config.settings.ci stoqs > stoqs/fixtures/stoqs_test_data.json
fi

# Run tests using the continuous integration (ci) setting
# Need to create and drop test_ databases using shell account or sa url, hence reassign DATABASE_URL
echo "Unit tests..."
DATABASE_URL=$DATABASE_SUPERUSER_URL
coverage run -a --source=utils,stoqs manage.py test stoqs.tests.unit_tests --settings=config.settings.ci
unit_tests_status=$?

# Instructions for running functional tests, instead of running them here
echo "===================================================================================================================="
echo "Functional tests may be run in a separate session using a different docker-compose yml file..."
echo "----------------------------------------------------------------------------------------------"
echo "cd docker"
echo "docker-compose down"
echo "docker-compose -f docker-compose-ci.yml up -d --build"
echo "docker-compose -f docker-compose-ci.yml run --rm stoqs /bin/bash"
echo "DATABASE_URL=\$DATABASE_SUPERUSER_URL stoqs/manage.py test stoqs.tests.functional_tests --settings=config.settings.ci"
echo "===================================================================================================================="
echo "Open http://localhost:7900/?autoconnect=1&resize=scale&password=secret to monitor progress of the tests

# Report results of unit and functional tests
coverage report -m --omit utils/geo.py,utils/utils.py
tools/removeTmpFiles.sh > /dev/null 2>&1
cd ..

# Save tests_status to ${STOQS_HOME}/stoqs/stoqs/tests for Dockerclud and return it for Travis-CI 
echo "unit_tests_status = $unit_tests_status"
echo "Executing echo $unit_tests_status > stoqs/stoqs/tests/unit_tests_status..."
echo $unit_tests_status > stoqs/stoqs/tests/unit_tests_status
echo "Executing cat stoqs/stoqs/tests/unit_tests_status..."
cat stoqs/stoqs/tests/unit_tests_status
# For when we're confident that all tests will pass in CI - for now, rely on just unit tests
##exit $(($unit_tests_status + $loading_tests_status + $functional_tests_status))
exit $unit_tests_status

