#!/bin/bash
# This script is executed following provisioning of a server with the 
# prerequisite system software.
pushd $(dirname $0)
HOMEDIR=$(pwd)
LOG_DIR="$HOMEDIR/log"
if [ $1 ]; then
    REQ="$HOMEDIR/requirements/$1.txt"
else
    REQ="$HOMEDIR/requirements/development.txt"
fi
echo "Using pip requirements file: $REQ"

if [ -z $VIRTUAL_ENV ]; then
    echo "Need to be in your virtual environment."
    exit 1
else
    VENV_NAME=$(basename $VIRTUAL_ENV)
    VENV_DIR="$HOMEDIR/$VENV_NAME"
fi

# Put link to gdal-config in venv/bin
CONFIG=$(which gdal-config)
if [ $? -ne 0 ]; then
    echo "gdal-config is not in PATH"
    rm -rf $VENV_DIR
    exit 1
fi

PG_CONFIG=$(locate --regex "bin/pg_config$")
# Pick last path if multiple versions of Postgresql installed
PG_CONFIG=`echo $PG_CONFIG | grep -o '[^ ]*$'`
echo "Using PG_CONFIG=$PG_CONFIG"
PATH=$(dirname $PG_CONFIG):$PATH

ln -s $CONFIG $VENV_DIR/bin/

# GDAL 1.9.2 pip install requires this environment variable
export LD_PRELOAD=/usr/lib64/libgdal.so.1


# Required to install the netCDF4 python module
echo "Need to sudo to install hdf5 packages..."
sudo yum -y install hdf5 hdf5-devel
if [ $? -ne 0 ] ; then
    echo "Exiting $0"
    exit 1
fi

# Required to install the netCDF4 python module
pushd ~/Downloads
wget ftp://ftp.unidata.ucar.edu/pub/netcdf/netcdf-4.3.3.tar.gz
tar -xzf netcdf-4.3.3.tar.gz
cd netcdf-4.3.3
./configure --enable-hl --enable-shared
make; sudo make install
popd

# Required for plotting basemap in LRAUV plots
pushd ~/Downloads
wget 'http://sourceforge.net/projects/matplotlib/files/matplotlib-toolkits/basemap-1.0.7/basemap-1.0.7.tar.gz'
tar -xzf basemap-1.0.7.tar.gz
cd basemap-1.0.7/geos-3.3.3
export GEOS_DIR=/usr/local
./configure --prefix=/usr/local
make; sudo make install
cd ..
python setup.py install
popd

# Install everything in $REQ
if [ -f "$REQ" ]; then
    pip install -r $REQ
    if [ $? -ne 0 ] ; then
        echo "*** pip install -r $REQ failed. ***"
        exit 1
    fi
fi

# NCAR's natgrid needed for contour plotting
pushd ~/Downloads
wget http://sourceforge.net/projects/matplotlib/files/matplotlib-toolkits/natgrid-0.2/natgrid-0.2.1.tar.gz
tar -xzf natgrid-0.2.1.tar.gz
cd natgrid-0.2.1
python setup.py install
popd

echo "$0 finished."

