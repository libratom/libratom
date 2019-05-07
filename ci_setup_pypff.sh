#!/usr/bin/env bash

export TEST_DIR=${LIBRATOM_TEST_DIR:="/tmp/libratom"}
export LIBPFF_ROOT_DIR="${TEST_DIR}/libpff-20180714"

if [[ $CONTINUOUS_INTEGRATION ]]; then

    # Download libpff
    mkdir -p $TEST_DIR
    cd $TEST_DIR
    wget https://github.com/libyal/libpff/releases/download/20180714/libpff-experimental-20180714.tar.gz
    tar -xzvf libpff-experimental-20180714.tar.gz

    # Configure libpff with python support
    cd $LIBPFF_ROOT_DIR
    ./configure --enable-python3

    # Build pypff
    python setup.py build

fi

# Install pypff
cd $LIBPFF_ROOT_DIR
python setup.py install
