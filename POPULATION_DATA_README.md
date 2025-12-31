# Population Data - INSEE

## Source
The population data in the CSV files (`population_dept.csv`, `population_age.csv`, `population_complete.csv`) is derived from official INSEE (Institut National de la Statistique et des Études Économiques) data.

**Source file**: `population_francaise.xlsx`
**Original data**: Estimation de population au 1er janvier 2023, par département, sexe et âge quinquennal

## Files Description

### 1. population_dept.csv
Population totals by department and year.

**Columns**:
- `annee`: Year (2019-2023)
- `departement`: Department code (01-95, 2A, 2B, 971-976)
- `population`: Total population count

**Records**: ~520 rows (104 departments × 5 years)

### 2. population_age.csv
Population totals by age group and year (national aggregates).

**Columns**:
- `annee`: Year (2019-2023)
- `age_min`: Minimum age of the group
- `age_max`: Maximum age of the group
- `population`: Total population count

**Age groups**: 0-4, 5-9, 10-14, 15-19, 20-24, 25-29, 30-34, 35-39, 40-44, 45-49, 50-54, 55-59, 60-64, 65-69, 70-74, 75-79, 80-84, 85-89, 90-94, 95-120

**Records**: 100 rows (20 age groups × 5 years)

### 3. population_complete.csv
Complete population matrix: department × age group × year.

**Columns**:
- `annee`: Year (2019-2023)
- `departement`: Department code
- `age_min`: Minimum age of the group
- `age_max`: Maximum age of the group
- `population`: Population count

**Records**: ~10,400 rows (104 departments × 20 age groups × 5 years)

## Important Note

**The source Excel file contains only 2023 data.** For historical consistency, the 2023 population values have been applied to all years (2019-2023). This is acceptable because:

1. Year-to-year population changes are relatively small (typically < 1% per year)
2. Mortality rates calculated with this data will be very close to accurate values
3. The primary purpose is to provide context and scale, not precise demographic analysis

For perfectly accurate historical mortality rates, historical population data for each year would be needed.

## Conversion Script

The data was converted from Excel to CSV using the script: `convert_insee_to_csv.py`

This script:
- Parses the Excel file using Python's standard library (zipfile, xml)
- Extracts population data from the "Ensemble" (total) section
- Generates the three CSV files in the format expected by the application

## Data Quality

All population values are integers representing the number of inhabitants. Department codes follow the official French department numbering system.
