#!/usr/bin/env python3
import os
import glob
import argparse
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Wymuszenie backendu bez GUI dla WSL (żeby multiprocessing działał stabilnie i się nie crashował)
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from concurrent.futures import ProcessPoolExecutor, as_completed

try:
    import seaborn as sns
    sns_available = True
except ImportError:
    sns_available = False
    print("Tip: Install seaborn for prettier plots (`pip install seaborn`)")

def visualize_file(filename):
    # print(f"Processing {filename}...")
    try:
        df = pd.read_csv(filename, comment='#')
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return False

    if df.empty:
        return False

    min_x, max_x = df['X'].min(), df['X'].max()
    min_y, max_y = df['Y'].min(), df['Y'].max()
    
    abs_max = max(abs(min_x), abs(max_x), abs(min_y), abs(max_y))
    radius = abs_max
    grid_size = 2 * radius + 1
    
    data_grid = np.zeros((grid_size, grid_size))
    total_hits = 0
    
    for _, row in df.iterrows():
        x = int(row['X'])
        y = int(row['Y'])
        hits = int(row['Hits'])
        total_hits += hits
        
        row_idx = radius - y
        col_idx = x + radius
        
        if 0 <= row_idx < grid_size and 0 <= col_idx < grid_size:
            data_grid[row_idx][col_idx] = hits

    fig_size = min(20, max(10, grid_size / 8))
    fig = plt.figure(figsize=(fig_size, fig_size))
    
    is_large_grid = grid_size > 50
    
    if sns_available:
        sns.set_theme(style="white", font_scale=0.8)
        mask = (data_grid == 0)
        
        if total_hits > 0:
            norm = LogNorm()
            cbar_kws = {'label': 'Hits (Log Scale)', 'shrink': 0.7, 'aspect': 20}
        else:
            norm = None
            cbar_kws = {'label': 'Hits (Linear)', 'shrink': 0.7, 'aspect': 20}
        
        if is_large_grid:
            ax = sns.heatmap(data_grid, annot=False, norm=norm, cmap='OrRd', mask=mask, 
                             cbar_kws=cbar_kws, square=True, linewidths=0, rasterized=True)
        else:
            ax = sns.heatmap(data_grid, annot=True, fmt='g', norm=norm, cmap='OrRd', mask=mask, 
                             cbar_kws=cbar_kws, square=True, linewidths=0.5, linecolor='#e0e0e0',
                             annot_kws={"size": 6, "color": "#333333", "weight": "light"})
        
        ax.set_facecolor('white')
        sns.despine(left=True, bottom=True)
        
        if grid_size > 100: num_ticks = 11
        elif grid_size > 50: num_ticks = 11
        else: num_ticks = min(11, grid_size)
        
        major_ticks = np.linspace(0, grid_size-1, num_ticks, dtype=int)
        ax.set_xticks(major_ticks + 0.5)
        ax.set_xticklabels([str(i-radius) for i in major_ticks], fontsize=9)
        ax.set_yticks(major_ticks + 0.5)
        ax.set_yticklabels([str(radius-i) for i in major_ticks], rotation=0, fontsize=9)
        ax.tick_params(length=0)
        
        plt.xlabel("X Position", fontsize=10, labelpad=15, color="#555555")
        plt.ylabel("Y Position", fontsize=10, labelpad=15, color="#555555")
        
        plt.suptitle("Electro-Magnetic Shower Distribution", fontsize=16, weight='bold', color="#222222", y=0.95)
        plt.title(f"File: {os.path.basename(filename)} | Grid: {grid_size}×{grid_size}\nTotal Hits: {total_hits}", 
                  fontsize=10, color="#666666", pad=10)
    else:
        plt.imshow(data_grid, cmap='OrRd', interpolation='nearest', norm=LogNorm() if total_hits > 0 else None)
        plt.colorbar(label='Hits (Log Scale)')
        plt.title(f"Detector Hits: {os.path.basename(filename)}\nTotal: {total_hits}")

    output_filename = filename.replace('.csv', '.svg')
    plt.savefig(output_filename, format='svg', bbox_inches='tight', transparent=False)
    plt.close(fig)
    return True

def main():
    parser = argparse.ArgumentParser(description='Batch Convert CSV to SVG')
    parser.add_argument('folder', help='Path to folder containing CSV files')
    parser.add_argument('--workers', type=int, default=os.cpu_count(), help='Number of worker processes')
    args = parser.parse_args()

    csv_files = glob.glob(os.path.join(args.folder, '**', '*.csv'), recursive=True)
    
    if not csv_files:
        print(f"Nie znaleziono plików CSV w: {args.folder}")
        return
        
    print(f"Znaleziono {len(csv_files)} plików CSV. Generowanie SVG ({args.workers} procesy)...")
    
    success_count = 0
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(visualize_file, f): f for f in csv_files}
        
        # Wyświetlanie paska postępu w konsoli
        for i, future in enumerate(as_completed(futures), 1):
            try:
                if future.result():
                    success_count += 1
            except Exception as e:
                print(f"Błąd przy pliku {futures[future]}: {e}")
            
            print(f"\rPrzetworzono: {i}/{len(csv_files)}", end='', flush=True)
                
    print(f"\nZakończono! Pomyślnie wygenerowano {success_count}/{len(csv_files)} obrazów SVG.")

if __name__ == "__main__":
    main()
