#!/usr/bin/env bash
#
# Environment variables to be defined prior to running the containers:
#

# STOQS_HOST: publically accesible host name, used for ALLOWED_HOSTS and MAPSERVER_HOST
# May want to be explicit if hostname command isn't accurate
export STOQS_HOST=`hostname`

# STOQS_VOLS_DIR: Base volume directory on the host
export STOQS_VOLS_DIR=${PWD}/tmp/stoqs_vols

# ___ RabbitMQ ___
export RABBITMQ_DEFAULT_VHOST=stoqs
export RABBITMQ_DEFAULT_USER=stoqs
export RABBITMQ_DEFAULT_PASS=stoqs

# STOQS_HOST_RABBITMQ_PORT: host port to map rabbitmq container's 4369 port
export STOQS_HOST_RABBITMQ_PORT=4369


# ___ Postgres/Postgis ___

# POSTGRES_PASSWORD: Desired password for the super user in Postgres
export POSTGRES_PASSWORD=changeme

# STOQSADM_PASS: Desired password for the 'stoqsadm' user in Postgres
export STOQSADM_PASS=changeme

# STOQS_HOST_POSTGRES_PORT: host port to map postgres container's 5432 port
# Default value set so as not to conflict with Vagrant VM's instance
export STOQS_HOST_POSTGRES_PORT=5433


# ___ MapServer ___

# STOQS_HOST_MAPSERVER_PORT: host port to map mapserver container's 80 port
export STOQS_HOST_MAPSERVER_PORT=7000
export MAPSERVER_HOST="${STOQS_HOST}:${STOQS_HOST_MAPSERVER_PORT}"

# ___ STOQS ___

# Django's database connection string
export STOQS_PGHOST=stoqs-postgis
export DATABASE_URL="postgis://stoqsadm:${STOQSADM_PASS}@${STOQS_PGHOST}:5432/stoqs"

# STOQS_HOST_DJANGO_PORT: host port to map container's django 8000 port
export STOQS_HOST_DJANGO_PORT=8002

# TODO remove, this is temporary..
# STOQS_HOST_HTTP_PORT: host port to map container's http server 80 port
export STOQS_HOST_HTTP_PORT=88

