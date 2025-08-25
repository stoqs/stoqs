# FROM postgis/postgis:15-3.5-alpine
# For use from production_localhost.yml when developing on Mac M1/M2 Arm
# https://github.com/postgis/docker-postgis/issues/216#issuecomment-1763399631
FROM imresamu/postgis:15-3.4

COPY ./compose/production/postgres/maintenance /usr/local/bin/maintenance
RUN chmod +x /usr/local/bin/maintenance/*
RUN mv /usr/local/bin/maintenance/* /usr/local/bin \
    && rmdir /usr/local/bin/maintenance
