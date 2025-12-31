# 📋 PROMPT POUR NOUVELLE CONVERSATION

Copiez-collez ce prompt dans une nouvelle conversation avec Claude :

---

## Contexte

Je travaille sur une application Streamlit d'analyse de mortalité en France (`stat_deces`). J'ai un problème avec un graphique en barres qui affiche l'évolution des décès par année.

## Le Problème

Dans l'onglet "Synthèse", le graphique "📅 Évolution par année" affiche **TOUTES les années de 1900 à 2025** sur l'axe X, ce qui rend le graphique **complètement illisible**.

**Je veux** : Afficher UNIQUEMENT les années qui ont réellement des données (ex: 2024 et 2025).

**Capture d'écran du problème** : L'axe X montre "1900 1901 1902 ... 2022 2023 2024 2025" avec des centaines d'étiquettes superposées.

## Code Actuel (app.py, lignes ~418-465)

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
        if count > 0:
            years_list.append(str(y))
            deaths_list.append(count)

    if years_list:
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
                type='category',
                categoryorder='array',
                categoryarray=years_list
            )
        )
        st.plotly_chart(fig, use_container_width=True)
```

## Ce Qui a Été Tenté (3 fois, toutes ont échoué)

1. ✗ Filtrer avec `if count > 0` avant d'ajouter à la liste
2. ✗ Convertir les années en strings avec `str(y)`
3. ✗ Utiliser `go.Bar` au lieu de `px.bar` avec `type='category'`

**Aucune de ces solutions n'a fonctionné** - le graphique affiche toujours 1900-2025.

## Hypothèse

Le problème vient probablement de `etl_utils.get_available_years()` qui retourne TOUTES les années de 1900 à 2025, pas seulement celles avec des données.

## Informations Contextuelles

- **Base de données** : DuckDB (`deaths.db`)
- **Table principale** : `deaths`
- **Colonne de date** : `datedeces` (format: YYYYMMDD ou date)
- **Total d'enregistrements** : 5 796 485
- **Période affichée** : 1900-02-12 à 2025-11-30
- **Années avec vraies données** : Probablement seulement 2024 et 2025

## Ce Dont J'ai Besoin

1. **Diagnostiquer** : Vérifier ce que retourne `etl_utils.get_available_years()`
2. **Corriger** : Faire en sorte que le graphique affiche UNIQUEMENT les années avec des données réelles
3. **Solutions possibles** :
   - Modifier `get_available_years()` pour retourner seulement les années avec données
   - OU créer une nouvelle fonction qui récupère les années distinctes directement depuis la base
   - OU ajouter un print/debug pour voir ce qui se passe

## Fichiers Importants

- `app.py` - Fonction `render_synthesis_tab()` (lignes ~418-465)
- `etl_utils.py` - Fonction `get_available_years()` (à vérifier)

## Question Précise

**Peux-tu m'aider à corriger ce graphique pour qu'il affiche UNIQUEMENT les années qui ont réellement des enregistrements dans la base de données ?**

Commence par :
1. Lire `etl_utils.py` pour voir comment `get_available_years()` fonctionne
2. Identifier pourquoi toutes les années 1900-2025 apparaissent
3. Proposer une solution définitive

---

**Fichier de référence complet** : Voir `PROBLEME_GRAPHIQUE_ANNEES.md` pour plus de détails
