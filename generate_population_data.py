"""
Script to generate population data for France
Based on INSEE public statistics
"""

import csv

# ============================================================================
# POPULATION DATA BY DEPARTMENT AND YEAR
# ============================================================================

# Population totale par département (données approximatives basées sur INSEE 2024)
dept_populations_2024 = {
    '01': 664000, '02': 529000, '03': 334000, '04': 165000, '05': 142000,
    '06': 1108000, '07': 331000, '08': 270000, '09': 153000, '10': 311000,
    '11': 377000, '12': 279000, '13': 2044000, '14': 694000, '15': 143000,
    '16': 350000, '17': 652000, '18': 301000, '19': 238000, '21': 534000,
    '22': 612000, '23': 115000, '24': 412000, '25': 592000, '26': 517000,
    '27': 611000, '28': 430000, '29': 927000, '2A': 163000, '2B': 184000,
    '30': 747000, '31': 1413000, '32': 191000, '33': 1652000, '34': 1204000,
    '35': 1091000, '36': 218000, '37': 613000, '38': 1270000, '39': 259000,
    '40': 416000, '41': 328000, '42': 770000, '43': 227000, '44': 1444000,
    '45': 687000, '46': 172000, '47': 333000, '48': 76000, '49': 818000,
    '50': 495000, '51': 565000, '52': 172000, '53': 305000, '54': 731000,
    '55': 180000, '56': 763000, '57': 1040000, '58': 201000, '59': 2604000,
    '60': 829000, '61': 277000, '62': 1465000, '63': 663000, '64': 684000,
    '65': 227000, '66': 479000, '67': 1149000, '68': 764000, '69': 1920000,
    '70': 236000, '71': 553000, '72': 567000, '73': 440000, '74': 831000,
    '75': 2145000, '76': 1254000, '77': 1424000, '78': 1444000, '79': 374000,
    '80': 571000, '81': 389000, '82': 262000, '83': 1089000, '84': 563000,
    '85': 685000, '86': 439000, '87': 374000, '88': 363000, '89': 333000,
    '90': 139000, '91': 1335000, '92': 1629000, '93': 1650000, '94': 1403000,
    '95': 1257000, '971': 384000, '972': 362000, '973': 295000, '974': 863000,
    '976': 310000
}

# Générer les données pour les années 2020-2024
years = [2020, 2021, 2022, 2023, 2024]
dept_data = []

for year in years:
    for dept, pop_2024 in dept_populations_2024.items():
        # Ajustement léger de la population pour les années précédentes
        # Croissance moyenne de 0.3% par an
        growth_factor = (year - 2024) * 0.003
        population = int(pop_2024 * (1 + growth_factor))

        dept_data.append({
            'annee': year,
            'departement': dept,
            'population': population
        })

# Écrire le fichier CSV
with open('population_dept.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['annee', 'departement', 'population'])
    writer.writeheader()
    writer.writerows(dept_data)
print(f"✅ Créé population_dept.csv avec {len(dept_data)} lignes")

# ============================================================================
# POPULATION DATA BY AGE AND YEAR
# ============================================================================

# Pyramide des âges française (pourcentages approximatifs de la population totale)
# Basé sur les statistiques INSEE
age_distribution = {
    0: 0.58, 5: 0.58, 10: 0.59, 15: 0.58, 20: 0.56,
    25: 0.56, 30: 0.59, 35: 0.62, 40: 0.64, 45: 0.66,
    50: 0.68, 55: 0.67, 60: 0.61, 65: 0.58, 70: 0.54,
    75: 0.46, 80: 0.36, 85: 0.26, 90: 0.16, 95: 0.06
}

# Population totale France par année (en millions)
france_pop = {
    2020: 67.39,
    2021: 67.59,
    2022: 67.84,
    2023: 68.04,
    2024: 68.17
}

age_data = []

for year in years:
    total_pop = france_pop[year] * 1_000_000  # Convertir en nombre d'habitants

    for age_min, pct in age_distribution.items():
        age_max = age_min + 4
        # Population pour cette tranche d'âge (5 ans)
        population = int(total_pop * pct / 100)

        age_data.append({
            'annee': year,
            'age_min': age_min,
            'age_max': age_max,
            'population': population
        })

# Écrire le fichier CSV
with open('population_age.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['annee', 'age_min', 'age_max', 'population'])
    writer.writeheader()
    writer.writerows(age_data)
print(f"✅ Créé population_age.csv avec {len(age_data)} lignes")

# ============================================================================
# COMBINED FILE (pour référence complète)
# ============================================================================

# Créer un fichier combiné département x âge x année (optionnel)
combined_data = []

for year in years:
    total_france = france_pop[year] * 1_000_000

    for dept, pop_2024 in dept_populations_2024.items():
        growth_factor = (year - 2024) * 0.003
        dept_pop = int(pop_2024 * (1 + growth_factor))
        dept_pct = dept_pop / total_france

        for age_min, age_pct in age_distribution.items():
            age_max = age_min + 4
            # Population département x tranche d'âge
            population = int(total_france * age_pct / 100 * dept_pct)

            combined_data.append({
                'annee': year,
                'departement': dept,
                'age_min': age_min,
                'age_max': age_max,
                'population': population
            })

# Écrire le fichier CSV combiné
with open('population_complete.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['annee', 'departement', 'age_min', 'age_max', 'population'])
    writer.writeheader()
    writer.writerows(combined_data)
print(f"✅ Créé population_complete.csv avec {len(combined_data)} lignes")

print("\n📊 Résumé des fichiers créés:")
print(f"  - population_dept.csv: {len(dept_data)} lignes (dept x année)")
print(f"  - population_age.csv: {len(age_data)} lignes (âge x année)")
print(f"  - population_complete.csv: {len(combined_data)} lignes (dept x âge x année)")
