#!/bin/bash
# This script should be run whenever new packages are installed to ensure things are
# set for future runs, and of course to setup a new virtualenv
pushd $(dirname $0)
HOMEDIR=$(pwd)
LOG_DIR="$HOMEDIR/log"
if [ $1 ]; then
    REQ="$HOMEDIR/$1"
    echo "Using pip requirements file $1"
else
    REQ="$HOMEDIR/requirements.txt"
fi
EGG_CACHE="$HOMEDIR/wsgi/egg-cache"
PG_CONFIG=$(locate --regex "bin/pg_config$")
PATH=$(dirname $PG_CONFIG):$PATH

if [ -z $VIRTUAL_ENV ]; then
    echo "Need to be in your virtual environment."
    exit 1
else
    VENV_NAME=$(basename $VIRTUAL_ENV)
    VENV_DIR="$HOMEDIR/$VENV_NAME"
fi

# Required to install the hdf5 libraries
echo "Need to sudo to install hdf5 packages..."
sudo yum -y install hdf5 hdf5-devel
if [ $? -ne 0 ] ; then
    echo "Exiting $0"
    exit
fi
sudo yum -y remove numpy

# Install GDAL in venv
CONFIG=$(which gdal-config)
if [ $? -ne 0 ]; then
    echo "gdal-config is not in PATH"
    rm -rf $VENV_DIR
    exit 1
fi
ln -s $CONFIG $VENV_DIR/bin/

# Make sure weh have pip in the virtualenv
easy_install pip

# Install numpy
NUMPY=$(grep numpy requirements.txt)
echo "Installing numpy (${NUMPY:=numpy})"
pip install $NUMPY
if [ $? -ne 0 ] ; then
    echo "*** pip install $NUMPY failed. ***"
    exit 1
fi

# Install Matplotlib from GIT
#pip install -e git+https://github.com/matplotlib/matplotlib.git#egg=matplotlib
#if [ $? -ne 0 ] ; then
#    echo "*** pip install -e git+https://github.com/matplotlib/matplotlib.git#egg=matplotlib failed. ***"
#    exit 1
#fi

# Install everything in $REQ
if [ -f "$REQ" ]; then
    pip install -r $REQ
    if [ $? -ne 0 ] ; then
        echo "*** pip install -r $REQ failed. ***"
        exit 1
    fi
fi

# Save config and give apache access
pip freeze | grep -v pysqlite | grep -v ga_ows | grep -v matplotlib > requirements_installed.txt
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
# Required for specific versions of psycopg and postgis as of 2013

pushd venv-stoqs/lib/python*/site-packages
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

echo "$0 finished."

