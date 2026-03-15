import os
import glob
import re
import csv
import sys

def parse_thickness(thickness_str):
    """Convert thickness string to mm for sorting."""
    match = re.search(r'([\d\.]+)(cm|mm)', thickness_str)
    if not match:
        return 999999.0 # fallback
    
    val = float(match.group(1))
    unit = match.group(2)
    
    if unit == 'cm':
        return val * 10.0
    return val

def process_directory(dir_path):
    dir_name = os.path.basename(dir_path)
    csv_files = glob.glob(os.path.join(dir_path, "results_*.csv"))
    
    if not csv_files:
        return
    
    print(f"Processing directory: {dir_name} with {len(csv_files)} files...", flush=True)
    
    data = []
    
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        
        thickness = ""
        total_hits = 0
        
        parts = filename.split('_')
        if len(parts) >= 3:
            thickness_from_name = parts[2]
        else:
            thickness_from_name = "unknown"
            
        metadata_found = False
        calculated_hits = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
                # Check for metadata
                for line in reversed(lines[-5:]):
                    if line.startswith("# METADATA:"):
                        m = re.search(r'thickness=\s*([\d\.]+\s*(?:cm|mm))', line)
                        if m:
                            thickness = m.group(1).replace(" ", "")
                        
                        m2 = re.search(r'total_hits=\s*(\d+)', line)
                        if m2:
                            total_hits = int(m2.group(1))
                            metadata_found = True
                        break
                
                if not metadata_found:
                    thickness = thickness_from_name
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
            print(f"Error reading {file_path}: {e}", file=sys.stderr, flush=True)
            continue
            
        if not thickness:
            thickness = thickness_from_name
            
        data.append({
            'thickness': thickness,
            'total_hits': total_hits,
            'sort_val': parse_thickness(thickness)
        })
        
    data.sort(key=lambda x: x['sort_val'])
    
    summary_filename = f"summary_{dir_name}.csv"
    summary_path = os.path.join(os.path.dirname(dir_path), summary_filename)
    
    try:
        with open(summary_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['thickness', 'total_hits'])
            for row in data:
                writer.writerow([row['thickness'], row['total_hits']])
        print(f"  -> Generated {summary_filename} with {len(data)} entries.", flush=True)
    except Exception as e:
        print(f"  -> Error saving {summary_filename}: {e}", file=sys.stderr, flush=True)

def main():
    base_dir = "/Users/maksu/symulacjaa/Ostateczne wyniki !"
    print("Starting generation...", flush=True)
    
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path):
            process_directory(item_path)
            
    print("Done.", flush=True)

if __name__ == "__main__":
    main()
