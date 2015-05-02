#!/bin/bash 
cd /opt/stoqshg/venv-stoqs/bin
source activate
cd /opt/stoqshg/loaders/CANON
python oa_loadsep2013.py -t > /tmp/oa_loadsep2013.log
date >> /tmp/oa_load.log
