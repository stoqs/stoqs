#!/bin/bash
# Do database operations to create default database and load data for testing

psql -c "CREATE USER stoqsadm WITH PASSWORD 'CHANGEME';" -U postgres
psql -c "CREATE DATABASE template_postgis WITH TEMPLATE postgis;" -U postgres
psql -c "CREATE DATABASE stoqs owner=stoqsadm template=template_postgis;" -U postgres
psql -c "ALTER DATABASE stoqs SET TIMEZONE='GMT';" -U postgres
psql -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO stoqsadm;" -U postgres -d stoqs

cat /var/lib/pgsql/data/pg_hba.conf

# Assume in stoqsgit directory
export DJANGO_SECRET_KEY='SET_YOUR_OWN_IMPOSSIBLE_TO_GUESS_SECRET_KEY_ENVIRONMENT_VARIABLE'
export DATABASE_URL="postgis://stoqsadm:CHANGEME@127.0.0.1:5432/stoqs"
stoqs/manage.py syncdb --settings=config.local --noinput --database=default
stoqs/loaders/loadTestData.py
