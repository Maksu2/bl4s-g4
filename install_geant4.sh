#!/bin/bash
set -e

echo "Starting Geant4 Installation (Attempt 2)..."
echo "Cleaning previous build..."
rm -rf geant4_build
mkdir -p geant4_build
mkdir -p geant4_install

cd geant4_build

echo "Configuring cmake..."
# Configure with system zlib to avoid macOS SDK conflict
cmake ../geant4-v11.2.1 \
    -DCMAKE_INSTALL_PREFIX=../geant4_install \
    -DGEANT4_INSTALL_DATA=ON \
    -DGEANT4_USE_SYSTEM_EXPAT=OFF \
    -DGEANT4_USE_SYSTEM_ZLIB=ON \
    -DGEANT4_BUILD_MULTITHREADED=ON \
    -DCMAKE_BUILD_TYPE=Release

echo "Building (this will take time)..."
# Build
make -j4

# Install
make install

echo "Geant4 Installed Successfully!"
