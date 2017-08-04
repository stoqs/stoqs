#!/bin/bash
#
# Remove all temporary files produced by operating the STOQS UI
#
HOME=/vagrant
PD=$HOME/dev/stoqsgit

# Section and ParameterParameter plots
rm -v $PD/stoqs/stoqs/media/sections/*.png
rm -v $PD/stoqs/stoqs/media/parameterparameter/*.png

# Unit test fixture data - Handy to have for being able to rerun tests
#rm -v $PD/stoqs/fixtures/*.json

# Mapserver .map files and log file
rm -vf /dev/shm/*.map
rm -vf /tmp/functional_tests_server.log
#rm -vf /tmp/mapserver_stoqshg.log       # Owned by apache, can't remove

# HTML templates
rm -v /tmp/*.html
