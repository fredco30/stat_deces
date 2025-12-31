"""
Script de diagnostic pour vérifier le chargement des données de population.
"""

from pathlib import Path
import sys

# Chemins des fichiers
POPULATION_DEPT_PATH = Path(__file__).parent / "population_dept.csv"
POPULATION_AGE_PATH = Path(__file__).parent / "population_age.csv"
POPULATION_COMPLETE_PATH = Path(__file__).parent / "population_complete.csv"

print("=== Diagnostic des fichiers de population ===\n")

# Vérification de l'existence des fichiers
print("1. Vérification de l'existence des fichiers:")
print(f"   population_dept.csv: {POPULATION_DEPT_PATH.exists()} - {POPULATION_DEPT_PATH}")
print(f"   population_age.csv: {POPULATION_AGE_PATH.exists()} - {POPULATION_AGE_PATH}")
print(f"   population_complete.csv: {POPULATION_COMPLETE_PATH.exists()} - {POPULATION_COMPLETE_PATH}")

# Test de chargement avec pandas
print("\n2. Test de chargement avec pandas:")
try:
    import pandas as pd

    print("   Chargement de population_dept.csv...")
    df_dept = pd.read_csv(POPULATION_DEPT_PATH)
    print(f"   ✓ Chargé: {len(df_dept)} lignes, colonnes: {list(df_dept.columns)}")
    print(f"   Années: {sorted(df_dept['annee'].unique())}")
    print(f"   Départements: {len(df_dept['departement'].unique())} uniques")

    print("\n   Chargement de population_age.csv...")
    df_age = pd.read_csv(POPULATION_AGE_PATH)
    print(f"   ✓ Chargé: {len(df_age)} lignes, colonnes: {list(df_age.columns)}")
    print(f"   Années: {sorted(df_age['annee'].unique())}")

    print("\n   Chargement de population_complete.csv...")
    df_complete = pd.read_csv(POPULATION_COMPLETE_PATH)
    print(f"   ✓ Chargé: {len(df_complete)} lignes, colonnes: {list(df_complete.columns)}")

    print("\n3. Test de recherche de données pour 2025:")
    # Vérifier si 2025 existe dans les données
    dept_2025 = df_dept[df_dept['annee'] == 2025]
    age_2025 = df_age[df_age['annee'] == 2025]

    print(f"   Départements avec données 2025: {len(dept_2025)}")
    print(f"   Groupes d'âge avec données 2025: {len(age_2025)}")

    if len(dept_2025) == 0:
        print("\n   ⚠️ PROBLÈME: Pas de données pour l'année 2025!")
        print(f"   Années disponibles: {sorted(df_dept['annee'].unique())}")

    print("\n4. Test de la fonction get_population_dept:")
    from etl_utils import get_population_dept

    # Test avec 2023 (devrait exister)
    pop_2023 = get_population_dept(2023, '01')
    print(f"   Population dept 01 en 2023: {pop_2023}")

    # Test avec 2025 (ne devrait pas exister)
    pop_2025 = get_population_dept(2025, '01')
    print(f"   Population dept 01 en 2025: {pop_2025}")

except ImportError as e:
    print(f"   ✗ Erreur d'import: {e}")
except Exception as e:
    print(f"   ✗ Erreur: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Fin du diagnostic ===")
