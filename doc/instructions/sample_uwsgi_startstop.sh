#!/bin/bash

# SAMPLE /etc/init.d/uwsgi start|stop script for CentOS 6

# uwsgi - Use uwsgi to run python and wsgi web apps.
#
# chkconfig: - 85 15
# description: Use uwsgi to run python and wsgi web apps.
# processname: uwsgi

unset DJANGO_SETTINGS_MODULE
NAME=uwsgi
DESC=uwsgi
PATH=/opt/stoqsgit:/sbin:/bin:/usr/sbin:/usr/bin
DAEMON=/usr/local/bin/uwsgi

OWNER=stoqsadm

test -x $DAEMON || exit 0

# Include uwsgi defaults if available
if [ -f /etc/default/uwsgi ] ; then
    . /etc/default/uwsgi
fi

set -e

get_pid() {
   if [ -f /var/run/$NAME.pid ]; then
       echo `cat /var/run/$NAME.pid`
   fi
}   


case "$1" in
 start)
    echo -n "Starting $DESC: "
       PID=$(get_pid)
       if [ -z "$PID" ]; then
           [ -f /var/run/$NAME.pid ] && rm -f /var/run/$NAME.pid

           touch /var/run/$NAME.pid                                         
           chown $OWNER /var/run/$NAME.pid
        su - $OWNER -pc /opt/stoqsgit_dj1.8/start_uwsgi_initd.sh
        echo "$NAME."
       fi

    ;;
 stop)
    echo -n "Stopping $DESC: "
       PID=$(get_pid)
       [ ! -z "$PID" ] && kill -s 3 $PID &> /dev/null
       if [ $? -gt 0 ]; then
           echo "was not running" 
           exit 1
       else 
        echo "$NAME."
           rm -f /var/run/$NAME.pid &> /dev/null
       fi
    ;;
 restart)
       $0 stop
       sleep 2
       $0 start
    ;;
 status)  
    killall -10 $DAEMON
    ;;
     *)  
        N=/etc/init.d/$NAME
        echo "Usage: $N {start|stop|restart|status}" >&2
        exit 1
        ;;
   esac
exit 0

