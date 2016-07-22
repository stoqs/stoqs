#!/bin/bash
cd /opt/stoqsgit_dj1.8/venv-stoqs/bin
source activate
cd /opt/stoqsgit_dj1.8/stoqs/loaders/LakeMichigan
python load_2016.py
