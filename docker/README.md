# Dockerized STOQS

**NOTE: WIP**

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

For convenience, we capture a key set of OS level libraries/tools 
in a base image, `mbari/stoqs-base`.

```
$ docker build -f Dockerfile-base -t "mbari/stoqs-base:0.0.1" .
```

We then build the STOQS image on top of the above:

**WIP**

```
$ cd ..    # i.e., cd to root directory of this repo
$ docker build -f docker/Dockerfile-stoqs -t "mbari/stoqs:0.0.1" .
```


## Publishing the images

When the time comes:

```
$ docker push mbari/stoqs-postgis:0.0.1
$ docker push mbari/stoqs-base:0.0.1
$ docker push mbari/stoqs:0.0.1
```
