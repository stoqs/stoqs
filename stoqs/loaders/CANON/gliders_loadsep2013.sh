#!/bin/bash 
cd /opt/stoqshg/venv-stoqs/bin
source activate
cd /opt/stoqshg/loaders/CANON
python gliders_loadsep2013.py -t > /tmp/glider_loadsep2013.log
date >> /tmp/glider_load.log
