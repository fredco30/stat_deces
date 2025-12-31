"""
Process INSEE population Excel file and convert to CSV format.
Run this script in your venv where pandas and openpyxl are installed.
"""

import pandas as pd
import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def main():
    excel_file = 'population_francaise.xlsx'

    if not os.path.exists(excel_file):
        print(f"[ERREUR] Fichier {excel_file} non trouve !")
        print(f"Repertoire actuel: {os.getcwd()}")
        print(f"Fichiers presents: {os.listdir('.')[:10]}")
        sys.exit(1)

    print("Lecture du fichier Excel de population INSEE...")

    try:
        # Lire toutes les feuilles
        xlsx = pd.ExcelFile(excel_file)

        print(f"\n📑 Feuilles disponibles : {xlsx.sheet_names}\n")

        # Analyser chaque feuille
        all_sheets = {}
        for sheet_name in xlsx.sheet_names:
            print(f"\n{'='*60}")
            print(f"🔍 Feuille : '{sheet_name}'")
            print("="*60)
            df = pd.read_excel(xlsx, sheet_name=sheet_name)
            all_sheets[sheet_name] = df

            print(f"Dimensions : {df.shape[0]} lignes × {df.shape[1]} colonnes")
            print(f"\nColonnes ({len(df.columns)}) :")
            for i, col in enumerate(df.columns):
                print(f"  {i+1}. {col}")

            print(f"\nAperçu des 5 premières lignes :")
            print(df.head())
            print(f"\nTypes de données :")
            print(df.dtypes)
            print("\n")

        # Essayer de détecter automatiquement la structure
        print("\n" + "="*60)
        print("🔎 Tentative de détection automatique de la structure...")
        print("="*60)

        for sheet_name, df in all_sheets.items():
            print(f"\n📄 Analyse de '{sheet_name}':")

            # Chercher des colonnes qui pourraient contenir année, département, âge, population
            cols_lower = [str(c).lower() for c in df.columns]

            has_year = any('ann' in c or 'year' in c for c in cols_lower)
            has_dept = any('dep' in c or 'departement' in c for c in cols_lower)
            has_age = any('age' in c or 'âge' in c for c in cols_lower)
            has_pop = any('pop' in c or 'hab' in c or 'effectif' in c for c in cols_lower)

            print(f"  - Contient année ? {has_year}")
            print(f"  - Contient département ? {has_dept}")
            print(f"  - Contient âge ? {has_age}")
            print(f"  - Contient population ? {has_pop}")

            if has_year and has_dept and has_pop:
                print(f"  ✅ Semble être les données par DÉPARTEMENT")
            elif has_year and has_age and has_pop:
                print(f"  ✅ Semble être les données par ÂGE")
            elif has_dept and has_age and has_pop:
                print(f"  ✅ Semble être les données COMPLÈTES (dept × âge)")

        # Proposer une conversion
        print("\n" + "="*60)
        print("💡 Suggestions de conversion :")
        print("="*60)
        print("\nPour utiliser ce fichier, nous avons besoin de 2 ou 3 fichiers CSV :")
        print("  1. population_dept.csv : annee, departement, population")
        print("  2. population_age.csv : annee, age_min, age_max, population")
        print("  3. (optionnel) population_complete.csv : annee, departement, age_min, age_max, population")

        print("\n📝 Veuillez indiquer :")
        print("  - Quelle(s) feuille(s) utiliser")
        print("  - Quelles colonnes correspondent à quoi")
        print("  - S'il faut faire des transformations")

    except Exception as e:
        print(f"❌ Erreur lors de la lecture : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
