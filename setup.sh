#!/bin/bash
# This script should be run whenever new packages are installed to ensure things are
# set for future runs, and of course to setup a new virtualenv

REQ="requirements.txt"
EGG_CACHE="wsgi/egg-cache"
VENV_NAME="venv-stoqs"

which virtualenv &>/dev/null
if [ $? -ne 0 ]; then
 echo "virtualenv command not found"
 echo "sudo easy_install virtualenv"
fi

if [ -d $VENV_NAME ]; then
 echo "virtualenv has already been created"
else
 virtualenv $VENV_NAME
 # Install GDAL in venv
 CONFIG=$(which gdal-config)
 if [ $? -ne 0 ]; then
   echo "gdal-config is not in PATH"
   rm -rf $VENV_NAME
   exit 1
 fi
 ln -s $CONFIG $VENV_NAME/bin/
fi
source $VENV_NAME/bin/activate
easy_install pip

if [ -f "$REQ" ]; then
 pip install -r $REQ
fi


pip freeze|grep -v pysqlite > $REQ
if [ ! -d $EGG_CACHE ]; then
 echo "Creating the egg cache"
 mkdir $EGG_CACHE
fi
sudo chown www-data $EGG_CACHE

sudo chgrp apache log
sudo chmod g+s log
touch log/django.log
chmod g+w log/django.log

# echo running a quick test to make sure things aren't broke
export PYTHONPATH=$(pwd)
export DJANGO_SETTINGS_MODULE=settings
python stoqs/views/management.py

