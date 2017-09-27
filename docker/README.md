# Dockerized STOQS

**NOTE: WIP**

# Some TODOs

- `yum -y groups install "GNOME Desktop"` - perhaps unneeded?
- seems like some pieces from setup.sh could be put in the base image:
  - `export LD_PRELOAD=...`  BTW check the actual path to ligdal.so.1
  - Basemap installation
  - natgrid installation
- stoqs image:
  - volume mappings
  - environment variables
- in general, "interlinking" in terms of the stoqs container able to
  interact with the database, rabbitmq, etc.


## Basic idea

Images involved toward a fully operational STOQS instance would be:

- `rabbitmq:3`: RabbitMQ
- `???/mapserver`: mapServer
- `mbari/stoqs-postgis`: Configured Postgres/Postgis server/database for STOQS use
- `mbari/stoqs`: STOQS system itself

The basic idea is that each image corresponds to a service that can be started/stopped/restarted
as a unit, and, of course, according to relevant dependencies (for example, the STOQS system
itself requires the Postgres service, while perhaps RabbitMQ is optional..).

## Building / running / testing

`setenv.sh` captures environment variables that are used in build/run commands below.

```shell
$ cd docker/
$ vim setenv.sh
$ source setenv.sh
```

For the tests I'm using `$PWD/vols/` as a base directory for volume mappings.


**Note**: Along with the direct `docker run ...` commands below I'm also 
capturing the component set-up in docker-compose.yml. 


### RabbitMQ

We simply run a `rabbitmq:3` container directly:

```shell
$ docker run --name stoqs-rabbitmq \
       -e RABBITMQ_DEFAULT_VHOST=${RABBITMQ_DEFAULT_VHOST} \
       -e RABBITMQ_DEFAULT_USER=${RABBITMQ_DEFAULT_USER} \
       -e RABBITMQ_DEFAULT_PASS=${RABBITMQ_DEFAULT_PASS} \
       -e STOQS_RABBITMQ_PORT=${STOQS_RABBITMQ_PORT} \
       -d rabbitmq:3
```

- Using official image `rabbitmq:3` directly as the necessary settings 
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

This image can be run as follows:

```shell
$ docker run --name stoqs-postgis \
         -e POSTGRES_PASSWORD=${POSTGRES_PASSWORD} \
         -e STOQSADM_PASS=${STOQSADM_PASS} \
         -v $PWD/vols/pgdata:/var/lib/postgresql/data \
         -d mbari/stoqs-postgis:0.0.1
```

**NOTE**: The host `$PWD/vols/pgdata` directory is created upon first 
execution of the command above. Subsequent runs will use the existing
contents. So, keep this in mind in particular regarding any futher
needed adjustments to `pg_hba.conf` and `pg_hba_ident.conf`.

### STOQS image

#### stoqs-base

For convenience, we capture a key set of OS level libraries/tools 
in a base image, `mbari/stoqs-base`.

```
$ docker build -f Dockerfile-base -t "mbari/stoqs-base:0.0.1" .
```

#### stoqs-mapserver

Then we build a MapServer image on top of `mbari/stoqs-base`:

```
$ docker build -f Dockerfile-mapserver -t "mbari/stoqs-mapserver:0.0.1" .
```

Basically, this image sets up MapServer and starts `httpd`.

A basic test:

```shell
$ docker run --name stoqs-mapserver -it --rm \
         -p ${STOQS_HOST_PORT}:80 \
         mbari/stoqs-mapserver:0.0.1
```

Then, in your browser:
- open http://localhost:${STOQS_HOST_PORT}/ - 
  should show the typical Apache "Testing 123.." default page  
- open http://localhost:${STOQS_HOST_PORT}/cgi-bin/mapserv -
  should show `No query information to decode. QUERY_STRING is set, but empty.`

#### stoqs

We then build the STOQS image on top of `mbari/stoqs-mapserver`:

```
$ cd ..    # i.e., cd to root directory of the stoqs repo
$ docker build -f docker/Dockerfile-stoqs -t "mbari/stoqs:0.0.1" .
```

Basic test (similar to the mapserver case above but with the stoqs image):

```shell
$ docker run --name stoqs -it --rm \
         -p ${STOQS_HOST_PORT}:80 \
         mbari/stoqs:0.0.1
```

Then, in your browser:
- open http://localhost:${STOQS_HOST_PORT}/ 
- open http://localhost:${STOQS_HOST_PORT}/cgi-bin/mapserv 


TO BE CONTINUED ...


## Publishing the images

When the time comes:

```
$ docker push mbari/stoqs-postgis:0.0.1
$ docker push mbari/stoqs-base:0.0.1
$ docker push mbari/stoqs-mapserver:0.0.1
$ docker push mbari/stoqs:0.0.1
```
