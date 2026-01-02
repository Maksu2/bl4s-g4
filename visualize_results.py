#!/usr/bin/env python3
import argparse

# Try importing seaborn for better aesthetics
try:
    import seaborn as sns
    sns_available = True
except ImportError:
    sns_available = False
    print("Tip: Install seaborn for prettier plots (`pip install seaborn`)")

def visualize_file(filename, energy=None, electrons=None, thickness=None):
    print(f"Processing {filename}...")
    
    # 1. Read CSV
    try:
        df = pd.read_csv(filename)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # 2. Prepare Data Grid (21x21)
    grid_size = 21
    data_grid = np.zeros((grid_size, grid_size))
    total_hits = 0
    
    # Coordinates -10 to 10 mapped to 0..20
    for index, row in df.iterrows():
        x = int(row['X'])
        y = int(row['Y'])
        hits = int(row['Hits'])
        total_hits += hits
        
        # Row 0 is Y=10 (Top), Row 20 is Y=-10 (Bottom)
        row_idx = 10 - y
        col_idx = x + 10
        
        if 0 <= row_idx < grid_size and 0 <= col_idx < grid_size:
            data_grid[row_idx][col_idx] = hits

    # 3. Plotting
    plt.figure(figsize=(10, 10)) # Slightly taller for text
    
    # Minimalist Theme
    if sns_available:
        sns.set_theme(style="white", font_scale=0.8)
        
        mask = (data_grid == 0)
        
        ax = sns.heatmap(data_grid, 
                         annot=True, 
                         fmt='g',            
                         norm=LogNorm(),     
                         cmap='OrRd',        
                         mask=mask,          
                         cbar_kws={'label': 'Hits (Log Scale)', 'shrink': 0.7, 'aspect': 20},
                         square=True,
                         linewidths=0.5,     
                         linecolor='#e0e0e0',
                         annot_kws={"size": 6, "color": "#333333", "weight": "light"} 
                         )
        
        ax.set_facecolor('white')
        sns.despine(left=True, bottom=True)
        
        major_ticks = np.arange(0, grid_size, 5)
        if grid_size-1 not in major_ticks:
            major_ticks = np.append(major_ticks, grid_size-1)

        ax.set_xticks(major_ticks + 0.5)
        ax.set_xticklabels([str(i-10) for i in major_ticks], fontsize=9)
        
        ax.set_yticks(major_ticks + 0.5)
        ax.set_yticklabels([str(10-i) for i in major_ticks], rotation=0, fontsize=9)
        ax.tick_params(length=0)
        
        plt.xlabel("X Position", fontsize=10, labelpad=15, color="#555555")
        plt.ylabel("Y Position", fontsize=10, labelpad=15, color="#555555")
        
        # Build Title/Subtitle
        title_text = "Electro-Magnetic Shower Distribution"
        subtitle_text = f"File: {filename}\nTotal Hits: {total_hits}"
        
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
