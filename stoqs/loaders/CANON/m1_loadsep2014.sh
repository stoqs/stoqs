#!/bin/bash 
cd /opt/stoqshg
source /opt/stoqshg/venv-stoqs/bin/activate
/opt/stoqshg/loaders/CANON/m1_loadsep2014.py --append -v > /opt/stoqshg/loaders/CANON/m1_loadsep2014.out 2>&1
