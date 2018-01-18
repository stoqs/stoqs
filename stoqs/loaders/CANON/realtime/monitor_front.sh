#!/bin/bash
cd /opt/stoqsgit/venv-stoqs/bin
source activate
cd /opt/stoqsgit/stoqs/loaders/CANON/realtime
export SLACKTOKEN=${SLACKTOCKEN}
python monitor_front.py -i /mbari/LRAUV/ -p tethys daphne makai opah aku ahi &
