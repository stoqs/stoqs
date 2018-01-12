Building Docker Images for STOQS
--------------------------------

The Docker images for STOQS can be built from a Vagrant VM or directly from 
a git clone if the host OS has Docker installed.
`setenv.sh` captures environment variables that are used in build/run commands below.

```shell
cd docker/
vim setenv.sh
source setenv.sh

sudo docker build -f Dockerfile-postgis -t "mbari/stoqs-postgis" .

cd ..
sudo docker build -f docker/Dockerfile-stoqs -t "mbari/stoqs" .

# Alternatively... Do we need to set these environment variables at build time?
sudo docker build -f docker/Dockerfile-stoqs \
         --build-arg STOQS_HOST=${STOQS_HOST} \
         --build-arg MAPSERVER_HOST=${MAPSERVER_HOST} \
         --build-arg DATABASE_URL=${DATABASE_URL} \
         -t "mbari/stoqs" .
```

With the images described above in place, the complete STOQS system can be lauched
as follows:

```shell
cd docker
sudo -E docker-compose up -d
```

Bringing the system up the first time should run the test.sh script which populates
the default database and runs a set of unit and functional tests.  Should this happen
as part of the build as it is a one time operation?  However, the test.sh script
cannot be run before the stoqs-postgis and stoqs-mapserver containers are started.

The stoqs-nginx container is needed for production; test.sh uses just the development
server.  How is both tesiting and production done in Docker?


Test the production server by visiting http://<host>.

Push to Docker Hub
------------------

```shell
sudo docker push mbari/stoqs-postgis
sudo docker push mbari/stoqs-base
sudo docker push mbari/stoqs
```

