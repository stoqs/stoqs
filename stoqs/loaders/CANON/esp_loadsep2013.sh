#!/bin/bash 
cd /opt/stoqshg/venv-stoqs/bin
source activate
cd /opt/stoqshg/loaders/CANON
python esp_loadsep2013.py -t > /tmp/esp_loadsep2013.log
date >> /tmp/esp_load.log
