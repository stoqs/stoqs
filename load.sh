#!/bin/bash
# Do database operations to create default database and load data for testing

su - postgres -c "psql -c \"CREATE USER stoqsadm WITH PASSWORD 'CHANGEME';\""
su - postgres -c "psql -c \"CREATE DATABASE template_postgis WITH TEMPLATE postgis;\""
su - postgres -c "psql -c \"CREATE DATABASE stoqs owner=stoqsadm template=template_postgis;\""
su - postgres -c "psql -c \"ALTER DATABASE stoqs SET TIMEZONE='GMT';\""
su - postgres -c "psql -c -d stoqs \"GRANT ALL ON ALL TABLES IN SCHEMA public TO stoqsadm;\""

# Assume in stoqsgit directory
export DJANGO_SECRET_KEY='SET_YOUR_OWN_IMPOSSIBLE_TO_GUESS_SECRET_KEY_ENVIRONMENT_VARIABLE'
export DATABASE_URL="postgis://stoqsadm:CHANGEME@localhost:5432/stoqs"
stoqs/manage.py syncdb --settings=config.local --noinput --database=default
stoqs/loaders/loadTestData.py
