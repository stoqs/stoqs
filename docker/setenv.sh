#!/usr/bin/env bash
#
# Environment variables to be defined prior to running the containers:
#

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
