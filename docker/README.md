# Dockerized STOQS

**WIP**

# Some TODOs/comments/questions

- `yum -y groups install "GNOME Desktop"` - perhaps unneeded?
- seems like most of setup.sh (with the `production` argument) could 
  actually be put in the base image:
  - `export LD_PRELOAD=/usr/lib64/libgdal.so.1`
  - Basemap installation
  - natgrid installation
- base image:
  - for now _installing_ nginx (as opposed to _extending_ some image) 
    due to the whole needed provisioning.
- stoqs image:
  - volume mappings?
  - environment variables?
- No really need to create any python virtualenv because the enviroment 
  is already containerized


## General approach

Images involved toward a fully operational STOQS instance would be:

- `rabbitmq:3`: RabbitMQ
- `???/mapserver`: mapServer
- `mbari/stoqs-postgis`: Configured Postgres/Postgis server/database for STOQS use
- `mbari/stoqs`: STOQS system itself

The basic idea is that each image corresponds to a service that can be started/stopped/restarted
as a unit, and, of course, according to relevant dependencies (for example, the STOQS system
itself requires the Postgres and MapServer services, while RabbitMQ is optional..).

## Building the mbari/stoqs* images

`setenv.sh` captures environment variables that are used in build/run commands below.

```shell
$ cd docker/
$ vim setenv.sh
$ source setenv.sh
```

### RabbitMQ image

- We directly use the official image `rabbitmq:3` as the necessary settings 
  ("stoqs" vhost, username and password), as seen in `provision.sh`,
  can simply be indicated via environment variables in this entry.

- At the moment only port 4369 is explicitly exposed to the host.

- No dependencies on other services.

- TODO: any needed data volume mappings?


### Postgis image

In this case we build an image on top of 
[mdillon/postgis:9.6](https://hub.docker.com/r/mdillon/postgis/)
to include the intialization of the database and the necessary 
adjustments to `pg_hba.conf` and `pg_hba_ident.conf`:

```
$ docker build -f Dockerfile-postgis -t "mbari/stoqs-postgis:0.0.1" .
```

**NOTE**: 

- In particular, the following line:

        host    all     stoqsadm     stoqs          md5
        
  is added to `pg_hba_conf` so the `stoqs` container (see below) 
  can access the database,  e.g., via `psql --host=stoqs-postgis ...`.
  
- The host `${STOQS_VOLS_DIR}/pgdata` directory is created upon first 
  execution of the command above. Subsequent runs will use the existing
  contents. So, keep this in mind in particular regarding any futher
  needed adjustments to `pg_hba.conf` and `pg_hba_ident.conf`.

### MapServer image

Currently playing with `geodata/mapserver:7.0.1` directly.


### STOQS base image

For convenience, we capture a key set of OS level libraries/tools 
in a base image, `mbari/stoqs-base`.

```
$ docker build -f Dockerfile-base -t "mbari/stoqs-base:0.0.1" .
```

This image also has nginx enabled as entry point.

### STOQS image

We build the STOQS image on top of `mbari/stoqs-base`:

In this case, `cd` to the root directory of the stoqs repository clone
as its contents are to be `COPY`'ed to the image:

```
$ cd ..    # i.e., 
$ docker build -f docker/Dockerfile-stoqs \
         --build-arg STOQSADM_PASS=${STOQSADM_PASS} \
         -t "mbari/stoqs:0.0.1" .
```


## Execution

**Docker Compose** 

I'm using docker-compose.yml as the central service specification for execution. 

With the images described above in place, the complete STOQS system can be lauched
as follows:

```shell
$ docker-compose up -d
```

### Basic tests

#### Postgis

Assumimg you have `psql` on your host:

```shell
$ psql -h localhost -p 5432 -U stoqsadm -d postgres
Password for user stoqsadm:
psql (9.6.2, server 9.6.3)
Type "help" for help.

postgres=> \d
               List of relations
 Schema |       Name        | Type  |  Owner
--------+-------------------+-------+----------
 public | geography_columns | view  | postgres
 public | geometry_columns  | view  | postgres
 public | raster_columns    | view  | postgres
 public | raster_overviews  | view  | postgres
 public | spatial_ref_sys   | table | postgres
(5 rows)
```

#### MapServer

- open "http://localhost:${STOQS_HOST_MAPSERVER_PORT}/" - 
  should show `No query information to decode. QUERY_STRING is set, but empty.`

- open "http://localhost:${STOQS_HOST_MAPSERVER_PORT}/?map=/usr/local/share/mapserver/examples/test.map&mode=map" - 
  should show the basic example provided in the docker image.

#### STOQS image

Basic:

- open "http://localhost:${STOQS_HOST_HTTP_PORT}/"
  - currently this shows the default nginx page.


Interaction with the database:

```shell
$ docker exec -it stoqs bash
(venv-stoqs) [root@a9bbe3f55dc6 stoqsgit]# psql -U stoqsadm -d postgres
Password for user stoqsadm:
psql (9.6.5, server 9.6.3)
Type "help" for help.

postgres=> \d
               List of relations
 Schema |       Name        | Type  |  Owner
--------+-------------------+-------+----------
 public | geography_columns | view  | postgres
 public | geometry_columns  | view  | postgres
 public | raster_columns    | view  | postgres
 public | raster_overviews  | view  | postgres
 public | spatial_ref_sys   | table | postgres
(5 rows)
```

Trying some of the instructions included in test.sh:

```shell
(venv-stoqs) [root@a9bbe3f55dc6 stoqsgit]# cd stoqs
(venv-stoqs) [root@a9bbe3f55dc6 stoqs]# ./manage.py makemigrations stoqs --settings=config.settings.ci --noinput
# (completed fine)
```

However:

```shell
(venv-stoqs) [root@a9bbe3f55dc6 stoqs]# ./manage.py migrate --settings=config.settings.ci --noinput --database=default
Traceback (most recent call last):
  File "/opt/stoqsgit/venv-stoqs/lib64/python3.6/site-packages/django/db/backends/utils.py", line 63, in execute
    return self.cursor.execute(sql)
psycopg2.ProgrammingError: permission denied to create extension "postgis"
HINT:  Must be superuser to create this extension.
```

TODO 
- actually, the "postgis" extension already exists.
  Are there still missing privileges to be given to stoqsadm?
 


Other exercises:

Adjusted the image so it launches django as entry point ..

Running this container directly:

```shell
$ docker run --name stoqs -it --rm \
         -p 8000:8000 \
         --net docker_default mbari/stoqs:0.0.1


Performing system checks...

System check identified no issues (0 silenced).
```

seems to work. I can open ???? and see



But not when launched via docker compose 
(note, I'm temporarily commenting out the rabbitqs service):

```shell
$ docker-compose up
Starting stoqs-mapserver ...
Starting stoqs-mapserver
Starting stoqs-postgis ...
Starting stoqs-mapserver ... done
Recreating stoqs ...
Recreating stoqs ... done
Attaching to stoqs-postgis, stoqs-mapserver, stoqs
stoqs-mapserver |  * Starting FastCGI wrapper fcgiwrap
stoqs-mapserver |    ...done.
stoqs exited with code 0
stoqs-postgis | LOG:  database system was interrupted; last known up at 2017-09-29 00:12:13 UTC
stoqs-postgis | LOG:  database system was not properly shut down; automatic recovery in progress
stoqs-postgis | LOG:  invalid record length at 0/2D64510: wanted 24, got 0
stoqs-postgis | LOG:  redo is not required
stoqs-postgis | LOG:  MultiXact member wraparound protections are now enabled
stoqs-postgis | LOG:  database system is ready to accept connections
stoqs-postgis | LOG:  autovacuum launcher started
```

That is, the stoqs container is launched but it exits immediately.


## Publishing the images

When the time comes:

```
$ docker push mbari/stoqs-postgis:0.0.1
$ docker push mbari/stoqs-base:0.0.1
$ docker push mbari/stoqs:0.0.1
```


## Some notes

Regarding the `firewall-cmd` commands in provision.sh, 
"You don't want to run a firewall inside the container,"
see https://github.com/CentOS/sig-cloud-instance-images/issues/2#issuecomment-57486012
