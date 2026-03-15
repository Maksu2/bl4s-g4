#ifndef Constants_h
#define Constants_h 1

#include "G4SystemOfUnits.hh"

// World Geometry
constexpr G4double kWorldSize = 25.0 * m;

// Detector Array Geometry
constexpr G4int kDetRows = 10;
constexpr G4int kDetCols = 10;
constexpr G4double kDetectorSize = 2.0 * cm;
constexpr G4double kDetectorGap = 0.0 * cm; // No gap as requested

#endif
