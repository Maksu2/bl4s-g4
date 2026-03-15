#include "PhysicsList.hh"
#include "FTFP_BERT.hh"
#include "G4EmStandardPhysics.hh"

PhysicsList::PhysicsList() : G4VModularPhysicsList() {
  // Use the reference physics list FTFP_BERT logic
  // Or simply RegisterPhysics
  RegisterPhysics(new G4EmStandardPhysics());
  // In a real scenario we might want full FTFP_BERT but for basic e-
  // scattering: This is sufficient. If high energy hadrons are involved, we'd
  // add more.
}

PhysicsList::~PhysicsList() {}
