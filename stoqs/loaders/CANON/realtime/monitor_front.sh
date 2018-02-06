#!/bin/bash
cd /opt/stoqsgit/venv-stoqs/bin
source activate
cd /opt/stoqsgit/stoqs/loaders/CANON/realtime
export SLACKTOKEN=${SLACKTOCKEN}
python monitor_front.py -i /mbari/LRAUV/  -s 'realtime/sbdlogs/2018' 'realtime/cell-logs' -p tethys daphne makai &
