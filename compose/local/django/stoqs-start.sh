#!/bin/bash

STOQS_SRVHOME=/app
STOQS_SRVPROJ=/app/stoqs

# Allow for psql execution (used for database creation) without a password
echo ${POSTGRES_HOST}:\*:\*:${POSTGRES_USER}:${POSTGRES_PASSWORD} > /root/.pgpass
echo ${POSTGRES_HOST}:\*:\*:stoqsadm:${STOQSADM_PASSWORD} >> /root/.pgpass
chmod 600 /root/.pgpass

# Wait for postgres to be ready
#echo "Waiting for postgres to be ready..."
#until psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d postgres -c '\q' 2>/dev/null; do
#  >&2 echo "Postgres is unavailable - sleeping"
#  sleep 1
#done
#>&2 echo "Postgres is up - continuing"

echo "Creating stoqsadm user in the database..."
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "${POSTGRES_DB}" -v ON_ERROR_STOP=1 <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'stoqsadm') THEN
            CREATE USER stoqsadm WITH PASSWORD '$STOQSADM_PASSWORD';
        END IF;
    END
    \$\$;
    ALTER USER stoqsadm CREATEDB;
    GRANT ALL PRIVILEGES ON DATABASE "$POSTGRES_DB" TO stoqsadm;
EOSQL

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
#POSTGRES_DB=stoqs python ${STOQS_SRVHOME}/docker/database-check.py
#if [[ $? != 0 ]]; then
#    echo "Creating default stoqs database and running tests..."
#    ./test.sh changeme load noextraload
#fi
./test.sh changeme load noextraload

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
