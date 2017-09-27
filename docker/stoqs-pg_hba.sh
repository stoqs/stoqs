#!/bin/bash
set -e

echo "STOQS: PGDATA = ${PGDATA}"

# pg_hba.conf
echo "STOQS: Adjusting pg_hba.conf ..."
cp -p ${PGDATA}/pg_hba.conf ${PGDATA}/pg_hba.conf.bak
echo -e "\
# -------------------------\n\
# Allow user/password login\n\
host    all     stoqsadm     127.0.0.1/32   md5\n\
host    all     stoqsadm     10.0.2.0/24    md5\n\
local   all     all                         trust\n\
# Allow root to login as postgres (as travis-ci allows) - See also pg_ident.conf\n\
local   all     all                     peer map=root_as_others\n\
host    all     all     127.0.0.1/32    ident map=root_as_others\n" >> ${PGDATA}/pg_hba.conf

# pg_ident.conf
echo "STOQS: Adjusting pg_ident.conf ..."
cp -p ${PGDATA}/pg_ident.conf ${PGDATA}/pg_ident.conf.bak
echo -e "root_as_others  root                     postgres\n" >> ${PGDATA}/pg_ident.conf
