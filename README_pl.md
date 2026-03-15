# Symulacja Kaskady Elektromagnetycznej w Geant4 ⚛️
## Projekt na konkurs CERN Beamline for Schools (BL4S)

---

## 📖 Spis Treści

1. [Wstęp – O czym jest ten projekt?](#wstęp--o-czym-jest-ten-projekt)
2. [Fizyka – Kaskada Elektromagnetyczna](#fizyka--kaskada-elektromagnetyczna)
3. [Architektura Projektu – Mapa Plików](#architektura-projektu--mapa-plików)
4. [Szczegółowy Opis Klas C++](#szczegółowy-opis-klas-c)
5. [Przepływ Danych – Jak Działa Symulacja](#przepływ-danych--jak-działa-symulacja)
6. [Skrypty Pomocnicze (Python)](#skrypty-pomocnicze-python)
7. [Instrukcja Obsługi](#instrukcja-obsługi)
8. [Jak Rozszerzyć Projekt](#jak-rozszerzyć-projekt)
9. [FAQ – Częste Pytania](#faq--częste-pytania)

---

## Wstęp – O czym jest ten projekt?

Ten projekt to **symulacja Monte Carlo** stworzona w oparciu o toolkit **Geant4** – profesjonalne narzędzie używane w CERN do projektowania wielkich detektorów (ATLAS, CMS, LHCb).

**Cel**: Zbadać zachowanie **kaskady elektromagnetycznej** – lawinowego procesu, w którym jeden elektron o wysokiej energii wchodzący w gęsty materiał (ołów) produkuje chmurę wtórnych cząstek.

**Pytanie badawcze**: Jak grubość ołowianej tarczy wpływa na liczbę i rozkład przestrzenny cząstek wykrytych przez kalorymetr?

---

## Fizyka – Kaskada Elektromagnetyczna

### Dwa kluczowe procesy:

| Proces | Opis | Równanie |
|--------|------|----------|
| **Bremsstrahlung** (promieniowanie hamowania) | Elektron hamowany w polu jądra emituje foton γ | e⁻ → e⁻ + γ |
| **Kreacja par** | Foton γ w pobliżu jądra zamienia się w parę elektron-pozyton | γ → e⁻ + e⁺ |

### Efekt lawinowy:
```
1 e⁻ (1 GeV) → foton γ → 2 cząstki (e⁻ + e⁺) → 2 fotony → 4 cząstki → ...
```
Z jednego elektronu na wejściu powstaje **chmura setek lub tysięcy** cząstek wtórnych. To dlatego detektory rejestrują więcej trafień niż wystrzeliliśmy elektronów.

### Dlaczego ołów?
- Wysoka liczba atomowa (Z=82) → silne pole elektryczne jądra
- Gęstość 11.34 g/cm³ → dużo jąder na jednostkę objętości
- Krótka **długość radiacyjna** (X₀ ≈ 0.56 cm) → kaskada rozwija się szybko

---

## Architektura Projektu – Mapa Plików

```
symulacjaa/
├── main.cc                    # 🚀 Punkt wejścia programu
├── CMakeLists.txt             # ⚙️ Konfiguracja budowania (CMake)
├── compile_sim.sh             # 🔧 Skrypt kompilacji
├── run.mac                    # 📜 Domyślny plik konfiguracyjny symulacji
├── init_vis.mac               # 👁️ Konfiguracja trybu interaktywnego (grafika)
│
├── include/                   # 📁 Nagłówki C++ (deklaracje klas)
│   ├── DetectorConstruction.hh
│   ├── PrimaryGeneratorAction.hh
│   ├── PhysicsList.hh
│   ├── ActionInitialization.hh
│   ├── RunAction.hh
│   └── CountingSD.hh
│
├── src/                       # 📁 Implementacje C++ (ciała funkcji)
│   ├── DetectorConstruction.cc
│   ├── PrimaryGeneratorAction.cc
│   ├── PhysicsList.cc
│   ├── ActionInitialization.cc
│   ├── RunAction.cc
│   └── CountingSD.cc
│
├── build/                     # 📁 Skompilowany program (po kompilacji)
│   └── GeantSim              # Plik wykonywalny symulacji
│
├── main.py                    # 🐍 GUI do uruchamiania serii symulacji
├── gui_launcher.py            # 🐍 Alternatywne GUI (prostsza wersja)
├── visualize_results.py       # 📊 Skrypt do wizualizacji wyników (heatmapy)
│
├── geant4_install/            # 📦 Zainstalowany Geant4 (biblioteki)
└── Results_Batch_*/           # 📁 Foldery z wynikami symulacji
```

---

## Szczegółowy Opis Klas C++

### 1. `main.cc` – Punkt Startowy

**Lokalizacja**: `/symulacjaa/main.cc`

**Co robi**:
- Inicjalizuje generator liczb losowych (seed oparty na czasie systemowym)
- Tworzy `G4RunManager` – serce symulacji
- Rejestruje 3 obowiązkowe komponenty: `DetectorConstruction`, `PhysicsList`, `ActionInitialization`
- Obsługuje tryb wsadowy (batch) i interaktywny (graficzny)

**Kluczowy fragment**:
```cpp
G4Random::setTheEngine(new CLHEP::RanecuEngine);
G4long seed = time(NULL);
G4Random::setTheSeed(seed);  // Każde uruchomienie = inne wyniki
```

**Jak podłączyć nowy komponent**: Dodaj `#include` i wywołaj `runManager->SetUserInitialization(new TwójKomponent())`.

---

### 2. `DetectorConstruction` – Geometria Eksperymentu

**Pliki**: `include/DetectorConstruction.hh`, `src/DetectorConstruction.cc`

**Co robi**:
- Buduje całą geometrię: świat (próżnia), tarczę (ołów), detektory (szkło ołowiowe)
- Rejestruje komendę `/det/setLeadThickness` do zmiany grubości tarczy z poziomu pliku `.mac`
- Przypisuje `CountingSD` jako "sensitive detector" do komórek kalorymetru

**Geometria**:
| Element | Materiał | Wymiary |
|---------|----------|---------|
| Świat | Próżnia (G4_Galactic) | 5 × 5 × 5 m |
| Tarcza | Ołów (G4_Pb) | 50 × 50 cm, grubość konfigurowalna |
| Kalorymetr | Szkło ołowiowe (G4_GLASS_LEAD) | 21×21 siatka komórek 10×10×10 cm |

**Kluczowe zmienne**:
```cpp
fLeadThickness  // Grubość tarczy (domyślnie 1 cm)
fLogicDetector  // Wskaźnik do logicznej objętości detektora
```

**Jak zmienić geometrię**:
- Liczba detektorów: zmień `nRows` i `nCols` (linie ~74-75)
- Rozmiar komórki: zmień `singleDetSize` (linia ~76)
- Odległość kalorymetru: zmień `detDist` (linia ~70)

---

### 3. `PrimaryGeneratorAction` – Działo Elektronowe

**Pliki**: `include/PrimaryGeneratorAction.hh`, `src/PrimaryGeneratorAction.cc`

**Co robi**:
- Definiuje źródło cząstek pierwotnych (elektron)
- Ustawia energię, kierunek i pozycję startową wiązki

**Domyślne ustawienia**:
| Parametr | Wartość |
|----------|---------|
| Cząstka | Elektron (e⁻) |
| Energia | 1 GeV |
| Kierunek | (0, 0, 1) – wzdłuż osi Z |
| Pozycja startowa | (0, 0, -2 m) – przed tarczą |

**Jak zmienić**:
- Z pliku `.mac`: `/gun/energy 500 MeV`, `/gun/particle proton`
- Z kodu: modyfikuj linie w konstruktorze `PrimaryGeneratorAction()`

---

### 4. `PhysicsList` – Procesy Fizyczne

**Pliki**: `include/PhysicsList.hh`, `src/PhysicsList.cc`

**Co robi**:
- Definiuje, jakie procesy fizyczne są symulowane
- Używa `G4EmStandardPhysics` – standardowy pakiet elektromagnetyczny

**Co zawiera G4EmStandardPhysics**:
- Bremsstrahlung (promieniowanie hamowania)
- Kreacja par (pair production)
- Efekt fotoelektryczny
- Rozpraszanie Comptona
- Jonizacja, wielokrotne rozpraszanie...

**Jak dodać więcej fizyki**:
```cpp
// W konstruktorze PhysicsList:
RegisterPhysics(new G4EmStandardPhysics());      // EM
RegisterPhysics(new G4HadronPhysicsQGSP_BERT()); // Hadrony (wymagany dodatkowy include)
```

---

### 5. `ActionInitialization` – Fabryka Akcji

**Pliki**: `include/ActionInitialization.hh`, `src/ActionInitialization.cc`

**Co robi**:
- Centralne miejsce rejestracji wszystkich "User Actions"
- `Build()` – wywoływane dla każdego wątku roboczego
- `BuildForMaster()` – wywoływane tylko dla wątku głównego

**Aktualnie rejestruje**:
- `PrimaryGeneratorAction` – generacja cząstek
- `RunAction` – obsługa początku/końca runu

**Jak dodać nową akcję** (np. `EventAction` do analizy pojedynczych zdarzeń):
```cpp
// W Build():
SetUserAction(new EventAction());
```

---

### 6. `RunAction` – Zbieranie Wyników

**Pliki**: `include/RunAction.hh`, `src/RunAction.cc`

**Co robi**:
- `BeginOfRunAction()`: resetuje liczniki przed rozpoczęciem runu
- `EndOfRunAction()`: po zakończeniu – zapisuje wyniki do pliku CSV
- `AddHits(id, count)`: interfejs do dodawania trafień z `CountingSD`

**System zliczania**:
- Używa `G4Accumulable` – thread-safe agregator danych
- 441 akumulatorów (jeden na każdy detektor w siatce 21×21)

**Format wyjściowy CSV**:
```
X,Y,Hits
-10,-10,5
-9,-10,12
...
```
Gdzie (0,0) to środek siatki detektorów.

**Automatyczne nazewnictwo plików**:
`results_<grubość>_<numer>.csv` np. `results_2cm_1.csv`, `results_2cm_2.csv`...

---

### 7. `CountingSD` – Czujnik Trafień

**Pliki**: `include/CountingSD.hh`, `src/CountingSD.cc`

**Co robi**:
- Implementuje "sensitive detector" – obiekt reagujący na przejście cząstki
- Zlicza tylko elektrony (`e-`)
- Rozpoznaje, do którego detektora (copyNo) weszła cząstka
- Przekazuje trafienie do `RunAction::AddHits()`

**Warunek zliczenia**:
```cpp
if (step->GetPreStepPoint()->GetStepStatus() == fGeomBoundary)
```
Cząstka jest liczona tylko gdy **wchodzi** do detektora (przecina granicę), nie gdy jest w środku.

**Jak zmienić filtr cząstek**:
```cpp
// Aktualnie:
if (particle->GetParticleName() != "e-") return false;

// Żeby liczyć wszystkie naładowane:
if (particle->GetPDGCharge() == 0) return false;
```

---

## Przepływ Danych – Jak Działa Symulacja

```
┌─────────────────┐
│    main.cc      │  Uruchamia G4RunManager
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ DetectorConstr. │  Buduje geometrię (ołów + detektory)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PhysicsList    │  Rejestruje procesy fizyczne
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ActionInitializ. │  Rejestruje PrimaryGeneratorAction + RunAction
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ /run/beamOn N   │  Startuje N eventów
└────────┬────────┘
         │
         ▼ (dla każdego eventu)
┌─────────────────┐
│ PrimaryGenerat. │  Strzela elektron
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Propagacja    │  Geant4 śledzi cząstki przez geometrię
│   (wewnętrzna)  │  Stosuje procesy fizyczne (bremsstrahlung, kreacja par...)
└────────┬────────┘
         │
         ▼ (gdy cząstka wchodzi do detektora)
┌─────────────────┐
│   CountingSD    │  ProcessHits() → zlicza trafienie
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   RunAction     │  AddHits() akumuluje trafienia
└────────┬────────┘
         │
         ▼ (po zakończeniu wszystkich eventów)
┌─────────────────┐
│ EndOfRunAction  │  Zapisuje CSV: X, Y, Hits
└─────────────────┘
```

---

## Skrypty Pomocnicze (Python)

### `main.py` – Zaawansowane GUI

**Funkcje**:
- Dodawanie zadań do kolejki (różne grubości, energie)
- Uruchamianie serii z wieloma cyklami (repeats)
- Automatyczne tworzenie folderów `Results_Batch_TIMESTAMP/run1/`, `run2/`...
- Pomijanie wyników z 0 trafień (nie generuje pustych plików)

**Użycie**: `python main.py`

---

### `visualize_results.py` – Generowanie Heatmap

**Funkcje**:
- Wczytuje plik CSV
- Generuje kolorową mapę cieplną (heatmapa) w formacie SVG
- Używa skali logarytmicznej dla lepszej wizualizacji

**Użycie**:
```bash
python visualize_results.py results_2cm_1.csv --energy "1 GeV" --electrons "1000" --thickness "2 cm"
```

---

## Instrukcja Obsługi

### Wymagania
- Geant4 11.x (zainstalowany w `geant4_install/`)
- CMake 3.16+
- Python 3.x z bibliotekami: `PyQt5`, `pandas`, `matplotlib`, `seaborn`

### Kompilacja
```bash
./compile_sim.sh
```

### Uruchomienie (tryb wsadowy)
```bash
./build/GeantSim run.mac
```

### Uruchomienie (tryb graficzny)
```bash
./build/GeantSim
```
Otworzy się okno wizualizacji Geant4.

### Uruchomienie przez GUI
```bash
python main.py
```

---

## Jak Rozszerzyć Projekt

### Dodanie nowego rodzaju detektora
1. Edytuj `DetectorConstruction.cc`
2. Utwórz nowy `G4Box`/`G4Tubs`/inny kształt
3. Zdefiniuj `G4LogicalVolume` z wybranym materiałem
4. Umieść w geometrii za pomocą `G4PVPlacement`
5. (Opcjonalnie) Przypisz `SensitiveDetector`

### Zmiana cząstki pierwotnej
1. Edytuj `PrimaryGeneratorAction.cc` lub użyj komend w `.mac`:
```
/gun/particle proton
/gun/energy 10 GeV
```

### Dodanie nowych procesów fizycznych
1. Edytuj `PhysicsList.cc`
2. Dodaj `#include` dla wybranej listy (np. `G4HadronPhysicsQGSP_BERT.hh`)
3. Wywołaj `RegisterPhysics(new G4HadronPhysicsQGSP_BERT())`

### Zapisywanie dodatkowych danych
1. Edytuj `RunAction.cc` → `EndOfRunAction()`
2. Możesz zapisywać do osobnych plików lub rozszerzyć format CSV

---

## FAQ – Częste Pytania

**P: Dlaczego niektóre symulacje mają 0 trafień?**
O: Przy bardzo grubych tarczach (>20 cm) kaskada "grzęźnie" w ołowiu i żadne cząstki nie docierają do detektorów.

**P: Czy mogę usunąć folder `geant4_build`?**
O: Tak, bezpiecznie. To tylko pliki tymczasowe z kompilacji. `geant4_install` zawiera gotowe biblioteki.

**P: Jak zwiększyć liczbę detektorów?**
O: W `DetectorConstruction.cc` zmień `nRows` i `nCols` (np. na 41×41). Pamiętaj też zaktualizować `nDetectors` w `RunAction.cc`.

**P: Skąd bierze się losowość wyników?**
O: Z `main.cc` – seed generatora oparty na `time(NULL)`. Każde uruchomienie daje inne wyniki (statystyczne fluktuacje Monte Carlo).

---

*Ostatnia aktualizacja: Luty 2026*
