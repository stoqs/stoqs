#! /bin/bash
if [[ -z "${NGINX_TMPL}" ]]; then
    echo "*** NGINX_TMPL not found in environment - setting it to nginx.tmpl"
    NGINX_TMPL=nginx.tmpl
fi
if [[ -z "${NGINX_SERVER_NAME}" ]]; then
    # Likely running in DockerHub Autotest via an MBARIMike push to stoqs, must export these
    echo "*** NGINX_SERVER_NAME not found in environment - setting it and NGINX_[CRT,KEY]_NAME to localhost"
    export NGINX_SERVER_NAME=localhost
    export NGINX_CRT_NAME=localhost
    export NGINX_KEY_NAME=localhost
fi
DOLLAR='$' envsubst < ${NGINX_TMPL} > /etc/nginx/nginx.conf

nginx -g "daemon off;"
