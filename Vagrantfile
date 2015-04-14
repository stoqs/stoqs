# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
  config.vm.box = "base"
  config.vm.box_url = "https://github.com/2creatives/vagrant-centos/releases/download/v6.5.3/centos65-x86_64-20140116.box"
  config.vm.provision "shell", inline: <<-SHELL
  echo Step 1 / 18 - Disable Selinux
  echo 0 > /selinux/enforce
  echo Step 2 / 18 - Install Pre-requisites
  yum -y install wget
  wget http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
  wget http://rpms.famillecollet.com/enterprise/remi-release-6.rpm
  rpm -Uvh remi-release-6*.rpm epel-release-6*.rpm
  echo Step 3 / 18 - Install Git and Postgres
  yum -y install git
  git clone https://github.com/stoqs/stoqs.git stoqsgit
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
  sudo su - postgres -c 'createuser -s vagrant'
  su - postgres -c "/usr/pgsql-9.3/bin/pg_ctl -D /var/lib/pgsql/9.3/data -l logfile start"
  chown postgres stoqs
  echo Step 5 / 18 - Install Mercurial
  yum -y install mercurial
  echo Step 6 / 18 - Instal the Development Tools for PostGres
  yum -y groupinstall 'Development Tools'
  echo Step 7 / 18 - Download and install CMake
  wget http://www.cmake.org/files/v2.8/cmake-2.8.3.tar.gz
  tar xzf cmake-2.8.3.tar.gz
  cd cmake-2.8.3
  ./configure --prefix=/opt/cmake
  gmake
  make
  make install
  mkdir -m 700 build
  cd ..
  echo Step 8 / 18 Install Python, Virtual Environment, & Rabbit Server
  yum -y install python-setuptools
  su -c "easy_install virtualenv"
  su -c "yum -y install rabbitmq-server scipy mod_wsgi memcached python-memcached"
  su -c "/sbin/chkconfig rabbitmq-server on"
  su -c "/sbin/service rabbitmq-server start"
  su -c "rabbitmqctl add_user stoqs stoqs"       
  su -c "rabbitmqctl add_vhost stoqs"             
  su -c 'rabbitmqctl set_permissions -p stoqs stoqs ".*" ".*" ".*"'
  echo Step 9 / 18 - Install Graph for Mapping Software
  su -c "yum -y install graphviz-devel"
  su -c "yum -y install graphviz-python"
  echo Step 10 / 18 - Install ImageMagick
  su -c "yum -y install ImageMagick"
  echo Step 11 / 18 - Setup Postgis2
  cd /home/vagrant/stoqs
  su -c "yum -y install postgis2_93"    
  su - postgres -c "psql template1"
  su - postgres -c "psql CREATE USER stoqs WITH PASSWORD 'stoqs';"
  su - postgres -c "createdb postgis"
  su - postgres -c "createlang plpgsql postgis"
  su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/postgis.sql"
  su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/spatial_ref_sys.sql"
  su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/postgis_comments.sql"
  su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/rtpostgis.sql"
  su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/raster_comments.sql"
  su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/topology.sql"
  su - postgres -c "psql -d postgis -f /usr/pgsql-9.3/share/contrib/postgis-2.1/topology_comments.sql"
  mkdir -m 700 /tmp/media
  ln -s /tmp/media /var/www/html/media   
  echo Step 12 / 18 - G-dal
  wget http://download.osgeo.org/gdal/gdal-1.9.2.tar.gz        
  yum -y install gdal
  cd cmake-2.8.3
  echo 'pathmunge /cmake-2.8.3' > /etc/profile.d/custompath.sh
  chmod +x /etc/profile.d/custompath.sh
  . /etc/profile
  ./configure --with-python
  gmake       
  make
  su -c "make install"
  cd ..
  echo Step 13 / 18 - Map Server Libraries
  su -c "yum -y install freetype-devel libpng-devel giflib-devel libjpeg-devel gd-devel proj-devel"
  su -c "yum -y install proj-nad proj-epsg curl-devel libxml2-devel postgresql91-devel libxslt-devel pam-devel openssl-devel readline-devel"
  wget http://download.osgeo.org/mapserver/mapserver-6.4.1.tar.gz
  yum -y install mapserver
  yum -y install python-psycopg2
  export PATH="/usr/pgsql-9.3/bin:$PATH"
  yum -y install libpqxx-devel
  echo Step 14 / 18 - Epsg File Alteration
  sed -i '$a<900913> +proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs <>' /usr/share/proj/epsg    
  echo Step 15 / 18 - Gdal & psql continued setup
  cd /home/vagrant/cmake-2.8.3
  ./configure --with-proj=/usr --with-ogr=/usr/local/bin/gdal-config --with-gdal=/usr/local/bin/gdal-config --with-wfs --with-wfsclient --with-wmsclient --with-postgis=/usr/pgsql-9.1/bin/pg_config
  su -c "ln -s /usr/pgsql-9.3/lib/libpq.so.5.4 /usr/pgsql-9.3/lib/libpq.so"
  gmake
  make
  su -c "make install"
  cd /home/vagrant
  echo Step 16 / 18 - System Check and Service Restart
  su -c "chkconfig httpd on"
  su -c "/sbin/service httpd start"
  su -c "chkconfig memcached on"
  su -c "/sbin/service memcached start"
  echo Step 17 / 18 - Virtual environment with Python Tools
  yum -y install gdal gdal-python gdal-devel mapserver mapserver-python libxml2 libxml2-python python-lxml python-pip python-devel gcc
  cd /home/vagrant/stoqsgit
  virtualenv venv-stoqs
  source venv-stoqs/bin/activate      
  yum -y install numpy scipy python-matplotlib ipython python-pandas sympy python-nose
  export CPLUS_INCLUDE_PATH=/usr/include/gdal
  export C_INCLUDE_PATH=/usr/include/gdal
  cd /home/vagrant/stoqs
  ./setup.sh
  SHELL
end

