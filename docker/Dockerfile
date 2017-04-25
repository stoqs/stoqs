#####################################################################
# NOTE: preliminary, see README.md
#####################################################################

FROM mbari/stoqs-base:0.0.0

MAINTAINER Carlos Rueda <carueda@mbari.org>

#-------------------------------------------------------------------------------------------------------
# NOTE: In general, NO start of services at all to be included in the image itself, but to be done as
# part of lanching the corresponding containers and in combination with support from host server (e.g.,
# Apache server, along with for proxy-passes, etc.)
#-------------------------------------------------------------------------------------------------------


# Configure and start services
#RUN /usr/pgsql-9.4/bin/postgresql94-setup initdb &&\
#    /usr/bin/systemctl enable postgresql-9.4 &&\
#    /usr/bin/systemctl start postgresql-9.4 &&\
#    /sbin/chkconfig rabbitmq-server on &&\
#    /sbin/service rabbitmq-server start &&\
#    rabbitmqctl add_user stoqs stoqs &&\
#    rabbitmqctl add_vhost stoqs &&\
#    rabbitmqctl set_permissions -p stoqs stoqs ".*" ".*" ".*" &&\
#    /usr/bin/systemctl enable httpd.service &&\
#    /usr/bin/systemctl start httpd.service &&\
#    /usr/bin/systemctl enable memcached.service &&\
#    /usr/bin/systemctl start memcached.service

# Modify pg_hba.conf
RUN mv -f /var/lib/pgsql/9.4/data/pg_hba.conf /var/lib/pgsql/9.4/data/pg_hba.conf.bak &&\
    echo "\
# Allow user/password login\n\
host    all     stoqsadm     127.0.0.1/32   md5\n\
host    all     stoqsadm     10.0.2.0/24    md5\n\
local   all     all                         trust\n\
# Allow root to login as postgres (as travis-ci allows) - See also pg_ident.conf\n\
local   all     all                     peer map=root_as_others\n\
host    all     all     127.0.0.1/32    ident map=root_as_others" > /var/lib/pgsql/9.4/data/pg_hba.conf &&\
    cat /var/lib/pgsql/9.4/data/pg_hba.conf.bak >> /var/lib/pgsql/9.4/data/pg_hba.conf &&\
    cp /var/lib/pgsql/9.4/data/pg_ident.conf /var/lib/pgsql/9.4/data/pg_ident.conf.bak &&\
    echo "root_as_others  root            postgres" >> /var/lib/pgsql/9.4/data/pg_ident.conf

RUN su - postgres -c 'createuser -s stoqsadm' &&\
    su - postgres -c "/usr/pgsql-9.4/bin/pg_ctl -D /var/lib/pgsql/9.4/data -l logfile start"

# Create postgis database
# (NOTE: NO restart of postgresql-9.4 -- see note above)
RUN su - postgres -c "createdb postgis" &&\
    su - postgres -c "createlang plpgsql postgis" &&\
    su - postgres -c "psql -d postgis -f /usr/pgsql-9.4/share/contrib/postgis-2.1/postgis.sql" &&\
    su - postgres -c "psql -d postgis -f /usr/pgsql-9.4/share/contrib/postgis-2.1/spatial_ref_sys.sql" &&\
    su - postgres -c "psql -d postgis -f /usr/pgsql-9.4/share/contrib/postgis-2.1/postgis_comments.sql" &&\
    su - postgres -c "psql -d postgis -f /usr/pgsql-9.4/share/contrib/postgis-2.1/rtpostgis.sql" &&\
    su - postgres -c "psql -d postgis -f /usr/pgsql-9.4/share/contrib/postgis-2.1/raster_comments.sql" &&\
    su - postgres -c "psql -d postgis -f /usr/pgsql-9.4/share/contrib/postgis-2.1/topology.sql" &&\
    su - postgres -c "psql -d postgis -f /usr/pgsql-9.4/share/contrib/postgis-2.1/topology_comments.sql" &&\
    su - postgres -c "psql -c \"CREATE DATABASE template_postgis WITH TEMPLATE postgis;\"" &&\
    su - postgres -c "psql -c \"CREATE USER stoqsadm LOGIN PASSWORD 'stoqsadm';\"" &&\
    su - postgres -c "psql -c \"ALTER ROLE stoqsadm SUPERUSER;\"" &&\
    #/usr/bin/systemctl restart postgresql-9.4 &&\
    cd ..

# STOQS
RUN  mkdir -p /home/stoqsadm
COPY . /home/stoqsadm/
RUN export PATH="/usr/local/bin:$PATH" &&\
    cd /home/stoqsadm/stoqs  &&\
    virtualenv venv-stoqs  &&\
    source venv-stoqs/bin/activate &&\
    ./setup.sh

# Give stoqsadm ownership of everything in /home/stoqsadm
RUN chown -R stoqsadm /home/stoqsadm

# TODO
WORKDIR    /home/stoqsadm/
#ENTRYPOINT ["./???"]
#CMD        []
