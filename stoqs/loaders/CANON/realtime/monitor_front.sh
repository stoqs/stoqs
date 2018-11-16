#!/bin/bash
if [ -z "$STOQS_HOME" ]; then
  echo "Set STOQS_HOME variable first, e.g. STOQS_HOME=/src/stoqsgit"
  exit 1
fi
if [ -z "$DATABASE_URL" ]; then
  echo "Set DATABASE_URL variable first"
  exit 1
fi
cd "$STOQS_HOME/stoqs/loaders/CANON/realtime"
python monitor_front.py -i /mbari/LRAUV/  -s 'realtime/sbdlogs/2018' 'realtime/cell-logs' -p tethys daphne makai aku ahi opah
