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
if [ $OS = 'centos' ]
then
    echo 0 > /selinux/enforce

    echo Add epel, remi, and postgres repositories
    yum -y install wget git
    wget -q -N http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
    wget -q -N http://rpms.famillecollet.com/enterprise/remi-release-6.rpm
    rpm -Uvh remi-release-6*.rpm epel-release-6*.rpm
    curl -O http://yum.postgresql.org/9.3/redhat/rhel-6-x86_64/pgdg-centos93-9.3-1.noarch.rpm
    rpm -ivh pgdg*
    yum -y install postgresql93-server
    yum -y groupinstall "PostgreSQL Database Server 9.3 PGDG"

    echo Install Python 2.7 and its support tools pip and virtalenv
    yum groupinstall -y development
    yum install -y zlib-devel openssl-devel sqlite-devel bzip2-devel xz-libs
    wget -q -N http://www.python.org/ftp/python/2.7.9/Python-2.7.9.tar.xz
    xz -d -c Python-2.7.9.tar.xz | tar -xvf -
    cd Python-2.7.9
    ./configure
    make && make altinstall
    cd ..
    wget -q --no-check-certificate -N https://pypi.python.org/packages/source/s/setuptools/setuptools-1.4.2.tar.gz
    tar -xvf setuptools-1.4.2.tar.gz
    cd setuptools-1.4.2
    python2.7 setup.py install
    cd ..
    curl https://raw.githubusercontent.com/pypa/pip/master/contrib/get-pip.py | sudo /usr/local/bin/python2.7 -
    /usr/local/bin/pip install virtualenv

    yum -y install rabbitmq-server scipy mod_wsgi memcached python-memcached
    yum -y install graphviz-devel graphviz-python ImageMagick postgis2_93
    yum -y install freetype-devel libpng-devel giflib-devel libjpeg-devel gd-devel proj-devel
    yum -y install proj-nad proj-epsg curl-devel libxml2-devel libxslt-devel pam-devel readline-devel
    yum -y install python-psycopg2 libpqxx-devel geos geos-devel
    yum -y install gdal gdal-python gdal-devel mapserver mapserver-python libxml2 libxml2-python python-lxml python-pip python-devel gcc mlocate
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
wget -q -N http://download.osgeo.org/gdal/gdal-1.9.2.tar.gz        
tar xzf gdal-1.9.2.tar.gz
cd gdal-1.9.2
export PATH=$(pwd):$PATH
./configure --with-python
gmake && gmake install
cd ..

echo Build Mapserver
wget -q -N http://download.osgeo.org/mapserver/mapserver-6.4.1.tar.gz
tar xzf mapserver-6.4.1.tar.gz
cd mapserver-6.4.1
##export PATH="/usr/pgsql-9.3/bin:$PATH"
##sed -i '$a<900913> +proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs <>' /usr/share/proj/epsg    
mkdir build
cd build
cmake .. -DWITH_FRIBIDI=0 -DWITH_CAIRO=0 -DWITH_FCGI=0 -DCMAKE_PREFIX_PATH="/usr/local;/usr/pgsql-9.3"
make && make install
cp /usr/local/bin/mapserv /var/www/cgi-bin
cd ../..

echo Build database for locate command
updatedb

echo Configure and start services
service postgresql-9.3 initdb
chkconfig postgresql-9.3 on
service postgresql-9.3 start
chkconfig postgresql-9.3 on
/sbin/chkconfig rabbitmq-server on
/sbin/service rabbitmq-server start
rabbitmqctl add_user stoqs stoqs
rabbitmqctl add_vhost stoqs
rabbitmqctl set_permissions -p stoqs stoqs ".*" ".*" ".*"
chkconfig httpd on
/sbin/service httpd start
chkconfig memcached on
/sbin/service memcached start

echo Modifying pg_hba.conf
sed -i '1i host all all ::/0 trust' /var/lib/pgsql/9.3/data/pg_hba.conf
sed -i '1i #IPv6 local connections:' /var/lib/pgsql/9.3/data/pg_hba.conf
sed -i '1i host all all 10.0.2.0/24 trust' /var/lib/pgsql/9.3/data/pg_hba.conf
sed -i '1i #IPv4 local connections: ' /var/lib/pgsql/9.3/data/pg_hba.conf
sed -i '1i local all all trust' /var/lib/pgsql/9.3/data/pg_hba.conf
sed -i '1i #local is for Unix domain socket connections only' /var/lib/pgsql/9.3/data/pg_hba.conf
su - postgres -c 'createuser -s $USER'
su - postgres -c "/usr/pgsql-9.3/bin/pg_ctl -D /var/lib/pgsql/9.3/data -l logfile start"

echo Create postgis database
su - postgres -c "createdb postgis"
su - postgres -c "createlang plpgsql postgis"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/postgis.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/spatial_ref_sys.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/postgis_comments.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/rtpostgis.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/raster_comments.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/topology.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/topology_comments.sql"

echo Clone STOQS repo, create virtual environment 
cd ..
mkdir dev && cd dev
git clone https://github.com/MBARIMike/stoqs.git stoqsgit
cd stoqsgit
git checkout django17upgrade
export PATH="/usr/local/bin:$PATH"
virtualenv venv-stoqs
chown -R $USER ..

