#!/bin/bash

set -e

source /root/.bashrc

cd /opt/stoqsgit
source venv-stoqs/bin/activate

stoqs/manage.py runserver 0.0.0.0:8000 --settings=config.settings.local
