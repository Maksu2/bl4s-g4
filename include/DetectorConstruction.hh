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

  G4double GetLeadThickness() const { return fLeadThickness; }

private:
  void DefineMaterials();
  G4VPhysicalVolume *DefineVolumes();

  G4GenericMessenger *fMessenger;
  G4double fLeadThickness;

  G4LogicalVolume *fLogicDetector;
};

#endif
