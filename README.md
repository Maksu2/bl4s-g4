# Geant4 Simulation for CERN Beamline for Schools (BL4S) ⚛️

## 📖 Introduction: What is this project?

This project is an advanced computer simulation built using the **Geant4** toolkit – the same software used by physicists at CERN to design massive detectors like ATLAS or CMS.

Our goal is to study the **electromagnetic shower** (cascade). We want to observe what happens when ultra-high-energy electrons strike a dense material like lead. Do they pass right through? Do they disappear? Or does something more spectacular occur?

This simulation allows us to "see" inside matter and verify our hypotheses without building an expensive real-world experiment (yet!).

## 🧠 The Physics: How does it work?

The main phenomenon we observe is the electromagnetic cascade. It consists of two alternating processes:

1.  **Bremsstrahlung (Braking Radiation)**:
    When a high-speed electron ($e^-$) passes close to a lead nucleus, it is rapidly decelerated by the electric field. According to electrodynamics, a decelerating charge must emit energy – it releases it as a high-energy gamma photon ($\gamma$).

2.  **Pair Production**:
    The gamma photon produced in the previous step, traveling through matter, interacts with a nucleus and converts into a pair of particles: an electron ($e^-$) and a positron ($e^+$).

**The Avalanche Effect**:
A single electron entering the lead target emits a photon. This photon converts into two new particles. These two decelerate again, emitting more photons...
From **one** input particle, we get a **cloud** of secondary particles at the output! This is why our detectors count more hits than the number of electrons we fired.

## 📐 Experiment Geometry

Everything takes place in a virtual vacuum chamber ($5 \times 5 \times 5$ m) to prevent air from interfering with the measurement.

1.  **Electron Gun**:
    *   Source of a **1 GeV** (1 billion electronvolts) electron beam.
    *   The beam is collimated (fires straight along the Z-axis).

2.  **Target**:
    *   A block of **Lead (Pb)**.
    *   Thickness is configurable (default 2 cm).
    *   This is where the "magic" of particle creation happens.

3.  **Calorimeter (Detectors)**:
    *   A **21 x 21** matrix of crystals (441 total).
    *   Each crystal is a $10 \times 10 \times 10$ cm cube made of **Lead Glass**.
    *   Placed 1 meter behind the target.
    *   Task: To count every charged particle that enters it.

## 🛠️ User Guide

### Requirements
You need to have Geant4 and CMake installed.

### 1. Compilation
To turn the C++ code into a running program, execute:
```bash
./compile_sim.sh
```
This creates the `./build/GeantSim` executable.

### 2. Running
Control the simulation using the `run.mac` file. Run:
```bash
./build/GeantSim run.mac
```

### 3. Configuration (No Recompilation Needed!)
Open `run.mac` in any text editor. You can change:
*   `/BFS/geometry/leadThickness 2 cm` -> Target thickness. Set to `0 cm` (or `1 um`) to see what happens without lead (no cascade!).
*   `/run/beamOn 1000` -> Number of fired electrons.
*   `/gun/energy 1 GeV` -> Beam energy. Try `100 MeV` and see if the shower gets smaller!

## 📊 Interpreting Results (`results.txt`)

After the run, check `results.txt`.

Example snippet:
```text
Detector (-1, 0) | 360 hits
Detector (0, 0)  | 1117 hits
Total Electrons Detected: 5222
```

*   **(0, 0)** is the center of the detector grid (where the beam aims).
*   Numbers in parentheses are $(X, Y)$ coordinates of the detector.
*   **Total Electrons Detected > Total Events**: This is proof of the cascade! We fired 1000 electrons, but the detectors "saw" 5222. This means every primary electron produced, on average, more than 5 secondary particles.

---

