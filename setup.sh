#!/bin/bash
# This script should be run whenever new packages are installed to ensure things are
# set for future runs, and of course to setup a new virtualenv

REQ="requirements.txt"
EGG_CACHE="wsgi/egg-cache"

which virtualenv &>/dev/null
if [ $? -ne 0 ]; then
  echo "virtualenv command not found"
  echo "sudo easy_install virtualenv"
fi
if [ -d venv-stoqs ]; then
  echo "virtualenv has already been created"
else
  virtualenv venv-stoqs

  # Setup gdal-config so we can install GDAL (if needed) in venv
  CONFIG=$(which gdal-config)
  if [ $? -ne 0 ]; then
    echo "gdal-config is not in PATH"

    ln -s $CONFIG venv-stoqs/bin/
  fi
fi
source venv-stoqs/bin/activate
easy_install pip
if [ -f "$REQ" ]; then
  pip install -r $REQ
fi
pip freeze > $REQ

# echo running a quick test to make sure things aren't broke
export PYTHONPATH=$(pwd)
export DJANGO_SETTINGS_MODULE=settings
python stoqs/views/management.py

