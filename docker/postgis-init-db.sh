#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE USER stoqsadm WITH PASSWORD '$STOQSADM_PASSWORD';
    CREATE DATABASE stoqsadm;
    GRANT ALL PRIVILEGES ON DATABASE stoqsadm TO stoqsadm;
EOSQL
