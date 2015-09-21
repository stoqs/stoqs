#!/bin/bash 
cd /opt/stoqshg/venv-stoqs/bin
source activate
cd /opt/stoqshg/loaders/CANON
python m1_loadsep2013.py -t > /tmp/m1_loadsep2013.log
date >> /tmp/m1_load.log
