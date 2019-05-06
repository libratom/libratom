#!/usr/bin/env bash

[[ $CONTINUOUS_INTEGRATION ]] || exit 0

# Download libpff and configure it with python support
export TEST_DIR="/tmp/libratom"
mkdir -p $TEST_DIR
cd $TEST_DIR
wget https://github.com/libyal/libpff/releases/download/20180714/libpff-experimental-20180714.tar.gz
tar -xzvf libpff-experimental-20180714.tar.gz
cd libpff-20180714/
./configure --enable-python3

# Build and install the python bindings
python setup.py build
python setup.py install
