#!/bin/bash
#
# Remove all temporary files produced by operating the STOQS UI
# Set STOQS_HOME environment variable before running, e.g.:
#   export STOQS_HOME=/vagrant/dev/stoqsgit
# or
#   export STOQS_HOME=/home/vagrant/dev/stoqsgit   # if not using NFS mount
#

# Section and ParameterParameter plots
rm -v $STOQS_HOME/stoqs/stoqs/media/sections/*.png
rm -v $STOQS_HOME/stoqs/stoqs/media/parameterparameter/*.png

# Unit test fixture data - Handy to have for being able to rerun tests
#rm -v $STOQS_HOME/stoqs/fixtures/*.json

# Mapserver .map files and log file
rm -vf /dev/shm/*.map
rm -vf /tmp/functional_tests_server.log
#rm -vf /tmp/mapserver_stoqshg.log       # Owned by apache, can't remove

# HTML templates
rm -v /tmp/*.html

# Loading tests fixture
rm stoqs/stoqs/fixtures/stoqs_load_test.json
