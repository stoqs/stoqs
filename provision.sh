#!/bin/bash
# Idempotent shell script to install system level prerequisites for STOQS
# Designed to be from Vagrantfile, where default USER is vagrant
if [ "$EUID" -ne 0 ]
then echo "Please run as root"
    exit 1
fi
if [ $1 ] 
then
    USER=$1
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

echo Step 1 / 18 - Disable Selinux and make Downloads directory in USER home
echo 0 > /selinux/enforce
cd /home/$USER
mkdir Downloads && cd Downloads
echo Step 2 / 18 - Add epel and remi repos
yum -y install wget
wget -q http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
wget -q http://rpms.famillecollet.com/enterprise/remi-release-6.rpm
rpm -Uvh remi-release-6*.rpm epel-release-6*.rpm
echo Step 3 / 18 - Install Git and Postgres
yum -y install git
curl -O http://yum.postgresql.org/9.3/redhat/rhel-6-x86_64/pgdg-centos93-9.3-1.noarch.rpm
rpm -ivh pgdg*
yum -y install postgresql93-server
service postgresql-9.3 initdb
chkconfig postgresql-9.3 on
service postgresql-9.3 start
yum -y groupinstall "PostgreSQL Database Server 9.3 PGDG"
chkconfig postgresql-9.3 on
echo Step 4 / 18 - Setup of the Postgres Enviroment
sed -i '1i host all all ::/0 trust' /var/lib/pgsql/9.3/data/pg_hba.conf
sed -i '1i #IPv6 local connections:' /var/lib/pgsql/9.3/data/pg_hba.conf
sed -i '1i host all all 10.0.2.0/24 trust' /var/lib/pgsql/9.3/data/pg_hba.conf
sed -i '1i #IPv4 local connections: ' /var/lib/pgsql/9.3/data/pg_hba.conf
sed -i '1i local all all trust' /var/lib/pgsql/9.3/data/pg_hba.conf
sed -i '1i #local is for Unix domain socket connections only' /var/lib/pgsql/9.3/data/pg_hba.conf
su - postgres -c 'createuser -s $USER'
su - postgres -c "/usr/pgsql-9.3/bin/pg_ctl -D /var/lib/pgsql/9.3/data -l logfile start"
echo Step 5 / 18 - Install Python 2.7 and its support tools pip and virtalenv
yum groupinstall -y development
yum install -y zlib-dev openssl-devel sqlite-devel bzip2-devel xz-libs
wget -q http://www.python.org/ftp/python/2.7.9/Python-2.7.9.tar.xz
xz -d -c Python-2.7.9.tar.xz | tar -xvf -
cd Python-2.7.9
./configure
make && make altinstall
cd ..
wget -q --no-check-certificate https://pypi.python.org/packages/source/s/setuptools/setuptools-1.4.2.tar.gz
tar -xvf setuptools-1.4.2.tar.gz
cd setuptools-1.4.2
python2.7 setup.py install
cd ..
curl https://raw.githubusercontent.com/pypa/pip/master/contrib/get-pip.py | sudo /usr/local/bin/python2.7 -
/usr/local/bin/pip install virtualenv
echo Step 6 / 18 - Install the Development Tools for Postgres
yum -y groupinstall 'Development Tools'
echo Step 7 / 18 - Download and install CMake
wget -q http://www.cmake.org/files/v2.8/cmake-2.8.3.tar.gz
tar xzf cmake-2.8.3.tar.gz
cd cmake-2.8.3
./configure --prefix=/opt/cmake
gmake
make
make install
mkdir -m 700 build
cd ..
echo Step 8 / 18 Install Python, Virtual Environment, & Rabbit Server
yum -y install rabbitmq-server scipy mod_wsgi memcached python-memcached
/sbin/chkconfig rabbitmq-server on
/sbin/service rabbitmq-server start
rabbitmqctl add_user stoqs stoqs
rabbitmqctl add_vhost stoqs
rabbitmqctl set_permissions -p stoqs stoqs ".*" ".*" ".*"
echo Step 9 / 18 - Install Graph for Mapping Software
yum -y install graphviz-devel
yum -y install graphviz-python
echo Step 10 / 18 - Install ImageMagick
yum -y install ImageMagick
echo Step 11 / 18 - Setup Postgis2
yum -y install postgis2_93
su - postgres -c "createdb postgis"
su - postgres -c "createlang plpgsql postgis"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/postgis.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/spatial_ref_sys.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/postgis_comments.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/rtpostgis.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/raster_comments.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/topology.sql"
su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/topology_comments.sql"
echo Step 12 / 18 - gdal
wget -q http://download.osgeo.org/gdal/gdal-1.9.2.tar.gz        
yum -y install gdal
cd cmake-2.8.3
export PATH=$(pwd):$PATH
./configure --with-python
gmake       
make
make install
cd ..
echo Step 13 / 18 - Map Server Libraries
yum -y install freetype-devel libpng-devel giflib-devel libjpeg-devel gd-devel proj-devel
yum -y install proj-nad proj-epsg curl-devel libxml2-devel libxslt-devel pam-devel readline-devel
wget -q http://download.osgeo.org/mapserver/mapserver-6.4.1.tar.gz
yum -y install python-psycopg2
export PATH="/usr/pgsql-9.3/bin:$PATH"
yum -y install libpqxx-devel
echo Step 14 / 18 - Epsg File Alteration
sed -i '$a<900913> +proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs <>' /usr/share/proj/epsg    
echo Step 15 / 18 - Gdal 
cd cmake-2.8.3
./configure --with-proj=/usr --with-ogr=/usr/local/bin/gdal-config --with-gdal=/usr/local/bin/gdal-config --with-wfs --with-wfsclient --with-wmsclient --with-postgis=/usr/pgsql-9.1/bin/pg_config
yum -y install gdal gdal-python gdal-devel mapserver mapserver-python libxml2 libxml2-python python-lxml python-pip python-devel gcc mlocate
ln -s /usr/pgsql-9.3/lib/libpq.so.5.4 /usr/pgsql-9.3/lib/libpq.so
gmake
make
make install
cd ..
updatedb
echo Step 16 / 18 - System Check and Service Restart
chkconfig httpd on
/sbin/service httpd start
chkconfig memcached on
/sbin/service memcached start
echo Step 17 / 18 - Clone STOQS, create virtual environment 
cd ..
mkdir dev && cd dev
git clone https://github.com/stoqs/stoqs.git stoqsgit
cd stoqsgit
git checkout django17upgrade
export PATH="/usr/local/bin:$PATH"
virtualenv venv-stoqs
chown -R $USER .

