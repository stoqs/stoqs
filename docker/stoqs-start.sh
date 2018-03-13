#!/bin/bash

# Ensure that stoqs-postgis container is serving databases before continuing
python ${STOQS_SRVHOME}/database-check.py > /dev/null 2>&1
while [[ $? != 0 ]] ; do
    sleep 5; echo "*** Waiting for postgres container ..."
    python ${STOQS_SRVHOME}/database-check.py > /dev/null 2>&1
done

# Allow for psql execution (used for database creation) without a password
echo ${PGHOST}:\*:\*:postgres:${POSTGRES_PASSWORD} > /root/.pgpass &&\
    chmod 600 /root/.pgpass

##export DATABASE_URL=postgis://postgres:changeme@stoqs-postgis:5432/stoqs
##DATABASE_URL=postgis://stoqsadm:CHANGEME@stoqs-postgis:5432/stoqs
export PYTHONPATH="${STOQS_SRVPROJ}:${PYTHONPATH}"

# Monterey Bay bathymetry data is needed for default (and many other) database loads
if [ -f ${STOQS_SRVPROJ}/loaders/Monterey25.grd ]; then
    echo "Getting Monterey25.grd..."
    wget -q -N -O ${STOQS_SRVPROJ}/loaders/Monterey25.grd http://stoqs.mbari.org/terrain/Monterey25.grd
fi

# If default stoqs database doesn't exist then load it - also running the unit and functional tests
echo "Checking for presence of stoqs database..."
POSTGRES_DB=stoqs python ${STOQS_SRVHOME}/database-check.py
if [[ $? != 0 ]]; then
    echo "Creating default stoqs database and running tests..."
    ./test.sh changeme
fi

# Fire up stoqs web app
if [ "$PRODUCTION" == "false" ]; then
    echo "Starting development server..."
    ${STOQS_SRVPROJ}/manage.py runserver 0.0.0.0:8000 --settings=config.settings.local
else
    echo "Starting production server..."

    python stoqs/manage.py collectstatic --noinput  # Collect static files

    # Taken from start_uwsgi.sh... Start the stoqs uWSGI application for nginx
    # TODO: move env variables to .env

    # These are set in docker-compose.yml...
    export STOQS_HOME=${STOQS_SRVHOME}
    ##export STATIC_ROOT=/usr/share/nginx/html/static
    ##export MEDIA_ROOT=/usr/share/nginx/html/media
    ##export DATABASE_URL="postgis://<dbuser>:<pw>@<host>:<port>/stoqs"
    ##export MAPSERVER_HOST="<mapserver_ip_address>"
    ##export STOQS_CAMPAIGNS="<comma_separated>,<databases>,<not_in_campaigns>"
    ##export SECRET_KEY="<random_sequence_of_impossible_to_guess_characters>"
    ##export GDAL_DATA=/usr/share/gdal

    # Connect with nginx
    /usr/local/bin/uwsgi --emperor /etc/uwsgi/django-uwsgi.ini
fi
