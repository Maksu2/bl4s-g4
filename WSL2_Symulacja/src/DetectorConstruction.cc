#include "DetectorConstruction.hh"
#include "Constants.hh"

#include "G4Box.hh"
#include "G4GenericMessenger.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4SystemOfUnits.hh"
#include "G4UnitsTable.hh"
#include "G4VisAttributes.hh"

DetectorConstruction::DetectorConstruction()
    : G4VUserDetectorConstruction(), fMessenger(nullptr),
      fTargetThickness(1.0 * cm), fTargetMaterialName("G4_Pb"),
      fLogicDetector(nullptr) {
  // Define UI commands using G4GenericMessenger
  fMessenger = new G4GenericMessenger(this, "/det/", "Geometry control");

  fMessenger->DeclarePropertyWithUnit("setTargetThickness", "cm",
                                      fTargetThickness,
                                      "Thickness of the target block.");
  fMessenger->DeclareProperty("setTargetMaterial", fTargetMaterialName,
                              "Material of the target (G4_Pb or G4_Cu).");
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
  nist->FindOrBuildMaterial("G4_Cu");         // Copper
  nist->FindOrBuildMaterial("G4_GLASS_LEAD"); // Lead Glass
}

G4VPhysicalVolume *DetectorConstruction::DefineVolumes() {
  // Get Materials
  G4NistManager *nist = G4NistManager::Instance();
  G4Material *vacuum = nist->FindOrBuildMaterial("G4_Galactic");
  G4Material *targetMaterial = nist->FindOrBuildMaterial(fTargetMaterialName);
  G4Material *leadGlass = nist->FindOrBuildMaterial("G4_GLASS_LEAD");

  // --- World ---
  G4cout << "--> Geometry: Building " << targetMaterial->GetName()
         << " Target with thickness: " << G4BestUnit(fTargetThickness, "Length")
         << G4endl;

  G4double worldSize = kWorldSize;
  auto *solidWorld =
      new G4Box("World", worldSize / 2, worldSize / 2, worldSize / 2);
  auto *logicWorld = new G4LogicalVolume(solidWorld, vacuum, "World");
  auto *physWorld =
      new G4PVPlacement(0, G4ThreeVector(), logicWorld, "World", 0, false, 0);

  // --- Target ---
  // A block of material.
  // Size X, Y can be large (e.g., 50cm), Z is fTargetThickness.
  G4double targetSizeXY = 50.0 * cm;

  auto *solidTarget = new G4Box("Target", targetSizeXY / 2, targetSizeXY / 2,
                                fTargetThickness / 2);
  auto *logicTarget =
      new G4LogicalVolume(solidTarget, targetMaterial, "Target");

  new G4PVPlacement(0, G4ThreeVector(0, 0, 0), logicTarget, "Target",
                    logicWorld, false, 0);

  // --- Detectors ---
  // A grid of detectors directly behind the target (no gap).
  G4double singleDetSize = kDetectorSize;
  G4double gap = kDetectorGap;

  G4double containerSizeX = kDetCols * (singleDetSize + gap);
  G4double containerSizeY = kDetRows * (singleDetSize + gap);
  G4double containerSizeZ = 10.0 * cm; // Thickness

  // Place detector container exactly 1.5m behind the Target box surface
  // target back face at +fTargetThickness/2
  // We want the container front face to be at +fTargetThickness/2 + 1.5m
  // container center Z = +fTargetThickness/2 + 1.5*m + containerSizeZ/2
  G4double gapDistance = 1.5 * m;
  G4double detDist =
      fTargetThickness / 2.0 + gapDistance + containerSizeZ / 2.0;

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
  // CopyNo = j * kDetCols + i.  Row-major.
  // We want center to be (0,0).
  // Center indices
  G4int centerCol = kDetCols / 2;
  G4int centerRow = kDetRows / 2;

  G4int copyNo = 0;
  for (int j = 0; j < kDetRows; ++j) {   // Rows first (Y)
    for (int i = 0; i < kDetCols; ++i) { // Cols second (X)
      // Position
      // i goes from 0 to kDetCols-1
      // We want i=centerCol to be at x=0
      G4double x = (i - centerCol) * (singleDetSize + gap);
      G4double y = (j - centerRow) * (singleDetSize + gap);

      // Adjust if total count is even (not the case for 101, but good practice)
      if (kDetCols % 2 == 0)
        x += (singleDetSize + gap) / 2.0;
      if (kDetRows % 2 == 0)
        y += (singleDetSize + gap) / 2.0;

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
