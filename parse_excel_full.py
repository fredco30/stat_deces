"""
Parse full Excel structure to see all columns and sections.
"""

import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
import re

def get_shared_strings(zip_ref):
    """Extract shared strings from Excel."""
    strings_data = zip_ref.read('xl/sharedStrings.xml')
    root = ET.fromstring(strings_data)
    ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

    strings = []
    for si in root.findall('.//main:si', ns):
        t = si.find('.//main:t', ns)
        if t is not None and t.text:
            strings.append(t.text)
        else:
            strings.append('')
    return strings

def parse_cell_reference(ref):
    """Parse cell reference like 'A1' into (col, row)."""
    match = re.match(r'([A-Z]+)(\d+)', ref)
    if match:
        col_str, row_str = match.groups()
        col = 0
        for char in col_str:
            col = col * 26 + (ord(char) - ord('A') + 1)
        return col - 1, int(row_str) - 1
    return None, None

def analyze_full_sheet(zip_ref, shared_strings):
    """Analyze the full sheet to find all columns."""
    sheet_data = zip_ref.read('xl/worksheets/sheet1.xml')
    root = ET.fromstring(sheet_data)
    ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

    grid = defaultdict(dict)
    max_col_found = 0

    for cell in root.findall('.//main:c', ns):
        ref = cell.get('r')
        cell_type = cell.get('t')
        col, row = parse_cell_reference(ref)

        if col is None:
            continue

        max_col_found = max(max_col_found, col)

        v = cell.find('.//main:v', ns)
        if v is None or v.text is None:
            continue

        value = v.text
        if cell_type == 's':
            idx = int(value)
            value = shared_strings[idx] if idx < len(shared_strings) else value

        grid[row][col] = value

    print(f"Maximum column found: {max_col_found} (column index)")
    print(f"Total rows: {max(grid.keys()) + 1}\n")

    # Print header rows to understand structure
    print("="*120)
    print("HEADER ROWS (0-4):")
    print("="*120)

    for row in range(5):
        if row in grid:
            print(f"\nRow {row}:")
            for col in sorted(grid[row].keys()):
                val = str(grid[row][col])[:40]
                print(f"  Col {col:3d}: {val}")

    # Check row 3 and 4 across all columns to find section headers
    print("\n" + "="*120)
    print("SECTION HEADERS (Row 3 - should show Ensemble, Hommes, Femmes):")
    print("="*120)

    if 3 in grid:
        sections = []
        for col in sorted(grid[3].keys()):
            val = grid[3][col]
            if val in ['Ensemble', 'Hommes', 'Femmes']:
                sections.append((col, val))
                print(f"  Column {col}: {val}")

    print("\n" + "="*120)
    print("AGE HEADERS (Row 4):")
    print("="*120)

    if 4 in grid:
        age_headers = {}
        for col in sorted(grid[4].keys()):
            val = grid[4][col]
            if 'ans' in str(val) or val == 'Total':
                age_headers[col] = val
                print(f"  Col {col:3d}: {val}")

    # Sample data from first department
    print("\n" + "="*120)
    print("FIRST DEPARTMENT (Row 5) - All columns:")
    print("="*120)

    if 5 in grid:
        for col in sorted(grid[5].keys())[:50]:  # First 50 columns
            val = grid[5][col]
            print(f"  Col {col:3d}: {val}")

def main():
    excel_path = 'population_francaise.xlsx'

    with zipfile.ZipFile(excel_path, 'r') as zip_ref:
        shared_strings = get_shared_strings(zip_ref)
        analyze_full_sheet(zip_ref, shared_strings)

if __name__ == "__main__":
    main()
