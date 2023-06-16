#!/usr/bin/env bash

##
# Run Nginx with the mapserver FastCGI service.
#

# Exit on any non-zero status.
trap 'exit' ERR
set -E

service fcgiwrap start
nginx -g "daemon off;"
