#ifndef DetectorConstruction_h
#define DetectorConstruction_h 1

#include "G4VUserDetectorConstruction.hh"
#include "globals.hh"

class G4VPhysicalVolume;
class G4GenericMessenger;

class DetectorConstruction : public G4VUserDetectorConstruction {
public:
  DetectorConstruction();
  virtual ~DetectorConstruction();

  virtual G4VPhysicalVolume *Construct();

  virtual void ConstructSDandField();

  G4double GetTargetThickness() const { return fTargetThickness; }
  G4String GetTargetMaterialName() const { return fTargetMaterialName; }

private:
  void DefineMaterials();
  G4VPhysicalVolume *DefineVolumes();

  G4GenericMessenger *fMessenger;
  G4double fTargetThickness;
  G4String fTargetMaterialName;

  G4LogicalVolume *fLogicDetector;
};

#endif
