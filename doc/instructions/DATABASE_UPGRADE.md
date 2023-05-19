Instructions for Copying STOQS databases to a New Server
========================================================

Some upgrades of Postgres require a pg_dump/pg_restore process. Here are some steps to do that:

1. On the "from" server create .pgdump files of all the databases (this took 132 minutes in 2023):

    docker-compose run --rm stoqs stoqs/loaders/load.py --pg_dump

2. Copy the /opt/docker_stoqs_vols/pg_dumps/*.pg_dump files to the new "to" server:

    cd /opt/docker_stoqs_vols/
    scp -r pg_dumps/ kraken2:/tmp
    ssh stoqsadm@kraken2
    cp -r /tmp/pg_dumps /opt/docker_stoqs_vols/

3. On the "to" server configure and install the new version and start with "docker-compose up -d".

4. Run pg_restore script on the "to" server to load all of the .pg_dump files from /opt/docker_stoqs_vols/:

    cd /opt/stoqsgit/docker
    stoqs/tools/restore_pg_dumps.sh

--
Mike McCann
17 May 2023
