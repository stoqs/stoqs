#!/bin/bash
# Idempotent shell script to install system level prerequisites for STOQS.
# Designed to be run from Vagrantfile, where default USER is vagrant.
# Usage: provision.sh centos7 vagrant (default)
if [ "$EUID" -ne 0 ]
then echo "Please run as root"
    exit 1
fi

if [ $1 ]
then
    OS=$1
else
    OS='centos7'
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

# Initial package installs needed for building packages from source
# TODO: Add stanza for other OSes, e.g. 'ubuntu'
if [ $OS = 'centos7' ]
then
    echo Disable SELinux
    sed -i 's/SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config
    mkdir /selinux
    echo 0 > /selinux/enforce

    echo Add epel, remi, and postgres repositories
    yum makecache fast
    yum -y install wget git
    yum -y install epel-release
    yum repolist
    wget -q -N http://rpms.famillecollet.com/enterprise/remi-release-7.rpm
    rpm -Uvh remi-release-7*.rpm
    wget -q -N http://yum.postgresql.org/9.4/redhat/rhel-7-x86_64/pgdg-centos94-9.4-3.noarch.rpm
    if [ $? -ne 0 ] ; then
        echo "*** Provisioning for STOQS failed. RPM for specified PostgreSQL not found. ***"
        echo "Check http://yum.postgresql.org/9.4/redhat/rhel-7-x86_64/ and update provision.sh."
        exit 1
    fi
    rpm -ivh pgdg*
    yum groupinstall -y "Development Tools"

    echo Install Python 2.7 and its support tools pip and virtalenv
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
    /usr/local/bin/python2.7 setup.py install
    cd ..
    curl -sS https://bootstrap.pypa.io/get-pip.py | sudo /usr/local/bin/python2.7 - > /dev/null
    /usr/local/bin/pip install virtualenv

    echo Install package prerequisites for NetCDF4
    yum -y install curl-devel hdf5 hdf5-devel
fi

echo Build and install geos
echo '/usr/local/lib' >> /etc/ld.so.conf
wget -q -N http://download.osgeo.org/geos/geos-3.6.0.tar.bz2
tar -xjf geos-3.6.0.tar.bz2
cd geos-3.6.0
./configure
make -j 2 && make install
ldconfig
cd ..

echo Build and install NetCDF4
wget ftp://ftp.unidata.ucar.edu/pub/netcdf/netcdf-4.4.1.tar.gz
tar -xzf netcdf-4.4.1.tar.gz
cd netcdf-4.4.1
./configure
make -j 2 && sudo make install
cd ..
export LD_LIBRARY_PATH=/usr/local/lib
wget ftp://ftp.unidata.ucar.edu/pub/netcdf/netcdf-fortran-4.4.4.tar.gz
tar -xzf netcdf-fortran-4.4.4.tar.gz
cd netcdf-fortran-4.4.4
./configure
make -j 2 && sudo make install
cd ..

echo Build and install gdal
wget -q -N http://download.osgeo.org/gdal/2.1.2/gdal-2.1.2.tar.gz        
tar -xzf gdal-2.1.2.tar.gz
cd gdal-2.1.2
export PATH=$(pwd):$PATH
./configure --prefix=/usr/local
gmake -j 2 && gmake install
cd ..

# TODO: Add stanza for other OSes, e.g. 'ubuntu'
if [ $OS = 'centos7' ]
then
    yum -y install postgresql94-server
    yum -y groupinstall "PostgreSQL Database Server 9.4 PGDG"

    echo Put geckodriver in /usr/local/bin
    pushd /usr/local/bin
    wget -q -N https://github.com/mozilla/geckodriver/releases/download/v0.11.1/geckodriver-v0.11.1-linux64.tar.gz 
    tar -xzf geckodriver-v0.11.1-linux64.tar.gz
    popd

    yum -y install deltarpm rabbitmq-server scipy mod_wsgi memcached python-memcached
    yum -y install graphviz-devel graphviz-python ImageMagick postgis2_94
    yum -y install freetype-devel libpng-devel giflib-devel libjpeg-devel gd-devel proj-devel
    yum -y install proj-nad proj-epsg libxml2-devel libxslt-devel pam-devel readline-devel
    yum -y install python-psycopg2 libpqxx-devel hdf hdf-devel freetds-devel postgresql-devel
    yum -y install gdal-python mapserver mapserver-python libxml2 libxml2-python python-lxml python-pip python-devel gcc mlocate
    yum -y install scipy blas blas-devel lapack lapack-devel lvm2 firefox
    yum -y groups install "GNOME Desktop"
    yum -y install fftw-devel motif-devel ghc-OpenGL-devel
    # For InstantReality's aopt command referenced in doc/instructions/SPATIAL_3d.md
    yum -y install freeglut luajit
    wget http://doc.instantreality.org/media/uploads/downloads/2.8.0/InstantReality-RedHat-7-x64-2.8.0.38619.rpm
    rpm -Uvh InstantReality-RedHat-7-x64-2.8.0.38619.rpm
fi

# Configure and make (using 2 cpus) additional packages

echo Download and install CMake
wget -q -N http://www.cmake.org/files/v2.8/cmake-2.8.12.2.tar.gz
tar -xzf cmake-2.8.12.2.tar.gz
cd cmake-2.8.12.2
./configure --prefix=/opt/cmake
gmake -j 2 && gmake install
cd ..

echo Build and install GMT
wget -q -N ftp://ftp.iris.washington.edu/pub/gmt/gmt-5.3.1-src.tar.gz
tar -xzf gmt-5.3.1-src.tar.gz
cd gmt-5.3.1
cp cmake/ConfigUserTemplate.cmake cmake/ConfigUser.cmake
mkdir build
cd build
/opt/cmake/bin/cmake -DCMAKE_INSTALL_PREFIX=/usr/local -DCMAKE_BUILD_TYPE=RelWithDebInfo ..
make -j 2 && make install
cd ../..

echo Build and install OSU Tidal Prediction Software
pushd /usr/local
wget -q -N ftp://ftp.oce.orst.edu/dist/tides/OTPS2.tar.Z
tar -xzf OTPS2.tar.Z
cd /usr/local/OTPS2
wget -q -N ftp://ftp.oce.orst.edu/dist/tides/TPXO8_compact/tpxo8_atlas_compact_v1.tar.Z
tar -xzf tpxo8_atlas_compact_v1.tar.Z
make extract_HC
make predict_tide
cp setup.inp setup.inp.bak
cat <<EOT > setup.inp
DATA/Model_atlas_v1        ! 1. tidal model control file
lat_lon_time               ! 2. latitude/longitude/<time> file
z                          ! 3. z/U/V/u/v
m2,s2                      ! 4. tidal constituents to include
AP                         ! 5. AP/RI
oce                        ! 6. oce/geo
1                          ! 7. 1/0 correct for minor constituents
sample.out                 ! 8. output file (ASCII)
EOT
cp DATA/Model_atlas_v1 DATA/Model_atlas_v1.bak
cat <<EOT > DATA/Model_atlas_v1
/usr/local/OTPS2/DATA/hf.tpxo8_atlas_30_v1
/usr/local/OTPS2/DATA/uv.tpxo8_atlas_30_v1
/usr/local/OTPS2/DATA/grid_tpxo8atlas_30_v1
EOT
popd

echo Build and install MB-System, setting overcommit_memory to wizardry mode
wget -q -N ftp://ftp.ldeo.columbia.edu/pub/MB-System/mbsystem-5.5.2284.tar.gz
tar -xzf mbsystem-5.5.2284.tar.gz
cd mbsystem-5.5.2284/
./configure --with-otps-dir=/usr/local/OTPS2
make -j 2 && make install
echo 1 > /proc/sys/vm/overcommit_memory
cd ..

echo Build and install Mapserver
wget -q -N http://download.osgeo.org/mapserver/mapserver-6.4.1.tar.gz
tar xzf mapserver-6.4.1.tar.gz
cd mapserver-6.4.1
mkdir build
cd build
/opt/cmake/bin/cmake .. -DWITH_FRIBIDI=0 -DWITH_CAIRO=0 -DWITH_FCGI=0 -DCMAKE_PREFIX_PATH="/usr/local;/usr/pgsql-9.4"
make -j 2 && make install
cp /usr/local/bin/mapserv /var/www/cgi-bin
ldconfig
cp /etc/sysconfig/httpd /etc/sysconfig/httpd.bak
cat <<EOT >> /etc/sysconfig/httpd
# Needed for mapserv in /var/www/cgi-bin
LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib64
export LD_LIBRARY_PATH
EOT
cd ../..
touch /tmp/mapserver_stoqshg.log
chown apache.apache /tmp/mapserver_stoqshg.log
sudo chmod go+w /tmp/mapserver_stoqshg.log

echo Build database for locate command
updatedb

echo Configure and start services
/usr/pgsql-9.4/bin/postgresql94-setup initdb
/usr/bin/systemctl enable postgresql-9.4
/usr/bin/systemctl start postgresql-9.4
/sbin/chkconfig rabbitmq-server on
/sbin/service rabbitmq-server start
rabbitmqctl add_user stoqs stoqs
rabbitmqctl add_vhost stoqs
rabbitmqctl set_permissions -p stoqs stoqs ".*" ".*" ".*"
/usr/bin/systemctl enable httpd.service
/usr/bin/systemctl start httpd.service
/usr/bin/systemctl enable memcached.service
/usr/bin/systemctl start memcached.service

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
/usr/bin/systemctl restart postgresql-9.4
cd ..

echo Modifying local firewall to allow incoming connections on ports 80 and 8000
firewall-cmd --zone=public --add-port=8000/tcp --permanent
firewall-cmd --zone=public --add-port=80/tcp --permanent
firewall-cmd --reload

echo Configuring vim edit environment
cd /home/$USER
cat <<EOT > .vimrc
:set tabstop=4
:set expandtab
:set shiftwidth=4
EOT

echo Cloning STOQS repo from https://github.com/stoqs/stoqs.git... 
echo ">>> See CONTRIBUTING.md for how to configure your development system so that you can contribute to STOQS"
mkdir dev && cd dev
git clone --depth=50 https://github.com/stoqs/stoqs.git stoqsgit
cd stoqsgit
export PATH="/usr/local/bin:$PATH"
virtualenv venv-stoqs

echo Installing Python modules for a development system
source venv-stoqs/bin/activate
./setup.sh

echo Giving user $USER ownership of everything in /home/$USER
chown -R $USER /home/$USER

echo Provisioning and setup have finished. 
echo Default database loading and STOQS software tests should be run with:
echo "(These commands are also found in ~/dev/stoqsgit/README.md)"
echo ---------------------------------------------------------------------
echo vagrant ssh -- -X
echo "cd ~/dev/stoqsgit && source venv-stoqs/bin/activate"
echo export DATABASE_URL=postgis://stoqsadm:CHANGEME@127.0.0.1:5432/stoqs
echo ./test.sh CHANGEME

