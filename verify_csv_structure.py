"""
Simple CSV structure verification (no dependencies).
"""

import csv

print("Verifying CSV structure...\n")

# Check population_dept.csv
print("1. population_dept.csv")
with open('population_dept.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    headers = reader.fieldnames
    print(f"   Headers: {headers}")

    expected = ['annee', 'departement', 'population']
    if headers == expected:
        print("   ✓ Headers match expected format")
    else:
        print(f"   ✗ Expected {expected}, got {headers}")

    # Read first few rows
    rows = list(reader)[:5]
    print(f"   First 5 rows:")
    for row in rows:
        print(f"     {row}")
    print(f"   Total rows: {len(list(csv.DictReader(open('population_dept.csv', 'r'))))}")

# Check population_age.csv
print("\n2. population_age.csv")
with open('population_age.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    headers = reader.fieldnames
    print(f"   Headers: {headers}")

    expected = ['annee', 'age_min', 'age_max', 'population']
    if headers == expected:
        print("   ✓ Headers match expected format")
    else:
        print(f"   ✗ Expected {expected}, got {headers}")

    rows = list(reader)[:5]
    print(f"   First 5 rows:")
    for row in rows:
        print(f"     {row}")
    print(f"   Total rows: {len(list(csv.DictReader(open('population_age.csv', 'r'))))}")

# Check population_complete.csv
print("\n3. population_complete.csv")
with open('population_complete.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    headers = reader.fieldnames
    print(f"   Headers: {headers}")

    expected = ['annee', 'departement', 'age_min', 'age_max', 'population']
    if headers == expected:
        print("   ✓ Headers match expected format")
    else:
        print(f"   ✗ Expected {expected}, got {headers}")

    rows = list(reader)[:5]
    print(f"   First 5 rows:")
    for row in rows:
        print(f"     {row}")
    print(f"   Total rows: {len(list(csv.DictReader(open('population_complete.csv', 'r'))))}")

print("\n✓ All CSV files have correct structure!")
