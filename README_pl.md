# Symulacja Geant4 na konkurs CERN Beamline for Schools (BL4S) ⚛️

## 📖 Wstęp: O co chodzi w tym projekcie?

Ten projekt to zaawansowana symulacja komputerowa stworzona w oparciu o toolkit **Geant4** – to samo narzędzie, którego używają fizycy w CERN do projektowania wielkich detektorów, takich jak ATLAS czy CMS.

Naszym celem jest zbadanie **kaskady elektromagnetycznej** (ang. *electromagnetic shower*). Chcemy zobaczyć, co się dzieje, gdy elektrony o bardzo dużej energii uderzają w gęsty materiał (ołów). Czy przelatują na wylot? Czy znikają? A może dzieje się coś bardziej spektakularnego?

Symulacja pozwala nam "zajrzeć" w głąb materii i zweryfikować nasze hipotezy bez konieczności budowania kosztownego eksperymentu w rzeczywistości (jeszcze!).

## 🧠 Fizyka: Jak to działa?

Głównym zjawiskiem, które obserwujemy, jest kaskada elektromagnetyczna. Składa się ona z dwóch naprzemiennych procesów:

1.  **Promieniowanie Hamowania (Bremsstrahlung)**:
    Gdy rozpędzony elektron ($e^-$) przelatuje blisko jądra atomu ołowiu, jest gwałtownie hamowany przez jego pole elektryczne. Zgodnie z prawami elektrodynamiki, hamowany ładunek musi oddać energię – emituje ją w postaci fotonu gamma ($\gamma$) o wysokiej energii.

2.  **Produkcja Par (Pair Production)**:
    Foton gamma powstały w poprzednim kroku, mknąc przez materię, może w pobliżu jądra atomowego zamienić się w parę cząstek: elektron ($e^-$) i pozyton ($e^+$).

**Efekt lawinowy**:
Jeden elektron wchodzący w ołowianą tarczę emituje foton. Ten foton zamienia się w dwa nowe elektrony (jeden ujemny, jeden dodatni). Te dwa znowu hamują, emitując kolejne fotony...
Z **jednej** cząstki na wejściu robi się **cała chmura** cząstek wtórnych na wyjściu! To właśnie dlatego nasze detektory zliczają więcej trafień niż wystrzeliliśmy elektronów.

## 📐 Geometria Eksperymentu

Wszystko dzieje się w wirtualnej komorze próżniowej ($5 \times 5 \times 5$ m), aby powietrze nie zakłócało pomiaru.

1.  **Działo elektronowe**:
    *   Źródło wiązki elektronów o energii **1 GeV** (1 miliard elektronowoltów).
    *   Wiązka jest skolimowana (leci prosto wzdłuż osi Z).

2.  **Tarcza (Target)**:
    *   Blok **ołowiu (Pb)**.
    *   Grubość można zmieniać w pliku konfiguracyjnym (domyślnie 2 cm).
    *   To tutaj zachodzi "magia" tworzenia nowych cząstek.

3.  **Kalorymetr (Detektory)**:
    *   Matryca **21 x 21** kryształów ($441$ sztuk).
    *   Każdy kryształ to sześcian $10 \times 10 \times 10$ cm wykonany ze **szkła ołowiowego**.
    *   Umieszczone 1 metr za tarczą.
    *   Zadanie: Zliczyć każdą naładowaną cząstkę, która do niego wpadnie.

## 🛠️ Instrukcja Obsługi

### Wymagania
Musisz mieć zainstalowany Geant4 oraz CMake.

### 1. Kompilacja
Aby zamienić kod C++ w działający program, uruchom w terminalu:
```bash
./compile_sim.sh
```
Stworzy to plik `./build/GeantSim`.

### 2. Uruchamianie
Symulację sterujemy plikiem `run.mac`. Uruchom komendę:
```bash
./build/GeantSim run.mac
```

### 3. Konfiguracja (bez rekompilacji!)
Otwórz plik `run.mac` w dowolnym edytorze tekstu. Możesz tam zmienić:
*   `/BFS/geometry/leadThickness 2 cm` -> Grubość tarczy. Ustaw `0 cm` (lub `1 um`), żeby zobaczyć co się dzieje bez ołowiu (brak kaskady!).
*   `/run/beamOn 1000` -> Liczba wystrzelonych elektronów.
*   `/gun/energy 1 GeV` -> Energia wiązki. Spróbuj `100 MeV` i zobacz czy kaskada będzie mniejsza!

## 📊 Interpretacja Wyników (`results.txt`)

Po zakończeniu programu zajrzyj do pliku `results.txt`.

Przykładowy fragment:
```text
Detector (-1, 0) | 360 hits
Detector (0, 0)  | 1117 hits
Total Electrons Detected: 5222
```

*   **(0, 0)** to środek siatki detektorów (tam celuje wiązka).
*   Liczby w nawiasach to współrzędne $(X, Y)$ detektora (w "kratkach").
*   **Total Electrons Detected > Total Events**: To dowód na działanie kaskady! Wystrzeliliśmy 1000 elektronów, a detektory "zobaczyły" ich 5222. Oznacza to, że każdy elektron wybił średnio ponad 5 cząstek wtórnych.

---
