#!/bin/bash 
STOQSDIR=/opt/stoqshg
cd $STOQSDIR
source venv-stoqs/bin/activate
loaders/CANON/realtime/nps29_loadsep2014.py --append > loaders/CANON/realtime/nps29_loadsep2014.out 2>&1
