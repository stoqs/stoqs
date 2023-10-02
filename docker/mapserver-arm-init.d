#!/bin/sh
### BEGIN INIT INFO
# Provides:          fcgiwrap
# Required-Start:    $remote_fs
# Required-Stop:     $remote_fs
# Should-Start:
# Should-Stop:
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: FastCGI wrapper
# Description:       Simple server for running CGI applications over FastCGI
### END INIT INFO

PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

SPAWN_FCGI="/usr/bin/spawn-fcgi"
DAEMON="/usr/sbin/fcgiwrap"
NAME="fcgiwrap"
DESC="FastCGI wrapper"

PIDFILE="/var/run/$NAME.pid"

test -x $SPAWN_FCGI || exit 0
test -x $DAEMON || exit 0

# FCGI_APP Variables
FCGI_CHILDREN="1"
FCGI_SOCKET="/var/run/$NAME.socket"
FCGI_USER="www-data"
FCGI_GROUP="www-data"
# Socket owner/group (will default to FCGI_USER/FCGI_GROUP if not defined)
FCGI_SOCKET_OWNER="www-data"
FCGI_SOCKET_GROUP="www-data"

. /lib/lsb/init-functions

# Default options, these can be overriden by the information
# at /etc/default/$NAME
DAEMON_OPTS="-f"        # By default we redirect STDERR output from executed
                        # CGI through FastCGI, to disable this behaviour set
                        # DAEMON_OPTS to an empty value in the default's file

ENV_VARS="PATH='$PATH'" # We reset the environ for spawn-fcgi, but we use the
                        # contents of this variable as a prefix when calling it
                        # to export some variables (currently just the PATH)
DIETIME=10              # Time to wait for the server to die, in seconds
                        # If this value is set too low you might not
                        # let some servers to die gracefully and
                        # 'restart' will not work
QDIETIME=0.5            # The same as DIETIME, but a lot shorter for the
                        # stop case.

#STARTTIME=2            # Time to wait for the server to start, in seconds
                        # If this value is set each time the server is
                        # started (on start or restart) the script will
                        # stall to try to determine if it is running
                        # If it is not set and the server takes time
                        # to setup a pid file the log message might
                        # be a false positive (says it did not start
                        # when it actually did)

# Include defaults if available
if [ -f /etc/default/$NAME ] ; then
    . /etc/default/$NAME
fi

set -e

running_pid() {
# Check if a given process pid's cmdline matches a given name
    pid=$1
    name=$2
    [ -z "$pid" ] && return 1
    [ ! -d /proc/$pid ] &&  return 1
    cmd="$(cat /proc/$pid/cmdline | tr "\000" "\n"|head -n 1 |cut -d : -f 1)"
    # On Mac M1/2 arm cmdline="/usr/bin/qemu-x86_64/usr/sbin/fcgiwrap/usr/sbin/fcgiwrap-f"
    # Therefore we have this extraction of the name:
    cmd="$(cat /proc/$pid/cmdline | cut -d p -f 2,3 | cut -d - -f 1)"
    # Is this the expected server
    [ "$cmd" != "$name" ] && return 1
    return 0
}

running() {
# Check if the process is running looking at /proc
# (works for all users)
    # No pidfile, probably no daemon present
    [ ! -f "$PIDFILE" ] && return 1
    PIDS="$(cat "$PIDFILE")"
    for pid in $PIDS; do
      if [ -n "$pid" ]; then
        running_pid $pid $DAEMON && return 0 || true
      fi
    done
    return 1
}

start_server() {
    ARGS="-P $PIDFILE"
    # Adjust NUMBER of processes
    if [ -n "$FCGI_CHILDREN" ]; then
       ARGS="$ARGS -F '$FCGI_CHILDREN'"
    fi
    # Adjust SOCKET or PORT and ADDR
    if [ -n "$FCGI_SOCKET" ]; then
      ARGS="$ARGS -s '$FCGI_SOCKET'"
    elif [ -n "$FCGI_PORT" ]; then
      if [ -n "$FCGI_ADDR" ]; then
        ARGS="$ARGS -a '$FCGI_ADDR'"
      fi
      ARGS="$ARGS -p '$FCGI_PORT'"
    fi
    # Adjust user
    if [ -n "$FCGI_USER" ]; then
      ARGS="$ARGS -u '$FCGI_USER'"
      if [ -n "$FCGI_SOCKET" ]; then
        if [ -n "$FCGI_SOCKET_OWNER" ]; then
          ARGS="$ARGS -U '$FCGI_SOCKET_OWNER'"
        else
          ARGS="$ARGS -U '$FCGI_USER'"
        fi
      fi
    fi
    # Adjust group
    if [ -n "$FCGI_GROUP" ]; then
      ARGS="$ARGS -g '$FCGI_GROUP'"
      if [ -n "$FCGI_SOCKET" ]; then
        if [ -n "$FCGI_SOCKET_GROUP" ]; then
          ARGS="$ARGS -G '$FCGI_SOCKET_GROUP'"
        else
          ARGS="$ARGS -G '$FCGI_GROUP'"
        fi
      fi
    fi
    eval $(echo env -i $ENV_VARS $SPAWN_FCGI $ARGS -- $DAEMON $DAEMON_OPTS) \
        > /dev/null
    errcode="$?"
    return $errcode
}

stop_server() {
    # Force the process to die killing it manually
    [ ! -e "$PIDFILE" ] && return
    PIDS="$(cat "$PIDFILE")"
    for pid in $PIDS; do
      if running_pid $pid $DAEMON; then
        kill -15 $pid
        # Is it really dead?
        sleep "$QDIETIME"s
        if running_pid $pid $DAEMON; then
          kill -9 $pid
          sleep "$QDIETIME"s
          if running_pid $pid $DAEMON; then
              echo "Cannot kill $NAME (pid=$pid)!"
              exit 1
          fi
        fi
      fi
    done
    rm -f "$PIDFILE"
    if [ -n "$FCGI_SOCKET" ]; then
      rm -f "$FCGI_SOCKET"
    fi
}

case "$1" in
  start)
        log_daemon_msg "Starting $DESC" "$NAME"
        # Check if it's running first
        if running ;  then
            log_progress_msg "apparently already running"
            log_end_msg 0
            exit 0
        fi
        if start_server ; then
            # NOTE: Some servers might die some time after they start,
            # this code will detect this issue if STARTTIME is set
            # to a reasonable value
            [ -n "$STARTTIME" ] && sleep $STARTTIME # Wait some time
            if  running ;  then
                # It's ok, the server started and is running
                log_end_msg 0
            else
                # It is not running after we did start
                log_end_msg 1
            fi
        else
            # Either we could not start it
            log_end_msg 1
        fi
        ;;
  stop|force-stop)
        log_daemon_msg "Stopping $DESC" "$NAME"
        if running ; then
            # Only stop the server if we see it running
            errcode=0
            stop_server || errcode=$?
            log_end_msg $errcode
        else
            # If it's not running don't do anything
            log_progress_msg "apparently not running"
            log_end_msg 0
            exit 0
        fi
        ;;
  restart|force-reload)
        log_daemon_msg "Restarting $DESC" "$NAME"
        errcode=0
        stop_server || errcode=$?
        # Wait some sensible amount, some server need this
        [ -n "$DIETIME" ] && sleep $DIETIME
        start_server || errcode=$?
        [ -n "$STARTTIME" ] && sleep $STARTTIME
        running || errcode=$?
        log_end_msg $errcode
        ;;
  status)

        log_daemon_msg "Checking status of $DESC" "$NAME"
        if running ;  then
            log_progress_msg "running"
            log_end_msg 0
        else
            log_progress_msg "apparently not running"
            log_end_msg 1
            exit 1
        fi
        ;;
  # Use this if the daemon cannot reload
  reload)
        log_warning_msg "Reloading $NAME daemon: not implemented, as the daemon"
        log_warning_msg "cannot re-read the config file (use restart)."
        ;;
  *)
        N=/etc/init.d/$NAME
        echo "Usage: $N {start|stop|force-stop|restart|force-reload|status}" >&2
        exit 1
        ;;
esac

exit 0
