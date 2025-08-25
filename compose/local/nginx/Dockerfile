FROM docker.io/nginx:1.13

ARG NGINX_TMPL

# Add start script
ADD ./compose/local/nginx/nginx-start.sh /
RUN chmod +x nginx-start.sh

# Add nginx config file
ADD ./compose/local/nginx/${NGINX_TMPL} /${NGINX_TMPL}

# Add SSL certs to location specified in nginx.conf
ADD *.crt /etc/ssl/certs/
ADD *.key /etc/ssl/private/

CMD ["./nginx-start.sh"]
