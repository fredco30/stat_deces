# 🔍 Investigation - Fonction get_available_years()

## Code Actuel (etl_utils.py, lignes 429-439)

```python
def get_available_years() -> List[int]:
    """Get list of years with data."""
    conn = get_connection()
    result = conn.execute("""
        SELECT DISTINCT annee_deces
        FROM deces
        WHERE annee_deces IS NOT NULL
        ORDER BY annee_deces DESC
    """).fetchall()
    conn.close()
    return [r[0] for r in result]
```

## Ce Qu'elle Fait

Cette fonction :
1. Se connecte à la base DuckDB
2. Fait une requête `SELECT DISTINCT annee_deces FROM deces`
3. Retourne toutes les années DISTINCTES présentes dans la colonne `annee_deces`

## Le Vrai Problème

**Si la base contient des enregistrements de 1900 à 2025**, cette fonction retourne :
```python
[2025, 2024, 2023, 2022, ..., 1902, 1901, 1900]  # ~125 années !
```

**DONC** : La fonction fait exactement ce qu'elle est censée faire - retourner toutes les années présentes dans la base.

Le problème n'est PAS dans `get_available_years()`, mais dans le fait que :
1. La base contient vraiment des données pour toutes ces années (1900-2025)
2. OU il y a des années "vides" dans la colonne `annee_deces`

## Test à Faire

Pour vérifier combien d'enregistrements il y a par année :

```python
conn = get_connection()
result = conn.execute("""
    SELECT annee_deces, COUNT(*) as count
    FROM deces
    WHERE annee_deces IS NOT NULL
    GROUP BY annee_deces
    ORDER BY annee_deces DESC
""").fetchall()

for year, count in result:
    print(f"{year}: {count:,} décès")
```

**Cela dira** : Y a-t-il vraiment des décès enregistrés pour chaque année de 1900 à 2025 ?

## Solutions Possibles

### Solution 1 : Filtrer dans get_available_years()

Ne retourner que les années avec au moins X enregistrements :

```python
def get_available_years(min_records: int = 1000) -> List[int]:
    """Get list of years with significant data."""
    conn = get_connection()
    result = conn.execute("""
        SELECT annee_deces
        FROM deces
        WHERE annee_deces IS NOT NULL
        GROUP BY annee_deces
        HAVING COUNT(*) >= ?
        ORDER BY annee_deces DESC
    """, [min_records]).fetchall()
    conn.close()
    return [r[0] for r in result]
```

### Solution 2 : Nouvelle fonction pour le graphique

Créer une fonction spécifique qui retourne années + comptages :

```python
def get_years_with_counts(month=None, dept=None, sex=None) -> List[tuple]:
    """Get years with death counts, respecting filters."""
    conn = get_connection()

    query = "SELECT annee_deces, COUNT(*) as count FROM deces WHERE 1=1"
    params = []

    if month:
        query += " AND mois_deces = ?"
        params.append(month)
    if dept:
        query += " AND departement = ?"
        params.append(dept)
    if sex:
        query += " AND sexe = ?"
        params.append(sex)

    query += " GROUP BY annee_deces ORDER BY annee_deces DESC"

    result = conn.execute(query, params).fetchall()
    conn.close()

    return [(r[0], r[1]) for r in result]
```

### Solution 3 : Fix dans render_synthesis_tab()

Au lieu de :
```python
available_years = etl_utils.get_available_years()
for y in available_years:
    count = etl_utils.get_total_deaths(y, month, dept, sex)
    if count > 0:
        ...
```

Faire :
```python
# Récupérer directement les années avec leurs counts
conn = etl_utils.get_connection()
query = "SELECT annee_deces, COUNT(*) FROM deces WHERE 1=1"
params = []

if month:
    query += " AND mois_deces = ?"
    params.append(month)
if dept:
    query += " AND departement = ?"
    params.append(dept)
if sex:
    query += " AND sexe = ?"
    params.append(sex)

query += " GROUP BY annee_deces ORDER BY annee_deces"

result = conn.execute(query, params).fetchall()
conn.close()

years_list = [str(r[0]) for r in result]
deaths_list = [r[1] for r in result]
```

## Recommandation

**Solution 3** est la plus rapide et directe :
- Une seule requête SQL au lieu de N requêtes (une par année)
- Respecte automatiquement les filtres
- Retourne UNIQUEMENT les années avec des données pour les filtres actuels
- Plus performant

---

**À tester dans la nouvelle conversation** : Implémenter Solution 3 et vérifier que ça résout le problème.
