#ifndef PrimaryGeneratorAction_h
#define PrimaryGeneratorAction_h 1

#include "globals.hh"
#include "G4ParticleGun.hh"
#include "G4VUserPrimaryGeneratorAction.hh"

class G4Event;

class PrimaryGeneratorAction : public G4VUserPrimaryGeneratorAction {
public:
  PrimaryGeneratorAction();
  virtual ~PrimaryGeneratorAction();

  virtual void GeneratePrimaries(G4Event *);

  const G4ParticleGun *GetParticleGun() const { return fParticleGun; }

private:
  G4ParticleGun *fParticleGun;
};

#endif
