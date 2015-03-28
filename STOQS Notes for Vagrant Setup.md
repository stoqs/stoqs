/*  Setup:
    OS:   CentOS 6.5
    H/D:  50GB
    Env: VM-Ware  
          Root:     admin
          User:     admin   
          Password: admin
*/

#Step 1 (This Step not used when setting up Vagrant)
// First we need to start by disabling the firewall. May not be needed for Vagrant
//Anytime the system is restarted in the install process this need to be done.
su
echo 0 > /selinux/enforce 

#Step 2
// This commands will download and install the Epel and Yum to make installation easier
wget http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
wget http://rpms.famillecollet.com/enterprise/remi-release-6.rpm
rpm -Uvh remi-release-6*.rpm epel-release-6*.rpm

#Step 3
// Download and install Postgres v9.3
curl -O http://yum.postgresql.org/9.3/redhat/rhel-6-x86_64/pgdg-centos93-9.3-1.noarch.rpm
rpm -ivh pgdg*
yum -y install postgresql93-server
service postgresql-9.3 initdb
chkconfig postgresql-9.3 on
service postgresql-9.3 start
yum -y groupinstall "PostgreSQL Database Server 9.3 PGDG"
chkconfig postgresql-9.3 on

#Step 4
// We need to enter the Bash enviroment to alter the logfile for postgres.
su -c "su - postgres" // Bash
/usr/pgsql-9.3/bin/pg_ctl -D /var/lib/pgsql/9.3/data -l logfile start
exit

#Step 5
//Install Mercurial
yum -y install mercurial

#Step 6 (This next line of code will be changed before Vagrant Project is finalized)
//Download and install from Google Code the clone of the STOQS file.
hg clone https://code.google.com/p/stoqs/
chown postgres stoqs

#Step 7
//Instal the Development Tools for PostGres
yum -y groupinstall 'Development Tools' 

#Step 8
//Download and install CMake
wget http://www.cmake.org/files/v2.8/cmake-2.8.3.tar.gz
tar xzf cmake-2.8.3.tar.gz
cd cmake-2.8.3
./configure --prefix=/opt/cmake
gmake
make
make install 
mkdir -m 700 build
cd ..

#Step 9 
//Install Python, Virtual Enviroment, & Rabbit Server. This will also setup a user/host for stoqs.
//The credentials for user/host can be altered by user if needed.
yum -y install python-setuptools
su -c "easy_install virtualenv"
su -c "yum -y install rabbitmq-server scipy mod_wsgi memcached python-memcached"
su -c "/sbin/chkconfig rabbitmq-server on"
su -c "/sbin/service rabbitmq-server start"
su -c "rabbitmqctl add_user stoqs stoqs"       
su -c "rabbitmqctl add_vhost stoqs"             
su -c 'rabbitmqctl set_permissions -p stoqs stoqs ".*" ".*" ".*"'

#Step 10
// Install Graph for Mapping Software
su -c "yum -y install graphviz-devel"
su -c "yum -y install graphviz-python"

#Step 11
// Install ImageMagick image editor 
su -c "yum -y install ImageMagick"

#Step 12 (Vagrant Special Attention Needed) 
// Now we need to add changes to the pg_hba.conf, adding ip address for accessing the server.
// There first line where 192.168.110.0/24, needs to be replaced w/ your internet address.
// For Vagrant Need to request info from User. We need to be sure and check that a proper internet adress is given.
// The first line will open the file editor
vi /var/lib/pgsql/9.3/data/pg_hba.conf
// You need to add the next 4 lines to the start of the file and change 192.168.110.0 to your address 
# Allow logins from hosts with self-assigned IP addresses
host    all             all             192.168.110.0/24        trust 
# Allow logins like 'psql -h 127.0.0.1 -d stoqs -U stoqsadm'
host    all             all             127.0.0.1/32            trust

#Step 13
// Here we need to enter the Postgres Enviroment and setup the Postgis2 Software.
// In this enviroment we need to setup user name and password. Here these have 
// been left as stoqs(this can be changed, but changes need to be used at all point using the databases.
// The line \q will exit the psql setup and Exit will exit the postgres enviroment
cd stoqs
su -c postgres
su -c "yum -y install postgis2_93"		        
psql template1 
CREATE USER stoqs WITH PASSWORD 'stoqs';
\q  
createdb postgis
createlang plpgsql postgis 
psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/postgis.sql
psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/spatial_ref_sys.sql
psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/postgis_comments.sql
psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/rtpostgis.sql
psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/raster_comments.sql
psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/topology.sql
psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/topology_comments.sql
mkdir -m 700 /tmp/media
su -c 'ln -s /tmp/media /var/www/html/media'
exit

#Step 14
// Installation and setup of G-dal
wget http://download.osgeo.org/gdal/gdal-1.9.2.tar.gz        # Required for csv files and KML parsing support
yum install gdal
cd cmake-2.8.3
echo 'pathmunge /cmake-2.8.3' > /etc/profile.d/custompath.sh
chmod +x /etc/profile.d/custompath.sh
. /etc/profile
./configure --with-python
gmake       
make
su -c "make install"
cd ..

#Step 15
// Install and setup the various libraries Map Server
su -c "yum -y install freetype-devel libpng-devel giflib-devel libjpeg-devel gd-devel proj-devel"
su -c "yum -y install proj-nad proj-epsg curl-devel libxml2-devel postgresql91-devel libxslt-devel pam-devel openssl-devel readline-devel"
wget http://download.osgeo.org/mapserver/mapserver-6.4.1.tar.gz
yum -y install mapserver
yum -y install python-psycopg2
export PATH="/usr/pgsql-9.3/bin:$PATH"
yum install libpqxx-devel

#Step 16
// Now we need to add a few lines to the epsg file.
// The first line will open the file editor
vi /usr/share/proj/epsg
//Add the following lines to the End of the file.
# Manually add the next line to the end of /usr/share/proj/epsg 
<900913> +proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs <>

#Step 17
// Gdal & psql continued setup...
cd cmake-2.8.3
./configure --with-proj=/usr --with-ogr=/usr/local/bin/gdal-config --with-gdal=/usr/local/bin/gdal-config --with-wfs --with-wfsclient --with-wmsclient --with-postgis=/usr/pgsql-9.1/bin/pg_config
su -c "ln -s /usr/pgsql-9.3/lib/libpq.so.5.4 /usr/pgsql-9.3/lib/libpq.so"
gmake
make 
su -c "make install"
cd ..

#Step 18
// Now we are going to check that httpd and memcached are configured and running.
su -c "chkconfig httpd on"
su -c "/sbin/service httpd start"
su -c "chkconfig memcached on"
su -c "/sbin/service memcached start"

#Step 19
// Setup vertual enviroment with Python Tools
yum -y install gdal gdal-python gdal-devel mapserver mapserver-python libxml2 libxml2-python python-lxml python-pip python-devel gcc
virtualenv venv-stoqs

#Step 20
// This line will take us into the virtual Enviroment, where we will install several tools for python 
// and add gdal to the Linux path 
source venv-stoqs/bin/activate      
cd stoqs //*Starts here for backup
yum -y install numpy scipy python-matplotlib ipython python-pandas sympy python-nose
export CPLUS_INCLUDE_PATH=/usr/include/gdal
export C_INCLUDE_PATH=/usr/include/gdal

#Step 21 (Vagrant Final Step)
// This will run the final setup step and should conclude with setup finnished. 
./setup.sh

