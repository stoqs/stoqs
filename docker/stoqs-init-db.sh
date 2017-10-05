#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE USER stoqsadm WITH PASSWORD '$STOQSADM_PASS';
    CREATE DATABASE stoqs owner=stoqsadm;
    GRANT ALL PRIVILEGES ON DATABASE stoqs TO stoqsadm;
    ALTER DATABASE stoqs SET TIMEZONE='GMT';
EOSQL
