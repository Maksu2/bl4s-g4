#!/bin/bash
set -e

echo "═══════════════════════════════════════"
echo " Rekompilacja symulacji..."
echo "═══════════════════════════════════════"

# Load Geant4 environment
if [ -f geant4_install/bin/geant4.sh ]; then
    source geant4_install/bin/geant4.sh
else
    echo "⚠ geant4.sh not found, trying CMAKE_PREFIX_PATH..."
    export CMAKE_PREFIX_PATH=$(pwd)/geant4_install/
fi

mkdir -p build
cd build
cmake ..
make -j$(nproc)
cd ..

echo ""
echo "═══════════════════════════════════════"
echo " ✔ Kompilacja zakończona!"
echo " Uruchom symulację: python3 run_sim.py"
echo "═══════════════════════════════════════"
