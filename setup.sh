#!/bin/bash
# This script should be run whenever new packages are installed to ensure things are
# set for future runs, and of course to setup a new virtualenv
pushd $(dirname $0)
HOMEDIR=$(pwd)
LOG_DIR="$HOMEDIR/log"
if [ $1 ]; then
    REQ="$HOMEDIR/$1"
else
    REQ="$HOMEDIR/requirements.txt"
fi
echo "Using pip requirements file $1"

if [ -z $VIRTUAL_ENV ]; then
    echo "Need to be in your virtual environment."
    exit 1
else
    VENV_NAME=$(basename $VIRTUAL_ENV)
    VENV_DIR="$HOMEDIR/$VENV_NAME"
fi

# Put link to gdal-config in venv/bin
CONFIG=$(which gdal-config)
if [ $? -ne 0 ]; then
    echo "gdal-config is not in PATH"
    rm -rf $VENV_DIR
    exit 1
fi

PG_CONFIG=$(locate --regex "bin/pg_config$")
PATH=$(dirname $PG_CONFIG):$PATH

ln -s $CONFIG $VENV_DIR/bin/

# GDAL 1.9.2 pip install requires this environment variable
export LD_PRELOAD=/usr/lib64/libgdal.so.1


# Install everything in $REQ
if [ -f "$REQ" ]; then
    pip install -r $REQ
    if [ $? -ne 0 ] ; then
        echo "*** pip install -r $REQ failed. ***"
        exit 1
    fi
fi

popd

echo "$0 finished."

