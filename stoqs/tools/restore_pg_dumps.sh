#!/bin/bash
#
# Loop through all .pg_dump files in backup location and create and
# restore databases.  To be used when transferring databases to a 
# new server.
# 
# 17 May 2023

for pg_dump_file in /opt/docker_stoqs_vols/pg_dumps/*.pg_dump
do
    db_alias=$(echo $pg_dump_file | cut -d/ -f5 | cut -d. -f1)
    echo "docker-compose run --rm postgis createdb -U postgres $db_alias"
    docker-compose run --rm postgis createdb -U postgres $db_alias
    echo "docker-compose run --rm postgis pg_restore -Fc -U postgres -d $db_alias < $pg_dump_file"
    docker-compose run --rm postgis pg_restore -Fc -U postgres -d $db_alias < $pg_dump_file
done

