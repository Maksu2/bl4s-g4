#!/usr/bin/env python3
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
try:
    import seaborn as sns
    sns_available = True
except ImportError:
    sns_available = False
    print("Tip: Install seaborn for prettier plots (`pip install seaborn`)")

def visualize_file(filename, energy=None, electrons=None, thickness=None):
    print(f"Processing {filename}...")
    
    # 1. Read CSV (skip comment lines starting with #)
    try:
        df = pd.read_csv(filename, comment='#')
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # 2. Determine Grid Size dynamically
    if df.empty:
        print("File is empty.")
        return

    min_x, max_x = df['X'].min(), df['X'].max()
    min_y, max_y = df['Y'].min(), df['Y'].max()
    
    # Determine the extent needed to center at 0,0
    abs_max = max(abs(min_x), abs(max_x), abs(min_y), abs(max_y))
    # Add some padding or ensure it covers at least the old range
    # abs_max = max(abs_max, 10) 
    
    # Grid radius (from center)
    radius = abs_max
    
    # Total grid width/height = 2*radius + 1
    # Example: radius 10 -> -10..10 -> size 21
    # Example: radius 50 -> -50..50 -> size 101
    grid_size = 2 * radius + 1
    
    data_grid = np.zeros((grid_size, grid_size))
    total_hits = 0
    
    # Coordinates -R to R mapped to 0..2R
    for index, row in df.iterrows():
        x = int(row['X'])
        y = int(row['Y'])
        hits = int(row['Hits'])
        total_hits += hits
        
        # Mapping: 
        # Center (0,0) -> (radius, radius)
        # Top-Left (-R, R) -> (0, 0) ?? No, usually heatmap:
        # Array index: rows (Y) usually 0 is top or bottom depending on convention.
        # Let's keep logic: Row 0 is Top (Y=max), Row Last is Bottom (Y=min)
        
        # Y=radius (Top) -> row 0
        # Y=-radius (Bottom) -> row 2*radius
        row_idx = radius - y
        col_idx = x + radius
        
        if 0 <= row_idx < grid_size and 0 <= col_idx < grid_size:
            data_grid[row_idx][col_idx] = hits

    # 3. Plotting
    # Dynamic figure size based on grid
    fig_size = min(20, max(10, grid_size / 8))
    plt.figure(figsize=(fig_size, fig_size))
    
    # Determine if this is a large grid (disable annotations)
    is_large_grid = grid_size > 50
    
    # Minimalist Theme
    if sns_available:
        sns.set_theme(style="white", font_scale=0.8)
        
        mask = (data_grid == 0)
        
        if total_hits > 0:
            norm = LogNorm()
            cbar_kws = {'label': 'Hits (Log Scale)', 'shrink': 0.7, 'aspect': 20}
        else:
            norm = None
            cbar_kws = {'label': 'Hits (Linear)', 'shrink': 0.7, 'aspect': 20}
        
        # Optimize for large grids
        if is_large_grid:
            ax = sns.heatmap(data_grid, 
                             annot=False,           # No annotations for large grids
                             norm=norm,     
                             cmap='OrRd',        
                             mask=mask,          
                             cbar_kws=cbar_kws,
                             square=True,
                             linewidths=0,          # No grid lines for performance
                             rasterized=True        # Rasterize for smaller SVG
                             )
        else:
            ax = sns.heatmap(data_grid, 
                             annot=True, 
                             fmt='g',            
                             norm=norm,     
                             cmap='OrRd',        
                             mask=mask,          
                             cbar_kws=cbar_kws,
                             square=True,
                             linewidths=0.5,     
                             linecolor='#e0e0e0',
                             annot_kws={"size": 6, "color": "#333333", "weight": "light"} 
                             )
        
        ax.set_facecolor('white')
        sns.despine(left=True, bottom=True)
        
        # Adaptive tick spacing based on grid size
        if grid_size > 100:
            num_ticks = 11
        elif grid_size > 50:
            num_ticks = 11
        else:
            num_ticks = min(11, grid_size)
        
        major_ticks = np.linspace(0, grid_size-1, num_ticks, dtype=int)
        
        ax.set_xticks(major_ticks + 0.5)
        ax.set_xticklabels([str(i-radius) for i in major_ticks], fontsize=9)
        
        ax.set_yticks(major_ticks + 0.5)
        ax.set_yticklabels([str(radius-i) for i in major_ticks], rotation=0, fontsize=9)
        ax.tick_params(length=0)
        
        plt.xlabel("X Position", fontsize=10, labelpad=15, color="#555555")
        plt.ylabel("Y Position", fontsize=10, labelpad=15, color="#555555")
        
        # Build Title/Subtitle
        title_text = "Electro-Magnetic Shower Distribution"
        subtitle_text = f"File: {filename} | Grid: {grid_size}×{grid_size}\nTotal Hits: {total_hits}"
        
        if energy or electrons or thickness:
            details = []
            if energy: details.append(f"Energy: {energy}")
            if thickness: details.append(f"Thickness: {thickness}")
            if electrons: details.append(f"Electrons: {electrons}")
            subtitle_text += " | " + ", ".join(details)
            
        plt.suptitle(title_text, fontsize=16, weight='bold', color="#222222", y=0.95)
        plt.title(subtitle_text, fontsize=10, color="#666666", pad=10)
        
    else:
        plt.imshow(data_grid, cmap='OrRd', interpolation='nearest', norm=LogNorm())
        plt.colorbar(label='Hits (Log Scale)')
        plt.title(f"Detector Hits: {filename}\nTotal: {total_hits}")

    # 4. Save
    output_filename = filename.replace('.csv', '.svg')
    plt.savefig(output_filename, format='svg', bbox_inches='tight', transparent=False)
    plt.close()
    
    print(f"✅ Visualization saved to: {output_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Visualize Geant4 Simulation Results')
    parser.add_argument('file', help='Path to CSV file')
    parser.add_argument('--energy', help='Beam Energy')
    parser.add_argument('--electrons', help='Number of Electrons')
    parser.add_argument('--thickness', help='Lead Thickness')
    
    args = parser.parse_args()
    
    visualize_file(args.file, args.energy, args.electrons, args.thickness)
