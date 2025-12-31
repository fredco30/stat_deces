"""
Quick test to verify population data loads correctly.
"""

import sys
sys.path.insert(0, '.')

from etl_utils import (
    load_population_dept,
    load_population_age,
    load_population_complete,
    get_population_dept,
    calculate_mortality_rate
)

print("Testing population data loading...\n")

# Test 1: Load department data
print("1. Loading department population data...")
df_dept = load_population_dept()
print(f"   Loaded {len(df_dept)} records")
print(f"   Years: {sorted(df_dept['annee'].unique())}")
print(f"   Departments: {len(df_dept['departement'].unique())} unique")
print(f"   Sample:")
print(df_dept.head(10))

# Test 2: Load age data
print("\n2. Loading age population data...")
df_age = load_population_age()
print(f"   Loaded {len(df_age)} records")
print(f"   Years: {sorted(df_age['annee'].unique())}")
print(f"   Age groups: {len(df_age[df_age['annee'] == 2023])} per year")
print(f"   Sample:")
print(df_age.head(10))

# Test 3: Load complete data
print("\n3. Loading complete population data...")
df_complete = load_population_complete()
print(f"   Loaded {len(df_complete)} records")
print(f"   Years: {sorted(df_complete['annee'].unique())}")
print(f"   Sample:")
print(df_complete.head(10))

# Test 4: Get specific population
print("\n4. Testing get_population_dept function...")
pop_01_2023 = get_population_dept(2023, '01')
print(f"   Population of dept 01 in 2023: {pop_01_2023:,}")

pop_75_2023 = get_population_dept(2023, '75')
print(f"   Population of dept 75 (Paris) in 2023: {pop_75_2023:,}")

# Test 5: Calculate mortality rate
print("\n5. Testing mortality rate calculation...")
deaths = 1000
population = 100000
rate = calculate_mortality_rate(deaths, population, per=100000)
print(f"   {deaths:,} deaths / {population:,} population = {rate} per 100k")

deaths = 5000
population = 2000000
rate = calculate_mortality_rate(deaths, population, per=100000)
print(f"   {deaths:,} deaths / {population:,} population = {rate} per 100k")

print("\n✓ All tests passed! Population data is ready to use.")
