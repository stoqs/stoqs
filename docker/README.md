# Initial approach

**NOTE** preliminary

The overall idea is to have separate images, initially as follows:

| Docker file | Image | Purpose |
| ----------- | ----- | ------  |
| Dockerfile-base     | mbari/stoqs-base:0.0.0     | Base image with most of the OS level installations |
| Dockerfile-postgres | mbari/stoqs-postgres:0.0.0 | Configured Postgres server/database for STOQS use |
| Dockerfile-rabbitmq | mbari/stoqs-rabbitmq:0.0.0 | Configured Rabbitmq service |
| Dockerfile          | mbari/stoqs:0.0.0          |  STOQS system itself |


Initial build commands in the Docker files are basically a direct translation of (most of) provision.sh,
but it will surely also include commads from setup.sh, and maybe even from test.sh.


# Building


For the folloiwing, `cd` to the root directory of this repo.

To build the base image:

```
$ cd ..    #  i.e., root directory of this repo
$ docker build -f docker/Dockerfile-base -t "mbari/stoqs-base:0.0.0" .
```


To build the other images (at this point, Dockerfile basically contains all the other commands
from provision.sh after the ones in Dockerfile-base. This is so while initial experimentation is done.


```
$ docker build -f docker/Dockerfile -t "mbari/stoqs:0.0.0" .
```


# Publishing

When the time comes:

```
$ docker push mbari/stoqs-base:0.0.0
$ docker push mbari/stoqs-postgres:0.0.0
$ docker push mbari/stoqs-rabbitmq:0.0.0
$ docker push mbari/stoqs:0.0.0
```

