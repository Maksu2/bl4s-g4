#!/bin/bash

# Ładowanie środowiska Geant4
source geant4_install/bin/geant4.sh

# Ładowanie środowiska Pythona
source venv/bin/activate

# Uruchomienie aplikacji
python3 gui_launcher.py
