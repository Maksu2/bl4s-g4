# Geant4 Simulation - Beamline for Schools (BL4S) ⚛️

## About the Project
This project is a Monte Carlo simulation developed using the **Geant4** toolkit for the **CERN Beamline for Schools (BL4S)** competition. The goal is to simulate an electron beam interacting with a lead target and to detect the resulting electromagnetic shower using a segmented calorimeter array.

The simulation enables the study of the spatial distribution of particles after passing through high-Z material, which is essential for understanding phenomena such as bremsstrahlung and pair production.

## Physics & Geometry 📐
The simulation models the following experimental setup in a vacuum environment:

1.  **The Beam**:
    *   Particles: Electrons ($e^-$).
    *   Energy: 1 GeV (configurable).
    *   Direction: Along the Z-axis.

2.  **The Target**:
    *   Material: Lead ($Pb$).
    *   Thickness: User-configurable (default 2 cm).
    *   Purpose: To induce an electromagnetic shower. High-energy electrons interacting with lead nuclei emit photons (bremsstrahlung), which subsequently convert into electron-positron pairs.

3.  **Detectors (Calorimeter Array)**:
    *   Layout: 21x21 matrix (441 detectors total).
    *   Single Cell Size: $10 \times 10 \times 10$ cm.
    *   Material: Lead Glass.
    *   Position: located 1 meter downstream from the target.
    *   Function: Counts the number of charged particles traversing each segment.

## Requirements
*   **Geant4** (v11.2 or later).
*   **CMake**.
*   C++17 compliant compiler.
*   OS: macOS (Apple Silicon tested) or Linux.

## How to Run 🚀

### 1. Compilation
A helper script is provided to compile the project, automatically detecting the number of CPU cores:

```bash
./compile_sim.sh
```

This will create a `build` directory containing the `GeantSim` executable.

### 2. Running the Simulation
Run the simulation in batch mode using the provided macro:

```bash
./build/GeantSim run.mac
```

### 3. Configuration (run.mac)
You can adjust simulation parameters in the `run.mac` file without recompiling:

*   **Change Target Thickness**:
    ```bash
    /BFS/geometry/leadThickness 5 cm
    ```
*   **Number of Events**:
    ```bash
    /run/beamOn 10000
    ```
*   **Beam Energy**:
    ```bash
    /gun/energy 500 MeV
    ```

## Results Analysis 📊
Upon completion, the simulation generates a `results.txt` file containing the hit map.

**File Format:**
```text
Total Events: 1000
Format: X Y | Hits (Center is 0 0)
-------------------
     0 0      |  1117   <-- Central detector (on beam axis)
     -1 0     |  360    <-- Adjacent detector
     ...
Total Electrons Detected: 5222
```
*   **X, Y**: Detector coordinates in the grid (0,0 is the center).
*   **Hits**: Number of particles counted in that specific detector.

Note that `Total Electrons Detected` is typically higher than `Total Events` because primary electrons generate multiple secondary particles (the shower) in the lead target.

