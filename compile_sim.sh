#!/bin/bash
set -e

# Set path to local Geant4 installation
export Geant4_DIR=/Users/maksu/symulacjaa/geant4_install/lib/Geant4-11.2.1
# Note: The suffix might be Geant4-11.2.1 or similar depending on exact version. 
# We'll set CMAKE_PREFIX_PATH to be safe.
export CMAKE_PREFIX_PATH=/Users/maksu/symulacjaa/geant4_install/

mkdir -p build
cd build

cmake ..
CORES=$(sysctl -n hw.ncpu)
make -j$CORES

echo "Simulation compiled successfully! Run with: ./GeantSim run.mac"
