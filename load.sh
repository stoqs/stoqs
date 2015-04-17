#!/bin/bash
# Do database operations to create default database and load data for testing

su - postgres -c "psql -c "CREATE USER stoqsadm WITH PASSWORD 'CHANGEME';"
