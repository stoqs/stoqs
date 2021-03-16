#!/bin/bash
# Can't Ctrl-C this script, instead Ctrl-Z and kill %1
while :
do
    docker stats --no-stream | grep "stoqs " | xargs echo
done
