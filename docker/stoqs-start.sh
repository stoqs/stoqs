#!/bin/bash

STOQS_SRVHOME=/srv
STOQS_SRVPROJ=/srv/stoqs

# Ensure that stoqs-postgis container is serving databases before continuing
POSTGRES_DB=postgres python ${STOQS_SRVHOME}/docker/database-check.py > /dev/null 2>&1
while [[ $? != 0 ]] ; do
    sleep 5; echo "*** Waiting for postgis container ..."
    POSTGRES_DB=postgres python ${STOQS_SRVHOME}/docker/database-check.py > /dev/null 2>&1
done

# Allow for psql execution (used for database creation) without a password
echo ${PGHOST}:\*:\*:postgres:${POSTGRES_PASSWORD} > /root/.pgpass &&\
    chmod 600 /root/.pgpass

export PYTHONPATH="${STOQS_SRVPROJ}:${PYTHONPATH}"

# Monterey Bay bathymetry data is needed for default (and many other) database loads
if [[ ! -e ${STOQS_SRVPROJ}/loaders/Monterey25.grd ]]; then
    echo "Getting Monterey25.grd..."
    wget -q -N -O ${STOQS_SRVPROJ}/loaders/Monterey25.grd http://stoqs.mbari.org/terrain/Monterey25.grd
fi

# Volume shared with nginx for writing Matplotlib-generated images
if [ "$PRODUCTION" == "true" ]; then
    echo "Checking for presence of ${MEDIA_ROOT}/sections..."
    if [[ ! -e ${MEDIA_ROOT}/sections ]]; then
        echo "Creating directories for image generation and serving by nginx..."
        mkdir -p ${MEDIA_ROOT}/sections ${MEDIA_ROOT}/parameterparameter
        chmod 733 ${MEDIA_ROOT}/sections ${MEDIA_ROOT}/parameterparameter
    fi
fi

echo "Checking for presence of directory for mapfiles: ${MAPFILE_DIR}"
if [[ ! -e ${MAPFILE_DIR} ]]; then
    echo "mkdir ${MAPFILE_DIR}"
    mkdir ${MAPFILE_DIR}
fi
# Ensure that shared volume for Mapserver map files is readable by nginx's uwsgi
chmod 777 ${MAPFILE_DIR}

# If default stoqs database doesn't exist then load it - also running the unit and functional tests
echo "Checking for presence of stoqs database..."
POSTGRES_DB=stoqs python ${STOQS_SRVHOME}/docker/database-check.py
if [[ $? != 0 ]]; then
    echo "Creating default stoqs database and running tests..."
    ./test.sh changeme load noextraload
fi

if [[ ! -z $CAMPAIGNS_MODULE ]]; then
    echo "Checking for presence of ${STOQS_SRVHOME}/stoqs/campaigns.py..."
    if [[ -e ${STOQS_SRVHOME}/stoqs/campaigns.py ]]; then
        echo "Warning: File ${STOQS_SRVHOME}/stoqs/campaigns.py exists!"
        echo "This may be a symbolic link to stoqs/mbari_campaigns.py for use in a development system."
        echo "File stoqs/campaigns.py must first be removed before running a Docker-based STOQS server."
        echo "Removing it for you..."
        /bin/rm ${STOQS_SRVHOME}/stoqs/campaigns.py
    fi
    echo "Copying ${STOQS_SRVHOME}/$CAMPAIGNS_MODULE to ${STOQS_SRVPROJ}/campaigns.py..."
    cp ${STOQS_SRVHOME}/$CAMPAIGNS_MODULE ${STOQS_SRVPROJ}/campaigns.py
fi

# Fire up stoqs web app
if [ "$PRODUCTION" == "false" ]; then
    export MAPSERVER_SCHEME=http
    echo "Starting development server with DATABASE_URL=${DATABASE_URL}..."
    ${STOQS_SRVPROJ}/manage.py runserver 0.0.0.0:8000 --settings=config.settings.local
else
    echo "Starting production server with DATABASE_URL=${DATABASE_URL}..."
    # For testing on port 8000 before certificate is in place make a security exception in your browser
    export MAPSERVER_SCHEME=https
    python stoqs/manage.py collectstatic --noinput -v 0 # Collect static files
    /usr/local/bin/uwsgi --emperor /etc/uwsgi/django-uwsgi.ini --pidfile=/tmp/uwsgi.pid
fi

