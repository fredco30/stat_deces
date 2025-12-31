"""
Analyze Excel file structure using zipfile (Excel files are ZIP archives).
This script uses only standard library modules.
"""

import zipfile
import xml.etree.ElementTree as ET
import sys

def analyze_excel_structure(excel_path):
    """Analyze the structure of an Excel file."""
    print(f"Analyzing: {excel_path}\n")

    try:
        with zipfile.ZipFile(excel_path, 'r') as zip_ref:
            # List all files in the archive
            print("Files in Excel archive:")
            for name in sorted(zip_ref.namelist()):
                print(f"  {name}")

            print("\n" + "="*60)
            print("Workbook structure:")
            print("="*60)

            # Read workbook.xml to get sheet information
            try:
                workbook_data = zip_ref.read('xl/workbook.xml')
                root = ET.fromstring(workbook_data)

                # Find namespace
                ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

                sheets = root.findall('.//main:sheet', ns)
                print(f"\nFound {len(sheets)} sheet(s):")

                for sheet in sheets:
                    sheet_name = sheet.get('name')
                    sheet_id = sheet.get('sheetId')
                    r_id = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                    print(f"  - {sheet_name} (ID: {sheet_id}, rId: {r_id})")

            except Exception as e:
                print(f"Error reading workbook: {e}")

            print("\n" + "="*60)
            print("Shared strings (first 50):")
            print("="*60)

            # Read shared strings
            try:
                strings_data = zip_ref.read('xl/sharedStrings.xml')
                strings_root = ET.fromstring(strings_data)

                # Find all text elements
                ns_strings = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                texts = strings_root.findall('.//main:t', ns_strings)

                print(f"\nTotal unique strings: {len(texts)}")
                print("\nFirst 50 strings (these are likely column headers or values):")
                for i, text in enumerate(texts[:50]):
                    print(f"  {i}: {text.text}")

            except Exception as e:
                print(f"Error reading shared strings: {e}")

            print("\n" + "="*60)
            print("Sheet files:")
            print("="*60)

            # List sheet files
            sheet_files = [f for f in zip_ref.namelist() if f.startswith('xl/worksheets/')]
            for sheet_file in sheet_files:
                print(f"\n  {sheet_file}:")
                try:
                    sheet_data = zip_ref.read(sheet_file)
                    sheet_root = ET.fromstring(sheet_data)

                    # Count rows
                    ns_sheet = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                    rows = sheet_root.findall('.//main:row', ns_sheet)
                    cells = sheet_root.findall('.//main:c', ns_sheet)

                    print(f"    Rows: {len(rows)}")
                    print(f"    Cells: {len(cells)}")

                    # Show first row cell references
                    if rows:
                        first_row = rows[0]
                        first_row_cells = first_row.findall('.//main:c', ns_sheet)
                        refs = [cell.get('r') for cell in first_row_cells[:20]]
                        print(f"    First row cells: {', '.join(refs)}")

                except Exception as e:
                    print(f"    Error: {e}")

    except FileNotFoundError:
        print(f"Error: File not found: {excel_path}")
        sys.exit(1)
    except zipfile.BadZipFile:
        print(f"Error: Not a valid Excel file: {excel_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    analyze_excel_structure('population_francaise.xlsx')
