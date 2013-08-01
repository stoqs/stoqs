#!/bin/bash
# This script should be run whenever new packages are installed to ensure things are
# set for future runs, and of course to setup a new virtualenv
pushd $(dirname $0)
HOMEDIR=$(pwd)
LOG_DIR="$HOMEDIR/log"
REQ="$HOMEDIR/requirements.txt"
EGG_CACHE="$HOMEDIR/wsgi/egg-cache"
VENV_NAME="venv-stoqs"
VENV_DIR="$HOMEDIR/$VENV_NAME"
PG_CONFIG=$(locate --regex "bin/pg_config$")
PATH=$(dirname $PG_CONFIG):$PATH


# Required to install the hdf5 libraries
sudo yum -y install hdf5 hdf5-devel
sudo yum -y remove numpy

which virtualenv &>/dev/null
if [ $? -ne 0 ]; then
 echo "virtualenv command not found"
 echo "sudo easy_install virtualenv"
fi

if [ -d $VENV_NAME ]; then
 echo "virtualenv has already been created"
else
 virtualenv $VENV_NAME
 # Install GDAL in venv
 CONFIG=$(which gdal-config)
 if [ $? -ne 0 ]; then
   echo "gdal-config is not in PATH"
   rm -rf $VENV_DIR
   exit 1
 fi
 ln -s $CONFIG $VENV_DIR/bin/
fi
source $VENV_DIR/bin/activate
easy_install pip

# Install numpy
NUMPY=$(grep numpy requirements.txt)
echo "Installing numpy (${NUMPY:=numpy})"
pip install $NUMPY

# Install the stuff thatcomes from GIT
# For server-side Matlab-style plotting of data
pip install -e git+https://github.com/matplotlib/matplotlib.git#egg=matplotlib

# For WFS to OpenLayers directly from the Django data model
pip install -e git+https://github.com/JeffHeard/ga_ows.git#egg=ga_ows


if [ -f "$REQ" ]; then
 pip install -r $REQ
fi


pip freeze|grep -v pysqlite|grep -v ga_ows|grep -v matplotlib > $REQ
if [ ! -d $EGG_CACHE ]; then
 echo "Creating the egg cache"
 mkdir -p $EGG_CACHE
fi
sudo chown apache $EGG_CACHE
mkdir -p $LOG_DIR
sudo chgrp apache $LOG_DIR
sudo chmod g+s $LOG_DIR
touch $LOG_DIR/django.log
chmod g+w log/django.log
##################################################################

# Apply the django patch to escape unicode strings properly

pushd 
patch django/contrib/gis/db/backends/postgis/adapter.py << __EOT__
--- django/contrib/gis/db/backends/postgis/adapter.py.orig	2011-09-09 11:51:27.769648151 +0100
+++ django/contrib/gis/db/backends/postgis/adapter.py	2011-09-09 11:51:38.279842827 +0100
@@ -3,7 +3,7 @@
 """
 
 from psycopg2 import Binary
-from psycopg2.extensions import ISQLQuote
+from psycopg2.extensions import ISQLQuote, adapt
 
 class PostGISAdapter(object):
     def __init__(self, geom):
@@ -12,6 +12,7 @@
         # the adaptor) and the SRID from the geometry.
         self.ewkb = str(geom.ewkb)
         self.srid = geom.srid
+        self._adapter = Binary(self.ewkb)
 
     def __conform__(self, proto):
         # Does the given protocol conform to what Psycopg2 expects?
@@ -26,10 +27,15 @@
     def __str__(self):
         return self.getquoted()
 
+    def prepare(self, conn):
+        # Pass the connection to the adapter: this allows escaping the binary
+        # in the style required by the server's standard_conforming_string setting.
+        self._adapter.prepare(conn)
+
     def getquoted(self):
         "Returns a properly quoted string for use in PostgreSQL/PostGIS."
-        # Want to use WKB, so wrap with psycopg2 Binary() to quote properly.
-        return 'ST_GeomFromEWKB(E%s)' % Binary(self.ewkb)
+        # psycopg will figure out whether to use E'\\000' or '\000'
+        return 'ST_GeomFromEWKB(%s)' % adapt(self._adapter)
 
     def prepare_database_save(self, unused):
         return self
__EOT__
popd
##################################################################
# echo running a quick test to make sure things aren't broke
export PYTHONPATH=$(pwd)
export DJANGO_SETTINGS_MODULE=settings
python stoqs/views/management.py
popd
