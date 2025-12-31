"""
French Mortality Data Application - Streamlit Interface
Professional dashboard for analyzing INSEE death records.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime

# Local imports
import etl_utils

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Mortalité France - Tableau de Bord",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* KPI Cards */
    .kpi-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 1.5rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    .kpi-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }

    .kpi-label {
        font-size: 0.9rem;
        opacity: 0.9;
        margin-top: 0.5rem;
    }

    .kpi-delta-positive {
        color: #ff6b6b;
        font-size: 1rem;
    }

    .kpi-delta-negative {
        color: #51cf66;
        font-size: 1rem;
    }

    /* Header styling */
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 1rem;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
        background-color: #f0f2f6;
        border-radius: 8px 8px 0 0;
    }

    .stTabs [aria-selected="true"] {
        background-color: #667eea;
        color: white;
    }

    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8f9fa;
    }

    /* Success/Error messages */
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 1rem;
        color: #155724;
    }

    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 8px;
        padding: 1rem;
        color: #721c24;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ============================================================================
# AUTHENTICATION
# ============================================================================

# Simple password authentication (in production, use proper auth)
APP_PASSWORD = "mortalite2024"


def check_password():
    """Simple password check."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.markdown("## 🔐 Connexion requise")
    st.markdown("Veuillez entrer le mot de passe pour accéder à l'application.")

    password = st.text_input("Mot de passe", type="password", key="password_input")

    if st.button("Se connecter", type="primary"):
        if password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect")

    return False


# ============================================================================
# SIDEBAR FILTERS
# ============================================================================

def render_sidebar():
    """Render sidebar with filters."""
    st.sidebar.markdown("## 🎛️ Filtres")

    # Get available options
    years = etl_utils.get_available_years()
    departments = etl_utils.get_available_departments()

    # Year filter
    selected_year = st.sidebar.selectbox(
        "Année",
        options=[None] + years,
        format_func=lambda x: "Toutes" if x is None else str(x),
        index=1 if years else 0
    )

    # Month filter
    months = {
        None: "Tous",
        1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
        5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
        9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
    }
    selected_month = st.sidebar.selectbox(
        "Mois",
        options=list(months.keys()),
        format_func=lambda x: months[x]
    )

    # Department filter
    selected_dept = st.sidebar.selectbox(
        "Département",
        options=[None] + departments,
        format_func=lambda x: "Tous" if x is None else x
    )

    # Sex filter
    sexes = {None: "Tous", 1: "Hommes", 2: "Femmes"}
    selected_sex = st.sidebar.selectbox(
        "Sexe",
        options=list(sexes.keys()),
        format_func=lambda x: sexes[x]
    )

    st.sidebar.markdown("---")

    # Database stats
    st.sidebar.markdown("### 📈 Statistiques BDD")
    stats = etl_utils.get_database_stats()
    st.sidebar.metric("Total enregistrements", f"{stats['total_records']:,}".replace(",", " "))
    st.sidebar.metric("Départements", stats['departments_count'])

    if stats['date_range'][0] and stats['date_range'][1]:
        st.sidebar.caption(f"Période: {stats['date_range'][0]} à {stats['date_range'][1]}")

    return selected_year, selected_month, selected_dept, selected_sex


# ============================================================================
# IMPORT TAB
# ============================================================================

def render_import_tab():
    """Render the import data tab."""
    st.markdown("### 📥 Import de données INSEE")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        **Instructions:**
        - Uploadez les fichiers CSV des décès de l'INSEE
        - Format attendu: séparateur `;` avec colonnes INSEE standard:
          `nomprenom`, `sexe`, `datenaiss`, `lieunaiss`, `commnaiss`, `paysnaiss`, `datedeces`, `lieudeces`, `actedeces`
        - Les doublons sont automatiquement détectés et ignorés
        """)

        uploaded_files = st.file_uploader(
            "Glissez-déposez vos fichiers CSV ici",
            type=['csv'],
            accept_multiple_files=True,
            help="Fichiers CSV de l'INSEE au format standard"
        )

        if uploaded_files:
            # Afficher les fichiers sélectionnés
            st.info(f"📁 {len(uploaded_files)} fichier(s) sélectionné(s)")

            if st.button("🚀 Lancer l'import", type="primary", use_container_width=True):
                # Conteneur pour la progression
                progress_container = st.container()

                with progress_container:
                    st.markdown("---")
                    st.markdown("### ⏳ Import en cours...")

                    # Barre de progression globale
                    progress_bar = st.progress(0)

                    # Affichage du statut détaillé
                    col_status1, col_status2, col_status3 = st.columns(3)
                    with col_status1:
                        progress_percent = st.empty()
                        progress_percent.metric("Progression", "0%")
                    with col_status2:
                        current_file_display = st.empty()
                        current_file_display.metric("Fichier", "-")
                    with col_status3:
                        rows_counter = st.empty()
                        rows_counter.metric("Lignes traitées", "0")

                    # Texte de statut détaillé
                    status_text = st.empty()
                    status_text.info("🔄 Initialisation...")

                total_added = 0
                total_duplicates = 0
                total_rows_processed = 0
                results = []

                for i, file in enumerate(uploaded_files):
                    file_progress = i / len(uploaded_files)

                    # Mise à jour affichage
                    current_file_display.metric("Fichier", f"{i+1}/{len(uploaded_files)}")
                    status_text.info(f"🔄 Traitement de **{file.name}**...")

                    content = file.read()

                    # Callback pour la progression intra-fichier
                    def update_progress(p, rows=0):
                        nonlocal total_rows_processed
                        overall = (i + p) / len(uploaded_files)
                        progress_bar.progress(overall)
                        percent = int(overall * 100)
                        progress_percent.metric("Progression", f"{percent}%")
                        if rows > 0:
                            total_rows_processed = rows
                            rows_counter.metric("Lignes traitées", f"{total_rows_processed:,}".replace(",", " "))

                    added, dups, message = etl_utils.import_csv_batch(
                        content,
                        file.name,
                        update_progress
                    )

                    total_added += added
                    total_duplicates += dups
                    total_rows_processed += added + dups

                    results.append({
                        'Fichier': file.name,
                        'Lignes ajoutées': added,
                        'Doublons': dups,
                        'Statut': '✅' if 'réussi' in message.lower() else '❌'
                    })

                    # Mise à jour après chaque fichier
                    progress_bar.progress((i + 1) / len(uploaded_files))
                    progress_percent.metric("Progression", f"{int((i + 1) / len(uploaded_files) * 100)}%")
                    rows_counter.metric("Lignes traitées", f"{total_rows_processed:,}".replace(",", " "))

                # Finalisation
                progress_bar.progress(1.0)
                progress_percent.metric("Progression", "100%")
                status_text.empty()

                # Message de succès
                st.markdown("---")
                st.success(f"""
                ### ✅ Import terminé!

                - **{total_added:,}** lignes ajoutées
                - **{total_duplicates:,}** doublons ignorés
                - **{len(uploaded_files)}** fichier(s) traité(s)
                """.replace(",", " "))

                # Tableau des résultats
                st.markdown("#### 📊 Détail par fichier")
                st.dataframe(
                    pd.DataFrame(results),
                    use_container_width=True,
                    hide_index=True
                )

    with col2:
        st.markdown("### 📋 Historique des imports")
        history = etl_utils.get_import_history()
        if not history.empty:
            st.dataframe(
                history,
                use_container_width=True,
                hide_index=True,
                height=300
            )
        else:
            st.info("Aucun import effectué")


# ============================================================================
# SYNTHESIS TAB (KPIs)
# ============================================================================

def render_synthesis_tab(year, month, dept, sex):
    """Render the synthesis dashboard with KPIs."""
    st.markdown("### 📊 Tableau de bord - Synthèse")

    # Check if data exists
    total = etl_utils.get_total_deaths(year, month, dept, sex)

    if total == 0:
        st.warning("Aucune donnée disponible pour les filtres sélectionnés. Veuillez importer des données.")
        return

    # KPIs row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📊 Total Décès",
            value=f"{total:,}".replace(",", " ")
        )

    with col2:
        avg_age = etl_utils.get_average_age(year, month, dept, sex)
        st.metric(
            label="👤 Âge moyen",
            value=f"{avg_age:.1f} ans" if avg_age else "N/A"
        )

    with col3:
        if year:
            evolution = etl_utils.get_yoy_evolution(year, month, dept, sex)
            delta_str = f"{evolution:+.1f}%" if evolution else "N/A"
            st.metric(
                label=f"📈 Évolution vs {year-1}",
                value=delta_str,
                delta=f"{evolution:.1f}%" if evolution else None,
                delta_color="inverse"
            )
        else:
            st.metric(label="📈 Évolution", value="Sélectionnez une année")

    with col4:
        # Deaths by sex
        hommes = etl_utils.get_total_deaths(year, month, dept, 1)
        femmes = etl_utils.get_total_deaths(year, month, dept, 2)
        ratio = (hommes / femmes * 100) if femmes > 0 else 0
        st.metric(
            label="⚖️ Ratio H/F",
            value=f"{ratio:.1f}%"
        )

    st.markdown("---")

    # Monthly breakdown chart
    if year:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Décès par mois")
            monthly_data = []
            for m in range(1, 13):
                count = etl_utils.get_total_deaths(year, m, dept, sex)
                monthly_data.append({'Mois': m, 'Décès': count})

            df_monthly = pd.DataFrame(monthly_data)
            month_names = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
                          'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
            df_monthly['Mois_nom'] = df_monthly['Mois'].apply(lambda x: month_names[x-1])

            fig = px.bar(
                df_monthly,
                x='Mois_nom',
                y='Décès',
                color='Décès',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(
                showlegend=False,
                xaxis_title="",
                yaxis_title="Nombre de décès",
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Répartition par sexe")
            sex_data = pd.DataFrame({
                'Sexe': ['Hommes', 'Femmes'],
                'Décès': [hommes, femmes]
            })

            fig = px.pie(
                sex_data,
                values='Décès',
                names='Sexe',
                color='Sexe',
                color_discrete_map={'Hommes': '#3498db', 'Femmes': '#e74c3c'},
                hole=0.4
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# VISUAL ANALYSIS TAB
# ============================================================================

def render_analysis_tab(year, month, dept, sex):
    """Render visual analysis dashboard."""
    st.markdown("### 📈 Analyse Visuelle")

    # Get available years for comparison
    available_years = etl_utils.get_available_years()

    if not available_years:
        st.warning("Aucune donnée disponible.")
        return

    # Multi-year selector
    st.markdown("#### 🎯 Sélection des années à comparer")

    col1, col2 = st.columns([3, 1])

    with col1:
        # Default selection: current year if available, otherwise the most recent
        default_years = [year] if year and year in available_years else [available_years[0]]

        selected_years = st.multiselect(
            "Choisissez les années à comparer (plusieurs possibles)",
            options=available_years,
            default=default_years,
            help="Sélectionnez une ou plusieurs années pour comparer les évolutions"
        )

    with col2:
        # Quick select buttons
        if st.button("📊 Toutes les années"):
            selected_years = available_years
            st.rerun()

    if not selected_years:
        st.warning("Veuillez sélectionner au moins une année.")
        return

    # Palette de couleurs distinctes pour les courbes
    color_palette = [
        '#e74c3c',  # Rouge vif
        '#3498db',  # Bleu
        '#2ecc71',  # Vert
        '#f39c12',  # Orange
        '#9b59b6',  # Violet
        '#1abc9c',  # Turquoise
        '#e67e22',  # Orange foncé
        '#34495e',  # Gris foncé
        '#16a085',  # Cyan foncé
        '#c0392b',  # Rouge foncé
        '#27ae60',  # Vert foncé
        '#2980b9',  # Bleu foncé
        '#8e44ad',  # Violet foncé
        '#d35400',  # Orange brûlé
        '#c0392b',  # Bordeaux
    ]

    # Graph 1: Daily evolution comparison (Multi-year)
    st.markdown("#### 📉 Évolution journalière comparée")

    fig = go.Figure()

    for idx, selected_year in enumerate(sorted(selected_years, reverse=True)):
        df_year = etl_utils.get_daily_deaths(selected_year, month, dept, sex)

        if not df_year.empty:
            df_year['datedeces'] = pd.to_datetime(df_year['datedeces'])
            df_year['day_of_year'] = df_year['datedeces'].dt.dayofyear

            # Utiliser une couleur de la palette
            color = color_palette[idx % len(color_palette)]

            # L'année la plus récente est en trait plein et plus épais
            is_most_recent = (selected_year == max(selected_years))
            line_style = dict(
                color=color,
                width=5 if is_most_recent else 4,
                dash='solid' if is_most_recent else 'solid'
            )

            fig.add_trace(go.Scatter(
                x=df_year['day_of_year'],
                y=df_year['count'],
                mode='lines',
                name=f"{selected_year}" + (" ⭐" if is_most_recent else ""),
                line=line_style,
                hovertemplate='<b>%{fullData.name}</b><br>Jour: %{x}<br>Décès: %{y}<extra></extra>'
            ))

    fig.update_layout(
        xaxis_title="Jour de l'année",
        yaxis_title="Nombre de décès",
        height=500,
        hovermode='x unified',
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="rgba(0, 0, 0, 0.2)",
            borderwidth=1
        ),
        plot_bgcolor='rgba(250, 250, 250, 0.5)',
        font=dict(size=12)
    )

    # Ajouter une grille pour faciliter la lecture
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(200, 200, 200, 0.3)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(200, 200, 200, 0.3)')

    st.plotly_chart(fig, use_container_width=True)

    # Statistiques comparatives
    if len(selected_years) > 1:
        st.markdown("#### 📊 Statistiques comparatives")
        stats_cols = st.columns(len(selected_years))

        for idx, selected_year in enumerate(sorted(selected_years, reverse=True)):
            with stats_cols[idx]:
                total_year = etl_utils.get_total_deaths(selected_year, month, dept, sex)
                avg_age = etl_utils.get_average_age(selected_year, month, dept, sex)

                st.metric(
                    label=f"📅 {selected_year}",
                    value=f"{total_year:,}".replace(",", " "),
                    delta=f"Âge moy: {avg_age:.1f} ans" if avg_age else None
                )

    # Two columns for heatmap and pyramid
    col1, col2 = st.columns(2)

    # Use the most recent selected year for heatmap and pyramid
    display_year = max(selected_years)

    with col1:
        # Graph 2: Calendar Heatmap
        st.markdown(f"#### 🗓️ Heatmap Calendaire ({display_year})")

        df_heatmap = etl_utils.get_deaths_by_month_day(display_year, dept, sex)

        if not df_heatmap.empty:
            # Pivot for heatmap
            pivot = df_heatmap.pivot(index='month', columns='day', values='count').fillna(0)

            month_names = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
                          'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']

            fig = px.imshow(
                pivot,
                labels=dict(x="Jour", y="Mois", color="Décès"),
                x=list(range(1, 32)),
                y=month_names[:len(pivot)],
                color_continuous_scale='YlOrRd',
                aspect='auto'
            )
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Données insuffisantes pour la heatmap")

    with col2:
        # Graph 3: Age Pyramid
        st.markdown(f"#### 👥 Pyramide des âges ({display_year})")

        df_pyramid = etl_utils.get_age_pyramid_data(display_year, month, dept)

        if not df_pyramid.empty:
            # Separate men and women
            df_men = df_pyramid[df_pyramid['sexe'] == 1].copy()
            df_women = df_pyramid[df_pyramid['sexe'] == 2].copy()

            # Create age labels
            df_men['age_label'] = df_men['age_group'].apply(lambda x: f"{int(x)}-{int(x)+4}")
            df_women['age_label'] = df_women['age_group'].apply(lambda x: f"{int(x)}-{int(x)+4}")

            # Men values negative for pyramid effect
            df_men['count_display'] = -df_men['count']

            fig = go.Figure()

            # Men (left side - negative values)
            fig.add_trace(go.Bar(
                y=df_men['age_label'],
                x=df_men['count_display'],
                orientation='h',
                name='Hommes',
                marker_color='#3498db'
            ))

            # Women (right side - positive values)
            fig.add_trace(go.Bar(
                y=df_women['age_label'],
                x=df_women['count'],
                orientation='h',
                name='Femmes',
                marker_color='#e74c3c'
            ))

            max_val = max(df_men['count'].max(), df_women['count'].max()) if not df_men.empty and not df_women.empty else 1000

            fig.update_layout(
                barmode='overlay',
                xaxis=dict(
                    title='Nombre de décès',
                    range=[-max_val * 1.1, max_val * 1.1],
                    tickvals=[-max_val, -max_val/2, 0, max_val/2, max_val],
                    ticktext=[f'{int(max_val)}', f'{int(max_val/2)}', '0', f'{int(max_val/2)}', f'{int(max_val)}']
                ),
                yaxis=dict(title='Tranche d\'âge'),
                height=450,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Données insuffisantes pour la pyramide")


# ============================================================================
# GEOGRAPHY TAB
# ============================================================================

def render_geography_tab(year, month, sex):
    """Render geographic analysis with choropleth map."""
    st.markdown("### 🗺️ Analyse Géographique")

    # Get department data
    df_dept = etl_utils.get_deaths_by_department(year, month, sex)

    if df_dept.empty:
        st.warning("Aucune donnée géographique disponible.")
        return

    # Load GeoJSON
    geojson = etl_utils.get_geojson()

    if geojson is None:
        st.error("Impossible de charger le fichier GeoJSON des départements.")
        return

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("#### Carte choroplèthe des décès par département")

        # Create Plotly choropleth
        fig = px.choropleth(
            df_dept,
            geojson=geojson,
            locations='code',
            featureidkey='properties.code',
            color='count',
            color_continuous_scale='YlOrRd',
            labels={'count': 'Décès', 'code': 'Département'},
            title=''
        )

        fig.update_geos(
            fitbounds="locations",
            visible=False
        )

        fig.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            height=600,
            coloraxis_colorbar=dict(
                title="Nombre de décès",
                thicknessmode="pixels",
                thickness=20,
                lenmode="pixels",
                len=300
            )
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Top 10 Départements")

        # Top departments
        top_depts = df_dept.nlargest(10, 'count')

        fig = px.bar(
            top_depts,
            x='count',
            y='code',
            orientation='h',
            color='count',
            color_continuous_scale='YlOrRd'
        )

        fig.update_layout(
            showlegend=False,
            xaxis_title="Décès",
            yaxis_title="Département",
            height=400,
            yaxis={'categoryorder': 'total ascending'}
        )

        st.plotly_chart(fig, use_container_width=True)

        # Summary stats
        st.markdown("#### Statistiques")
        st.metric("Moyenne par département", f"{df_dept['count'].mean():,.0f}".replace(",", " "))
        st.metric("Médiane", f"{df_dept['count'].median():,.0f}".replace(",", " "))
        st.metric("Écart-type", f"{df_dept['count'].std():,.0f}".replace(",", " "))


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point."""
    # Check authentication
    if not check_password():
        return

    # Render sidebar and get filters
    year, month, dept, sex = render_sidebar()

    # Main header
    st.markdown("# 📊 Mortalité France - Tableau de Bord")
    st.markdown("*Analyse des données de décès INSEE*")

    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📥 Import",
        "📊 Synthèse",
        "📈 Analyse Visuelle",
        "🗺️ Géographie"
    ])

    with tab1:
        render_import_tab()

    with tab2:
        render_synthesis_tab(year, month, dept, sex)

    with tab3:
        render_analysis_tab(year, month, dept, sex)

    with tab4:
        render_geography_tab(year, month, sex)


if __name__ == "__main__":
    main()
