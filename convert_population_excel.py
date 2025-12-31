"""
Convert INSEE population Excel file to CSV format for use in the application.
"""

import pandas as pd
import sys

try:
    # Lire le fichier Excel
    print("📊 Lecture du fichier Excel de population INSEE...")
    xlsx = pd.ExcelFile('population_francaise.xlsx')

    print(f"\n📑 Feuilles disponibles : {xlsx.sheet_names}\n")

    # Analyser chaque feuille
    for sheet_name in xlsx.sheet_names:
        print(f"\n🔍 Analyse de la feuille : '{sheet_name}'")
        print("-" * 60)
        df = pd.read_excel(xlsx, sheet_name=sheet_name)
        print(f"Dimensions : {df.shape[0]} lignes × {df.shape[1]} colonnes")
        print(f"\nColonnes : {list(df.columns)[:10]}")
        print(f"\nAperçu des premières lignes :")
        print(df.head())
        print("\n")

    # Demander à l'utilisateur quelle feuille utiliser
    print("\n" + "=" * 60)
    print("Quelle feuille contient les données de population ?")
    print("Les colonnes devraient inclure : année, département/âge, population")

except Exception as e:
    print(f"❌ Erreur : {e}")
    sys.exit(1)
