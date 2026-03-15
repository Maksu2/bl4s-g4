import os
import glob
import re
import csv
import sys

def parse_thickness(thickness_str):
    """Convert thickness string to mm for sorting."""
    match = re.search(r'([\d\.]+)(cm|mm)', thickness_str)
    if not match:
        return 999999.0
    val = float(match.group(1))
    unit = match.group(2)
    if unit == 'cm':
        return val * 10.0
    return val

def main():
    dir_path = "/Users/maksu/symulacjaa/Ostateczne wyniki !/Pb_2GeV"
    csv_files = glob.glob(os.path.join(dir_path, "results_*.csv"))
    
    if not csv_files:
        print("No files found!")
        return
        
    data = []
    
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        
        parts = filename.split('_')
        if len(parts) >= 3:
            thickness = parts[2]
        else:
            continue
            
        metadata_found = False
        calculated_hits = 0
        total_hits = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
                for line in reversed(lines[-5:]):
                    if line.startswith("# METADATA:"):
                        m2 = re.search(r'total_hits=\s*(\d+)', line)
                        if m2:
                            total_hits = int(m2.group(1))
                            metadata_found = True
                        break
                
                if not metadata_found:
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#') and not line.startswith('X'):
                            cols = line.split(',')
                            if len(cols) >= 3:
                                try:
                                    calculated_hits += int(cols[2])
                                except ValueError:
                                    pass
                    total_hits = calculated_hits
                    
        except Exception as e:
            continue
            
        data.append({
            'thickness': thickness,
            'total_hits': total_hits,
            'sort_val': parse_thickness(thickness)
        })
        
    data.sort(key=lambda x: x['sort_val'])
    
    summary_path = "/Users/maksu/symulacjaa/Ostateczne wyniki !/summary2gevpg.csv"
    
    try:
        with open(summary_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['thickness', 'total_hits'])
            for row in data:
                writer.writerow([row['thickness'], row['total_hits']])
        print(f"Dane zapisano we wspólnym pliku: {summary_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
