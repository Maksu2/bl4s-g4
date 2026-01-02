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

// Include at top
#include "DetectorConstruction.hh"
#include "G4UnitsTable.hh"
#include <algorithm> // for remove matches
// ...

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

    // --- Dynamic Filename Generation ---
    const DetectorConstruction *detector =
        static_cast<const DetectorConstruction *>(
            G4RunManager::GetRunManager()->GetUserDetectorConstruction());
    G4double thickness = detector->GetLeadThickness();

    // Format thickness string (e.g. "2 cm")
    G4String thickStr = G4BestUnit(thickness, "Length");
    // Remove space to make it "2cm"
    thickStr.erase(std::remove(thickStr.begin(), thickStr.end(), ' '),
                   thickStr.end());

    std::string fileName;
    int counter = 1;
    do {
      fileName = "results_" + thickStr + "_" + std::to_string(counter) + ".csv";
      counter++;
    } while (std::ifstream(fileName.c_str()).good()); // Check if exists

    std::ofstream outFile(fileName);
    // CSV Header
    outFile << "X,Y,Hits" << std::endl;

    G4int totalHits = 0;
    int nCols = 21;

    for (auto const &[copyNo, acc] : fAccumulableHits) {
      G4int hits = acc->GetValue();
      if (hits > 0) {
        // copyNo = j * nCols + i
        int i = copyNo % nCols;
        int j = copyNo / nCols;
        // Center is at 10, 10
        int x = i - 10;
        int y = j - 10;

        outFile << x << "," << y << "," << hits << std::endl;
        totalHits += hits;
      }
    }

    outFile.close();

    G4cout << " Total Electrons Detected: " << totalHits << G4endl;
    G4cout << " Results written to '" << fileName << "'" << G4endl;
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
