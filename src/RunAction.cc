#include "RunAction.hh"
#include "CountingSD.hh"
#include "G4Run.hh"
#include "G4RunManager.hh"
#include "G4SDManager.hh"
#include "G4SystemOfUnits.hh"
#include <fstream>

#include "G4AccumulableManager.hh"
#include "G4RunManager.hh"

RunAction::RunAction() : G4UserRunAction() {
  // Register accumulables for 21x21 = 441 detectors
  G4int nDetectors = 21 * 21;
  auto accumulableManager = G4AccumulableManager::Instance();
  for (int i = 0; i < nDetectors; ++i) {
    G4String accName = "DetHit_" + std::to_string(i);
    fAccumulableHits[i] = new G4Accumulable<G4int>(accName, 0);
    accumulableManager->RegisterAccumulable(fAccumulableHits[i]);
  }
}

RunAction::~RunAction() {}

void RunAction::BeginOfRunAction(const G4Run *) {
  // Reset allocators
  G4AccumulableManager::Instance()->Reset();

  // Inform the runManager to save random number seed
  G4RunManager::GetRunManager()->SetRandomNumberStore(false);
}

void RunAction::EndOfRunAction(const G4Run *run) {
  G4int nofEvents = run->GetNumberOfEvent();
  if (nofEvents == 0)
    return;

  // Merge accumulables
  auto accumulableManager = G4AccumulableManager::Instance();
  accumulableManager->Merge();

  // Print results only on Master
  if (IsMaster()) {
    G4cout << "------------------------------------------------------------"
           << G4endl;
    G4cout << " Run ended! Number of events: " << nofEvents << G4endl;

    std::ofstream outFile("results.txt");
    outFile << "--- Simulation Results ---" << std::endl;
    outFile << "Total Events: " << nofEvents << std::endl;
    outFile << "Format: X Y | Hits (Center is 0 0)" << std::endl;
    outFile << "-------------------" << std::endl;

    G4int totalHits = 0;

    // Geometry params matched with DetectorConstruction
    int nCols = 21;
    int nRows = 21;

    for (auto const &[copyNo, acc] : fAccumulableHits) {
      G4int hits = acc->GetValue();
      if (hits > 0) {
        // Convert copyNo to X, Y
        // copyNo = j * nCols + i
        int i = copyNo % nCols;
        int j = copyNo / nCols;

        // Convert to centered coordinates
        // Center is at 10, 10 (since 21/2 = 10)
        int x = i - 10;
        int y = j - 10;

        outFile << "     " << x << " " << y << "      |  " << hits << std::endl;
        // Optional: print to console only significant hits to avoid spam
        if (hits > 10) {
          G4cout << " Detector (" << x << ", " << y << "): " << hits << " hits"
                 << G4endl;
        }
        totalHits += hits;
      }
    }

    outFile << "-------------------" << std::endl;
    outFile << "Total Electrons Detected: " << totalHits << std::endl;
    G4cout << " Total Electrons Detected: " << totalHits << G4endl;

    outFile.close();
    G4cout << " Results written to 'results.txt'" << G4endl;
    G4cout << "------------------------------------------------------------"
           << G4endl;
  }
}

void RunAction::AddHits(G4int id, G4int hits) {
  if (fAccumulableHits.find(id) != fAccumulableHits.end()) {
    *(fAccumulableHits[id]) += hits;
  } else {
    // In case dynamic resizing needed or error, but here we fixed size
  }
}
