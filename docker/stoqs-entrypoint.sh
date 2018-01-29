#!/bin/bash

# On first entry into container create the default database
##if
##then
##fi

# Allow for psql execution (used for database creation) without a password
echo ${PGHOST}:\*:\*:postgres:${POSTGRES_PASSWORD} > /root/.pgpass &&\
    chmod 600 /root/.pgpass

SAVE_DATABASE_URL=$DATABASE_URL
DATABASE_URL=postgis://postgres:changeme@stoqs-postgis:5432/stoqs
export PYTHONPATH="${STOQS_SRVPROJ}:${PYTHONPATH}"

python stoqs/manage.py makemigrations stoqs --settings=config.settings.local --noinput
python stoqs/manage.py migrate --settings=config.settings.local --noinput --database=default

wget -q -N -O stoqs/loaders/Monterey25.grd http://stoqs.mbari.org/terrain/Monterey25.grd
##DATABASE_URL=$SAVE_DATABASE_URL
##python stoqs/loaders/loadTestData.py

##python stoqs/manage.py collectstatic --noinput  # Collect static files


# Prepare log files and start outputting logs to stdout
touch /srv/logs/gunicorn.log
touch /srv/logs/access.log
tail -n 0 -f /srv/logs/*.log &

# Start Gunicorn processes
##echo Starting Gunicorn.
##exec gunicorn stoqs.wsgi:application \
##    --pythonpath "${STOQS_SRVPROJ}:${PYTHONPATH}" \
##    --name stoqs \
##    --bind 0.0.0.0:8000 \
##    --workers 3 \
##    --log-level=info \
##    --log-file=/srv/logs/gunicorn.log \
##    --access-logfile=/srv/logs/access.log \
##    "$@"

# Taken from start_uwsgi.sh... Start the stoqs uWSGI application for nginx
# TODO: move env variables to setenv.sh
export STOQS_HOME=/srv
##export STATIC_ROOT=/usr/share/nginx/html/static
##export MEDIA_ROOT=/usr/share/nginx/html/media
##export DATABASE_URL="postgis://<dbuser>:<pw>@<host>:<port>/stoqs"
##export MAPSERVER_HOST="<mapserver_ip_address>"
##export STOQS_CAMPAIGNS="<comma_separated>,<databases>,<not_in_campaigns>"
##export SECRET_KEY="<random_sequence_of_impossible_to_guess_characters>"
##export GDAL_DATA=/usr/share/gdal

# Execute uwsgi for command-line testing
##uwsgi --ini stoqs/stoqs_uwsgi_docker.ini
uwsgi --http :9090 --wsgi-file stoqs/wsgi.py --master --processes 4 --threads 2

# Start development server
##stoqs/manage.py runserver 0.0.0.0:8000 --settings=config.settings.local
