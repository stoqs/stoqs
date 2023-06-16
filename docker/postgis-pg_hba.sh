#!/bin/bash
set -e

echo "STOQS: PGDATA = ${PGDATA}"

# pg_hba.conf
echo "STOQS: Moving pg_hba.conf to pg_hba.conf.bak ..."
mv ${PGDATA}/pg_hba.conf ${PGDATA}/pg_hba.conf.bak
echo "STOQS: Setting pg_hba.conf ..."
echo -e "\
# Allow all MBARI systems access - modify for your institution
host    all everyone,stoqsadm   134.89.0.0/16   scram-sha-256\n\
# === STOQS - allow all private addresses that may be docker host\n\
host    all stoqsadm,postgres   10.0.0.0/8      scram-sha-256\n\
host    all stoqsadm,postgres   172.16.0.0/12   scram-sha-256\n\
host    all stoqsadm,postgres   192.168.0.0/16  scram-sha-256\n\
host    all stoqsadm,postgres   127.0.0.1/8     scram-sha-256\n\
local   all all                                 trust" > ${PGDATA}/pg_hba.conf
