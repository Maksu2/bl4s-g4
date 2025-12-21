#include "CountingSD.hh"
#include "G4HCofThisEvent.hh"
#include "G4RunManager.hh"
#include "G4SDManager.hh"
#include "G4Step.hh"
#include "G4ThreeVector.hh"
#include "G4ios.hh"
#include "RunAction.hh"

CountingSD::CountingSD(const G4String &name, const G4String &hitsCollectionName)
    : G4VSensitiveDetector(name) {
  collectionName.insert(hitsCollectionName);
}

CountingSD::~CountingSD() {}

void CountingSD::Initialize(G4HCofThisEvent *hce) {}

G4bool CountingSD::ProcessHits(G4Step *step, G4TouchableHistory *) {
  // Get the particle definition
  auto particle = step->GetTrack()->GetDefinition();

  if (particle->GetParticleName() != "e-")
    return false;

  // Get the Touchable to find out which detector replica this is
  const G4VTouchable *touchable = step->GetPreStepPoint()->GetTouchable();
  // Copy number of the detector volume
  G4int copyNo = touchable->GetCopyNumber();

  // Increment count for this detector ID
  if (step->GetPreStepPoint()->GetStepStatus() == fGeomBoundary) {
    // fHitsMap[copyNo]++; // Old way

    // New way: Pass to RunAction
    const auto *userRunAction =
        G4RunManager::GetRunManager()->GetUserRunAction();
    auto *runAction =
        const_cast<RunAction *>(static_cast<const RunAction *>(userRunAction));
    if (runAction) {
      runAction->AddHits(copyNo, 1);
    }
  }

  return true;
}

void CountingSD::EndOfEvent(G4HCofThisEvent *) {}
