#include "DetectorConstruction.hh"

#include "G4Box.hh"
#include "G4GenericMessenger.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4SystemOfUnits.hh"
#include "G4VisAttributes.hh"

DetectorConstruction::DetectorConstruction()
    : G4VUserDetectorConstruction(), fMessenger(nullptr),
      fLeadThickness(1.0 * cm), fLogicDetector(nullptr) {
  // Define UI commands using G4GenericMessenger
  fMessenger =
      new G4GenericMessenger(this, "/BFS/geometry/", "Geometry control");

  fMessenger->DeclarePropertyWithUnit("leadThickness", "cm", fLeadThickness,
                                      "Thickness of the lead block.");
}

DetectorConstruction::~DetectorConstruction() { delete fMessenger; }

G4VPhysicalVolume *DetectorConstruction::Construct() {
  DefineMaterials();
  return DefineVolumes();
}

void DetectorConstruction::DefineMaterials() {
  G4NistManager *nist = G4NistManager::Instance();
  // Ensure materials exist
  nist->FindOrBuildMaterial("G4_Galactic");   // Vacuum
  nist->FindOrBuildMaterial("G4_Pb");         // Lead
  nist->FindOrBuildMaterial("G4_GLASS_LEAD"); // Lead Glass
}

G4VPhysicalVolume *DetectorConstruction::DefineVolumes() {
  // Get Materials
  G4NistManager *nist = G4NistManager::Instance();
  G4Material *vacuum = nist->FindOrBuildMaterial("G4_Galactic");
  G4Material *lead = nist->FindOrBuildMaterial("G4_Pb");
  G4Material *leadGlass = nist->FindOrBuildMaterial("G4_GLASS_LEAD");

  // --- World ---
  G4double worldSize = 5.0 * m;
  auto *solidWorld =
      new G4Box("World", worldSize / 2, worldSize / 2, worldSize / 2);
  auto *logicWorld = new G4LogicalVolume(solidWorld, vacuum, "World");
  auto *physWorld =
      new G4PVPlacement(0, G4ThreeVector(), logicWorld, "World", 0, false, 0);

  // --- Lead Target ---
  // A block of lead.
  // Size X, Y can be large (e.g., 50cm), Z is fLeadThickness.
  G4double targetSizeXY = 50.0 * cm;

  auto *solidTarget = new G4Box("Target", targetSizeXY / 2, targetSizeXY / 2,
                                fLeadThickness / 2);
  auto *logicTarget = new G4LogicalVolume(solidTarget, lead, "Target");

  new G4PVPlacement(0, G4ThreeVector(0, 0, 0), logicTarget, "Target",
                    logicWorld, false, 0);

  // --- Detectors ---
  // A grid of detectors behind the target.
  G4double detDist = 1.0 * m;

  // Container for the array
  // Container for the array
  G4int nRows = 21; // Odd number for center
  G4int nCols = 21;
  G4double singleDetSize = 10.0 * cm;
  G4double gap = 1.0 * cm;

  G4double containerSizeX = nCols * (singleDetSize + gap);
  G4double containerSizeY = nRows * (singleDetSize + gap);
  G4double containerSizeZ = 10.0 * cm; // Thickness

  auto *solidContainer = new G4Box("DetContainer", containerSizeX / 2,
                                   containerSizeY / 2, containerSizeZ / 2);
  auto *logicContainer =
      new G4LogicalVolume(solidContainer, vacuum, "DetContainer");

  new G4PVPlacement(0, G4ThreeVector(0, 0, detDist), logicContainer,
                    "Container", logicWorld, false, 0);

  // Single Detector (Cell)
  auto *solidCell = new G4Box("Cell", singleDetSize / 2, singleDetSize / 2,
                              containerSizeZ / 2);
  fLogicDetector = new G4LogicalVolume(solidCell, leadGlass, "Cell_LV");

  // Place cells in a loop
  // CopyNo = j * nCols + i.  Row-major.
  // We want center to be (0,0).
  // Let idx = i (column index 0..20)
  // Let idy = j (row index 0..20)
  // Center is at 10, 10.
  // x_coord = i - 10, y_coord = j - 10.

  G4int copyNo = 0;
  for (int j = 0; j < nRows; ++j) {   // Rows first (Y)
    for (int i = 0; i < nCols; ++i) { // Cols second (X)
      // Position
      G4double x = (i - nCols / 2.0 + 0.5) * (singleDetSize + gap);
      G4double y = (j - nRows / 2.0 + 0.5) * (singleDetSize + gap);

      new G4PVPlacement(0, G4ThreeVector(x, y, 0), fLogicDetector, "Cell_Phys",
                        logicContainer, false, copyNo++);
    }
  }

  // Visualization Attributes
  auto *visTarget = new G4VisAttributes(G4Colour::Gray());
  visTarget->SetForceSolid(true);
  logicTarget->SetVisAttributes(visTarget);

  auto *visDetector =
      new G4VisAttributes(G4Colour(0.0, 1.0, 1.0, 0.5)); // Transparent Cyan
  visDetector->SetForceSolid(true);
  fLogicDetector->SetVisAttributes(visDetector);

  logicContainer->SetVisAttributes(G4VisAttributes::GetInvisible());

  logicWorld->SetVisAttributes(G4VisAttributes::GetInvisible());

  return physWorld;
}

#include "CountingSD.hh"
#include "G4SDManager.hh"

void DetectorConstruction::ConstructSDandField() {
  // Create sensitive detector
  auto *sd = new CountingSD("CountingSD", "HitsCollection");
  G4SDManager::GetSDMpointer()->AddNewDetector(sd);
  SetSensitiveDetector(fLogicDetector, sd);
}
