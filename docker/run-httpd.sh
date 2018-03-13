#!/bin/bash

# TODO rather simplistic at the moment.
# Possible reference: https://github.com/sclorg/httpd-container/blob/master/2.4/root/usr/bin/run-httpd

set -eu

exec httpd -D FOREGROUND $@
