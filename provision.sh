#!/bin/bash
# Idempotent shell script to install system level prerequisites for STOQS
# Designed to be from Vagrantfile, where default USER is vagrant
# Usage: provision.sh centos vagrant (default) -or- provision.sh ubuntu
if [ "$EUID" -ne 0 ]
then echo "Please run as root"
    exit 1
fi

if [ $1 ]
then
    OS=$1
else
    OS='centos'
fi      

if [ $2 ] 
then
    USER=$2
else
    USER='vagrant'
fi
if id -u "$USER" >/dev/null 2>&1; 
then
    echo "user $USER exists"
else
    echo "user $USER does not exist"
    exit 1
fi

cd /home/$USER
mkdir Downloads && cd Downloads

# OS specific provisioning
# TODO: Add stanza for other OSes, e.g. 'ubuntu'
if [ $OS = 'centos' ]
then
    echo Disable SELinux
    sed -i 's/SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config
    echo 0 > /selinux/enforce

    echo Add epel, remi, and postgres repositories
    yum -y install wget git
    wget -q -N http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
    wget -q -N http://rpms.famillecollet.com/enterprise/remi-release-6.rpm
    rpm -Uvh remi-release-6*.rpm epel-release-6*.rpm
    curl -sS -O http://yum.postgresql.org/9.4/redhat/rhel-6-x86_64/pgdg-centos94-9.4-1.noarch.rpm > /dev/null
    rpm -ivh pgdg*
    yum -y install postgresql94-server
    yum -y groupinstall "PostgreSQL Database Server 9.4 PGDG"

    echo Install Python 2.7 and its support tools pip and virtalenv
    yum groupinstall -y development
    yum install -y zlib-devel openssl-devel sqlite-devel bzip2-devel xz-libs firefox
    wget -q -N http://www.python.org/ftp/python/2.7.9/Python-2.7.9.tar.xz
    xz -d -c Python-2.7.9.tar.xz | tar -xvf -
    cd Python-2.7.9
    ./configure
    make && make altinstall
    cd ..
    wget -q --no-check-certificate -N https://pypi.python.org/packages/source/s/setuptools/setuptools-1.4.2.tar.gz
    tar -xvf setuptools-1.4.2.tar.gz
    cd setuptools-1.4.2
    /usr/local/bin/python2.7 setup.py install
    cd ..
    curl -sS https://raw.githubusercontent.com/pypa/pip/master/contrib/get-pip.py | sudo /usr/local/bin/python2.7 - > /dev/null
    /usr/local/bin/pip install virtualenv

    yum -y install rabbitmq-server scipy mod_wsgi memcached python-memcached
    yum -y install graphviz-devel graphviz-python ImageMagick postgis2_94
    yum -y install freetype-devel libpng-devel giflib-devel libjpeg-devel gd-devel proj-devel
    yum -y install proj-nad proj-epsg curl-devel libxml2-devel libxslt-devel pam-devel readline-devel
    yum -y install python-psycopg2 libpqxx-devel geos geos-devel hdf hdf-devel freetds-devel postgresql-devel
    yum -y install gdal gdal-python gdal-devel mapserver mapserver-python libxml2 libxml2-python python-lxml python-pip python-devel gcc mlocate
    yum -y install scipy blas blas-devel lapack lapack-devel GMT
fi

# Commands that work on any *nix

echo Download and install CMake
wget -q -N http://www.cmake.org/files/v2.8/cmake-2.8.3.tar.gz
tar xzf cmake-2.8.3.tar.gz
cd cmake-2.8.3
./configure --prefix=/opt/cmake
gmake && gmake install
cd ..

echo Build and install gdal
wget -q -N http://download.osgeo.org/gdal/2.0.0/gdal-2.0.0.tar.gz        
tar xzf gdal-2.0.0.tar.gz
cd gdal-2.0.0
export PATH=$(pwd):$PATH
./configure --with-python
gmake && gmake install
cd ..

echo Build and install Mapserver
wget -q -N http://download.osgeo.org/mapserver/mapserver-6.4.1.tar.gz
tar xzf mapserver-6.4.1.tar.gz
cd mapserver-6.4.1
mkdir build
cd build
/opt/cmake/bin/cmake .. -DWITH_FRIBIDI=0 -DWITH_CAIRO=0 -DWITH_FCGI=0 -DCMAKE_PREFIX_PATH="/usr/local;/usr/pgsql-9.4"
make && make install
cp /usr/local/bin/mapserv /var/www/cgi-bin
echo "/etc/ld.so.conf.d/mapserver.conf" > /etc/ld.so.conf.d/mapserver.conf
ldconfig
cp /etc/sysconfig/httpd /etc/sysconfig/httpd.bak
cat <<EOT >> /etc/sysconfig/httpd
# Needed for mapserv in /var/www/cgi-bin
LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib64
export LD_LIBRARY_PATH
EOT
cd ../..

echo Build database for locate command
updatedb

echo Configure and start services
service postgresql-9.4 initdb
chkconfig postgresql-9.4 on
service postgresql-9.4 start
chkconfig postgresql-9.4 on
/sbin/chkconfig rabbitmq-server on
/sbin/service rabbitmq-server start
rabbitmqctl add_user stoqs stoqs
rabbitmqctl add_vhost stoqs
rabbitmqctl set_permissions -p stoqs stoqs ".*" ".*" ".*"
chkconfig httpd on
/sbin/service httpd start
chkconfig memcached on
/sbin/service memcached start

echo Modify pg_hba.conf
mv -f /var/lib/pgsql/9.4/data/pg_hba.conf /var/lib/pgsql/9.4/data/pg_hba.conf.bak
cat <<EOT > /var/lib/pgsql/9.4/data/pg_hba.conf
# Allow user/password login
host    all     stoqsadm     127.0.0.1/32   md5
host    all     stoqsadm     10.0.2.0/24    md5
host    all     vagrant      127.0.0.1/32   trust
local   all     all                         trust
# Allow root to login as postgres (as travis-ci allows) - See also pg_ident.conf
local   all     all                     peer map=root_as_others
host    all     all     127.0.0.1/32    ident map=root_as_others
EOT
cat /var/lib/pgsql/9.4/data/pg_hba.conf.bak >> /var/lib/pgsql/9.4/data/pg_hba.conf
cp /var/lib/pgsql/9.4/data/pg_ident.conf /var/lib/pgsql/9.4/data/pg_ident.conf.bak
echo "root_as_others  root            postgres" >> /var/lib/pgsql/9.4/data/pg_ident.conf

su - postgres -c 'createuser -s $USER'
su - postgres -c "/usr/pgsql-9.4/bin/pg_ctl -D /var/lib/pgsql/9.4/data -l logfile start"

echo Create postgis database and restart postgresql-9.4
su - postgres -c "createdb postgis"
su - postgres -c "createlang plpgsql postgis"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.4/share/contrib/postgis-2.1/postgis.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.4/share/contrib/postgis-2.1/spatial_ref_sys.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.4/share/contrib/postgis-2.1/postgis_comments.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.4/share/contrib/postgis-2.1/rtpostgis.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.4/share/contrib/postgis-2.1/raster_comments.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.4/share/contrib/postgis-2.1/topology.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.4/share/contrib/postgis-2.1/topology_comments.sql"
su - postgres -c "psql -c \"CREATE DATABASE template_postgis WITH TEMPLATE postgis;\""
su - postgres -c "psql -c \"CREATE USER vagrant LOGIN PASSWORD 'vagrant';\""
su - postgres -c "psql -c \"ALTER ROLE vagrant SUPERUSER;\""
service postgresql-9.4 restart

echo Clone STOQS repo from https://github.com/stoqs/stoqs.git. See CONTRIBUTING for how to clone from your fork.
cd ..
mkdir dev && cd dev
git clone https://github.com/stoqs/stoqs.git stoqsgit
cd stoqsgit
git checkout django17upgrade
export PATH="/usr/local/bin:$PATH"
virtualenv venv-stoqs
chown -R $USER ..
chown -R $USER /home/$USER/Downloads

echo Configuring vim edit environment
cat <<EOT > /home/$USER/.vimrc
:set tabstop=4
:set expandtab
:set shiftwidth=4
EOT

