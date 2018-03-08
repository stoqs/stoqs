#!/bin/bash

#####
# Postgres: wait until container is created
#
# $?                most recent foreground pipeline exit status
# > /dev/null 2>&1  get stderr while discarding stdout
#####
set -e
python ${STOQS_SRVHOME}/database-check.py > /dev/null 2>&1
while [[ $? != 0 ]] ; do
    sleep 5; echo "*** Waiting for postgres container ..."
    python3 ${STOQS_SRVHOME}/database-check.py > /dev/null 2>&1
done
set +e

# On first entry into container create the default database
##if
##then
##fi

# Allow for psql execution (used for database creation) without a password
echo ${PGHOST}:\*:\*:postgres:${POSTGRES_PASS} > /root/.pgpass &&\
    chmod 600 /root/.pgpass

SAVE_DATABASE_URL=$DATABASE_URL
DATABASE_URL=postgis://postgres:changeme@stoqs-postgis:5432/stoqs
export PYTHONPATH="${STOQS_SRVPROJ}:${PYTHONPATH}"

python ${STOQS_SRVPROJ}/manage.py makemigrations stoqs --settings=config.settings.local --noinput
python ${STOQS_SRVPROJ}/manage.py migrate --settings=config.settings.local --noinput --database=default

wget -q -N -O ${STOQS_SRVPROJ}/loaders/Monterey25.grd http://stoqs.mbari.org/terrain/Monterey25.grd
##DATABASE_URL=$SAVE_DATABASE_URL
##python stoqs/loaders/loadTestData.py

##python stoqs/manage.py collectstatic --noinput  # Collect static files


# Prepare log files and start outputting logs to stdout
touch ${STOQS_SRVHOME}/logs/access.log
tail -n 0 -f ${STOQS_SRVHOME}/logs/*.log &


# Taken from start_uwsgi.sh... Start the stoqs uWSGI application for nginx
# TODO: move env variables to .env
export STOQS_HOME=${STOQS_SRVHOME}
##export STATIC_ROOT=/usr/share/nginx/html/static
##export MEDIA_ROOT=/usr/share/nginx/html/media
##export DATABASE_URL="postgis://<dbuser>:<pw>@<host>:<port>/stoqs"
##export MAPSERVER_HOST="<mapserver_ip_address>"
##export STOQS_CAMPAIGNS="<comma_separated>,<databases>,<not_in_campaigns>"
##export SECRET_KEY="<random_sequence_of_impossible_to_guess_characters>"
##export GDAL_DATA=/usr/share/gdal

# Execute uwsgi for command-line testing
##uwsgi --ini ${STOQS_SRVPROJ}/stoqs_uwsgi_docker.ini
##uwsgi --http :9090 --wsgi-file ${STOQS_SRVPROJ}/wsgi.py --master --processes 4 --threads 2

# Start development server
${STOQS_SRVPROJ}/manage.py runserver 0.0.0.0:8000 --settings=config.settings.local

