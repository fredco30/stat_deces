"""
Convert INSEE Excel population data to CSV files for the application.
Uses only standard library to work without pandas.
"""

import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
import re
import csv

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

def parse_excel(zip_ref, shared_strings):
    """Parse Excel data into structured format."""
    sheet_data = zip_ref.read('xl/worksheets/sheet1.xml')
    root = ET.fromstring(sheet_data)
    ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

    grid = defaultdict(dict)

    for cell in root.findall('.//main:c', ns):
        ref = cell.get('r')
        cell_type = cell.get('t')
        col, row = parse_cell_reference(ref)

        if col is None:
            continue

        v = cell.find('.//main:v', ns)
        if v is None or v.text is None:
            continue

        value = v.text
        if cell_type == 's':
            idx = int(value)
            value = shared_strings[idx] if idx < len(shared_strings) else value

        grid[row][col] = value

    return grid

# Age group mapping (column offset to age range)
AGE_GROUPS = [
    (0, 4),    # 0-4 ans
    (5, 9),    # 5-9 ans
    (10, 14),  # 10-14 ans
    (15, 19),  # 15-19 ans
    (20, 24),  # 20-24 ans
    (25, 29),  # 25-29 ans
    (30, 34),  # 30-34 ans
    (35, 39),  # 35-39 ans
    (40, 44),  # 40-44 ans
    (45, 49),  # 45-49 ans
    (50, 54),  # 50-54 ans
    (55, 59),  # 55-59 ans
    (60, 64),  # 60-64 ans
    (65, 69),  # 65-69 ans
    (70, 74),  # 70-74 ans
    (75, 79),  # 75-79 ans
    (80, 84),  # 80-84 ans
    (85, 89),  # 85-89 ans
    (90, 94),  # 90-94 ans
    (95, 120), # 95+ ans
]

def main():
    excel_path = 'population_francaise.xlsx'

    # Years to generate (we'll use 2023 data for all years)
    years = [2019, 2020, 2021, 2022, 2023, 2024, 2025]

    print("Reading Excel file...")
    with zipfile.ZipFile(excel_path, 'r') as zip_ref:
        shared_strings = get_shared_strings(zip_ref)
        grid = parse_excel(zip_ref, shared_strings)

    print(f"Parsed {len(grid)} rows")

    # Structure:
    # Columns 0-1: Dept code, Dept name
    # Columns 2-22: Ensemble (Total) - 20 age groups + 1 total
    # Columns 23-43: Hommes (Men)
    # Columns 44-64: Femmes (Women)
    # Rows 5-110: Department data

    print("\n1. Creating population_dept.csv...")

    with open('population_dept.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['annee', 'departement', 'population'])

        for year in years:
            for row_idx in range(5, 111):  # Rows 5-110 are departments
                if row_idx not in grid:
                    continue

                dept_code = grid[row_idx].get(0, '')
                total_pop = grid[row_idx].get(22, 0)  # Column 22 is Total for Ensemble

                if dept_code and total_pop:
                    try:
                        pop = int(float(total_pop))
                        writer.writerow([year, dept_code, pop])
                    except (ValueError, TypeError):
                        continue

    print("   Created with", (111 - 5) * len(years), "records")

    print("\n2. Creating population_age.csv...")

    # Aggregate population by age group across all departments
    age_totals = {}

    for year in years:
        for age_idx, (age_min, age_max) in enumerate(AGE_GROUPS):
            total_pop = 0

            # Sum across all departments for this age group
            for row_idx in range(5, 111):
                if row_idx not in grid:
                    continue

                # Column 2 + age_idx gives us the age group column in Ensemble section
                pop_value = grid[row_idx].get(2 + age_idx, 0)

                if pop_value:
                    try:
                        total_pop += int(float(pop_value))
                    except (ValueError, TypeError):
                        continue

            age_totals[(year, age_min, age_max)] = total_pop

    with open('population_age.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['annee', 'age_min', 'age_max', 'population'])

        for (year, age_min, age_max), pop in sorted(age_totals.items()):
            writer.writerow([year, age_min, age_max, pop])

    print("   Created with", len(age_totals), "records")

    print("\n3. Creating population_complete.csv...")

    with open('population_complete.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['annee', 'departement', 'age_min', 'age_max', 'population'])

        record_count = 0

        for year in years:
            for row_idx in range(5, 111):  # Departments
                if row_idx not in grid:
                    continue

                dept_code = grid[row_idx].get(0, '')
                if not dept_code:
                    continue

                for age_idx, (age_min, age_max) in enumerate(AGE_GROUPS):
                    # Column 2 + age_idx for Ensemble section
                    pop_value = grid[row_idx].get(2 + age_idx, 0)

                    if pop_value:
                        try:
                            pop = int(float(pop_value))
                            writer.writerow([year, dept_code, age_min, age_max, pop])
                            record_count += 1
                        except (ValueError, TypeError):
                            continue

    print("   Created with", record_count, "records")

    print("\nDone! Created 3 CSV files:")
    print("  - population_dept.csv: Population by department and year")
    print("  - population_age.csv: Population by age group and year")
    print("  - population_complete.csv: Complete matrix (dept x age x year)")
    print("\nNote: 2023 INSEE data is used for all years (2019-2025)")

if __name__ == "__main__":
    main()
