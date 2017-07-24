#!/bin/bash
cd /opt/stoqsgit_dj1.8/venv-stoqs/bin
source activate
cd /opt/stoqsgit_dj1.8/stoqs/loaders/CANON/realtime
export SLACKTOKEN=${SLACKTOCKEN}
python monitor_front.py -i /mbari/LRAUV/ -p tethys daphne makai opah aku ahi &
