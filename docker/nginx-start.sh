#! /bin/bash
if [[ -z "${NGINX_TMPL}" ]]; then
    NGINX_TMPL=nginx.tmpl
fi
DOLLAR='$' envsubst < ${NGINX_TMPL} > /etc/nginx/nginx.conf

nginx -g "daemon off;"
