#!/usr/bin/env python3
"""
Zautomatyzowany skrypt do hurtowej analizy danych Geant4 (Ostateczne wyniki !)
- Odczytuje foldery i wyciąga z nich metadane: Materiał (Cu/Pb) oraz Energię.
- Przetwarza każdy z plików w folderze, wydobywając z jego nazwy grubość tarczy [cm].
- Oblicza poprzez funkcje zaimportowane z `analysis_app.py`:
  • Całkowitą liczbę trafień (Hits).
  • Wymiar fraktalny (Fractal Dimension, R²).
  • Klastry DBSCAN (Ilość, Śr. Rozmiar, Punkty Szumu).
- Łączy wyniki w potężny i czytelny DataFrame, a następnie eksportuje do `summary_ostateczne.csv`.

Użycie:
  python3 batch_analyzer.py
"""
import os
import sys
import re
import pandas as pd
import numpy as np

# Importujemy logikę matematyczną ze stworzonego już GUI
from analysis_app import load_csv, build_grid, compute_fractal_dimension_3d, run_dbscan

# Konfiguracja środowiska
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_ROOT = os.path.join(BASE_DIR, "Ostateczne wyniki !")
OUTPUT_CSV = os.path.join(BASE_DIR, "summary_ostateczne.csv")

# Parametry algorytmu DBSCAN z GUI
EPS_DBSCAN = 2.0
MIN_SAMPLES = 3

def wyluskanie_metadanych_z_folderu(nazwa_folderu):
    """Próbuje odczytać Materiał (Cu/Pb) oraz Energię w GeV z macierzystego folderu"""
    material = "Unknown"
    if "Cu" in nazwa_folderu:
        material = "Cu"
    elif "Pb" in nazwa_folderu:
        material = "Pb"
        
    energia = "Unknown"
    # Szuka liczby przed literami "GeV"
    m_energy = re.search(r'(\d+(?:\.\d+)?)\s*GeV', nazwa_folderu)
    if m_energy:
        energia = m_energy.group(1)
        
    return material, energia

def parse_thickness_from_file(filename):
    """Odczytuje wymiar [w centymetrach] z nazwy pliku 'results_Cu_1.1cm_1.csv'"""
    # Preferensja do dokładnego dopasowania słowa .cm, ew .m / mm. 
    # Normalnie pliki po prostu nazywają się np: results_Pb_14.8cm_1.csv
    m = re.search(r'_(?:\w+_)?([\d\.]+)(cm|mm|m)_', filename)
    if m:
        war = float(m.group(1))
        unit = m.group(2)
        if unit == 'mm': return round(war / 10.0, 4)
        elif unit == 'm': return round(war * 100.0, 4)
        return round(war, 4)
    return 0.0

def main():
    if not os.path.exists(RESULTS_ROOT):
        print(f"BŁĄD: Katalog '{RESULTS_ROOT}' nie istnieje.")
        sys.exit(1)
        
    print(f"Rozpoczynam zrobotyzowaną analizę danych z katalogu:\n{RESULTS_ROOT}\n")
    
    # Składujemy wszystkie rzędy analizy w docelowej liście na obiekty słownikowe
    ostateczne_rzędy = []
    
    foldery = [f for f in os.listdir(RESULTS_ROOT) if os.path.isdir(os.path.join(RESULTS_ROOT, f))]
    
    for folder in foldery:
        sciezka_folderu = os.path.join(RESULTS_ROOT, folder)
        material, energia = wyluskanie_metadanych_z_folderu(folder)
        
        pliki_csv = [p for p in os.listdir(sciezka_folderu) if p.startswith("results_") and p.endswith(".csv")]
        
        if not pliki_csv:
            continue
            
        print(f"📁 Przetwarzanie: {folder} (Wykryto: {material}, {energia} GeV, {len(pliki_csv)} plików)...")
        
        for plik in pliki_csv:
            sciezka_pliku = os.path.join(sciezka_folderu, plik)
            grubosc = parse_thickness_from_file(plik)
            
            try:
                # 1. Ładowanie rzadkich danych
                df = load_csv(sciezka_pliku)
                total_hits = int(df['Hits'].sum())
                
                # 2. Fraktale (box-counting z analysis_app.py)
                grid = build_grid(df)
                frac_res = compute_fractal_dimension_3d(grid)
                dim = frac_res['dimension']
                r2 = frac_res['r_squared']
                
                # 3. Klastrowanie DBSCAN
                dbscan_res = run_dbscan(df, eps=EPS_DBSCAN, min_samples=MIN_SAMPLES)
                n_clusters = dbscan_res['n_clusters']
                labels = dbscan_res['labels']
                noise_pts = int((labels == -1).sum()) if len(labels) > 0 else 0
                
                rzeczywiste_klastry = [s for s in dbscan_res['cluster_stats'] if s['id'] >= 0]
                sr_rozmiar_klastra = np.mean([s['n_detectors'] for s in rzeczywiste_klastry]) if rzeczywiste_klastry else 0.0
                
            except Exception as e:
                print(f" ⚠️ Błąd matematyczny przy pliku {plik}: {e}")
                continue
                
            # Zapis pełnych cech jednego symulowanego wariantu (np. 1.2cm Ołów 5 Gev)
            ostateczne_rzędy.append({
                "Material": material,
                "Energy_GeV": float(energia) if energia != "Unknown" else np.nan,
                "Thickness_cm": grubosc,
                "Zrodlowy_Folder": folder,
                "Plik_CSV": plik,
                "Total_Hits": total_hits,
                "Fractal_Dimension_D": round(dim, 5) if not np.isnan(dim) else 0.0,
                "Fractal_R2": round(r2, 5) if not np.isnan(r2) else 0.0,
                "Clusters_Count": n_clusters,
                "Avg_Cluster_Size": round(float(sr_rozmiar_klastra), 2),
                "Noise_Points": noise_pts
            })
            
    # Zakończenie pracy silnika, stworzenie pandas df i eksport csv
    if ostateczne_rzędy:
        master_df = pd.DataFrame(ostateczne_rzędy)
        
        # Sortowanie logiczne ułatwiające przegląd i tworzenie wykresów.
        # Np względem Pb -> 6 GeV -> 0.1, 0.2 ... 30.0 cm
        master_df.sort_values(by=["Material", "Energy_GeV", "Thickness_cm"], inplace=True)
        master_df.to_csv(OUTPUT_CSV, index=False)
        print(f"\n✅ Sukces! Zebrano pomiary z {len(ostateczne_rzędy)} symulacji.")
        print(f"📊 Zapisano piękny raport zbiorczy do:\n   👉 {OUTPUT_CSV}")
    else:
        print("\n⚠️ Ostrzeżenie: Nie zdołałem przetworzyć żadnego ze zgromadzonych w folderze plików.")
        sys.exit(1)

if __name__ == "__main__":
    main()
