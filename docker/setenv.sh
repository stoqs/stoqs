#!/usr/bin/env bash
#
# Environment variables to be defined prior to running the containers:
#

# STOQS_VOLS_DIR: Base volume directory on the host
export STOQS_VOLS_DIR=/tmp/stoqs_vols

# ___ RabbitMQ ___
export RABBITMQ_DEFAULT_VHOST=stoqs
export RABBITMQ_DEFAULT_USER=stoqs
export RABBITMQ_DEFAULT_PASS=stoqs

# STOQS_RABBITMQ_PORT: host port to map rabbitmq container's 4369 port
export STOQS_RABBITMQ_PORT=4369


# ___ Postgres/Postgis ___

# POSTGRES_PASSWORD: Desired password for the super user in Postgres
export POSTGRES_PASSWORD=changeme

# STOQSADM_PASS: Desired password for the 'stoqsadm' user in Postgres
export STOQSADM_PASS=changeme

# STOQS_POSTGRES_PORT: host port to map postgres container's 5432 port
export STOQS_POSTGRES_PORT=5432


# ___ STOQS ___

# STOQS_HOST_PORT: host port to map container's httpd 80 port
export STOQS_HOST_PORT=80
