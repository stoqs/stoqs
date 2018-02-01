#!/bin/sh
#
# To build STOQS docker images (Steps 1-3 are done in Vagrant STOQS install):
# 1. Install Docker
# 2. Install git
# 3. Clone the STOQS repo: git clone https://github.com/stoqs/stoqs.git stoqsgit

# 4. cd stoqsgit/docker
# 5. Edit .env to customize your installation
# 5. Execute this script: ./build.sh

docker_dir=`dirname $0`
pushd $docker_dir 

source ./.env

echo "Building mbari/stoqs-mapserver image..."
docker build -f Dockerfile-mapserver -t "mbari/stoqs-mapserver" .

echo "Building mbari/stoqs-postgis image..."
docker build -f Dockerfile-postgis -t "mbari/stoqs-postgis" .

pushd ..
echo "Building mbari/stoqs image..."
docker build -f docker/Dockerfile-stoqs -t "mbari/stoqs" .
popd

popd
