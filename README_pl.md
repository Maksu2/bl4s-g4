# Symulacja Geant4 - Beamline for Schools (BL4S) ⚛️

## O Projekcie
Ten projekt jest symulacją Monte Carlo stworzoną przy użyciu toolkitu **Geant4** na potrzeby konkursu **CERN Beamline for Schools (BL4S)**. Celem symulacji jest wymodelowanie zachowania wiązki elektronów przechodzącej przez ołowianą tarczę i rejestracja powstałej kaskady elektromagnetycznej za pomocą macierzy detektorów.

Symulacja pozwala na badanie rozkładu przestrzennego cząstek po przejściu przez materiał o dużej liczbie atomowej (Z), co jest kluczowe dla zrozumienia zjawisk takich jak promieniowanie hamowania (bremsstrahlung) i produkcja par.

## Fizyka i Geometria 📐
Symulacja modeluje następujący scenariusz eksperymentalny w środowisku próżniowym:

1.  **Wiązka (Beam)**:
    *   Cząstki: Elektrony ($e^-$).
    *   Energia: 1 GeV.
    *   Kierunek: Oś Z.

2.  **Tarcza (Target)**:
    *   Materiał: Ołów ($Pb$).
    *   Grubość: Konfigurowalna (domyślnie 2 cm).
    *   Cel: Wywołanie kaskady elektromagnetycznej. Elektrony o wysokiej energii oddziałując z jądrami ołowiu emitują fotony (bremsstrahlung), które następnie konwertują w pary elektron-pozyton.

3.  **Detekcja (Calorimeter Array)**:
    *   Układ: Matryca 21x21 detektorów (łącznie 441 kryształów).
    *   Wymiary pojedynczego detektora: $10 \times 10 \times 10$ cm.
    *   Materiał: Szkło ołowiowe (Lead Glass).
    *   Pozycja: Umieszczone 1 metr za tarczą.
    *   Funkcja: Rejestracja liczby cząstek naładowanych przechodzących przez dany segment (licznik uderzeń).

## Wymagania
*   **Geant4** (wersja 11.2 lub nowsza).
*   **CMake** (do kompilacji).
*   Kompilator C++ obsługujący standard C++17.
*   System operacyjny: macOS/Linux (testowano na macOS Apple Silicon).

## Instrukcja Uruchomienia 🚀

### 1. Kompilacja
Projekt zawiera skrypt pomocniczy do kompilacji, który automatycznie wykrywa liczbę rdzeni procesora:

```bash
./compile_sim.sh
```

W wyniku kompilacji powstanie folder `build` z plikiem wykonywalnym `GeantSim`.

### 2. Uruchomienie Symulacji
Symulację najlepiej uruchamiać w trybie wsadowym (batch mode) przy użyciu makra:

```bash
./build/GeantSim run.mac
```

### 3. Konfiguracja (run.mac)
W pliku `run.mac` możesz dowolnie zmieniać parametry bez ponownej kompilacji:

*   **Zmiana grubości tarczy**:
    ```bash
    /BFS/geometry/leadThickness 5 cm  # Ustawienie 5 cm ołowiu
    ```
*   **Liczba zdarzeń**:
    ```bash
    /run/beamOn 10000  # Symulacja 10 tysięcy elektronów
    ```
*   **Energia wiązki**:
    ```bash
    /gun/energy 500 MeV
    ```

## Analiza Wyników 📊
Po zakończeniu symulacji generowany jest plik `results.txt`. Jest to czytelny plik tekstowy zawierający mapę uderzeń.

**Format pliku:**
```text
Total Events: 1000
Format: X Y | Hits (Center is 0 0)
-------------------
     0 0      |  1117   <-- Centralny detektor (na osi wiązki)
     -1 0     |  360    <-- Detektor obok środka
     ...
Total Electrons Detected: 5222
```
*   **X, Y**: Współrzędne detektora w siatce (0,0 to środek matrycy).
*   **Hits**: Liczba zliczonych cząstek w danym detektorze.

Zauważ, że `Total Electrons Detected` jest często większa niż `Total Events`, ponieważ pierwotne elektrony generują w ołowiu wiele cząstek wtórnych (kaskada), które trafiają w detektory.

---
*Autor: Maksu*
*Stworzono przy pomocy asystenta AI.*
