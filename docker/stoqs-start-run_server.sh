#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

export MAPSERVER_SCHEME=http
export ALLOWED_HOSTS=stoqs
echo "Starting development server with DATABASE_URL=${DATABASE_URL}..."
# https://stackoverflow.com/a/72206748/1281657
python stoqs/manage.py runserver_plus --keep-meta-shutdown 0.0.0.0:8001 --settings=config.settings.local
