#ifndef RunAction_h
#define RunAction_h 1

#include "G4UserRunAction.hh"
#include "globals.hh"

#include "G4Accumulable.hh"
#include <map>

class G4Run;

class RunAction : public G4UserRunAction {
public:
  RunAction();
  virtual ~RunAction();

  virtual void BeginOfRunAction(const G4Run *);
  virtual void EndOfRunAction(const G4Run *);

  void AddHits(G4int id, G4int hits);

private:
  std::map<G4int, G4Accumulable<G4int> *> fAccumulableHits;
};

#endif
