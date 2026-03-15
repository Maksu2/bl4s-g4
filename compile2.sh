#!/bin/bash
set -e

echo "═══════════════════════════════════════"
echo " EKSZTREMALNA KOMPILACJA (-O3 -march=native)"
echo "═══════════════════════════════════════"

if [ -f geant4_install/bin/geant4.sh ]; then
    source geant4_install/bin/geant4.sh
else
    echo "Brak pliku geant4.sh, próba po CMAKE_PREFIX_PATH..."
    export CMAKE_PREFIX_PATH=$(pwd)/geant4_install/
fi

mkdir -p build
cd build

# Wracamy do maksymalnie stabilnej i w 100% sprawdzonej wersji:
cmake .. -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_CXX_FLAGS="-O3 -march=native"

# Zbuduj wszystko z pełną prędkością wszystkich rdzeni:
make -j$(nproc)

cd ..

echo " "
echo "═══════════════════════════════════════"
echo " ✔ Optymalizacja i kompilacja zakończona sukcesem!"
echo " Uruchom resztę symulacji: python3 run_new2.py"
echo "═══════════════════════════════════════"
