import pandas as pd
import os

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "summary_ostateczne.csv")
EXCEL_FILE_MULTISHEET = os.path.join(BASE_DIR, "summary_english_multisheet.xlsx")

def apply_excel_styles(writer, df, sheet_name):
    """Applies styles, borders and adjustments to the Excel dataframe printout."""
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]

    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'vcenter',
        'align': 'center',
        'fg_color': '#D7E4BC',
        'border': 1
    })
    
    cell_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    col_widths = {
        'A': 10, 'B': 12, 'C': 15, 'D': 25, 'E': 25, 
        'F': 15, 'G': 20, 'H': 15, 'I': 15, 'J': 20, 'K': 15
    }
    
    for row in range(1, len(df) + 1):
       worksheet.set_row(row, None, cell_format)

    for col_num, value in enumerate(df.columns.values):
        col_letter = chr(65 + col_num)
        worksheet.write(0, col_num, value, header_format)
        width = col_widths.get(col_letter, 15)
        worksheet.set_column(f"{col_letter}:{col_letter}", width)

    worksheet.freeze_panes(1, 0)
    worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)

def main():
    if not os.path.exists(CSV_FILE):
        print(f"Input file missing: {CSV_FILE}")
        return

    print("Loading CSV data into memory...")
    df = pd.read_csv(CSV_FILE)

    # 1. Translate column names
    df.rename(columns={
        'Zrodlowy_Folder': 'Source_Directory',
        'Plik_CSV': 'CSV_Filename',
        'Material': 'Material',
        'Energy_GeV': 'Energy_GeV',
        'Thickness_cm': 'Thickness_cm',
        'Total_Hits': 'Total_Hits',
        'Fractal_Dimension_D': 'Fractal_Dimension_D',
        'Fractal_R2': 'Fractal_R2',
        'Clusters_Count': 'Clusters_Count',
        'Avg_Cluster_Size': 'Avg_Cluster_Size',
        'Noise_Points': 'Noise_Points'
    }, inplace=True)
    
    # 2. Iterate groups and save as different sheets in one file
    print("Generating Multi-Sheet Excel workbook (.xlsx)...")
    groups = df.groupby(['Material', 'Energy_GeV'])
    
    with pd.ExcelWriter(EXCEL_FILE_MULTISHEET, engine='xlsxwriter') as writer:
        for (material, energy), subset_df in groups:
            sheet_title = f"{material} {int(energy)}GeV"
            apply_excel_styles(writer, subset_df, sheet_name=sheet_title)
            
    print("✅ Success! Single multi-sheet workbook generation complete.")
    print(f"💼 Saved into: {EXCEL_FILE_MULTISHEET}")

if __name__ == "__main__":
    main()
