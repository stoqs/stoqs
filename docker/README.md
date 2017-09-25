# Dockerized STOQS

**NOTE: WIP**

## Images

Images involved toward a fully operational STOQS instance would be:

| Image                  | Purpose |
| -----                  | ------  |
| `rabbitmq:3          ` | RabbitMQ |
| `???/mapserver       ` | mapServer |
| `mbari/stoqs-postgres` | Configured Postgres server/database for STOQS use |
| `mbari/stoqs         ` | STOQS system itself |

The basic idea is that each image corresponds to a service that can be started/stopped/restarted
as a unit, and, of course, according to relevant dependencies (for example, the STOQS system
itself requires the Postgres service, while perhaps RabbitMQ is optional..).


## docker-compose.yml

Mainly as a preliminary mechanism to specify the orchestration of the corresponding containers
at run time (data volumes, ports, environment, etc),
I'm using Docker Compose.

For the tests I'm using `$PWD/vols/` as a base directory for volume mappings.

### RabbitMQ

- Using official image `rabbitmq:3` directly as the necessary settings 
  ("stoqs" vhost, username and password), as seen in provision.sh,
  can simply be indicated via environment variables in this entry.

- Port 4369 is exposed to the host as is, but can be adjusted as needed.
  Other ports can of course also be mapped as needed.

- No dependencies on other services.


### Postgres

TODO


### MapServer

TODO


### STOQS

TODO


## Building the images

```
$ cd docker/
```

### Base image

It seems that a key set of OS level libraries/tools could be captured in a base
image, `mbari/stoqs-base`.

```
$ docker build -f Dockerfile-base -t "mbari/stoqs-base:0.0.1" .
```

### Postgres image

- Base on the mbari/stoqs-postgres image

```
$ docker build -f Dockerfile-postgres -t "mbari/stoqs-postgres:0.0.1" .
```

### STOQS image

- Base on the mbari/stoqs-postgres image

```
$ cd ..    # i.e., cd to root directory of this repo
$ docker build -f docker/Dockerfile -t "mbari/stoqs:0.0.1" .
```


## Publishing the images

When the time comes:

```
$ docker push mbari/stoqs-base:0.0.1
$ docker push mbari/stoqs-postgres:0.0.1
$ docker push mbari/stoqs:0.0.1
```
