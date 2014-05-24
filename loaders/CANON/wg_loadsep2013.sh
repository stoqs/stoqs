#!/bin/bash 
cd /opt/stoqshg/venv-stoqs/bin
source activate
cd /opt/stoqshg/loaders/CANON
python wg_loadsep2013.py -t > /tmp/wg_loadsep2013.log
date >> /tmp/wg_load.log
