#!/bin/bash
set -e

echo "STOQS: PGDATA = ${PGDATA}"

# pg_hba.conf
echo "STOQS: Moving pg_hba.conf to pg_hba.conf.bak ..."
mv ${PGDATA}/pg_hba.conf ${PGDATA}/pg_hba.conf.bak
echo "STOQS: Setting pg_hba.conf ..."
echo -e "\
# === STOQS - allow all private addresses that may be docker host\n\
host    all     stoqsadm     10.0.0.0/8     md5\n\
host    all     stoqsadm     172.16.0.0/12  md5\n\
host    all     stoqsadm     192.168.0.0/16 md5\n\
host    all     postgres     all            trust\n\
host    all     all          all            ident map=root_as_others\n\
local   all     all                         trust\n\
local   all     all                         peer map=root_as_others" > ${PGDATA}/pg_hba.conf

# pg_ident.conf
echo "STOQS: Moving pg_ident.conf to pg_ident.conf.bak ..."
mv ${PGDATA}/pg_ident.conf ${PGDATA}/pg_ident.conf.bak
echo "STOQS: Setting pg_ident.conf ..."
echo -e "\
# === STOQS ====================================================\n\
# MAPNAME       SYSTEM-USERNAME         PG-USERNAME\n\
root_as_others  root                    postgres" > ${PGDATA}/pg_ident.conf
