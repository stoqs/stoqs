#!/bin/bash
# Idempotent shell script to install system level prerequisites for STOQS.
# Designed to be run from Vagrantfile, where default USER is vagrant.
# INSTALL_* variables may be set to "true" for optional software
if [ "$EUID" -ne 0 ]
then echo "Please run as root"
    exit 1
fi

# For easier setting of Postgresql version: 10, 11, ...
PG_VER=11

# For a minimal STOQS development system set to "false"
INSTALL_MB_SYSTEM="true"
INSTALL_OTPS="false"
INSTALL_DESKTOP_GRAPHICS="true"
INSTALL_DOCKER="true"

# Sometimes we'd like to test newer versions of software built from source
# Set these to "true" to build rather than use the repository version:
BUILD_GEO="true"
BUILD_GDAL="true"
BUILD_GMT="true"
BUILD_NETCDF="false"

USER='vagrant'
if id -u "$USER" >/dev/null 2>&1; 
then
    echo "user $USER exists"
else
    echo "user $USER does not exist"
    exit 1
fi

cd /home/$USER
mkdir Downloads && pushd Downloads

# Initial package installs needed for building packages from source
echo Disable SELinux
sed -i 's/SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config
mkdir /selinux
echo 0 > /selinux/enforce

echo Add epel, remi, and postgres repositories
yum makecache fast
yum -y install wget git
yum -y install epel-release
yum -y update epel-release
yum repolist
wget -q -N http://rpms.famillecollet.com/enterprise/remi-release-7.rpm
rpm -Uvh remi-release-7*.rpm

echo Install Python 3.8
yum groupinstall -y "Development Tools"
yum -y install zlib-devel openssl-devel sqlite-devel bzip2-devel xz-libs xz-devel readline-devel libffi-devel
wget -q -N https://www.python.org/ftp/python/3.8.1/Python-3.8.1.tgz
tar xzf Python-3.8.1.tgz
cd Python-3.8.1
sudo ./configure --enable-optimizations
sudo make altinstall
cd ..

if [ $BUILD_GEO = "true" ];
then
    echo Build and install geos
    echo '/usr/local/lib' >> /etc/ld.so.conf
    wget -q -N http://download.osgeo.org/geos/geos-3.6.0.tar.bz2
    tar -xjf geos-3.6.0.tar.bz2
    cd geos-3.6.0
    ./configure
    make -j 2 && make install
    ldconfig
    cd ..
else
    ##yum install geos38-devel
    echo Let postgis30_${PG_VER} install geos
fi

if [ $BUILD_NETCDF = "true" ];
then
    echo Install package prerequisites for NetCDF4
    yum -y install curl-devel hdf5 hdf5-devel
    echo Build and install NetCDF4
    wget ftp://ftp.unidata.ucar.edu/pub/netcdf/netcdf-c-4.7.3.tar.gz
    tar -xzf netcdf-c-4.7.3.tar.gz
    cd netcdf-c-4.7.3
    ./configure
    make -j 2 && sudo make install
    cd ..
    export LD_LIBRARY_PATH=/usr/local/lib:/usr/local/lib64
    wget ftp://ftp.unidata.ucar.edu/pub/netcdf/netcdf-fortran-4.5.2.tar.gz
    tar -xzf netcdf-fortran-4.5.2.tar.gz
    cd netcdf-fortran-4.5.2
    ./configure
    make -j 2 && sudo make install
    cd ..
else
    ##yum install netcdf
    echo Let postgis30_${PG_VER} install netcdf
fi

echo Install PostgreSQL
yum -y install centos-release-scl
yum -y install https://download.postgresql.org/pub/repos/yum/11/redhat/rhel-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
yum -y groupinstall "PostgreSQL Database Server ${PG_VER} PGDG"

if [ $BUILD_GEO = "true" ];
then
    echo Build and install proj 6
    wget -q -N https://download.osgeo.org/proj/proj-datumgrid-1.8.zip
    wget -q -N wget https://download.osgeo.org/proj/proj-6.2.1.tar.gz
    tar -xzf proj-6.2.1.tar.gz
    cd proj-6.2.1
    unzip -o -q ../proj-datumgrid-1.8.zip -d data
    export PROJ_LIB=$(pwd)/data
    ./configure --prefix=/usr/local
    make -j 2 && make install
    cd ..
else
    ##yum install proj62-devel
    export PROJ_LIB=/usr/proj62/share/proj
    echo Let postgis30_${PG_VER} install proj with PROJ_LIB = $PROJ_LIB
fi

if [ $BUILD_GDAL = "true" ];
then
    echo Build and install gdal
    wget -q -N http://download.osgeo.org/gdal/2.4.3/gdal-2.4.3.tar.gz
    tar -xzf gdal-2.4.3.tar.gz
    cd gdal-2.4.3
    export PATH=$(pwd):$PATH
    ./configure --prefix=/usr/local
    gmake -j 2 && gmake install
    cd ..
else
    ##yum install gdal23-devel
    export GDAL_DATA=/usr/gdal30/share/
    echo Let postgis30_${PG_VER} install gdal with GDAL_DATA = $GDAL_DATA
fi

echo Put geckodriver in /usr/local/bin
pushd /usr/local/bin
wget -q -N https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux32.tar.gz
tar -xzf geckodriver-v0.24.0-linux32.tar.gz
popd

yum -y install deltarpm rabbitmq-server mod_wsgi memcached python-memcached
yum -y install graphviz-devel graphviz-python ImageMagick postgis30_${PG_VER} SFCGAL-devel
yum -y install freetype-devel libpng-devel giflib-devel libjpeg-devel gd-devel
yum -y install libxml2-devel libxslt-devel pam-devel
yum -y install python-psycopg2 libpqxx-devel hdf hdf-devel freetds-devel
echo Install libxml and more
yum -y install libxml2 libxml2-python python-lxml python-pip gcc mlocate
echo Install scipy and more
yum -y install scipy blas blas-devel lapack lapack-devel lvm2 firefox cachefilesd
yum -y install harfbuzz-devel fribidi-devel

if [ $INSTALL_DOCKER = "true" ];
then
    yum -y install docker docker-compose nginx
fi

if [ $INSTALL_DESKTOP_GRAPHICS = "true" ];
then
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

if [ $BUILD_GMT = "true" ];
then
    echo Install package prerequisites for NetCDF4
    yum -y install curl-devel hdf5 hdf5-devel
    echo Build and install NetCDF4
    wget ftp://ftp.unidata.ucar.edu/pub/netcdf/netcdf-c-4.7.3.tar.gz
    tar -xzf netcdf-c-4.7.3.tar.gz
    cd netcdf-c-4.7.3
    ./configure
    make -j 2 && sudo make install
    cd ..
    export LD_LIBRARY_PATH=/usr/local/lib:/usr/local/lib64
    wget ftp://ftp.unidata.ucar.edu/pub/netcdf/netcdf-fortran-4.5.2.tar.gz
    tar -xzf netcdf-fortran-4.5.2.tar.gz
    cd netcdf-fortran-4.5.2
    ./configure
    make -j 2 && sudo make install
    cd ..
    echo Build and install GMT
    wget -q -N ftp://ftp.iris.washington.edu/pub/gmt/gmt-6.1.1-src.tar.gz
    tar -xzf gmt-6.1.1-src.tar.gz
    cd gmt-6.1.1
    cp cmake/ConfigUserTemplate.cmake cmake/ConfigUser.cmake
    mkdir build
    cd build
    /opt/cmake/bin/cmake -DCMAKE_INSTALL_PREFIX=/usr/local -DCMAKE_BUILD_TYPE=RelWithDebInfo ..
    make -j 2 && make install
    cd ../..
else
    yum install GMT GMT-devel
fi

if [ $INSTALL_MB_SYSTEM = "true" ];
then
    if [ $INSTALL_OTPS = "true" ];
    then
        # TODO: Verify that this build works
        # During script maintenance in September 2020 I discovered
        # that registration is required for obtaining the TPXO models:
        #   https://www.tpxo.net/tpxo-products-and-registration
        # Retaining code here in case tidal prediction is needed.
        echo Build and install OSU Tidal Prediction Software
        pushd /usr/local
        wget -q -N ftp://ftp.oce.orst.edu/dist/tides/OTPS.tar.Z
        tar -xzf OTPS.tar.Z
        cd /usr/local/OTPS
        make extract_HC
        make predict_tide
        cp setup.inp setup.inp.bak
        cat <<EOT > setup.inp
DATA/Model_tpxo9.v1        ! 1. tidal model control file
lat_lon_time               ! 2. latitude/longitude/time file
z                          ! 3. z/U/V/u/v
m2,s2,n2,k2,k1,o1,p1,q1    ! 4. tidal constituents to include
AP                         ! 5. AP/RI
oce                        ! 6. oce/geo
1                          ! 7. 1/0 correct for minor constituents
tmp                        ! 8. output file (ASCII)
EOT
        cp DATA/Model_tpxo9.v1 DATA/Model_tpxo9.v1.bak
        cat <<EOT > DATA/Model_tpxo9.v1
/usr/local/OTPS/DATA/TPXO9v1/h_tpxo9.v1
/usr/local/OTPS/DATA/TPXO9v1/u_tpxo9.v1
/usr/local/OTPS/DATA/TPXO9v1/grid_tpxo9
EOT
        popd
    fi

    echo Build and install MB-System, set overcommit_memory to wizardry mode
    wget -q -N https://github.com/dwcaress/MB-System/archive/5.7.6beta55.tar.gz
    tar -xzf 5.7.6beta55.tar.gz
    cd MB-System-5.7.6beta55
    if [ $INSTALL_OTPS = "true" ];
    then
        ./configure --with-otps-dir=/usr/local/OTPS
    else
        ./configure --with-gdal-config=/usr/local/bin \
                    --with-gmt-config=/usr/local/bin
    fi
    export GMT_CUSTOM_LIBS=/usr/local/lib/libmbgmt.so
    make -j 2 && make install
    echo 1 > /proc/sys/vm/overcommit_memory
    cd ..
fi

echo Build and install Mapserver
wget -q -N http://download.osgeo.org/mapserver/mapserver-7.4.3.tar.gz
tar xzf mapserver-7.4.3.tar.gz
cd mapserver-7.4.3
mkdir build
cd build
/opt/cmake/bin/cmake .. -DWITH_FRIBIDI=1 -DWITH_CAIRO=0 -DWITH_FCGI=0 -DWITH_PROTOBUFC=0 -DCMAKE_PREFIX_PATH="/usr/local;/usr/pgsql-${PG_VER}"
if [ $? != 0 ];
then
    echo "cmake for mapserver failed, correct the problem and re-provision"
    exit 1
fi
make -j 2 && make install
cp /usr/local/bin/mapserv /var/www/cgi-bin
ldconfig
cp /etc/sysconfig/httpd /etc/sysconfig/httpd.bak
cat <<EOT >> /etc/sysconfig/httpd
# Needed for mapserv in /var/www/cgi-bin
LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib64
export LD_LIBRARY_PATH
EOT
cp /etc/httpd/conf/httpd.conf /etc/httpd/conf/httpd.conf.bak
sed -i 's#Listen 80#Listen 8080#' /etc/httpd/conf/httpd.conf
cd ../..
touch /tmp/mapserver_stoqshg.log
chown apache.apache /tmp/mapserver_stoqshg.log
sudo chmod go+w /tmp/mapserver_stoqshg.log

echo Build database for locate command
updatedb

echo Configure and start services
/usr/pgsql-${PG_VER}/bin/postgresql-${PG_VER}-setup initdb
/usr/bin/systemctl enable postgresql-${PG_VER}
/usr/bin/systemctl start postgresql-${PG_VER}
/usr/bin/systemctl enable rabbitmq-server
/usr/bin/systemctl start rabbitmq-server
rabbitmqctl add_user stoqs stoqs
rabbitmqctl add_vhost stoqs
rabbitmqctl set_permissions -p stoqs stoqs ".*" ".*" ".*"
/usr/bin/systemctl enable httpd.service
/usr/bin/systemctl start httpd.service
/usr/bin/systemctl enable memcached.service
/usr/bin/systemctl start memcached.service
/usr/bin/systemctl enable cachefilesd
/usr/bin/systemctl start cachefilesd
/usr/bin/systemctl enable docker
/usr/bin/systemctl start docker

echo Have postgresql listen on port 5438
cp /var/lib/pgsql/${PG_VER}/data/postgresql.conf /var/lib/pgsql/${PG_VER}/data/postgresql.conf.bak
sed -i 's/#port = 5432/port = 5438/' /var/lib/pgsql/${PG_VER}/data/postgresql.conf

echo Modify pg_hba.conf
mv -f /var/lib/pgsql/${PG_VER}/data/pg_hba.conf /var/lib/pgsql/${PG_VER}/data/pg_hba.conf.bak
cat <<EOT > /var/lib/pgsql/${PG_VER}/data/pg_hba.conf
# Allow user/password login
host    all     stoqsadm     127.0.0.1/32   md5
host    all     stoqsadm     10.0.2.0/24    md5
host    all     vagrant      127.0.0.1/32   trust
local   all     all                         trust
# Allow root to login as postgres (as travis-ci allows) - See also pg_ident.conf
local   all     all                     peer map=root_as_others
host    all     all     127.0.0.1/32    ident map=root_as_others
EOT
cat /var/lib/pgsql/${PG_VER}/data/pg_hba.conf.bak >> /var/lib/pgsql/${PG_VER}/data/pg_hba.conf
cp /var/lib/pgsql/${PG_VER}/data/pg_ident.conf /var/lib/pgsql/${PG_VER}/data/pg_ident.conf.bak
echo "root_as_others  root            postgres" >> /var/lib/pgsql/${PG_VER}/data/pg_ident.conf

su - postgres -c 'createuser -s $USER'
su - postgres -c "/usr/pgsql-${PG_VER}/bin/pg_ctl -D /var/lib/pgsql/${PG_VER}/data -l logfile start"
su - postgres -c "psql -c \"CREATE DATABASE template_postgis WITH TEMPLATE postgis;\""
su - postgres -c "psql -c \"CREATE USER vagrant LOGIN PASSWORD 'vagrant';\""
su - postgres -c "psql -c \"ALTER ROLE vagrant SUPERUSER;\""
/usr/bin/systemctl restart postgresql-${PG_VER}
cd ..

echo Modifying local firewall to allow incoming connections on ports 80 and 8000
firewall-cmd --zone=public --add-port=8000/tcp --permanent
firewall-cmd --zone=public --add-port=80/tcp --permanent
firewall-cmd --reload

echo Configuring vim and ssh
cd /home/$USER
cat <<EOT > .vimrc
:set tabstop=4
:set expandtab
:set shiftwidth=4
EOT
cat <<EOT > .ssh/config
Host *
    ServerAliveInterval 120
    ServerAliveCountMax 30
    ConnectTimeout 30
EOT
chmod 600 .ssh/config

echo Configure and restart sshd for enabling PyCharm interpreter
sed -i 's#/usr/lib/openssh/sftp-server#/usr/libexec/openssh/sftp-server#' /etc/ssh/sshd_config
/usr/bin/systemctl restart sshd

# Use STOQS_HOME=/home/vagrant/dev/stoqsgit if your host doesn't support NFS file serving
STOQS_HOME=/vagrant/dev/stoqsgit
echo Cloning STOQS repo from https://github.com/stoqs/stoqs.git into $STOQS_HOME... 
echo ">>> See CONTRIBUTING.md for how to configure your development system so that you can contribute to STOQS"

mkdir -p $STOQS_HOME
git clone https://github.com/stoqs/stoqs.git $STOQS_HOME
cd $STOQS_HOME
git config core.preloadindex true
export PATH="/usr/local/bin:$PATH"
python3.8 -m venv venv-stoqs

echo Creating venv-stoqs...
source venv-stoqs/bin/activate
pip install --upgrade pip
# scikit-bio and pymsssql setups are broken, install numpy and Cython here first
pip install numpy Cython
echo Executing pip install -r docker/requirements/development.txt...
pip install -r docker/requirements/development.txt
pip install -U git+https://github.com/matplotlib/basemap.git

echo Adding LD_LIBRARY_PATH to ~/.bashrc
echo "export LD_LIBRARY_PATH=/usr/local/lib:/usr/local/lib64" >> ~/.bashrc

echo Creating ~/gmt.conf with GMT_CUSTOM_LIBS = /usr/local/lib/mbsystem.so
echo "GMT_CUSTOM_LIBS = /usr/local/lib/mbsystem.so" > ~/gmt.conf

echo Giving user $USER ownership of everything in /home/$USER
chown -R $USER /home/$USER

echo Forward network traffic to support using docker without sudo - need to restart network at end of provisioning
hostnamectl set-hostname localhost
cat <<EOT >> /etc/sysctl.conf
net.ipv4.ip_forward=1
EOT
systemctl restart network
groupadd docker
usermod -aG docker $USER

echo Provisioning has finished. 
echo Default database loading and STOQS software tests should be run with:
echo "(Note: These commands are also found in $STOQS_HOME/README.md)"
echo ---------------------------------------------------------------------
echo vagrant ssh -- -X                        # Wait for [vagrant@localhost ~]$ prompt
echo export STOQS_HOME=/vagrant/dev/stoqsgit  # Use STOQS_HOME=/home/vagrant/dev/stoqsgit if not using NFS mount
echo cd $STOQS_HOME 
echo source venv-stoqs/bin/activate
echo export DATABASE_URL=postgis://stoqsadm:CHANGEME@127.0.0.1:5438/stoqs
echo ./test.sh CHANGEME load noextraload
