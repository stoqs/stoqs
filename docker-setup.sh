#!/bin/bash

# Script adapted/simplified from original setup.sh for production env.
# Run by Dockerfile-stoqs from root directory.

set -e

HOMEDIR=$(pwd)

REQ="$HOMEDIR/requirements/production.txt"
echo "Using pip requirements file: $REQ"

VENV_NAME=$(basename $VIRTUAL_ENV)
VENV_DIR="$HOMEDIR/$VENV_NAME"

# Put link to gdal-config in venv/bin
CONFIG=$(which gdal-config)

PG_CONFIG=$(locate --regex "bin/pg_config$")
# Pick last path if multiple versions of Postgresql installed
PG_CONFIG=`echo $PG_CONFIG | grep -o '[^ ]*$'`
echo "Using PG_CONFIG=$PG_CONFIG"
PATH=$(dirname $PG_CONFIG):$PATH

ln -s $CONFIG $VENV_DIR/bin/

# GDAL 1.9.2 pip install requires this environment variable
export LD_PRELOAD=/usr/lib64/libgdal.so.1

# Install everything in $REQ
pip install -r $REQ

cd $HOMEDIR

# TODO temporarily downloaded locally to speed up initial set-up:
tar -xzf basemap-1.0.7.tar.gz --directory /tmp
tar -xzf natgrid-0.2.1.tar.gz --directory /tmp

# Required for plotting basemap in LRAUV plots
#-cd /tmp
echo Build and install Basemap
#-wget 'http://sourceforge.net/projects/matplotlib/files/matplotlib-toolkits/basemap-1.0.7/basemap-1.0.7.tar.gz'
#-tar -xzf basemap-1.0.7.tar.gz
cd /tmp/basemap-1.0.7
export GEOS_DIR=/usr/local
python3.6 setup.py install
#-cd ..

# NCAR's natgrid needed for contour plotting
#-wget http://sourceforge.net/projects/matplotlib/files/matplotlib-toolkits/natgrid-0.2/natgrid-0.2.1.tar.gz
#-tar -xzf natgrid-0.2.1.tar.gz
cd /tmp/natgrid-0.2.1
python3.6 setup.py install

echo "$0 finished."
