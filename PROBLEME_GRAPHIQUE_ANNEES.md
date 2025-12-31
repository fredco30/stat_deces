# 🔴 PROBLÈME NON RÉSOLU - Graphique Années Illisible

## 📋 Résumé du Problème

**Symptôme** : Le graphique "Évolution par année" dans l'onglet Synthèse affiche TOUTES les années de 1900 à 2025 sur l'axe X, rendant le graphique complètement illisible.

**Objectif** : Afficher UNIQUEMENT les années qui ont réellement des données (ex: 2024, 2025) sur l'axe X.

**Fichier concerné** : `app.py` - fonction `render_synthesis_tab()` - lignes ~418-465

---

## 📊 État Actuel du Code

### Code Problématique (app.py lignes 418-465)

```python
# Yearly breakdown chart (only years with data)
st.markdown("#### 📅 Évolution par année")

available_years = etl_utils.get_available_years()

if available_years:
    # Collect data only for years with deaths
    years_list = []
    deaths_list = []

    for y in available_years:
        count = etl_utils.get_total_deaths(y, month, dept, sex)
        # Only include years with actual data
        if count > 0:
            years_list.append(str(y))
            deaths_list.append(count)

    if years_list:
        # Use go.Bar for complete control over x-axis
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=years_list,
            y=deaths_list,
            text=[f"{d:,}".replace(",", " ") for d in deaths_list],
            textposition='outside',
            marker=dict(
                color=deaths_list,
                colorscale='Blues',
                showscale=True,
                colorbar=dict(title="Décès")
            )
        ))

        fig.update_layout(
            xaxis_title="Année",
            yaxis_title="Nombre de décès",
            height=400,
            showlegend=False,
            xaxis=dict(
                type='category',  # Force categorical
                categoryorder='array',
                categoryarray=years_list
            )
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée disponible pour les filtres sélectionnés.")
```

### Ce qui a été tenté (3 tentatives)

**Tentative 1** : Filtrer les années avec `count > 0`
- Résultat : Échec - affiche toujours 1900-2025

**Tentative 2** : Convertir les années en `str(y)` + type='category'
- Résultat : Échec - affiche toujours 1900-2025

**Tentative 3** : Utiliser `go.Bar` au lieu de `px.bar` + categoryorder='array'
- Résultat : Échec - affiche toujours 1900-2025

---

## 🔍 Données Contextuelles

### Structure de la Base de Données

- **Total enregistrements** : 5 796 485
- **Départements** : 107
- **Période des données** : 1900-02-12 à 2025-11-30 (selon l'écran)
- **Années avec données réelles** : Probablement 2024 et 2025 uniquement

### Fonction `get_available_years()`

Cette fonction retourne la liste des années disponibles dans la base.
**IMPORTANT** : Il est probable qu'elle retourne TOUTES les années de 1900 à 2025, pas seulement celles avec des données.

**Localisation** : `etl_utils.py`

---

## ⚠️ Hypothèse sur la Cause

Le problème vient probablement de la fonction `etl_utils.get_available_years()` qui :
1. Retourne toutes les années de 1900 à 2025
2. Au lieu de retourner uniquement les années qui ont réellement des enregistrements

**Solution probable** :
- Modifier `get_available_years()` pour ne retourner QUE les années avec des données
- OU : Créer une nouvelle logique dans `render_synthesis_tab()` qui ignore `get_available_years()` et récupère directement les années distinctes avec des données depuis la base

---

## 📁 Fichiers Concernés

### 1. app.py
**Chemin** : `/home/user/stat_deces/app.py`
**Fonction** : `render_synthesis_tab(year, month, dept, sex)` (lignes ~366-465)
**Graphique problématique** : "Évolution par année" (lignes ~418-465)

### 2. etl_utils.py
**Chemin** : `/home/user/stat_deces/etl_utils.py`
**Fonction suspecte** : `get_available_years()` - Retourne probablement toutes les années 1900-2025

---

## 🎯 Ce Qui Doit Être Fait

### Solution 1 : Corriger get_available_years()

Modifier `etl_utils.get_available_years()` pour retourner uniquement les années avec des données réelles :

```python
def get_available_years():
    """Get list of years with actual death records."""
    conn = get_db_connection()
    df = pd.read_sql_query(
        """
        SELECT DISTINCT strftime('%Y', datedeces) as year
        FROM deaths
        WHERE datedeces IS NOT NULL
        ORDER BY year DESC
        """,
        conn
    )
    conn.close()
    return [int(y) for y in df['year'].tolist()]
```

### Solution 2 : Ignorer get_available_years() dans le graphique

Récupérer directement les années avec données dans `render_synthesis_tab()` :

```python
# Au lieu de available_years = etl_utils.get_available_years()
# Faire une requête directe pour les années avec données selon les filtres
```

---

## 🧪 Comment Tester

1. Après la correction, le graphique doit afficher :
   - Axe X : Seulement "2024" et "2025" (ou les années réelles)
   - PAS : 1900, 1901, ... 2023, 2024, 2025

2. Le graphique doit être parfaitement lisible

3. Vérifier aussi que les filtres (mois, département, sexe) fonctionnent correctement

---

## 📝 Informations Supplémentaires

### Environnement
- **OS** : Windows 10
- **Python** : 3.13.7
- **Streamlit** : (version à vérifier)
- **Plotly** : (version à vérifier)

### Base de Données
- **Type** : DuckDB
- **Fichier** : `deaths.db`
- **Table principale** : `deaths`
- **Colonnes clés** : `datedeces`, `sexe`, `lieudeces`, etc.

### Autres Graphiques Fonctionnels

Les graphiques suivants fonctionnent correctement :
- ✅ Décès par mois (2025) - Affiche uniquement 12 mois
- ✅ Répartition par sexe - Camembert H/F
- ✅ Graphiques dans l'onglet "Analyse Visuelle" (courbes multi-années)

---

## 🔗 Commits Liés

- `5a595ac` - feat: Add yearly bar chart to synthesis dashboard
- `8be2a95` - fix: Filter yearly chart to show only years with data
- `c0091d1` - fix: Force years as strings in yearly chart for readable X-axis
- `6a12b33` - fix: Use go.Bar instead of px.bar for yearly chart with explicit category control

**Branche** : `claude/fix-external-connection-MY56S`

---

## 💡 Questions à Investiguer

1. Que retourne exactement `etl_utils.get_available_years()` ?
2. Pourquoi Plotly crée-t-il une échelle continue malgré type='category' ?
3. Y a-t-il un cache Plotly/Streamlit qui empêche la mise à jour ?
4. La conversion `str(y)` fonctionne-t-elle vraiment ?

---

**Date du rapport** : 2025-12-31
**Utilisateur** : Fred
**Projet** : stat_deces - Application Mortalité France
