#!/bin/bash
#
# Remove all temporary files produced by operating the STOQS UI

PD=$HOME/dev/stoqsgit

# Section and ParameterParameter plots
rm -v $PD/stoqs/media/sections/*.png
rm -v $PD/stoqs/media/parameterparameter/*.png

# Mapserver .map files and log file
rm -vf /dev/shm/*.map
rm -vf /tmp/mapserver_stoqshg.log

# HTML templates
rm -v /tmp/*.html
