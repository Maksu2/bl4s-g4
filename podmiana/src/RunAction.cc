#include "RunAction.hh"
#include "Constants.hh"
#include "CountingSD.hh"
#include "G4Run.hh"
#include "G4RunManager.hh"
#include "G4SDManager.hh"
#include "G4SystemOfUnits.hh"
#include <fstream>

#include "G4AccumulableManager.hh"
#include "G4RunManager.hh"

RunAction::RunAction() : G4UserRunAction() {
  // Register accumulables
  G4int nDetectors = kDetRows * kDetCols;
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

#include <vector>

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
    G4double thickness = detector->GetTargetThickness();
    G4String material = detector->GetTargetMaterialName();

    if (material == "G4_Pb")
      material = "Pb";
    else if (material == "G4_Cu")
      material = "Cu";

    // Format thickness string (e.g. "2 cm")
    G4String thickStr = G4BestUnit(thickness, "Length");
    // Remove space to make it "2cm"
    thickStr.erase(std::remove(thickStr.begin(), thickStr.end(), ' '),
                   thickStr.end());

    std::string fileName;
    int counter = 1;
    do {
      fileName = "results_" + material + "_" + thickStr + "_" +
                 std::to_string(counter) + ".csv";
      counter++;
    } while (std::ifstream(fileName.c_str()).good()); // Check if exists

    std::ofstream outFile(fileName);
    // CSV Header
    outFile << "X,Y,Hits" << std::endl;

    G4int totalHits = 0;

    // Grid center logic
    int centerCol = kDetCols / 2;
    int centerRow = kDetRows / 2;

    for (auto const &[copyNo, acc] : fAccumulableHits) {
      G4int hits = acc->GetValue();
      if (hits > 0) {
        // copyNo = j * kDetCols + i
        int i = copyNo % kDetCols;
        int j = copyNo / kDetCols;

        // Map to coordinates centered at (0,0)
        int x = i - centerCol;
        int y = j - centerRow;

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
