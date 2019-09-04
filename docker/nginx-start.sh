#! /bin/bash
if [[ -z "${NGINX_TMPL}" ]]; then
    NGINX_TMPL=nginx.tmpl
fi
if [[ -z "${NGINX_SERVER_NAME}" ]]; then
    NGINX_SERVER_NAME=localhost
fi

DOLLAR='$' envsubst < ${NGINX_TMPL} > /etc/nginx/nginx.conf

nginx -g "daemon off;"
