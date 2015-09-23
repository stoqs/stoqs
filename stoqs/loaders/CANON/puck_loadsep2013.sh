#!/bin/bash 
cd /opt/stoqshg/venv-stoqs/bin
source activate
cd /opt/stoqshg/loaders/CANON
python puck_loadsep2013.py -t > /tmp/puck_loadsep2013.log
date >> /tmp/puck_load.log
