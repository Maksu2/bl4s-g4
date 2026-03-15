#!/bin/bash
set -e

echo "========================================="
echo " 1. Installing Ubuntu WSL2 Dependencies"
echo "========================================="
sudo apt-get update
sudo apt-get install -y build-essential cmake libexpat1-dev libgl1-mesa-dev libglu1-mesa-dev libx11-dev libxmu-dev python3 python3-pip python3-venv python3-pyqt5 qtbase5-dev qt5-qmake qtbase5-dev-tools wget tar libqt5opengl5-dev

echo ""
echo "========================================="
echo " 2. Downloading & Extracting Geant4 11.2.1"
echo "========================================="
if [ ! -f geant4-v11.2.1.tar.gz ]; then
    wget https://gitlab.cern.ch/geant4/geant4/-/archive/v11.2.1/geant4-v11.2.1.tar.gz
fi

if [ ! -d geant4-v11.2.1 ]; then
    tar -xzf geant4-v11.2.1.tar.gz
fi

echo ""
echo "========================================="
echo " 3. Compiling Geant4 (Grab a coffee, ~15-30m)"
echo "========================================="
mkdir -p geant4_build
mkdir -p geant4_install

cd geant4_build
# Configure CMake with Qt and OpenGL for GUI support if needed
cmake ../geant4-v11.2.1 \
    -DCMAKE_INSTALL_PREFIX=../geant4_install \
    -DGEANT4_INSTALL_DATA=ON \
    -DGEANT4_USE_OPENGL_X11=ON \
    -DGEANT4_USE_QT=ON \
    -DGEANT4_BUILD_MULTITHREADED=ON \
    -DCMAKE_BUILD_TYPE=Release

make -j$(nproc)
make install
cd ..

echo ""
echo "========================================="
echo " 4. Compiling the Simulation App"
echo "========================================="
# Load Geant4 environment
source geant4_install/bin/geant4.sh

mkdir -p build
cd build
cmake ..
make -j$(nproc)
cd ..

echo ""
echo "========================================="
echo " 5. Setting up Python Environment"
echo "========================================="
python3 -m venv venv
source venv/bin/activate
pip install PyQt5 pandas pyarrow matplotlib
pip install scikit-learn seaborn scipy

echo ""
echo "========================================="
echo " INSTALACJA ZAKOŃCZONA SUKCESEM! 🎉 "
echo "========================================="
echo ""
echo "Jak uruchomić aplikację w przyszłości:"
echo "./run_wsl2.sh"
echo "========================================="
