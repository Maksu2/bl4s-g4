#ifndef CountingSD_h
#define CountingSD_h 1

#include "G4VSensitiveDetector.hh"
#include <map>

class G4Step;
class G4HCofThisEvent;

class CountingSD : public G4VSensitiveDetector {
public:
  CountingSD(const G4String &name, const G4String &hitsCollectionName);
  virtual ~CountingSD();

  // Methods from base class
  virtual void Initialize(G4HCofThisEvent *hitCollection);
  virtual G4bool ProcessHits(G4Step *step, G4TouchableHistory *history);
  virtual void EndOfEvent(G4HCofThisEvent *hitCollection);

  // Access to hits map
  std::map<G4int, G4int> &GetHitsMap() { return fHitsMap; }
  void Reset() { fHitsMap.clear(); }

private:
  std::map<G4int, G4int> fHitsMap; // Key: CopyNo (ID), Value: Count
};

#endif
