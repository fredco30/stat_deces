"""
Parse Excel file to understand exact data layout.
Uses only standard library to work without pandas.
"""

import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict

def get_shared_strings(zip_ref):
    """Extract shared strings from Excel."""
    strings_data = zip_ref.read('xl/sharedStrings.xml')
    root = ET.fromstring(strings_data)
    ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

    strings = []
    for si in root.findall('.//main:si', ns):
        # Try to get text from <t> element
        t = si.find('.//main:t', ns)
        if t is not None and t.text:
            strings.append(t.text)
        else:
            strings.append('')

    return strings

def parse_cell_reference(ref):
    """Parse cell reference like 'A1' into (col, row)."""
    import re
    match = re.match(r'([A-Z]+)(\d+)', ref)
    if match:
        col_str, row_str = match.groups()
        # Convert column letter to number (A=0, B=1, etc.)
        col = 0
        for char in col_str:
            col = col * 26 + (ord(char) - ord('A') + 1)
        return col - 1, int(row_str) - 1
    return None, None

def analyze_sheet(zip_ref, shared_strings):
    """Analyze the first sheet in detail."""
    sheet_data = zip_ref.read('xl/worksheets/sheet1.xml')
    root = ET.fromstring(sheet_data)
    ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

    # Build a grid of values
    grid = defaultdict(dict)

    for cell in root.findall('.//main:c', ns):
        ref = cell.get('r')
        cell_type = cell.get('t')

        col, row = parse_cell_reference(ref)
        if col is None:
            continue

        # Get value
        v = cell.find('.//main:v', ns)
        if v is None or v.text is None:
            continue

        value = v.text

        # If it's a shared string, look it up
        if cell_type == 's':
            idx = int(value)
            value = shared_strings[idx] if idx < len(shared_strings) else value

        grid[row][col] = value

    # Print the first 15 rows and 20 columns
    print("First 15 rows of data:\n")

    max_row = min(15, max(grid.keys()) + 1) if grid else 0
    max_col = 20

    for row in range(max_row):
        if row in grid:
            row_data = []
            for col in range(max_col):
                val = grid[row].get(col, '')
                # Truncate long values
                val_str = str(val)[:30]
                row_data.append(val_str)
            print(f"Row {row:2d}: {' | '.join(row_data)}")
        else:
            print(f"Row {row:2d}: (empty)")

    print("\n" + "="*80)
    print("Data sample from rows 5-10 (after headers):")
    print("="*80)

    for row in range(5, min(10, max(grid.keys()) + 1)):
        if row in grid:
            print(f"\nRow {row}:")
            for col in range(max_col):
                val = grid[row].get(col, '')
                if val:
                    print(f"  Col {col:2d}: {val}")

def main():
    excel_path = 'population_francaise.xlsx'

    with zipfile.ZipFile(excel_path, 'r') as zip_ref:
        print("Extracting shared strings...")
        shared_strings = get_shared_strings(zip_ref)
        print(f"Found {len(shared_strings)} shared strings\n")

        print("Analyzing sheet structure...")
        analyze_sheet(zip_ref, shared_strings)

if __name__ == "__main__":
    main()
