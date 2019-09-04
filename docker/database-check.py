#! /usr/bin/python

"""
database-check.py

This script will check whether the postgres container is up and running. It'll
connect to the database with the credentials provided in the environment
variables.
"""

import os
import sys
import psycopg2


def database_check():
    dbname = os.environ.get('POSTGRES_DB')
    user = os.environ.get('STOQSADM_USER')
    password = os.environ.get('STOQSADM_PASSWORD')
    host = os.environ.get('STOQS_PGHOST')
    port = os.environ.get('STOQS_PGHOST_PORT')

    if user and password and host and port:
        # All O.K. - variables defined in environment
        pass
    else:
        # Likely being run by DockerHub Autotest - set with defaults
        user = 'stoqsadm'
        password = 'CHANGEME'
        host = 'stoqs-postgis'
        port = '5432'

    print("HOST: {host}:{port}, DB: {dbname}, USER: {user}".format(
        dbname=dbname,
        user=user,
        host=host,
        port=port))

    try:
        psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port)
    except Exception as e:
        print(str(e))
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    database_check()
