# Dockerized STOQS

**WIP**

Status:

- STOQS GUI running and exposed on host: http://localhost:8000/

- On the `stoqs` container:
 
        docker exec -it stoqs bash
 
   all of the following seem to complete Ok:

        cd stoqs/
        ./manage.py makemigrations stoqs --settings=config.settings.ci --noinput
        ./manage.py migrate --settings=config.settings.ci --noinput --database=default
        wget -q -N -O loaders/Monterey25.grd http://stoqs.mbari.org/terrain/Monterey25.grd
        loaders/loadTestData.py

- However, if trying the above with the `stoqsadm` username, that is, with
  `DATABASE_URL=postgis://stoqsadm:changeme@stoqs-postgis:5432/stoqs`,
  then errors like `... FATAL:  Ident authentication failed for user "stoqsadm"`
  occur.

- NOTE: creating a stoqs/mapserver image (based on geodata/mapserver:7.0.1) 
only to proxy `/cgi-bin/mapserv` to `/`. 
That is, geodata/mapserver:7.0.1 sets the mapserver endpoint to simply `/`;
however, various STOQS resources add `/cgi-bin/mapserv` to the 
`MAPSERVER_HOST` setting.
Suggestion here would be to let the `MAPSERVER_HOST` to include any path
for the actual mapserver endpoint.  

# Some comments/questions/TODOs

- `yum -y groups install "GNOME Desktop"` - perhaps unneeded?
- base image:
  - for now _installing_ nginx (as opposed to _extending_ some image) 
    due to the whole needed provisioning.
  - includes basically what `setup.sh production` does, that is:
    - pip3.6 install -r requirements/production.txt
    - Basemap installation
    - natgrid installation
- stoqs image:
  - Note: no python virtualenv used as the environment is already containerized
  - TODO: any other volume mappings (besides the mapserver one)?
  - TODO: any additional environment variables?


## General approach

Images involved toward a fully operational STOQS instance would be:

- `rabbitmq:3`: RabbitMQ
- `???/mapserver`: MapServer
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

- The host `${STOQS_VOLS_DIR}/pgdata` directory is created upon first 
  execution of the command above. Subsequent runs will use the existing
  contents. So, keep this in mind in particular regarding any futher
  needed adjustments to `pg_hba.conf` and `pg_hba_ident.conf`.

### MapServer image

Currently playing with `geodata/mapserver:7.0.1` directly.
(NOTE: actually an adjusted one, see above)


### STOQS base image

We capture the whole set of OS level libraries/tools, as well
as all production requirements (basically what `setup.sh production` does) 
in a base image, `mbari/stoqs-base`.

The `docker build` command must be executed from the parent directory:

```
$ docker build -f docker/Dockerfile-base -t "mbari/stoqs-base:0.0.1" .
```

This image also has nginx enabled as entry point.

### STOQS image

We build the STOQS image on top of `mbari/stoqs-base`:

Also in this case, make sure to execute `docker build` from the parent directory:

```
$ docker build -f docker/Dockerfile-stoqs \
         --build-arg STOQS_HOST=${STOQSADM_HOST} \
         --build-arg MAPSERVER_HOST=${MAPSERVER_HOST} \
         --build-arg DATABASE_URL=${DATABASE_URL} \
         -t "mbari/stoqs" .
```

The entry point in this image launches the Django application in development mode.

TODO configure the STOQS app on the inherited nginx endpoint.


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

Assuming you have `psql` on your host:

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

- open "http://localhost:${STOQS_HOST_DJANGO_PORT}/"
  shows the STOQS GUI 
  (currently with an empty Campaigns table)
  
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
