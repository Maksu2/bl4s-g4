# Geant4 Electromagnetic Shower Simulation for BL4S ⚛️

## 📖 Introduction: What is this project?
This project is an advanced computer simulation built using the **Geant4** toolkit, developed for the **Beamline for Schools (BL4S)** competition. 

Our goal is to study the **electromagnetic shower** (cascade) development in dense absorbers. By firing ultra-high-energy electrons (1–6 GeV) at targets with varying radiation lengths and Molière radii (such as Aluminum, Copper, and Lead), we investigate how the absorber's properties affect shower geometry.

To analyze the spatial complexity of the resulting showers, we developed custom analytical pipelines using **fractal dimension analysis (3D box-counting)** and **graph-based clustering (DBSCAN)**. 

## 🧠 The Physics: How does it work?

The main phenomenon observed is the electromagnetic cascade. High-energy electrons initiate showers via two alternating processes until the average energy drops below the **Critical Energy ($E_c$)**:
1.  **Bremsstrahlung (Braking Radiation)**: A high-speed electron ($e^-$) passing close to a nucleus is decelerated by the electric field, releasing a high-energy gamma photon ($\gamma$).
2.  **Pair Production**: The gamma photon interacts with a nucleus to convert into an electron ($e^-$) and a positron ($e^+$).

**Key parameters analyzed:**
* **Radiation Length ($X_0$)**: The step size of the shower; shorter in Pb (0.56 cm) than Al (8.99 cm).
* **Molière Radius ($R_m$)**: Transverse size of the shower.
* **Shower Maximum ($X_{max}$)**: The depth of peak particle multiplication.

## 📐 Experiment Geometry

Everything takes place in a virtual vacuum chamber ($5 \times 5 \times 5$ m).

1.  **Electron Gun**: 
    * 1–6 GeV electron beam, perfectly collimated along the Z-axis. 
    * Fires up to 100,000 electrons per run.
2.  **Target (Absorber)**: 
    * Materials: Lead (Pb), Copper (Cu), and Aluminum (Al).
    * Target thickness continuously varied from 1 mm to 30 mm.
3.  **Calorimeter (Detectors)**:
    * A matrix of **10 x 10** detection cells ($10 \times 10$ cm each, 100 x 100 cm total area).
    * Placed 1.5 meters behind the target.

## 🛠️ User Guide

### Requirements
You need to have Geant4 and CMake installed, alongside Python 3 with `pandas`, `matplotlib`, and `scikit-learn` for analytical scripts.

### 1. Compilation
To turn the C++ code into a running program, execute:
```bash
./compile_sim.sh
```
This creates the `./build/GeantSim` executable. (Note: use `compile2.sh` depending on local configuration).

### 2. Running
Control the simulation using the macro files (e.g., `run.mac` or `sim_*.py` runners). Run manually:
```bash
./build/GeantSim run.mac
```

### 3. Configuration (No Recompilation Needed!)
Open `run.mac` in any text editor. You can easily modify:
*   `/BFS/geometry/leadThickness 2 cm` -> Change target thickness or set to `0 cm` to observe the beam without interaction.
*   `/run/beamOn 1000` -> Number of fired electrons.
*   `/gun/energy 4 GeV` -> Beam energy.

### 4. Data Analysis & Results 🎨
The simulation outputs results in CSV format (e.g., `results_Cu_1.1cm_1.csv`).

To interpret and visualize the findings, use the provided Python analytical apps:
```bash
python3 visualize_results.py results_Cu_1.1cm_1.csv
```
This produces a color-coded hit map and basic numeric statistics. For advanced metrics (Fractal Dimension, DBSCAN Clustering, Entropy), run `analysis_app.py` or `batch_analyzer.py` which process directories of CSVs and aggregate the parameters indicating cascade complexity scaling by beam energy and target thickness.

## 📊 Results Summary
* Aluminum targets allowed for significantly deeper and spread maximum energy depositions compared to Lead and Copper.
* Spatial entropy and fractal dimensions consistently scaled with the initial beam energy, confirming the inherently fractal scaling of energy distribution within electromagnetic showers.
