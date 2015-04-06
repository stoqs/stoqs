#!/bin/bash
# This script should be run whenever new packages are installed to ensure things are
# set for future runs, and of course to setup a new virtualenv
pushd $(dirname $0)
HOMEDIR=$(pwd)
LOG_DIR="$HOMEDIR/log"
if [ $1 ]; then
    REQ="$HOMEDIR/$1"
else
    REQ="$HOMEDIR/requirements/requirements_django17upgrade.txt"
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

##EGG_CACHE="$HOMEDIR/wsgi/egg-cache"
PG_CONFIG=$(locate --regex "bin/pg_config$")
PATH=$(dirname $PG_CONFIG):$PATH

ln -s $CONFIG $VENV_DIR/bin/

# GDAL 1.9.1 pip install requires these environment variables
##export CPLUS_INCLUDE_PATH=/usr/include/gdal
##export C_INCLUDE_PATH=/usr/include/gdal
export LD_PRELOAD=/usr/lib64/libgdal.so.1


# Make sure weh have pip in the virtualenv
easy_install pip

# Install everything in $REQ
if [ -f "$REQ" ]; then
    pip install -r $REQ
    if [ $? -ne 0 ] ; then
        echo "*** pip install -r $REQ failed. ***"
        exit 1
    fi
fi

# Save config and give apache access
##pip freeze | grep -v pysqlite | grep -v ga_ows | grep -v matplotlib > requirements_installed.txt
##if [ ! -d $EGG_CACHE ]; then
##    echo "Creating the egg cache"
##    mkdir -p $EGG_CACHE
##fi
##sudo chown apache $EGG_CACHE
##mkdir -p $LOG_DIR
##sudo chgrp apache $LOG_DIR
##sudo chmod g+s $LOG_DIR
##touch $LOG_DIR/django.log
##chmod g+w log/django.log

popd

echo "$0 finished."

