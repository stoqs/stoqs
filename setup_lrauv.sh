#!/bin/bash
# This script sets up the software required to run the real-time LRAUV loader and plotting code
pushd $(dirname $0)
HOMEDIR=$(pwd)
LOG_DIR="$HOMEDIR/log"
REQ="$HOMEDIR/requirements/lrauv.txt"
echo "Using pip requirements file: $REQ"

if [ -z $VIRTUAL_ENV ]; then
    echo "Need to be in your virtual environment."
    exit 1
else
    VENV_NAME=$(basename $VIRTUAL_ENV)
    VENV_DIR="$HOMEDIR/$VENV_NAME"
fihy

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

echo "$0 finished."

